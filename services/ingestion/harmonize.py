"""Harmonization: units, timestamps, QC, spatial alignment, bias-correction hooks."""

from __future__ import annotations

import math
from datetime import timezone

from aeris_schemas import CANONICAL_UNITS, UNIT_ALIASES, ForecastModelAdapter, HarmonizedField, Variable

VALUE_RANGES: dict[Variable, tuple[float, float]] = {
    Variable.RAINFALL: (0.0, 800.0),
    Variable.TEMPERATURE: (-40.0, 55.0),
    Variable.WIND_SPEED: (0.0, 80.0),
    Variable.WIND_DIRECTION: (0.0, 360.0),
    Variable.HUMIDITY: (0.0, 100.0),
    Variable.PRESSURE: (850.0, 1080.0),
}


def convert_units(value: float, from_unit: str, variable: Variable) -> float:
    target = CANONICAL_UNITS[variable]
    if from_unit in (target,):
        return value
    if variable == Variable.TEMPERATURE and from_unit in {"K", "kelvin"}:
        return value - 273.15
    if variable == Variable.TEMPERATURE and from_unit in {"F", "degF"}:
        return (value - 32.0) * 5.0 / 9.0
    table = UNIT_ALIASES.get(target, {})
    factor = table.get(from_unit)
    if factor is None:
        raise ValueError(f"Cannot convert {from_unit} to {target} for {variable}")
    return value * factor


def harmonize(adapter_payload: ForecastModelAdapter, bias_correction: dict[str, float] | None = None) -> HarmonizedField:
    """Align to canonical units/time; QC flags; optional additive bias correction per location."""
    if adapter_payload.initialization_time.tzinfo is None:
        adapter_payload.initialization_time = adapter_payload.initialization_time.replace(tzinfo=timezone.utc)
    if adapter_payload.valid_time.tzinfo is None:
        adapter_payload.valid_time = adapter_payload.valid_time.replace(tzinfo=timezone.utc)

    lo, hi = VALUE_RANGES[adapter_payload.variable]
    values: dict[str, float] = {}
    flags: dict[str, list[str]] = {}
    seen: set[str] = set()
    for loc_id, raw in zip(adapter_payload.location_ids, adapter_payload.forecast_values, strict=True):
        loc_flags: list[str] = []
        if loc_id in seen:
            loc_flags.append("duplicate")
        seen.add(loc_id)
        try:
            v = convert_units(float(raw), adapter_payload.units, adapter_payload.variable)
        except (TypeError, ValueError):
            loc_flags.append("invalid")
            continue
        if math.isnan(v) or math.isinf(v):
            loc_flags.append("nan")
            continue
        if v < lo or v > hi:
            loc_flags.append("range")
        if bias_correction and loc_id in bias_correction:
            v = v - bias_correction[loc_id]
        values[loc_id] = v
        if loc_flags:
            flags[loc_id] = loc_flags

    return HarmonizedField(
        model_id=adapter_payload.model_id,
        variable=adapter_payload.variable,
        units=CANONICAL_UNITS[adapter_payload.variable],
        valid_time=adapter_payload.valid_time,
        initialization_time=adapter_payload.initialization_time,
        lead_time_hours=adapter_payload.lead_time_hours,
        values=values,
        qc_flags=flags,
        metadata=adapter_payload.metadata,
    )


def detect_missing(expected_ids: list[str], values: dict[str, float]) -> list[str]:
    return [i for i in expected_ids if i not in values]
