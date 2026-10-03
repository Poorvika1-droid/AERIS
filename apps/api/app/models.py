from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ForecastSource(Base):
    __tablename__ = "forecast_sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(64))
    model_type: Mapped[str] = mapped_column(String(32))
    spatial_resolution: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    coverage: Mapped[str] = mapped_column(String(64), default="India (demo grid)")
    variables: Mapped[dict] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    region: Mapped[str] = mapped_column(String(64), index=True)
    elevation_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    admin_level: Mapped[str] = mapped_column(String(32), default="city")

    __table_args__ = (Index("ix_locations_lat_lon", "latitude", "longitude"),)


class ForecastRun(Base):
    __tablename__ = "forecast_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("forecast_sources.id"), index=True)
    initialization_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lead_time_hours: Mapped[int] = mapped_column(Integer)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    valid_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    units: Mapped[str] = mapped_column(String(32))
    data_mode: Mapped[str] = mapped_column(String(32), default="demonstration")


class ForecastValue(Base):
    __tablename__ = "forecast_values"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("forecast_runs.id"), index=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    value: Mapped[float] = mapped_column(Float)
    qc_flags: Mapped[list] = mapped_column(JSON, default=list)


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.id"), index=True)
    valid_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), default="demo-station")
    data_mode: Mapped[str] = mapped_column(String(32), default="demonstration")


class ModelSkill(Base):
    __tablename__ = "model_skill"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    lead_time_bin: Mapped[int] = mapped_column(Integer)
    season: Mapped[str] = mapped_column(String(16))
    regime: Mapped[str] = mapped_column(String(32), index=True)
    window: Mapped[str] = mapped_column(String(16), default="30d")
    mae: Mapped[float] = mapped_column(Float)
    rmse: Mapped[float] = mapped_column(Float)
    bias: Mapped[float] = mapped_column(Float)
    correlation: Mapped[float | None] = mapped_column(Float, nullable=True)
    brier: Mapped[float | None] = mapped_column(Float, nullable=True)
    crps: Mapped[float | None] = mapped_column(Float, nullable=True)
    csi: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ModelHealth(Base):
    __tablename__ = "model_health"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(64), index=True)
    health_score: Mapped[float] = mapped_column(Float)
    health_status: Mapped[str] = mapped_column(String(32))
    health_reasons: Mapped[list] = mapped_column(JSON)
    recommended_weight_adjustment: Mapped[float] = mapped_column(Float)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WeatherRegime(Base):
    __tablename__ = "weather_regimes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[str] = mapped_column(String(64), index=True)
    valid_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    current_regime: Mapped[str] = mapped_column(String(32))
    previous_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[dict] = mapped_column(JSON, default=dict)


class RegimeTransition(Base):
    __tablename__ = "regime_transitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[str] = mapped_column(String(64), index=True)
    valid_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    from_regime: Mapped[str] = mapped_column(String(32))
    to_regime: Mapped[str] = mapped_column(String(32))
    transition_probability: Mapped[float] = mapped_column(Float)
    transition_confidence: Mapped[float] = mapped_column(Float)


class DynamicWeight(Base):
    __tablename__ = "dynamic_weights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[str] = mapped_column(String(64), index=True)
    location_id: Mapped[str] = mapped_column(String(64), index=True)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    lead_time_hours: Mapped[int] = mapped_column(Integer)
    weights: Mapped[dict] = mapped_column(JSON)
    strategy: Mapped[str] = mapped_column(String(32))
    regime: Mapped[str] = mapped_column(String(32))


class TrustWeight(Base):
    __tablename__ = "trust_weights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[str] = mapped_column(String(64), index=True)
    location_id: Mapped[str] = mapped_column(String(64), index=True)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    lead_time_hours: Mapped[int] = mapped_column(Integer)
    model_name: Mapped[str] = mapped_column(String(64), index=True)
    weight: Mapped[float] = mapped_column(Float)
    strategy: Mapped[str] = mapped_column(String(32), default="real_IMD")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BlendedForecast(Base):
    __tablename__ = "blended_forecasts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(64), index=True)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    lead_time_hours: Mapped[int] = mapped_column(Integer, index=True)
    valid_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    initialization_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    value: Mapped[float] = mapped_column(Float)
    units: Mapped[str] = mapped_column(String(32))
    dominant_model: Mapped[str] = mapped_column(String(64))
    data_mode: Mapped[str] = mapped_column(String(32), default="demonstration")


