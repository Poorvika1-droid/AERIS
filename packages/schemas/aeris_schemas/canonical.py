"""Canonical meteorological types for AERIS (model-agnostic)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Variable(str, Enum):
    RAINFALL = "RAINFALL"
    TEMPERATURE = "TEMPERATURE"
    WIND_SPEED = "WIND_SPEED"
    WIND_DIRECTION = "WIND_DIRECTION"
    HUMIDITY = "HUMIDITY"
    PRESSURE = "PRESSURE"


CANONICAL_UNITS: dict[Variable, str] = {
    Variable.RAINFALL: "mm",
    Variable.TEMPERATURE: "degC",
    Variable.WIND_SPEED: "m s-1",
    Variable.WIND_DIRECTION: "degree",
    Variable.HUMIDITY: "percent",
    Variable.PRESSURE: "hPa",
}

UNIT_ALIASES: dict[str, dict[str, float]] = {
    "mm": {"mm": 1.0, "cm": 10.0, "in": 25.4, "kg m-2": 1.0},
    "degC": {"degC": 1.0, "C": 1.0, "K": 1.0},  # K handled specially
    "m s-1": {"m s-1": 1.0, "m/s": 1.0, "kt": 0.514444, "km/h": 0.277778, "mph": 0.44704},
    "degree": {"degree": 1.0, "deg": 1.0},
    "percent": {"percent": 1.0, "%": 1.0, "1": 100.0},
    "hPa": {"hPa": 1.0, "Pa": 0.01, "mb": 1.0},
}


class ModelType(str, Enum):
    NWP = "NWP"
    AI = "AI"
    ENSEMBLE = "ENSEMBLE"
    BLENDED = "BLENDED"
    OBSERVATION = "OBSERVATION"


class RegimeClass(str, Enum):
    """Operational regime classes for adaptive model weighting — not official taxonomies."""

    NORMAL = "NORMAL"
    MONSOON = "MONSOON"
    CONVECTIVE_RAIN = "CONVECTIVE_RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"
    HEATWAVE = "HEATWAVE"
    HIGH_WIND = "HIGH_WIND"
    CYCLONIC_INFLUENCE = "CYCLONIC_INFLUENCE"
    DRY_EXTREME = "DRY_EXTREME"
    TRANSITION = "TRANSITION"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class LeadTimeHours(int, Enum):
    H6 = 6
    H12 = 12
    H24 = 24
    H48 = 48
    H72 = 72
    H120 = 120


class WeightingStrategy(str, Enum):
    SKILL_WEIGHTED = "SKILL_WEIGHTED"
    CONTEXTUAL_ML = "CONTEXTUAL_ML"
    BAYESIAN_AVERAGE = "BAYESIAN_AVERAGE"
    OPTIMIZATION = "OPTIMIZATION"
    EVENT_SPECIFIC = "EVENT_SPECIFIC"


class ForecastModelAdapter(BaseModel):
    """Common interface every forecast source must implement as a payload."""

    model_id: str
    model_name: str
    provider: str
    model_type: ModelType
    initialization_time: datetime
    valid_time: datetime
    lead_time_hours: int
    variable: Variable
    spatial_resolution: str
    grid_definition: str
    units: str
    forecast_values: list[float]
    latitudes: list[float]
    longitudes: list[float]
    location_ids: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("lead_time_hours")
    @classmethod
    def lead_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("lead_time_hours must be >= 0")
        return v


class LocationPoint(BaseModel):
    location_id: str
    name: str
    latitude: float
    longitude: float
    region: str
    elevation_m: float | None = None
    admin_level: str = "city"


class HarmonizedField(BaseModel):
    model_id: str
    variable: Variable
    units: str
    valid_time: datetime
    initialization_time: datetime
    lead_time_hours: int
    values: dict[str, float]
    qc_flags: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
