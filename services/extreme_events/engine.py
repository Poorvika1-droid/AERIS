"""Extreme-event objects from blended fields (configurable thresholds)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from aeris_schemas import Variable
from services.blending.engine import default_thresholds, event_probability


@dataclass
class WeatherEvent:
    event_id: str
    event_type: str
    location_id: str
    location_name: str
    latitude: float
    longitude: float
    start_time: datetime
    end_time: datetime
    probability: float
    intensity_range: tuple[float, float]
    confidence: str
    affected_grid_area: float
    primary_model: str
    supporting_models: list[str]
    disagreement: float
    forecast_failure_risk: str
    variable: str
    lead_time_hours: int


def detect_events(
    *,
    location_id: str,
    location_name: str,
    latitude: float,
    longitude: float,
    valid_time: datetime,
    lead_time_hours: int,
    rainfall: float | None,
    temperature: float | None,
    wind: float | None,
    rain_spread: float,
    temp_spread: float,
    wind_spread: float,
    weights: dict[str, float],
    disagreement: float,
    failure_risk: str,
    confidence: str,
    thresholds: dict[str, dict[str, float]] | None = None,
) -> list[WeatherEvent]:
    thr = thresholds or {
        "RAINFALL": default_thresholds(Variable.RAINFALL),
        "TEMPERATURE": default_thresholds(Variable.TEMPERATURE),
        "WIND_SPEED": default_thresholds(Variable.WIND_SPEED),
    }
    ranked = sorted(weights.items(), key=lambda x: -x[1])
    primary = ranked[0][0] if ranked else "unknown"
    support = [m for m, w in ranked[1:] if w >= 0.15]
    events: list[WeatherEvent] = []

    def make(etype: str, var: str, value: float, threshold: float, spread: float) -> WeatherEvent:
        p = event_probability(value, threshold, max(spread, 0.5))
        return WeatherEvent(
            event_id=str(uuid.uuid4()),
            event_type=etype,
            location_id=location_id,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            start_time=valid_time,
            end_time=valid_time + timedelta(hours=max(lead_time_hours, 6)),
            probability=round(p, 3),
            intensity_range=(round(value - spread, 2), round(value + spread, 2)),
            confidence=confidence,
            affected_grid_area=0.25,
            primary_model=primary,
            supporting_models=support,
            disagreement=disagreement,
            forecast_failure_risk=failure_risk,
            variable=var,
            lead_time_hours=lead_time_hours,
        )

    if rainfall is not None and rainfall >= thr["RAINFALL"]["heavy"] * 0.45:
        ev = make("heavy_rainfall", "RAINFALL", rainfall, thr["RAINFALL"]["heavy"], rain_spread)
        if ev.probability >= 0.25:
            events.append(ev)
    if temperature is not None and temperature >= thr["TEMPERATURE"]["heat"] * 0.9:
        ev = make("heatwave", "TEMPERATURE", temperature, thr["TEMPERATURE"]["heat"], temp_spread)
        if ev.probability >= 0.25:
            events.append(ev)
    if wind is not None and wind >= thr["WIND_SPEED"]["high_wind"] * 0.7:
        ev = make("high_wind", "WIND_SPEED", wind, thr["WIND_SPEED"]["high_wind"], wind_spread)
        if ev.probability >= 0.25:
            events.append(ev)
    return events
