from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from aeris_schemas import Variable
from app.config import get_settings
from app.db import get_db
from app.models import (
    Alert,
    AuditLog,
    BlendedForecast,
    DynamicWeight,
    ExtremeEvent,
    ForecastExplanation,
    ForecastProvenance,
    ForecastRun,
    ForecastSource,
    ForecastValue,
    Location,
    MLModelRecord,
    ModelHealth,
    ModelSkill,
    Observation,
    PipelineRun,
    RegimeTransition,
    SimulationRun,
    SystemMetric,
    TrainingRun,
    TrustWeight,
    UncertaintyMetric,
    VerificationResult,
    WeatherRegime,
)
from app.pipeline import CURRENT_INIT, learning_step, seed_universe, simulate
from services.ingestion.harmonize import convert_units

log = logging.getLogger("aeris.api")
router = APIRouter()
ws_clients: list[WebSocket] = []


class BlendRequest(BaseModel):
    location_id: str
    variable: str = "RAINFALL"
    lead_time_hours: int = 48
    strategy: str = "CONTEXTUAL_ML"
    smoothing: str = "MEDIUM"


class CounterfactualBody(BaseModel):
    forecast_id: str | None = None
    location_id: str | None = None
    variable: str = "RAINFALL"
    lead_time_hours: int = 48
    remove_models: list[str] = Field(default_factory=list)
    simulate_outage: list[str] = Field(default_factory=list)
    weight_boosts: dict[str, float] = Field(default_factory=dict)
    strategy: str | None = None


class ImportBody(BaseModel):
    format: str
    payload: Any


def data_banner() -> dict[str, str]:
    s = get_settings()
    if s.aeris_data_mode == "real_IMD":
        banner = "Real IMD validation dataset"
        disclaimer = "Prototype for SIH 2026 PS 26081. Uses June 2020 IMD validation data and no synthetic runtime data."
    elif s.aeris_data_mode == "demonstration":
        banner = "Demonstration / Benchmark Data"
        disclaimer = "Prototype for SIH 2026 PS 26081. Not NCMRWF operational skill. Not government-endorsed."
    else:
        banner = "Operational data mode"
        disclaimer = "Prototype for SIH 2026 PS 26081. Real data path active."
    return {"data_mode": s.aeris_data_mode, "banner": banner, "disclaimer": disclaimer}


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    t0 = time.perf_counter()
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
        db.query(Location).count()
    except Exception:
        db_ok = False
    redis_ok = False
    try:
        import redis

        r = redis.from_url(get_settings().redis_url, socket_connect_timeout=0.4)
        redis_ok = bool(r.ping())
    except Exception:
        redis_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "api": "ok",
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "unavailable",
        "mlflow": get_settings().mlflow_tracking_uri,
        "data_mode": get_settings().aeris_data_mode,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        **data_banner(),
    }


@router.get("/meta")
def meta() -> dict:
    return {
        "product": "AERIS",
        "full_name": "Adaptive Ensemble & Regime Intelligence System",
        "subtitle": "Hybrid AI–NWP Multi-Model Forecast Blending for a Safer, Climate-Resilient India",
        "target": "Smart India Hackathon 2026",
        "problem_statement": "26081",
        "organization": "Ministry of Earth Sciences (MoES)",
        "department": "NCMRWF",
        "theme": "Disaster Management",
        "messages": [
            "One forecast is not always enough.",
            "The best model changes with context.",
            "AERIS learns when, where and why each model should be trusted.",
            "Forecast uncertainty is information, not a failure.",
            "Every verified forecast improves future model trust.",
        ],
        **data_banner(),
    }


@router.post("/admin/seed")
def seed(db: Session = Depends(get_db)) -> dict:
    if get_settings().aeris_data_mode == "real_IMD":
        return {
            "ok": False,
            "message": "Demo seeding is disabled in real_IMD mode. The real database and model artifact are preserved.",
            **data_banner(),
        }
    info = seed_universe(db)
    return {"ok": True, **info, **data_banner()}


