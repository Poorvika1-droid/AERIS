#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xarray as xr
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
for item in [ROOT, ROOT / "apps" / "api", ROOT / "packages" / "schemas", ROOT / "packages" / "shared"]:
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.db import Base
from app.models import AuditLog, ForecastSource, TrainingRun, VerificationResult

MODEL_NAMES = ["NCMRWF", "ECMWF"]
MODEL_FEATURES = [
    "model_flag",
    "lead_h",
    "forecast_mean_mm",
    "observed_mean_mm",
    "bias_mm",
    "mae_mm",
    "rmse_mm",
    "correlation",
    "month",
    "rain_event_indicator",
    "model_disagreement",
]


def validate_inputs(forecast_path: Path, verification_path: Path, metrics_path: Path) -> tuple[xr.Dataset, xr.Dataset, pd.DataFrame]:
    if not forecast_path.exists():
        raise FileNotFoundError(f"Real forecast file missing: {forecast_path}")
    if not verification_path.exists():
        raise FileNotFoundError(f"IMD verification file missing: {verification_path}")
    if not metrics_path.exists():
        raise FileNotFoundError(f"Metrics CSV missing: {metrics_path}")

    forecast_ds = xr.open_dataset(forecast_path)
    if "precipitation_total_mm" not in forecast_ds:
        raise ValueError("Forecast file missing precipitation_total_mm field.")
    forecast_models = [str(v) for v in np.asarray(forecast_ds["model"].values)]
    if sorted(forecast_models) != sorted(MODEL_NAMES):
        raise ValueError(f"Unexpected forecast models: {forecast_models}")
    if len(forecast_ds["init_time"]) != 7:
        raise ValueError(f"Expected 7 initialization dates, found {len(forecast_ds['init_time'])}.")
    if len(forecast_ds["step"]) != 20:
        raise ValueError(f"Expected 20 forecast lead times, found {len(forecast_ds['step'])}.")

    verification_ds = xr.open_dataset(verification_path)
    if "forecast_24h_mm" not in verification_ds or "imd_daily_rain_mm" not in verification_ds:
        raise ValueError("Verification file missing required precipitation fields.")
    verification_models = [str(v) for v in np.asarray(verification_ds["model"].values)]
    if sorted(verification_models) != sorted(MODEL_NAMES):
        raise ValueError(f"Unexpected verification models: {verification_models}")

    metrics_df = pd.read_csv(metrics_path)
    required = {"model", "init_time", "valid_date", "start_lead_h", "end_lead_h", "forecast_mean_mm", "observed_mean_mm", "bias_mm", "mae_mm", "rmse_mm", "correlation"}
    missing = required.difference(metrics_df.columns)
    if missing:
        raise ValueError(f"Metrics CSV missing required columns: {sorted(missing)}")

    return forecast_ds, verification_ds, metrics_df


def build_training_frame(metrics_df: pd.DataFrame) -> pd.DataFrame:
    df = metrics_df.copy()
    df["init_time"] = pd.to_datetime(df["init_time"])
    df["valid_date"] = pd.to_datetime(df["valid_date"])
    df["lead_h"] = (df["start_lead_h"] + df["end_lead_h"]) / 2.0
    df["month"] = df["init_time"].dt.month
    df["model_flag"] = df["model"].map({"NCMRWF": 0.0, "ECMWF": 1.0})
    df["rain_event_indicator"] = (df["observed_mean_mm"] >= 15.0).astype(float)
    df["reliability"] = 1.0 / (1.0 + df["mae_mm"].fillna(0.0))

    disagreement = (
        df.groupby(["init_time", "valid_date", "start_lead_h", "end_lead_h"], as_index=False)["forecast_mean_mm"]
        .agg(disagreement=lambda s: float(np.abs(s.iloc[0] - s.iloc[1])) if len(s) > 1 else 0.0)
    )
    df = df.merge(disagreement, on=["init_time", "valid_date", "start_lead_h", "end_lead_h"], how="left")
    df["weight_target"] = (
        df.groupby(["init_time", "valid_date", "start_lead_h", "end_lead_h"], group_keys=False)["reliability"]
        .transform(lambda s: s / s.sum())
    )
    df["model_disagreement"] = df["disagreement"].fillna(0.0)
    df["correlation"] = df["correlation"].fillna(0.0)
    df["mae_mm"] = df["mae_mm"].fillna(0.0)
    df["rmse_mm"] = df["rmse_mm"].fillna(0.0)
    df["bias_mm"] = df["bias_mm"].fillna(0.0)
    return df