class UncertaintyMetric(Base):
    __tablename__ = "uncertainty_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[str] = mapped_column(String(64), index=True)
    ensemble_spread: Mapped[float] = mapped_column(Float)
    inter_model_spread: Mapped[float] = mapped_column(Float)
    interval_low: Mapped[float] = mapped_column(Float)
    interval_high: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(16))
    uncertainty_score: Mapped[float] = mapped_column(Float)
    disagreement_score: Mapped[float] = mapped_column(Float)
    disagreement_label: Mapped[str] = mapped_column(String(16))
    frs: Mapped[float] = mapped_column(Float)
    frs_label: Mapped[str] = mapped_column(String(32))
    frs_components: Mapped[dict] = mapped_column(JSON)
    failure_risk: Mapped[str] = mapped_column(String(16))
    failure_explanation: Mapped[str] = mapped_column(Text)


class ExtremeEvent(Base):
    __tablename__ = "extreme_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    location_id: Mapped[str] = mapped_column(String(64), index=True)
    location_name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    probability: Mapped[float] = mapped_column(Float)
    intensity_low: Mapped[float] = mapped_column(Float)
    intensity_high: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(16))
    affected_grid_area: Mapped[float] = mapped_column(Float)
    primary_model: Mapped[str] = mapped_column(String(64))
    supporting_models: Mapped[list] = mapped_column(JSON)
    disagreement: Mapped[float] = mapped_column(Float)
    forecast_failure_risk: Mapped[str] = mapped_column(String(16))
    variable: Mapped[str] = mapped_column(String(32))
    lead_time_hours: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class VerificationResult(Base):
    __tablename__ = "verification_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(String(64), index=True)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(64), default="ALL")
    lead_time_hours: Mapped[int] = mapped_column(Integer, default=0)
    regime: Mapped[str] = mapped_column(String(32), default="ALL")
    mae: Mapped[float] = mapped_column(Float)
    rmse: Mapped[float] = mapped_column(Float)
    bias: Mapped[float] = mapped_column(Float)
    crps: Mapped[float | None] = mapped_column(Float, nullable=True)
    brier: Mapped[float | None] = mapped_column(Float, nullable=True)
    csi: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer)
    data_mode: Mapped[str] = mapped_column(String(32), default="demonstration")
    note: Mapped[str] = mapped_column(Text, default="DEMONSTRATION BENCHMARK")


class ForecastExplanation(Base):
    __tablename__ = "forecast_explanations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text)
    reasons: Mapped[dict] = mapped_column(JSON)
    shap_like: Mapped[dict] = mapped_column(JSON, default=dict)


class ForecastProvenance(Base):
    __tablename__ = "forecast_provenance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    input_models: Mapped[list] = mapped_column(JSON)
    timestamps: Mapped[dict] = mapped_column(JSON)
    model_versions: Mapped[dict] = mapped_column(JSON)
    weights: Mapped[dict] = mapped_column(JSON)
    calibration_version: Mapped[str] = mapped_column(String(32), default="bias-v0")
    blending_version: Mapped[str] = mapped_column(String(32), default="blend-v0.1")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_mode: Mapped[str] = mapped_column(String(32), default="demonstration")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    production_mutated: Mapped[bool] = mapped_column(default=False)


class MLModelRecord(Base):
    __tablename__ = "ml_models"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(32))
    stage: Mapped[str] = mapped_column(String(32), default="Staging")
    blending_strategy: Mapped[str] = mapped_column(String(32))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)
    dataset_version: Mapped[str] = mapped_column(String(32))
    feature_version: Mapped[str] = mapped_column(String(32))
    mlflow_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validation_status: Mapped[str] = mapped_column(String(32), default="benchmark-only")


class TrainingRun(Base):
    __tablename__ = "training_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(32), default="real_IMD")
    dataset_version: Mapped[str] = mapped_column(String(128), default="aeris_multimodel_ready")
    artifact_path: Mapped[str] = mapped_column(String(256))
    training_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    init_dates: Mapped[dict] = mapped_column(JSON, default=dict)
    lead_time_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acknowledged: Mapped[bool] = mapped_column(default=False)


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
