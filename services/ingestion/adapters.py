"""Forecast adapters: mock (demo) + extensible real stubs. Secrets never hardcoded."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from aeris_schemas import ForecastModelAdapter, LocationPoint, ModelType, Variable


class BaseForecastAdapter(ABC):
    model_id: str
    model_name: str
    provider: str
    model_type: ModelType
    spatial_resolution: str = "0.5deg-equiv"
    grid_definition: str = "india_station_grid_v1"

    @abstractmethod
    def fetch(
        self,
        locations: list[LocationPoint],
        initialization_time: datetime,
        lead_time_hours: int,
        variable: Variable,
    ) -> ForecastModelAdapter:
        raise NotImplementedError


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _climatology(loc: LocationPoint, valid: datetime, variable: Variable) -> float:
    lat, lon = loc.latitude, loc.longitude
    doy = valid.timetuple().tm_yday
    monsoon = 0.5 + 0.5 * np.sin(2 * np.pi * (doy - 150) / 365)
    if variable == Variable.TEMPERATURE:
        base = 32 - 0.35 * abs(lat - 20) - 4 * monsoon
        return float(base + 3 * np.sin(2 * np.pi * doy / 365))
    if variable == Variable.RAINFALL:
        coast = 1.0 if lon > 82 or lon < 73 or lat < 15 else 0.6
        return float(max(0.0, 18 * monsoon * coast * (0.4 + 0.6 * abs(np.sin(lat / 8)))))
    if variable == Variable.WIND_SPEED:
        return float(3.5 + 2.0 * monsoon + 0.05 * abs(lat - 22))
    if variable == Variable.WIND_DIRECTION:
        return float((220 + 40 * monsoon + lon) % 360)
    if variable == Variable.HUMIDITY:
        return float(np.clip(45 + 40 * monsoon, 10, 98))
    if variable == Variable.PRESSURE:
        return float(1010 - 8 * monsoon - 0.1 * (loc.elevation_m or 0) / 10)
    return 0.0


class MockNWPAdapter(BaseForecastAdapter):
    model_id = "nwp-mock-gfs-like"
    model_name = "Mock NWP (GFS-like)"
    provider = "DEMO"
    model_type = ModelType.NWP

    def fetch(self, locations, initialization_time, lead_time_hours, variable) -> ForecastModelAdapter:
        valid = initialization_time + timedelta(hours=lead_time_hours)
        seed = 101 + lead_time_hours + int(initialization_time.timestamp()) % 10000
        rng = _rng(seed)
        values = []
        for loc in locations:
            clim = _climatology(loc, valid, variable)
            # NWP stronger in NORMAL / large-scale; weaker in convective (injected in skill via error model)
            noise = rng.normal(0, 0.35 if variable != Variable.RAINFALL else 2.2)
            bias = 0.4 if variable == Variable.TEMPERATURE else 0.0
            val = clim + noise + bias
            if variable == Variable.RAINFALL:
                val = max(0.0, val * (1.05 + 0.08 * rng.normal()))
            values.append(float(val))
        return _pack(self, locations, initialization_time, valid, lead_time_hours, variable, values)


class MockAIAdapter(BaseForecastAdapter):
    model_id = "ai-mock-emulator"
    model_name = "Mock AI Weather Emulator"
    provider = "DEMO"
    model_type = ModelType.AI

    def fetch(self, locations, initialization_time, lead_time_hours, variable) -> ForecastModelAdapter:
        valid = initialization_time + timedelta(hours=lead_time_hours)
        seed = 202 + lead_time_hours * 3
        rng = _rng(seed)
        values = []
        lead_pen = min(lead_time_hours / 120.0, 1.0)
        for loc in locations:
            clim = _climatology(loc, valid, variable)
            # AI stronger short-lead / convective-ish via smaller noise at short lead
            noise = rng.normal(0, 0.22 + 0.55 * lead_pen if variable != Variable.RAINFALL else 1.4 + 3 * lead_pen)
            val = clim + noise
            if variable == Variable.RAINFALL:
                val = max(0.0, val * (0.92 + 0.06 * rng.normal()))
            values.append(float(val))
        return _pack(self, locations, initialization_time, valid, lead_time_hours, variable, values)


class MockEnsembleAdapter(BaseForecastAdapter):
    model_id = "ens-mock-mean"
    model_name = "Mock Ensemble Mean"
    provider = "DEMO"
    model_type = ModelType.ENSEMBLE

    def fetch(self, locations, initialization_time, lead_time_hours, variable) -> ForecastModelAdapter:
        valid = initialization_time + timedelta(hours=lead_time_hours)
        seed = 303 + lead_time_hours
        rng = _rng(seed)
        values = []
        for loc in locations:
            clim = _climatology(loc, valid, variable)
            noise = rng.normal(0, 0.28 if variable != Variable.RAINFALL else 1.8)
            val = clim + noise
            if variable == Variable.RAINFALL:
                val = max(0.0, val)
            values.append(float(val))
        return _pack(self, locations, initialization_time, valid, lead_time_hours, variable, values, extra={"members": 21})


class RealNWPAdapter(BaseForecastAdapter):
    """Stub for operational NWP. Configure NWP_BASE_URL / NWP_API_KEY via environment."""

    model_id = "nwp-operational"
    model_name = "Operational NWP"
    provider = "CONFIGURED"
    model_type = ModelType.NWP

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def fetch(self, locations, initialization_time, lead_time_hours, variable) -> ForecastModelAdapter:
        if not self.base_url:
            raise RuntimeError("Operational NWP adapter is not configured (NWP_BASE_URL empty).")
        raise NotImplementedError("Wire HTTP/grib ingest here without changing the blending engine.")


class ObservationAdapter(ABC):
    @abstractmethod
    def fetch_station(self, locations: list[LocationPoint], valid_time: datetime, variable: Variable) -> dict[str, float]:
        raise NotImplementedError


class MockObservationAdapter(ObservationAdapter):
    def fetch_station(self, locations, valid_time, variable) -> dict[str, float]:
        rng = _rng(404 + int(valid_time.timestamp()) % 99991)
        out = {}
        for loc in locations:
            clim = _climatology(loc, valid_time, variable)
            noise = rng.normal(0, 0.15 if variable != Variable.RAINFALL else 1.1)
            val = clim + noise
            if variable == Variable.RAINFALL:
                val = max(0.0, val)
            out[loc.location_id] = float(val)
        return out


class SatelliteAdapter:
    """Future satellite ingest — interface only."""

    def ingest(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("SatelliteAdapter reserved for operational mode.")


class RadarAdapter:
    def ingest(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("RadarAdapter reserved for operational mode.")


def _pack(
    adapter: BaseForecastAdapter,
    locations: list[LocationPoint],
    init: datetime,
    valid: datetime,
    lead: int,
    variable: Variable,
    values: list[float],
    extra: dict[str, Any] | None = None,
) -> ForecastModelAdapter:
    from aeris_schemas import CANONICAL_UNITS

    if init.tzinfo is None:
        init = init.replace(tzinfo=timezone.utc)
    if valid.tzinfo is None:
        valid = valid.replace(tzinfo=timezone.utc)
    return ForecastModelAdapter(
        model_id=adapter.model_id,
        model_name=adapter.model_name,
        provider=adapter.provider,
        model_type=adapter.model_type,
        initialization_time=init,
        valid_time=valid,
        lead_time_hours=lead,
        variable=variable,
        spatial_resolution=adapter.spatial_resolution,
        grid_definition=adapter.grid_definition,
        units=CANONICAL_UNITS[variable],
        forecast_values=values,
        latitudes=[l.latitude for l in locations],
        longitudes=[l.longitude for l in locations],
        location_ids=[l.location_id for l in locations],
        metadata={"demo": True, **(extra or {})},
    )


DEMO_ADAPTERS: dict[str, BaseForecastAdapter] = {
    "nwp-mock-gfs-like": MockNWPAdapter(),
    "ai-mock-emulator": MockAIAdapter(),
    "ens-mock-mean": MockEnsembleAdapter(),
}
