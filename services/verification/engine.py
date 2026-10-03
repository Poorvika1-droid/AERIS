"""Rolling skill memory and verification against observations."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from aeris_shared.metrics import bias as bias_fn
from aeris_shared.metrics import brier, crps_ensemble, csi, mae, pearson, rmse


WINDOWS = {"7d": 7, "30d": 30, "90d": 90, "seasonal": 90, "historical": 10_000}


@dataclass
class SkillRecord:
    model_id: str
    region: str
    variable: str
    lead_time_bin: int
    season: str
    regime: str
    mae: float
    rmse: float
    bias: float
    correlation: float
    brier: float | None
    crps: float | None
    csi: float | None
    precision: float | None
    recall: float | None
    sample_count: int
    window: str


def compute_skill(
    preds: list[float],
    obs: list[float],
    *,
    event_threshold: float | None = None,
    ensemble_members: list[list[float]] | None = None,
) -> dict[str, float | None]:
    m = mae(preds, obs)
    r = rmse(preds, obs)
    b = bias_fn(preds, obs)
    c = pearson(preds, obs)
    out: dict[str, float | None] = {
        "mae": m,
        "rmse": r,
        "bias": b,
        "correlation": c,
        "brier": None,
        "crps": None,
        "csi": None,
        "precision": None,
        "recall": None,
        "sample_count": float(len(preds)),
    }
    if event_threshold is not None:
        pe = [1 if p >= event_threshold else 0 for p in preds]
        oe = [1 if o >= event_threshold else 0 for o in obs]
        tp = sum(1 for a, b_ in zip(pe, oe) if a and b_)
        fp = sum(1 for a, b_ in zip(pe, oe) if a and not b_)
        fn = sum(1 for a, b_ in zip(pe, oe) if not a and b_)
        tn = sum(1 for a, b_ in zip(pe, oe) if not a and not b_)
        out["csi"] = csi(tp, fp, fn)
        out["precision"] = tp / (tp + fp) if (tp + fp) else None
        out["recall"] = tp / (tp + fn) if (tp + fn) else None
        probs = [min(max(p / (event_threshold * 1.5), 0), 1) for p in preds]
        out["brier"] = brier(probs, oe)
        _ = tn
    if ensemble_members:
        crps_vals = [crps_ensemble(o, mem) for o, mem in zip(obs, ensemble_members)]
        finite = [x for x in crps_vals if x == x]
        out["crps"] = sum(finite) / len(finite) if finite else None
    return out


def skill_score_composite(mae_v: float, rmse_v: float) -> float:
    if math.isnan(mae_v):
        return 0.0
    return 1.0 / (1.0 + 0.6 * mae_v + 0.4 * (rmse_v if not math.isnan(rmse_v) else mae_v))


def reliability_diagram(probs: list[float], events: list[int], bins: int = 10) -> list[dict[str, float]]:
    edges = [i / bins for i in range(bins + 1)]
    rows = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        idx = [j for j, p in enumerate(probs) if (p >= lo) and (p < hi or (i == bins - 1 and p <= hi))]
        if not idx:
            continue
        mp = sum(probs[j] for j in idx) / len(idx)
        fo = sum(events[j] for j in idx) / len(idx)
        rows.append({"bin": i, "mean_probability": mp, "observed_frequency": fo, "count": float(len(idx))})
    return rows


def group_key(model_id: str, region: str, variable: str, lead: int, season: str, regime: str) -> tuple:
    return (model_id, region, variable, lead, season, regime)