def train_weight_model(df: pd.DataFrame) -> tuple[RandomForestRegressor, dict]:
    X = df[MODEL_FEATURES].copy().fillna(0.0)
    y = df["reliability"].to_numpy(dtype=float)
    groups = df["init_time"].astype(str).to_numpy()

    model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1, max_depth=8)
    gk = GroupKFold(n_splits=min(3, len(np.unique(groups))))
    fold_scores = []
    fold_predictions = []

    for train_idx, val_idx in gk.split(X, y, groups):
        X_train = X.to_numpy(dtype=float)[train_idx]
        y_train = y[train_idx]
        X_val = X.to_numpy(dtype=float)[val_idx]
        y_val = y[val_idx]
        model.fit(X_train, y_train)
        pred = model.predict(X_val)
        true = y_val
        fold_scores.append({
            "mae": mean_absolute_error(true, pred),
            "rmse": float(np.sqrt(mean_squared_error(true, pred))),
            "r2": r2_score(true, pred),
        })
        fold_predictions.append({"idx": val_idx, "pred": pred})

    final_model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1, max_depth=8)
    final_model.fit(X, y)

    metrics = {
        "cv_mae": float(np.mean([s["mae"] for s in fold_scores])),
        "cv_rmse": float(np.mean([s["rmse"] for s in fold_scores])),
        "cv_r2": float(np.mean([s["r2"] for s in fold_scores])),
        "n_records": int(len(df)),
    }
    return final_model, metrics


def summarize_model_metrics(df: pd.DataFrame) -> dict[str, float]:
    summary = {}
    for model_name in MODEL_NAMES:
        rows = df[df["model"] == model_name]
        if rows.empty:
            continue
        summary[model_name] = {
            "mae_mm": float(rows["mae_mm"].mean()),
            "rmse_mm": float(rows["rmse_mm"].mean()),
            "bias_mm": float(rows["bias_mm"].mean()),
            "forecast_mean_mm": float(rows["forecast_mean_mm"].mean()),
            "observed_mean_mm": float(rows["observed_mean_mm"].mean()),
        }
    return summary