@router.post("/admin/learn")
def learn(db: Session = Depends(get_db)) -> dict:
    if get_settings().aeris_data_mode == "real_IMD":
        return {
            "status": "blocked",
            "message": "Continuous learning is disabled in real_IMD mode. The real database and model artifact are preserved.",
            "elapsed_s": 0.0,
            **data_banner(),
        }
    return {**learning_step(db), **data_banner()}


@router.get("/models")
def models(db: Session = Depends(get_db)) -> dict:
    rows = db.query(ForecastSource).all()
    return {
        "items": [
            {
                "model_id": r.id,
                "model_name": r.model_name,
                "provider": r.provider,
                "model_type": r.model_type,
                "status": r.status,
                "resolution": r.spatial_resolution,
                "coverage": r.coverage,
                "variables": r.variables,
            }
            for r in rows
        ],
        **data_banner(),
    }


@router.get("/models/{model_id}")
def model_one(model_id: str, db: Session = Depends(get_db)) -> dict:
    r = db.query(ForecastSource).filter(ForecastSource.id == model_id).first()
    if not r:
        raise HTTPException(404, "model not found")
    h = db.query(ModelHealth).filter(ModelHealth.model_id == model_id).order_by(ModelHealth.checked_at.desc()).first()
    skills = db.query(ModelSkill).filter(ModelSkill.model_id == model_id, ModelSkill.region == "ALL").all()
    return {
        "model": {
            "model_id": r.id,
            "model_name": r.model_name,
            "provider": r.provider,
            "type": r.model_type,
            "status": r.status,
            "metadata": r.metadata_json,
        },
        "health": None
        if not h
        else {
            "score": h.health_score,
            "status": h.health_status,
            "reasons": h.health_reasons,
            "weight_adjustment": h.recommended_weight_adjustment,
        },
        "skill": [
            {"variable": s.variable, "lead": s.lead_time_bin, "mae": s.mae, "rmse": s.rmse, "bias": s.bias, "n": s.sample_count}
            for s in skills
        ],
        **data_banner(),
    }


@router.get("/locations")
def locations(db: Session = Depends(get_db), q: str | None = None) -> dict:
    rows = db.query(Location).all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.name.lower() or ql in r.id.lower() or ql in r.region.lower()]
    return {
        "items": [
            {"id": r.id, "name": r.name, "lat": r.latitude, "lon": r.longitude, "region": r.region, "elevation_m": r.elevation_m}
            for r in rows
        ],
        **data_banner(),
    }


def _pack_forecast(bf: BlendedForecast, db: Session) -> dict:
    um = db.query(UncertaintyMetric).filter(UncertaintyMetric.forecast_id == bf.id).first()
    dw = db.query(DynamicWeight).filter(DynamicWeight.forecast_id == bf.id).first()
    ex = db.query(ForecastExplanation).filter(ForecastExplanation.forecast_id == bf.id).first()
    loc = db.query(Location).filter(Location.id == bf.location_id).first()
    members = {}
    for src in db.query(ForecastSource).filter(ForecastSource.model_type != "BLENDED"):
        run = (
            db.query(ForecastRun)
            .filter(
                ForecastRun.model_id == src.id,
                ForecastRun.variable == bf.variable,
                ForecastRun.lead_time_hours == bf.lead_time_hours,
                ForecastRun.valid_time == bf.valid_time,
            )
            .first()
        )
        if not run:
            continue
        fv = db.query(ForecastValue).filter(ForecastValue.run_id == run.id, ForecastValue.location_id == bf.location_id).first()
        if fv:
            members[src.id] = fv.value
    rg = db.query(WeatherRegime).filter(WeatherRegime.location_id == bf.location_id).first()
    return {
        "forecast_id": bf.id,
        "location": {"id": loc.id, "name": loc.name, "lat": loc.latitude, "lon": loc.longitude, "region": loc.region} if loc else None,
        "variable": bf.variable,
        "lead_time_hours": bf.lead_time_hours,
        "valid_time": bf.valid_time.isoformat(),
        "value": bf.value,
        "units": bf.units,
        "dominant_model": bf.dominant_model,
        "members": members,
        "weights": dw.weights if dw else {},
        "strategy": dw.strategy if dw else None,
        "regime": rg.current_regime if rg else None,
        "uncertainty": None
        if not um
        else {
            "spread": um.ensemble_spread,
            "interval": [um.interval_low, um.interval_high],
            "confidence": um.confidence,
            "uncertainty_score": um.uncertainty_score,
            "disagreement": um.disagreement_score,
            "disagreement_label": um.disagreement_label,
            "frs": um.frs,
            "frs_label": um.frs_label,
            "frs_components": um.frs_components,
            "failure_risk": um.failure_risk,
            "failure_explanation": um.failure_explanation,
        },
        "explanation": None if not ex else {"summary": ex.summary, "reasons": ex.reasons, "attribution": ex.shap_like},
        **data_banner(),
    }


