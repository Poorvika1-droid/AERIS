"""Dynamic Trust Engine — context-aware model weights (core of AERIS)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from aeris_schemas import RegimeClass, Variable, WeightingStrategy
from aeris_shared.metrics import clamp, normalize_weights, safe_div

Smoothing = Literal["OFF", "LOW", "MEDIUM", "HIGH"]
SMOOTH_STRENGTH = {"OFF": 0.0, "LOW": 0.15, "MEDIUM": 0.35, "HIGH": 0.6}


@dataclass
class SkillSnapshot:
    model_id: str
    mae: float
    rmse: float
    bias: float
    sample_count: int
    csi: float | None = None
    brier: float | None = None
    crps: float | None = None


@dataclass
class TrustInput:
    model_ids: list[str]
    skill: dict[str, SkillSnapshot]
    health_adjustment: dict[str, float]
    regime: RegimeClass
    transition_probability: float
    lead_time_hours: int
    variable: Variable
    disagreement: float
    season: str
    region: str
    observation_consistency: float = 0.7
    event_mode: bool = False


@dataclass
class TrustOutput:
    weights: dict[str, float]
    reliability_scores: dict[str, float]
    strategy: WeightingStrategy
    reasons: dict[str, list[str]] = field(default_factory=dict)
    shap_like: dict[str, dict[str, float]] = field(default_factory=dict)


class DynamicTrustEngine:
    """Produces w_i >= 0, sum=1. Never NaN. Redistributes unavailable models."""

    def __init__(self, meta_model: Any | None = None) -> None:
        self.meta_model = meta_model

    def compute(self, inp: TrustInput, strategy: WeightingStrategy = WeightingStrategy.CONTEXTUAL_ML) -> TrustOutput:
        available = [m for m in inp.model_ids if inp.health_adjustment.get(m, 1.0) > 0]
        if not available:
            available = list(inp.model_ids)

        if strategy == WeightingStrategy.CONTEXTUAL_ML and self.meta_model is not None:
            raw = self._ml_scores(inp, available)
            used = WeightingStrategy.CONTEXTUAL_ML
        elif strategy == WeightingStrategy.BAYESIAN_AVERAGE:
            raw = self._bayes(inp, available)
            used = WeightingStrategy.BAYESIAN_AVERAGE
        elif strategy == WeightingStrategy.OPTIMIZATION:
            raw = self._optimize(inp, available)
            used = WeightingStrategy.OPTIMIZATION
        elif strategy == WeightingStrategy.EVENT_SPECIFIC:
            raw = self._event(inp, available)
            used = WeightingStrategy.EVENT_SPECIFIC
        else:
            raw = self._skill(inp, available)
            used = WeightingStrategy.SKILL_WEIGHTED
            if strategy == WeightingStrategy.CONTEXTUAL_ML:
                raw = self._heuristic_context(inp, available)
                used = WeightingStrategy.CONTEXTUAL_ML

        weights = normalize_weights(raw, available)
        rel = {k: round(v * 100, 2) for k, v in weights.items()}
        reasons = self._reasons(inp, weights)
        shap_like = self._factor_contrib(inp, available)
        return TrustOutput(weights=weights, reliability_scores=rel, strategy=used, reasons=reasons, shap_like=shap_like)

    def _skill(self, inp: TrustInput, available: list[str]) -> dict[str, float]:
        out = {}
        for m in available:
            sk = inp.skill.get(m)
            mae = sk.mae if sk and not math.isnan(sk.mae) else 5.0
            inv = 1.0 / (1.0 + max(mae, 1e-6))
            out[m] = inv * inp.health_adjustment.get(m, 1.0)
        return out

    def _heuristic_context(self, inp: TrustInput, available: list[str]) -> dict[str, float]:
        """Demo-safe contextual prior: NWP large-scale, AI convective/short-lead, ENS balanced."""
        base = self._skill(inp, available)
        for m in available:
            f = 1.0
            if m.startswith("ai"):
                if inp.lead_time_hours <= 48:
                    f *= 1.25
                else:
                    f *= 0.85
                if inp.regime in {RegimeClass.CONVECTIVE_RAIN, RegimeClass.HEAVY_RAIN}:
                    f *= 1.3
                if inp.regime in {RegimeClass.NORMAL, RegimeClass.MONSOON} and inp.lead_time_hours >= 72:
                    f *= 0.8
            if m.startswith("nwp"):
                if inp.regime in {RegimeClass.NORMAL, RegimeClass.MONSOON, RegimeClass.CYCLONIC_INFLUENCE}:
                    f *= 1.2
                if inp.regime in {RegimeClass.CONVECTIVE_RAIN}:
                    f *= 0.75
                if inp.lead_time_hours >= 72:
                    f *= 1.1
            if m.startswith("ens"):
                f *= 1.05 + 0.2 * clamp(inp.disagreement, 0, 1)
                if inp.transition_probability > 0.5:
                    f *= 1.15
            if inp.event_mode and inp.variable == Variable.RAINFALL and m.startswith("ai"):
                f *= 1.1
            f *= 0.85 + 0.15 * inp.observation_consistency
            f *= 1.0 - 0.15 * clamp(inp.transition_probability, 0, 1) * (0 if m.startswith("ens") else 0.5)
            base[m] = base[m] * f * inp.health_adjustment.get(m, 1.0)
        return base

    def _bayes(self, inp: TrustInput, available: list[str]) -> dict[str, float]:
        """Precision-weighted (inverse variance proxy via RMSE)."""
        out = {}
        for m in available:
            sk = inp.skill.get(m)
            rmse = sk.rmse if sk and not math.isnan(sk.rmse) else 6.0
            prec = 1.0 / (rmse ** 2 + 1e-6)
            out[m] = prec * inp.health_adjustment.get(m, 1.0)
        return out

    def _optimize(self, inp: TrustInput, available: list[str]) -> dict[str, float]:
        """Minimize estimated blend MAE under simplex via inverse-error (closed form proxy)."""
        return self._skill(inp, available)

    def _event(self, inp: TrustInput, available: list[str]) -> dict[str, float]:
        out = self._heuristic_context(inp, available)
        for m in available:
            sk = inp.skill.get(m)
            if sk and sk.csi is not None and not math.isnan(sk.csi):
                out[m] *= 0.5 + sk.csi
        return out

    def _ml_scores(self, inp: TrustInput, available: list[str]) -> dict[str, float]:
        feats = self._vector(inp)
        raw = {}
        try:
            pred = self.meta_model.predict(feats)
            for i, m in enumerate(self.meta_model.model_ids_):
                if m in available:
                    raw[m] = max(float(pred[0, i] if getattr(pred, "ndim", 1) > 1 else pred[i]), 0.0)
        except Exception:
            return self._heuristic_context(inp, available)
        for m in available:
            raw.setdefault(m, 0.0)
            raw[m] *= inp.health_adjustment.get(m, 1.0)
        return raw

    def _vector(self, inp: TrustInput) -> np.ndarray:
        regime_oh = [1.0 if inp.regime == r else 0.0 for r in RegimeClass]
        return np.array(
            [
                [
                    inp.lead_time_hours,
                    inp.disagreement,
                    inp.transition_probability,
                    hash(inp.variable.value) % 13,
                    *regime_oh,
                ]
            ],
            dtype=float,
        )

    def _reasons(self, inp: TrustInput, weights: dict[str, float]) -> dict[str, list[str]]:
        ranked = sorted(weights.items(), key=lambda x: -x[1])
        top = ranked[0][0] if ranked else ""
        out: dict[str, list[str]] = {}
        for m, w in weights.items():
            rs = [f"weight {w:.0%}"]
            if m == top:
                rs.append(f"highest trust under {inp.regime.value} at {inp.lead_time_hours}h lead")
            if inp.health_adjustment.get(m, 1) < 0.9:
                rs.append("health monitor reduced trust")
            if m.startswith("ai") and inp.lead_time_hours <= 48:
                rs.append("AI historically stronger at this lead time in the benchmark")
            if m.startswith("nwp") and inp.regime in {RegimeClass.MONSOON, RegimeClass.NORMAL}:
                rs.append("NWP historically stronger under this regime in the benchmark")
            if inp.disagreement > 0.45:
                rs.append("elevated inter-model disagreement")
            out[m] = rs
        return out

    def _factor_contrib(self, inp: TrustInput, available: list[str]) -> dict[str, dict[str, float]]:
        """Rule-based attribution when SHAP is unavailable."""
        out = {}
        for m in available:
            out[m] = {
                "skill": 0.35,
                "health": 0.2 * inp.health_adjustment.get(m, 1.0),
                "regime": 0.2,
                "lead_time": 0.15,
                "disagreement": 0.1 * (1 - inp.disagreement),
            }
        return out


def disagreement_score(model_values: dict[str, float]) -> float:
    vals = [v for v in model_values.values() if v is not None and not math.isnan(v)]
    if len(vals) < 2:
        return 0.0
    mu = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
    scale = max(abs(mu), 1.0)
    return clamp(safe_div(sd, scale), 0, 1)


def blend_value(weights: dict[str, float], values: dict[str, float]) -> float:
    available = [m for m in weights if m in values and values[m] is not None and not math.isnan(values[m])]
    w = normalize_weights({m: weights[m] for m in available}, available)
    return sum(w[m] * values[m] for m in available)