def create_runtime_db(db_url: str, metadata: dict, metrics_summary: dict[str, dict[str, float]]) -> None:
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {}, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.query(VerificationResult).delete()
        db.query(TrainingRun).delete()
        db.query(AuditLog).delete()
        db.query(ForecastSource).delete()
        db.commit()

        for model_name in MODEL_NAMES:
            db.add(
                ForecastSource(
                    id=model_name,
                    model_name=model_name,
                    provider="NCMRWF/ECMWF",
                    model_type="NWP" if model_name == "NCMRWF" else "NWP",
                    spatial_resolution="0.25deg",
                    status="ACTIVE",
                    coverage="India",
                    variables=["precipitation_total_mm"],
                    metadata_json={"real_data": True, "source": "aeris_multimodel_ready.nc"},
                )
            )
        db.commit()

        for model_name in MODEL_NAMES:
            info = metrics_summary.get(model_name, {})
            db.add(
                VerificationResult(
                    model_id=model_name,
                    variable="RAINFALL",
                    region="ALL",
                    lead_time_hours=48,
                    regime="ALL",
                    mae=float(info.get("mae_mm", 0.0)),
                    rmse=float(info.get("rmse_mm", 0.0)),
                    bias=float(info.get("bias_mm", 0.0)),
                    sample_count=max(1, int(info.get("forecast_mean_mm", 1.0) * 1)),
                    data_mode="real_IMD",
                    note="Real IMD June 2020 validation metrics",
                )
            )

        db.add(
            TrainingRun(
                id=f"train-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                model_name="aeris_trust_engine",
                mode="real_IMD",
                dataset_version="aeris_multimodel_ready_v1",
                artifact_path=str(metadata["artifact_path"]),
                training_timestamp=datetime.now(timezone.utc),
                init_dates=metadata["initialization_dates"],
                lead_time_count=int(metadata["lead_time_count"]),
                metrics={"cv_mae": metadata["cv_mae"], "cv_rmse": metadata["cv_rmse"], "cv_r2": metadata["cv_r2"]},
                status="SUCCESS",
            )
        )
        db.add(
            AuditLog(
                event_type="real_training",
                message="Real AERIS trust engine training completed",
                details={"mode": "real_IMD", "artifact_path": metadata["artifact_path"]},
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()


def main() -> int:
    # This historical implementation predates the leakage firewall.  It used
    # verification-derived errors and observations as predictors and a
    # non-chronological GroupKFold evaluation.  Retaining it as an executable
    # "real" trainer would permit contaminated artifacts to be deployed.
    raise RuntimeError(
        "LEAKAGE DETECTED: scripts/train_aeris_real.py is retired. "
        "It contains target-derived features and non-chronological validation. "
        "Run scripts/audit_training_readiness.py and build a causal, contract-validated "
        "dataset before introducing a replacement trainer."
    )
    parser = argparse.ArgumentParser(description="Train the AERIS trust engine on real IMD June 2020 data.")
    parser.add_argument("--forecast", type=Path, required=True, help="Path to aeris_multimodel_ready.nc")
    parser.add_argument("--verification", type=Path, required=True, help="Path to aeris_rainfall_verification_june2020.nc")
    parser.add_argument("--metrics", type=Path, required=True, help="Path to aeris_rainfall_metrics_june2020.csv")
    parser.add_argument("--db", type=str, default=f"sqlite:///{(ROOT / 'data' / 'aeris.db').as_posix()}", help="Database URL")
    parser.add_argument("--mode", type=str, default="real_IMD", help="Training mode")
    args = parser.parse_args()

    t0 = time.perf_counter()
    forecast_ds, verification_ds, metrics_df = validate_inputs(args.forecast, args.verification, args.metrics)
    training_df = build_training_frame(metrics_df)
    if training_df.empty:
        raise ValueError("No valid training rows produced from the real metrics dataset.")

    model, cv_metrics = train_weight_model(training_df)
    artifact_dir = ROOT / "models"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "aeris_trust_engine.joblib"
    metadata_path = artifact_dir / "aeris_trust_engine_metadata.json"

    feature_names = MODEL_FEATURES
    payload = {
        "model": model,
        "feature_names": feature_names,
        "model_names": MODEL_NAMES,
        "mode": args.mode,
        "training_dataset": str(args.forecast),
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "initialization_dates": [str(v) for v in pd.to_datetime(training_df["init_time"]).unique().tolist()],
        "lead_time_count": int(len(np.unique(training_df["lead_h"].astype(int)))),
        "target": "reliability",
        "validation_strategy": "GroupKFold by init_time",
    }
    joblib.dump(payload, artifact_path)

    metrics_summary = summarize_model_metrics(training_df)
    metadata = {
        "model_type": "RandomForestRegressor",
        "training_mode": args.mode,
        "training_dataset": str(args.forecast),
        "features": feature_names,
        "target": "reliability",
        "initialization_dates": payload["initialization_dates"],
        "validation_strategy": "GroupKFold by init_time",
        "training_timestamp": payload["training_timestamp"],
        "metrics": {
            "cv_mae": cv_metrics["cv_mae"],
            "cv_rmse": cv_metrics["cv_rmse"],
            "cv_r2": cv_metrics["cv_r2"],
            "model_summary": metrics_summary,
        },
        "software": {"python": sys.version.split()[0], "scikit_learn": __import__("sklearn").__version__, "joblib": joblib.__version__, "xarray": xr.__version__},
        "artifact_path": str(artifact_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    report_path = ROOT / "data" / "processed" / "aeris_training_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "record_count": int(len(training_df)),
        "model_names": MODEL_NAMES,
        "init_dates": payload["initialization_dates"],
        "lead_times": sorted(int(v) for v in np.unique(training_df["lead_h"]))[:10],
        "feature_list": feature_names,
        "validation_strategy": "GroupKFold by init_time",
        "baseline_metrics": {"equal_weight_mae": 0.5, "equal_weight_rmse": 0.5},
        "trust_engine_metrics": {"cv_mae": cv_metrics["cv_mae"], "cv_rmse": cv_metrics["cv_rmse"], "cv_r2": cv_metrics["cv_r2"]},
        "training_time_seconds": round(time.perf_counter() - t0, 3),
        "artifact_path": str(artifact_path),
        "mode": args.mode,
    }
    report_path.write_text(json.dumps(report, indent=2))

    db_path = Path(args.db.replace("sqlite:///", "", 1))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    create_runtime_db(args.db, {**metadata, "artifact_path": str(artifact_path), "initialization_dates": payload["initialization_dates"], "lead_time_count": payload["lead_time_count"], "cv_mae": cv_metrics["cv_mae"], "cv_rmse": cv_metrics["cv_rmse"], "cv_r2": cv_metrics["cv_r2"]}, metrics_summary)

    print(f"Training artifacts saved to {artifact_path}")
    print(f"Metadata saved to {metadata_path}")
    print(f"Report saved to {report_path}")
    print(f"Database saved to {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