@router.get("/forecast")
def forecast(
    db: Session = Depends(get_db),
    location_id: str | None = None,
    variable: str = "RAINFALL",
    lead_time_hours: int = 48,
    model: str = "AERIS",
) -> dict:
    q = db.query(BlendedForecast).filter(BlendedForecast.variable == variable, BlendedForecast.lead_time_hours == lead_time_hours)
    if location_id:
        q = q.filter(BlendedForecast.location_id == location_id)
        bf = q.first()
        if not bf:
            raise HTTPException(404, "forecast not found — seed demo data first")
        packed = _pack_forecast(bf, db)
        packed["requested_model"] = model
        return packed
    items = []
    for bf in q.limit(400).all():
        loc = db.query(Location).filter(Location.id == bf.location_id).first()
        um = db.query(UncertaintyMetric).filter(UncertaintyMetric.forecast_id == bf.id).first()
        dw = db.query(DynamicWeight).filter(DynamicWeight.forecast_id == bf.id).first()
        items.append(
            {
                "forecast_id": bf.id,
                "location_id": bf.location_id,
                "name": loc.name if loc else bf.location_id,
                "lat": loc.latitude if loc else None,
                "lon": loc.longitude if loc else None,
                "region": loc.region if loc else None,
                "value": bf.value,
                "units": bf.units,
                "weights": dw.weights if dw else {},
                "dominant_model": bf.dominant_model,
                "frs": um.frs if um else None,
                "disagreement": um.disagreement_score if um else None,
                "uncertainty_score": um.uncertainty_score if um else None,
                "failure_risk": um.failure_risk if um else None,
                "confidence": um.confidence if um else None,
            }
        )
    return {"items": items, "variable": variable, "lead_time_hours": lead_time_hours, "valid_time": CURRENT_INIT.isoformat(), **data_banner()}


@router.post("/forecast/blend")
def blend(body: BlendRequest, db: Session = Depends(get_db)) -> dict:
    bf = (
        db.query(BlendedForecast)
        .filter(
            BlendedForecast.location_id == body.location_id,
            BlendedForecast.variable == body.variable,
            BlendedForecast.lead_time_hours == body.lead_time_hours,
        )
        .first()
    )
    if not bf:
        raise HTTPException(404, "no blended forecast; run /admin/seed")
    return _pack_forecast(bf, db)


