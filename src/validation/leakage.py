"""Fail-closed leakage firewall for forecast/blending training.

These checks intentionally raise, rather than warn: a caller must not be able
to train after discovering a causal or provenance violation.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


class LeakageDetectedError(RuntimeError):
    """Raised whenever a proposed sample or experiment is not causal."""


@dataclass(frozen=True)
class LeakageFinding:
    check: str
    message: str
    sample: str | None = None


TARGET_TOKENS = ("observed", "observation", "target", "label", "truth", "actual", "mae", "rmse", "bias", "error")


def _timestamp(value: Any, field: str) -> pd.Timestamp:
    if value is None:
        raise LeakageDetectedError(f"LEAKAGE DETECTED: missing required timestamp '{field}'.")
    value = pd.Timestamp(value)
    if value.tzinfo is None:
        value = value.tz_localize("UTC")
    return value


def _value(sample: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    return sample.get(key, default) if isinstance(sample, Mapping) else getattr(sample, key, default)


def validate_no_temporal_leakage(sample: Mapping[str, Any] | Any) -> None:
    """Validate one training/inference sample.

    Expected fields: initialization_time, target_time, feature_information_time
    (or feature_information_times), feature_names, and optional sample_id.
    """
    sample_id = str(_value(sample, "sample_id", "unknown"))
    init = _timestamp(_value(sample, "initialization_time"), "initialization_time")
    target = _timestamp(_value(sample, "target_time"), "target_time")
    information_times = _value(sample, "feature_information_times", None)
    if information_times is None:
        information_times = [_value(sample, "feature_information_time", init)]
    for value in information_times:
        if _timestamp(value, "feature_information_time") > init:
            raise LeakageDetectedError(
                f"LEAKAGE DETECTED: future feature information in sample={sample_id}; "
                f"feature_time={value}, initialization_time={init.isoformat()}"
            )
    if target <= init:
        raise LeakageDetectedError(
            f"LEAKAGE DETECTED: target must be after issuance in sample={sample_id}; "
            f"target_time={target.isoformat()}, initialization_time={init.isoformat()}"
        )
    features = [str(x).lower() for x in (_value(sample, "feature_names", []) or [])]
    prohibited = [name for name in features if any(token in name for token in TARGET_TOKENS)]
    if prohibited:
        raise LeakageDetectedError(
            f"LEAKAGE DETECTED: target-derived feature(s) in sample={sample_id}: {prohibited}"
        )


def validate_model_compatibility(models: Iterable[Mapping[str, Any]], *, valid_time: Any, lead_hours: int, variable: str) -> None:
    """Ensure every blend member describes the requested forecast, not a substitute."""
    requested_valid = _timestamp(valid_time, "valid_time")
    for model in models:
        name = model.get("model", model.get("model_id", "unknown"))
        if str(model.get("variable", "")).lower() != variable.lower():
            raise LeakageDetectedError(f"LEAKAGE DETECTED: {name} has incompatible variable.")
        if int(model.get("lead_hours", model.get("lead_time_hours", -1))) != int(lead_hours):
            raise LeakageDetectedError(f"LEAKAGE DETECTED: {name} has incompatible lead time.")
        if _timestamp(model.get("valid_time"), "valid_time") != requested_valid:
            raise LeakageDetectedError(f"LEAKAGE DETECTED: {name} has incompatible valid time.")


def validate_training_run(samples: pd.DataFrame, *, split_column: str = "split") -> None:
    """Run the non-negotiable experiment-level checks and fail closed."""
    required = {"initialization_time", "target_time", "feature_information_time", split_column}
    missing = required.difference(samples.columns)
    if missing:
        raise LeakageDetectedError(f"LEAKAGE DETECTED: required columns absent: {sorted(missing)}")
    for index, row in samples.iterrows():
        validate_no_temporal_leakage({
            "sample_id": row.get("sample_id", str(index)),
            "initialization_time": row["initialization_time"],
            "target_time": row["target_time"],
            "feature_information_time": row["feature_information_time"],
            "feature_names": [c for c in samples.columns if c not in required],
        })
    split_times = samples.assign(_init=pd.to_datetime(samples["initialization_time"], utc=True)).groupby(split_column) ["_init"].agg(["min", "max"])
    required_splits = {"train", "validation", "test"}
    if not required_splits.issubset(set(split_times.index)):
        raise LeakageDetectedError("LEAKAGE DETECTED: chronological train/validation/test splits are required.")
    if not (split_times.loc["train", "max"] < split_times.loc["validation", "min"] < split_times.loc["test", "min"]):
        raise LeakageDetectedError("LEAKAGE DETECTED: train, validation and test periods overlap or are unordered.")
    key_columns = [c for c in ("model", "initialization_time", "valid_time", "lead_hours", "lead_time_hours", "location_id", "variable", "ensemble_member") if c in samples]
    if key_columns and samples.duplicated(key_columns, keep=False).any():
        raise LeakageDetectedError(f"LEAKAGE DETECTED: duplicate logical samples on {key_columns}.")


def validate_rolling_skill(skill_rows: pd.DataFrame, forecast_time: Any) -> None:
    """Skill used at T must derive solely from verification records before T."""
    cutoff = _timestamp(forecast_time, "forecast_time")
    if "verification_time" not in skill_rows:
        raise LeakageDetectedError("LEAKAGE DETECTED: historical-skill rows need verification_time.")
    times = pd.to_datetime(skill_rows["verification_time"], utc=True)
    if (times >= cutoff).any():
        raise LeakageDetectedError("LEAKAGE DETECTED: historical skill includes current/future verification.")
