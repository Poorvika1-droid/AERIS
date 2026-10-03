"""Adaptive blending, uncertainty, FRS, failure risk, spatial smoothing, counterfactual."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from aeris_schemas import Variable
from aeris_shared.metrics import clamp, gaussian_smooth, normalize_weights

from .trust import DynamicTrustEngine, SkillSnapshot, TrustInput, TrustOutput, blend_value, disagreement_score

SMOOTH_MAP = {"OFF": 0.0, "LOW": 0.15, "MEDIUM": 0.35, "HIGH": 0.6}


@dataclass
class UncertaintyResult:
    ensemble_spread: float
    inter_model_spread: float
    prediction_interval_low: float
    prediction_interval_high: float
    confidence: str
    uncertainty_score: float
    disagreement_score: float
    disagreement_label: str


def uncertainty_from_members(
    blended: float,
    members: dict[str, float],
    historical_mae: float | None = None,
) -> UncertaintyResult:
    vals = [v for v in members.values() if v is not None and not math.isnan(v)]
    if not vals:
        spread = 0.0
    else:
        mu = sum(vals) / len(vals)
        spread = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
    disag = disagreement_score(members)
    sigma = spread if spread > 0 else (historical_mae or 1.0)
    lo = blended - 1.28 * sigma
    hi = blended + 1.28 * sigma
    u_score = clamp(safe_norm(spread, blended), 0, 1)
    conf = "HIGH" if u_score < 0.22 and disag < 0.3 else "MODERATE" if u_score < 0.45 else "LOW"
    dlab = "LOW" if disag < 0.2 else "MODERATE" if disag < 0.45 else "HIGH"
    return UncertaintyResult(
        ensemble_spread=round(spread, 3),
        inter_model_spread=round(spread, 3),
        prediction_interval_low=round(lo, 3),
        prediction_interval_high=round(hi, 3),
        confidence=conf,
        uncertainty_score=round(u_score, 3),
        disagreement_score=round(disag, 3),
        disagreement_label=dlab,
    )


def safe_norm(spread: float, value: float) -> float:
    return spread / max(abs(value), 1.0)


@dataclass
class FRSComponents:
    historical_skill: float
    model_health: float
    inter_model_agreement: float
    regime_certainty: float
    observation_consistency: float
    forecast_stability: float

    def score(self) -> float:
        w = {
            "historical_skill": 0.25,
            "model_health": 0.15,
            "inter_model_agreement": 0.2,
            "regime_certainty": 0.15,
            "observation_consistency": 0.15,
            "forecast_stability": 0.1,
        }
        s = (
            w["historical_skill"] * self.historical_skill
            + w["model_health"] * self.model_health
            + w["inter_model_agreement"] * self.inter_model_agreement
            + w["regime_certainty"] * self.regime_certainty
            + w["observation_consistency"] * self.observation_consistency
            + w["forecast_stability"] * self.forecast_stability
        )
        return round(clamp(s, 0, 100), 1)

    def label(self, score: float) -> str:
        if score >= 80:
            return "HIGH RELIABILITY"
        if score >= 60:
            return "MODERATE RELIABILITY"
        return "LOW RELIABILITY"


class ForecastFailureRiskEngine:
    def assess(
        self,
        *,
        disagreement: float,
        health_min: float,
        transition_probability: float,
        lead_time_hours: int,
        unusual_state: float,
        historical_error_rate: float,
    ) -> tuple[str, str]:
        risk = (
            0.3 * disagreement
            + 0.2 * (1 - health_min)
            + 0.2 * transition_probability
            + 0.15 * min(lead_time_hours / 120.0, 1)
            + 0.15 * unusual_state
            + 0.1 * historical_error_rate
        )
        if risk >= 0.55:
            level = "HIGH"
        elif risk >= 0.32:
            level = "MODERATE"
        else:
            level = "LOW"
        expl = (
            "Similar atmospheric configurations have historically produced elevated forecast error."
            if level != "LOW"
            else "Consensus is consistent with recent verified skill in this context."
        )
        expl += " Decision-support indicator only — not a claim of certain failure."
        return level, expl


def smooth_weight_fields(
    per_location: dict[str, dict[str, float]],
    neighbors: dict[str, list[str]],
    level: str,
) -> dict[str, dict[str, float]]:
    strength = SMOOTH_MAP.get(level, 0.0)
    if strength <= 0:
        return per_location
    models = set()
    for w in per_location.values():
        models.update(w.keys())
    out: dict[str, dict[str, float]] = {loc: {} for loc in per_location}
    for m in models:
        field = {loc: per_location[loc].get(m, 0.0) for loc in per_location}
        sm = gaussian_smooth(field, neighbors, strength)
        for loc, v in sm.items():
            out[loc][m] = v
    for loc, w in out.items():
        out[loc] = normalize_weights(w, list(w.keys()))
    return out


@dataclass
class CounterfactualRequest:
    remove_models: list[str] = field(default_factory=list)
    weight_boosts: dict[str, float] = field(default_factory=dict)
    regime_override: str | None = None
    lead_time_hours: int | None = None
    strategy: str | None = None
    simulate_outage: list[str] = field(default_factory=list)


def run_counterfactual(
    baseline_weights: dict[str, float],
    baseline_values: dict[str, float],
    request: CounterfactualRequest,
    trust: DynamicTrustEngine,
    trust_input: TrustInput,
) -> dict[str, Any]:
    """Simulation only — caller must not persist as production blend."""
    from aeris_schemas import WeightingStrategy

    ti = TrustInput(
        model_ids=list(trust_input.model_ids),
        skill=trust_input.skill,
        health_adjustment=dict(trust_input.health_adjustment),
        regime=trust_input.regime,
        transition_probability=trust_input.transition_probability,
        lead_time_hours=request.lead_time_hours or trust_input.lead_time_hours,
        variable=trust_input.variable,
        disagreement=trust_input.disagreement,
        season=trust_input.season,
        region=trust_input.region,
        observation_consistency=trust_input.observation_consistency,
        event_mode=trust_input.event_mode,
    )
    drop = set(request.remove_models) | set(request.simulate_outage)
    for m in drop:
        ti.health_adjustment[m] = 0.0
        ti.model_ids = [x for x in ti.model_ids if x not in drop]
    strat = WeightingStrategy(request.strategy) if request.strategy else WeightingStrategy.CONTEXTUAL_ML
    tout: TrustOutput = trust.compute(ti, strat)
    w = dict(tout.weights)
    for m, boost in request.weight_boosts.items():
        if m in w:
            w[m] *= 1.0 + boost
    w = normalize_weights(w, list(w.keys()))
    base = blend_value(baseline_weights, baseline_values)
    scen_vals = {k: v for k, v in baseline_values.items() if k in w}
    scen = blend_value(w, scen_vals)
    u_base = uncertainty_from_members(base, baseline_values)
    u_scen = uncertainty_from_members(scen, scen_vals)
    return {
        "simulation": True,
        "label": "SIMULATION",
        "baseline_forecast": base,
        "scenario_forecast": scen,
        "forecast_delta": scen - base,
        "baseline_weights": baseline_weights,
        "scenario_weights": w,
        "uncertainty_delta": u_scen.uncertainty_score - u_base.uncertainty_score,
        "baseline_uncertainty": u_base.uncertainty_score,
        "scenario_uncertainty": u_scen.uncertainty_score,
    }


def event_probability(value: float, threshold: float, spread: float) -> float:
    """Gaussian tail proxy — configurable threshold, not an official warning."""
    if spread <= 1e-6:
        return 1.0 if value >= threshold else 0.0
    z = (threshold - value) / spread
    return float(clamp(0.5 * math.erfc(z / math.sqrt(2)), 0, 1))


def default_thresholds(variable: Variable) -> dict[str, float]:
    """Configurable prototype thresholds — not official IMD/NCMRWF warnings."""
    if variable == Variable.RAINFALL:
        return {"heavy": 50.0, "very_heavy": 100.0}
    if variable == Variable.TEMPERATURE:
        return {"heat": 40.0}
    if variable == Variable.WIND_SPEED:
        return {"high_wind": 12.0}
    return {}