@router.get("/weights")
def weights(
    db: Session = Depends(get_db),
    variable: str = "RAINFALL",
    lead_time_hours: int = 48,
) -> dict:
    rows = db.query(DynamicWeight).filter(DynamicWeight.variable == variable, DynamicWeight.lead_time_hours == lead_time_hours).all()
    items = []
    for r in rows:
        loc = db.query(Location).filter(Location.id == r.location_id).first()
        items.append(
            {
                "location_id": r.location_id,
                "name": loc.name if loc else r.location_id,
                "lat": loc.latitude if loc else None,
                "lon": loc.longitude if loc else None,
                "weights": r.weights,
                "dominant": max(r.weights, key=r.weights.get) if r.weights else None,
                "regime": r.regime,
                "forecast_id": r.forecast_id,
            }
        )
    return {"items": items, **data_banner()}


@router.get("/reliability")
def reliability(db: Session = Depends(get_db), location_id: str | None = None, variable: str = "RAINFALL", lead_time_hours: int = 48) -> dict:
    q = db.query(BlendedForecast).filter(BlendedForecast.variable == variable, BlendedForecast.lead_time_hours == lead_time_hours)
    if location_id:
        q = q.filter(BlendedForecast.location_id == location_id)
    items = []
    for bf in q.limit(400):
        um = db.query(UncertaintyMetric).filter(UncertaintyMetric.forecast_id == bf.id).first()
        if um:
            items.append({"forecast_id": bf.id, "location_id": bf.location_id, "frs": um.frs, "label": um.frs_label, "components": um.frs_components})
    return {"items": items, "note": "FRS is a decision-support summary, not a universal scientific metric.", **data_banner()}


@router.get("/disagreement")
def disagreement(db: Session = Depends(get_db), variable: str = "RAINFALL", lead_time_hours: int = 48) -> dict:
    rows = db.query(BlendedForecast).filter(BlendedForecast.variable == variable, BlendedForecast.lead_time_hours == lead_time_hours).all()
    items = []
    for bf in rows:
        um = db.query(UncertaintyMetric).filter(UncertaintyMetric.forecast_id == bf.id).first()
        loc = db.query(Location).filter(Location.id == bf.location_id).first()
        items.append(
            {
                "location_id": bf.location_id,
                "lat": loc.latitude if loc else None,
                "lon": loc.longitude if loc else None,
                "disagreement": um.disagreement_score if um else None,
                "label": um.disagreement_label if um else None,
            }
        )
    return {"items": items, **data_banner()}


@router.get("/extremes")
def extremes(db: Session = Depends(get_db), event_type: str | None = None) -> dict:
    q = db.query(ExtremeEvent)
    if event_type:
        q = q.filter(ExtremeEvent.event_type == event_type)
    rows = q.order_by(ExtremeEvent.probability.desc()).limit(200).all()
    return {
        "items": [
            {
                "event_id": e.id,
                "event_type": e.event_type,
                "location_id": e.location_id,
                "location_name": e.location_name,
                "lat": e.latitude,
                "lon": e.longitude,
                "probability": e.probability,
                "intensity_range": [e.intensity_low, e.intensity_high],
                "confidence": e.confidence,
                "lead_time_hours": e.lead_time_hours,
                "primary_model": e.primary_model,
                "supporting_models": e.supporting_models,
                "disagreement": e.disagreement,
                "forecast_failure_risk": e.forecast_failure_risk,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
            }
            for e in rows
        ],
        "thresholds_note": "Configurable prototype thresholds — not official IMD/NCMRWF warnings.",
        **data_banner(),
    }


@router.get("/regimes")
def regimes(db: Session = Depends(get_db)) -> dict:
    rows = db.query(WeatherRegime).all()
    trans = db.query(RegimeTransition).all()
    tmap = {t.location_id: t for t in trans}
    items = []
    for r in rows:
        loc = db.query(Location).filter(Location.id == r.location_id).first()
        t = tmap.get(r.location_id)
        items.append(
            {
                "location_id": r.location_id,
                "name": loc.name if loc else r.location_id,
                "lat": loc.latitude if loc else None,
                "lon": loc.longitude if loc else None,
                "current_regime": r.current_regime,
                "previous_regime": r.previous_regime,
                "transition_probability": t.transition_probability if t else 0.1,
                "transition_confidence": t.transition_confidence if t else 0.5,
                "features": r.features,
            }
        )
    return {
        "items": items,
        "note": "Operational regime classes for adaptive model weighting — not official meteorological classifications.",
        **data_banner(),
    }


