"""Model health: completeness, delay, anomalies, recent skill degradation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from aeris_schemas import HealthStatus
from aeris_shared.metrics import clamp


@dataclass
class HealthReport:
    model_id: str
    health_score: float
    health_status: HealthStatus
    health_reasons: list[str] = field(default_factory=list)
    recommended_weight_adjustment: float = 1.0


class ModelHealthEngine:
    def evaluate(
        self,
        *,
        model_id: str,
        expected_locations: int,
        received_locations: int,
        initialization_time: datetime,
        now: datetime | None = None,
        expected_delay_hours: float = 6.0,
        value_outlier_rate: float = 0.0,
        recent_mae: float | None = None,
        baseline_mae: float | None = None,
        distribution_shift: float = 0.0,
    ) -> HealthReport:
        now = now or datetime.now(timezone.utc)
        reasons: list[str] = []
        score = 100.0
        adj = 1.0

        if received_locations == 0:
            return HealthReport(model_id, 0.0, HealthStatus.UNAVAILABLE, ["missing forecast"], 0.0)

        completeness = received_locations / max(expected_locations, 1)
        if completeness < 0.95:
            reasons.append(f"incomplete field ({completeness:.0%})")
            score -= (1 - completeness) * 40
            adj *= completeness

        if initialization_time.tzinfo is None:
            initialization_time = initialization_time.replace(tzinfo=timezone.utc)
        delay_h = (now - initialization_time).total_seconds() / 3600.0
        # Delay relative to a typical cycle, not wall-clock from init (demo uses historical init)
        stale = delay_h - expected_delay_hours
        if stale > 24:
            reasons.append("delayed / stale run")
            score -= min(25, stale)
            adj *= 0.85

        if value_outlier_rate > 0.05:
            reasons.append("abnormal value rate")
            score -= 15
            adj *= 0.8

        if distribution_shift > 0.35:
            reasons.append("distribution shift")
            score -= 12
            adj *= 0.9

        if recent_mae is not None and baseline_mae is not None and baseline_mae > 0:
            if recent_mae > 1.35 * baseline_mae:
                reasons.append("recent verification degradation")
                score -= 18
                adj *= 0.75

        score = clamp(score, 0, 100)
        if score >= 80:
            status = HealthStatus.HEALTHY
        elif score >= 60:
            status = HealthStatus.WARNING
        elif score > 0:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNAVAILABLE
            adj = 0.0

        if not reasons:
            reasons.append("nominal completeness and range checks")

        return HealthReport(model_id, round(score, 1), status, reasons, round(clamp(adj, 0, 1.2), 3))


def inject_demo_degradation(model_id: str, valid_time: datetime) -> float:
    """Deterministic occasional degradation for demo (AI on a known day)."""
    if model_id.startswith("nwp") and valid_time.day % 11 == 0:
        return 0.72
    return 1.0
