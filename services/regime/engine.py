"""Weather regime detection for adaptive weighting (operational classes, not official taxonomies)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from aeris_schemas import RegimeClass
from aeris_shared.metrics import clamp


REGIME_RULES: dict[int, RegimeClass] = {}  # filled after fit; fallback uses physics-inspired rules


@dataclass
class RegimeResult:
    current_regime: RegimeClass
    previous_regime: RegimeClass | None
    transition_probability: float
    transition_confidence: float
    cluster_id: int | None
    features: dict[str, float]


class RegimeDetector:
    """Hybrid: KMeans on standardized anomalies + rule overlay for readable labels."""

    def __init__(self, n_clusters: int = 7, random_state: int = 42) -> None:
        self.n_clusters = n_clusters
        self.random_state = random_state
        self._kmeans: KMeans | None = None
        self._scaler: StandardScaler | None = None
        self._cluster_to_label: dict[int, RegimeClass] = {}

    def fit(self, feature_matrix: np.ndarray) -> None:
        if len(feature_matrix) < self.n_clusters:
            return
        self._scaler = StandardScaler()
        x = self._scaler.fit_transform(feature_matrix)
        self._kmeans = KMeans(n_clusters=self.n_clusters, n_init=10, random_state=self.random_state)
        labels = self._kmeans.fit_predict(x)
        centers = self._scaler.inverse_transform(self._kmeans.cluster_centers_)
        self._cluster_to_label = {i: self._label_center(centers[i]) for i in range(self.n_clusters)}
        _ = labels

    def detect(
        self,
        *,
        temperature: float,
        rainfall: float,
        wind: float,
        pressure: float | None,
        humidity: float | None,
        month: int,
        temp_anomaly: float,
        rain_anomaly: float,
    ) -> tuple[RegimeClass, int | None, dict[str, float]]:
        feats = np.array(
            [
                temperature,
                rainfall,
                wind,
                pressure if pressure is not None else 1010.0,
                humidity if humidity is not None else 60.0,
                month,
                temp_anomaly,
                rain_anomaly,
            ],
            dtype=float,
        )
        rule_label = self._rules(
            temperature=temperature,
            rainfall=rainfall,
            wind=wind,
            month=month,
            temp_anomaly=temp_anomaly,
            rain_anomaly=rain_anomaly,
            pressure=pressure,
        )
        cluster_id = None
        if self._kmeans is not None and self._scaler is not None:
            x = self._scaler.transform(feats.reshape(1, -1))
            cluster_id = int(self._kmeans.predict(x)[0])
            mapped = self._cluster_to_label.get(cluster_id, rule_label)
            # Prefer rules for extremes so labels stay interpretable
            if rule_label in {
                RegimeClass.HEAVY_RAIN,
                RegimeClass.HEATWAVE,
                RegimeClass.HIGH_WIND,
                RegimeClass.CYCLONIC_INFLUENCE,
                RegimeClass.DRY_EXTREME,
            }:
                label = rule_label
            else:
                label = mapped
        else:
            label = rule_label
        return label, cluster_id, {
            "temperature": temperature,
            "rainfall": rainfall,
            "wind": wind,
            "temp_anomaly": temp_anomaly,
            "rain_anomaly": rain_anomaly,
            "month": float(month),
        }

    @staticmethod
    def _label_center(c: np.ndarray) -> RegimeClass:
        temp, rain, wind, _pres, _hum, month, t_an, r_an = c
        return RegimeDetector._rules(
            temperature=float(temp),
            rainfall=float(rain),
            wind=float(wind),
            month=int(np.clip(month, 1, 12)),
            temp_anomaly=float(t_an),
            rain_anomaly=float(r_an),
            pressure=None,
        )

    @staticmethod
    def _rules(
        *,
        temperature: float,
        rainfall: float,
        wind: float,
        month: int,
        temp_anomaly: float,
        rain_anomaly: float,
        pressure: float | None,
    ) -> RegimeClass:
        if rainfall >= 75 or rain_anomaly > 40:
            return RegimeClass.HEAVY_RAIN
        if temperature >= 42 or temp_anomaly > 6:
            return RegimeClass.HEATWAVE
        if wind >= 15:
            return RegimeClass.HIGH_WIND
        if pressure is not None and pressure < 996 and wind >= 10:
            return RegimeClass.CYCLONIC_INFLUENCE
        if month in {6, 7, 8, 9} and rainfall >= 8:
            return RegimeClass.MONSOON
        if rainfall >= 20:
            return RegimeClass.CONVECTIVE_RAIN
        if rainfall < 0.5 and temp_anomaly < -1 and month in {3, 4, 5}:
            return RegimeClass.DRY_EXTREME
        if rainfall < 0.2 and abs(temp_anomaly) < 1.5:
            return RegimeClass.NORMAL
        return RegimeClass.NORMAL


class RegimeTransitionDetector:
    def estimate(
        self,
        previous: RegimeClass | None,
        current: RegimeClass,
        rain_trend: float,
        temp_trend: float,
    ) -> tuple[float, float]:
        if previous is None or previous == current:
            return 0.12 if previous == current else 0.0, 0.7
        mag = clamp(abs(rain_trend) / 20.0 + abs(temp_trend) / 4.0, 0.15, 0.95)
        conf = clamp(0.45 + mag / 2, 0.4, 0.9)
        return mag, conf


def season_from_month(month: int) -> str:
    if month in {12, 1, 2}:
        return "DJF"
    if month in {3, 4, 5}:
        return "MAM"
    if month in {6, 7, 8, 9}:
        return "JJAS"
    return "ON"


def context_features(
    *,
    latitude: float,
    longitude: float,
    region: str,
    elevation_m: float | None,
    valid_time: datetime,
    lead_time_hours: int,
    variable: str,
    regime: RegimeClass,
    transition_probability: float,
    disagreement: float,
    health_mean: float,
) -> dict[str, float | str | int]:
    return {
        "latitude": latitude,
        "longitude": longitude,
        "region": region,
        "elevation_m": elevation_m if elevation_m is not None else 0.0,
        "season": season_from_month(valid_time.month),
        "month": valid_time.month,
        "day_of_year": valid_time.timetuple().tm_yday,
        "lead_time_hours": lead_time_hours,
        "variable": variable,
        "weather_regime": regime.value,
        "regime_transition_probability": transition_probability,
        "model_disagreement": disagreement,
        "model_health_mean": health_mean,
    }