@router.get("/verification")
def verification(
    db: Session = Depends(get_db),
    variable: str | None = None,
    region: str | None = None,
    lead_time_hours: int | None = None,
) -> dict:
    q = db.query(VerificationResult)
    if variable:
        q = q.filter(VerificationResult.variable == variable)
    rows = q.all()
    return {
        "items": [
            {
                "model_id": r.model_id,
                "variable": r.variable,
                "region": r.region,
                "mae": r.mae,
                "rmse": r.rmse,
                "bias": r.bias,
                "crps": r.crps,
                "brier": r.brier,
                "csi": r.csi,
                "f1": r.f1,
                "precision": r.precision,
                "recall": r.recall,
                "n": r.sample_count,
                "note": r.note,
            }
            for r in rows
        ],
        "label": "DEMONSTRATION BENCHMARK",
        **data_banner(),
    }


@router.get("/model-health")
def model_health(db: Session = Depends(get_db)) -> dict:
    rows = db.query(ModelHealth).all()
    return {
        "items": [
            {
                "model_id": r.model_id,
                "health_score": r.health_score,
                "health_status": r.health_status,
                "reasons": r.health_reasons,
                "weight_adjustment": r.recommended_weight_adjustment,
                "checked_at": r.checked_at.isoformat(),
            }
            for r in rows
        ],
        **data_banner(),
    }


@router.get("/skill")
def skill(db: Session = Depends(get_db), model_id: str | None = None) -> dict:
    q = db.query(ModelSkill)
    if model_id:
        q = q.filter(ModelSkill.model_id == model_id)
    rows = q.limit(2000).all()
    return {
        "items": [
            {
                "model_id": r.model_id,
                "region": r.region,
                "variable": r.variable,
                "lead": r.lead_time_bin,
                "season": r.season,
                "regime": r.regime,
                "window": r.window,
                "mae": r.mae,
                "rmse": r.rmse,
                "bias": r.bias,
                "correlation": r.correlation,
                "csi": r.csi,
                "n": r.sample_count,
            }
            for r in rows
        ],
        **data_banner(),
    }


@router.post("/simulations/counterfactual")
def counterfactual(body: CounterfactualBody, db: Session = Depends(get_db)) -> dict:
    fid = body.forecast_id
    if not fid:
        bf = (
            db.query(BlendedForecast)
            .filter(
                BlendedForecast.location_id == (body.location_id or "IN-DL-DEL"),
                BlendedForecast.variable == body.variable,
                BlendedForecast.lead_time_hours == body.lead_time_hours,
            )
            .first()
        )
        if not bf:
            raise HTTPException(404, "forecast not found")
        fid = bf.id
    result = simulate(
        db,
        fid,
        {
            "remove_models": body.remove_models,
            "simulate_outage": body.simulate_outage,
            "weight_boosts": body.weight_boosts,
            "strategy": body.strategy,
            "lead_time_hours": body.lead_time_hours,
        },
    )
    return {**result, **data_banner()}


@router.get("/provenance/{forecast_id}")
def provenance(forecast_id: str, db: Session = Depends(get_db)) -> dict:
    p = db.query(ForecastProvenance).filter(ForecastProvenance.forecast_id == forecast_id).first()
    if not p:
        raise HTTPException(404, "not found")
    return {
        "forecast_id": p.forecast_id,
        "input_models": p.input_models,
        "timestamps": p.timestamps,
        "model_versions": p.model_versions,
        "weights": p.weights,
        "calibration_version": p.calibration_version,
        "blending_version": p.blending_version,
        "generated_at": p.generated_at.isoformat(),
        "data_mode": p.data_mode,
        **data_banner(),
    }


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    n_models = db.query(ForecastSource).filter(ForecastSource.id != "aeris-blend").count()
    n_loc = db.query(BlendedForecast).filter(BlendedForecast.lead_time_hours == 48, BlendedForecast.variable == "RAINFALL").count()
    ev = db.query(ExtremeEvent).order_by(ExtremeEvent.probability.desc()).first()
    ums = db.query(UncertaintyMetric).all()
    frs = float(sum(u.frs for u in ums) / len(ums)) if ums else 0
    disag = float(sum(u.disagreement_score for u in ums) / len(ums)) if ums else 0
    degraded = db.query(ModelHealth).filter(ModelHealth.health_status != "HEALTHY").count()
    n_obs = db.query(Observation).count()
    last = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    weights_mean = {"nwp": 0.0, "ai": 0.0, "ens": 0.0}
    dws = db.query(DynamicWeight).filter(DynamicWeight.variable == "RAINFALL", DynamicWeight.lead_time_hours == 48).all()
    if dws:
        for k, prefix in [("nwp", "nwp"), ("ai", "ai"), ("ens", "ens")]:
            vals = []
            for d in dws:
                for mk, wv in d.weights.items():
                    if mk.startswith(prefix):
                        vals.append(wv)
            weights_mean[k] = float(sum(vals) / len(vals)) if vals else 0
    return {
        "kpis": {
            "active_models": n_models,
            "blended_locations": n_loc,
            "highest_risk_event": None
            if not ev
            else {"type": ev.event_type, "location": ev.location_name, "probability": ev.probability},
            "forecast_reliability": round(frs, 1),
            "model_disagreement": round(disag, 3),
            "latest_update": last.finished_at.isoformat() if last and last.finished_at else CURRENT_INIT.isoformat(),
            "models_degraded": degraded,
            "observations_processed": n_obs,
        },
        "contribution": weights_mean,
        **data_banner(),
    }


@router.get("/ml/registry")
def registry(db: Session = Depends(get_db)) -> dict:
    rows = db.query(MLModelRecord).all()
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "version": r.version,
                "stage": r.stage,
                "strategy": r.blending_strategy,
                "metrics": r.metrics,
                "hyperparameters": r.hyperparameters,
                "dataset_version": r.dataset_version,
                "feature_version": r.feature_version,
                "mlflow_run_id": r.mlflow_run_id,
                "trained_at": r.trained_at.isoformat(),
                "validation_status": r.validation_status,
            }
            for r in rows
        ],
        **data_banner(),
    }


@router.get("/system")
def system(db: Session = Depends(get_db)) -> dict:
    jobs = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(20).all()
    metrics = db.query(SystemMetric).order_by(SystemMetric.captured_at.desc()).limit(20).all()
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(20).all()
    h = health(db)
    model_path = Path(__file__).resolve().parents[3] / "models" / "aeris_trust_engine.joblib"
    training_run = db.query(TrainingRun).order_by(TrainingRun.training_timestamp.desc()).first()
    model_present = model_path.exists()
    dataset_summary = {
        "forecast_file": "data/processed/aeris_multimodel_ready.nc",
        "verification_file": "data/processed/aeris_rainfall_verification_june2020.nc",
        "metrics_file": "data/processed/aeris_rainfall_metrics_june2020.csv",
        "imd_reference_file": "data/observations/IMD/IMD_rain_2020.nc",
    }
    init_count = db.query(ForecastRun.initialization_time).distinct().count()
    lead_time_count = db.query(ForecastRun.lead_time_hours).distinct().count()
    verification_status = "ok" if db.query(VerificationResult).count() > 0 else "missing"
    return {
        "data_mode": get_settings().aeris_data_mode,
        "database": "connected" if h["database"] == "ok" else "disconnected",
        "trained_model": "available" if model_present else "unavailable",
        "trained_model_path": str(model_path),
        "training_timestamp": training_run.training_timestamp.isoformat() if training_run else None,
        "dataset_summary": dataset_summary,
        "models": [row.id for row in db.query(ForecastSource).all()],
        "initialization_count": init_count,
        "lead_time_count": lead_time_count,
        "verification_status": verification_status,
        "health": h,
        "jobs": [{"id": j.id, "name": j.job_name, "status": j.status, "detail": j.detail, "started": j.started_at.isoformat()} for j in jobs],
        "metrics": [{"name": m.name, "value": m.value} for m in metrics],
        "alerts": [{"level": a.level, "message": a.message, "at": a.created_at.isoformat()} for a in alerts],
        "queue": {"broker": get_settings().celery_broker_url, "note": "Real-data execution path; queue optional"},
        **data_banner(),
    }


@router.get("/data-hub")
def data_hub(db: Session = Depends(get_db)) -> dict:
    sources = db.query(ForecastSource).all()
    items = []
    for s in sources:
        last = db.query(ForecastRun).filter(ForecastRun.model_id == s.id).order_by(ForecastRun.valid_time.desc()).first()
        items.append(
            {
                "id": s.id,
                "name": s.model_name,
                "status": s.status if s.status in {"ACTIVE", "DEGRADED", "OFFLINE"} else ("ACTIVE" if s.status == "HEALTHY" else s.status),
                "latest_update": last.valid_time.isoformat() if last else None,
                "variables": s.variables,
                "resolution": s.spatial_resolution,
                "coverage": s.coverage,
                "quality": "demo-qc",
            }
        )
    n_missing = 0
    return {"items": items, "missing_records_flagged": n_missing, "import_formats": ["CSV", "JSON", "NetCDF"], **data_banner()}


@router.post("/data-hub/import")
def import_data(body: ImportBody) -> dict:
    return {
        "accepted": False,
        "reason": "Prototype import hook only. Operational ingest requires configured adapters and validated grids.",
        "format": body.format,
        **data_banner(),
    }


@router.get("/timeseries")
def timeseries(db: Session = Depends(get_db), location_id: str = "IN-DL-DEL", variable: str = "RAINFALL") -> dict:
    obs = (
        db.query(Observation)
        .filter(Observation.location_id == location_id, Observation.variable == variable)
        .order_by(Observation.valid_time)
        .all()
    )
    series = {"observation": [{"t": o.valid_time.isoformat(), "v": o.value} for o in obs]}
    for src in db.query(ForecastSource).filter(ForecastSource.model_type != "BLENDED"):
        pts = []
        runs = db.query(ForecastRun).filter(ForecastRun.model_id == src.id, ForecastRun.variable == variable, ForecastRun.lead_time_hours == 48).all()
        for run in runs:
            fv = db.query(ForecastValue).filter(ForecastValue.run_id == run.id, ForecastValue.location_id == location_id).first()
            if fv:
                pts.append({"t": run.valid_time.isoformat(), "v": fv.value})
        series[src.id] = sorted(pts, key=lambda x: x["t"])
    blend = (
        db.query(BlendedForecast)
        .filter(BlendedForecast.location_id == location_id, BlendedForecast.variable == variable)
        .order_by(BlendedForecast.valid_time)
        .all()
    )
    series["aeris-blend"] = [{"t": b.valid_time.isoformat(), "v": b.value} for b in blend]
    return {"location_id": location_id, "variable": variable, "series": series, **data_banner()}


@router.get("/skill/heatmap")
def skill_heatmap(db: Session = Depends(get_db), variable: str = "RAINFALL") -> dict:
    """Return MAE matrix: rows = model, cols = lead_time for use in heatmap chart."""
    rows = db.query(ModelSkill).filter(ModelSkill.variable == variable, ModelSkill.region == "ALL").all()
    leads = sorted({r.lead_time_bin for r in rows})
    models = sorted({r.model_id for r in rows})
    grid: dict[str, dict[int, float]] = {m: {} for m in models}
    for r in rows:
        grid[r.model_id][r.lead_time_bin] = r.mae
    return {"models": models, "leads": leads, "grid": grid, **data_banner()}


@router.get("/weights/history")
def weights_history(db: Session = Depends(get_db), location_id: str = "IN-DL-DEL", variable: str = "RAINFALL") -> dict:
    """Return weight series across all lead times for a location (simulates evolution)."""
    rows = db.query(DynamicWeight).filter(DynamicWeight.location_id == location_id, DynamicWeight.variable == variable).order_by(DynamicWeight.lead_time_hours).all()
    series = []
    for r in rows:
        entry: dict = {"lead": r.lead_time_hours, "regime": r.regime}
        for m, w in r.weights.items():
            entry[m.replace("-mock", "").replace("-gfs-like", "").replace("-emulator", "").replace("-mean", "")] = round(w * 100, 1)
        series.append(entry)
    return {"location_id": location_id, "variable": variable, "series": series, **data_banner()}


@router.get("/forecast/skill-lead")
def skill_by_lead(db: Session = Depends(get_db), variable: str = "RAINFALL", region: str = "ALL") -> dict:
    """MAE vs lead-time for each model — for line chart."""
    rows = db.query(ModelSkill).filter(ModelSkill.variable == variable, ModelSkill.region == region).order_by(ModelSkill.lead_time_bin).all()
    by_model: dict[str, list[dict]] = {}
    for r in rows:
        by_model.setdefault(r.model_id, []).append({"lead": r.lead_time_bin, "mae": r.mae, "rmse": r.rmse, "bias": r.bias})
    return {"variable": variable, "region": region, "models": by_model, **data_banner()}


@router.get("/verification/by-lead")
def verification_by_lead(db: Session = Depends(get_db), variable: str = "RAINFALL") -> dict:
    """Per-lead aggregated verification for line chart."""
    rows = db.query(ModelSkill).filter(ModelSkill.variable == variable, ModelSkill.region == "ALL").order_by(ModelSkill.lead_time_bin).all()
    data: dict[str, list] = {}
    for r in rows:
        data.setdefault(r.model_id, []).append({"lead": r.lead_time_bin, "mae": round(r.mae, 3), "rmse": round(r.rmse, 3)})
    return {"variable": variable, "data": data, "label": "DEMONSTRATION BENCHMARK", **data_banner()}


@router.get("/forecast/uncertainty-series")
def uncertainty_series(db: Session = Depends(get_db), location_id: str = "IN-DL-DEL", variable: str = "RAINFALL") -> dict:
    """Uncertainty metrics across all lead times for interval chart."""
    blends = db.query(BlendedForecast).filter(BlendedForecast.location_id == location_id, BlendedForecast.variable == variable).order_by(BlendedForecast.lead_time_hours).all()
    pts = []
    for bf in blends:
        um = db.query(UncertaintyMetric).filter(UncertaintyMetric.forecast_id == bf.id).first()
        if um:
            pts.append({
                "lead": bf.lead_time_hours,
                "value": round(bf.value, 2),
                "low": round(um.interval_low, 2),
                "high": round(um.interval_high, 2),
                "spread": round(um.ensemble_spread, 3),
                "frs": round(um.frs, 1),
                "disagreement": round(um.disagreement_score, 3),
                "confidence": um.confidence,
                "failure_risk": um.failure_risk,
            })
    return {"location_id": location_id, "variable": variable, "points": pts, **data_banner()}


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    ws_clients.append(ws)
    try:
        await ws.send_json({"type": "hello", "message": "AERIS live channel", **data_banner()})
        while True:
            data = await ws.receive_text()
            await ws.send_json({"type": "ack", "echo": data[:200]})
    except WebSocketDisconnect:
        if ws in ws_clients:
            ws_clients.remove(ws)
