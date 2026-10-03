"""Shared numeric helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def safe_div(n: float, d: float, default: float = 0.0) -> float:
    if d == 0 or math.isnan(d) or math.isnan(n):
        return default
    return n / d


def normalize_weights(raw: Mapping[str, float], available: Sequence[str] | None = None) -> dict[str, float]:
    """Non-negative, finite weights summing to 1. Redistribute if models missing."""
    keys = list(available) if available is not None else list(raw.keys())
    cleaned: dict[str, float] = {}
    for k in keys:
        v = float(raw.get(k, 0.0))
        if math.isnan(v) or math.isinf(v) or v < 0:
            v = 0.0
        cleaned[k] = v
    total = sum(cleaned.values())
    if total <= 0:
        n = len(keys)
        if n == 0:
            return {}
        return {k: 1.0 / n for k in keys}
    return {k: cleaned[k] / total for k in keys}


def mae(pred: Iterable[float], obs: Iterable[float]) -> float:
    pairs = [(float(p), float(o)) for p, o in zip(pred, obs, strict=True) if _finite(p) and _finite(o)]
    if not pairs:
        return float("nan")
    return sum(abs(p - o) for p, o in pairs) / len(pairs)


def rmse(pred: Iterable[float], obs: Iterable[float]) -> float:
    pairs = [(float(p), float(o)) for p, o in zip(pred, obs, strict=True) if _finite(p) and _finite(o)]
    if not pairs:
        return float("nan")
    return math.sqrt(sum((p - o) ** 2 for p, o in pairs) / len(pairs))


def bias(pred: Iterable[float], obs: Iterable[float]) -> float:
    pairs = [(float(p), float(o)) for p, o in zip(pred, obs, strict=True) if _finite(p) and _finite(o)]
    if not pairs:
        return float("nan")
    return sum(p - o for p, o in pairs) / len(pairs)


def pearson(pred: Sequence[float], obs: Sequence[float]) -> float:
    pairs = [(float(p), float(o)) for p, o in zip(pred, obs, strict=True) if _finite(p) and _finite(o)]
    n = len(pairs)
    if n < 3:
        return float("nan")
    mp = sum(p for p, _ in pairs) / n
    mo = sum(o for _, o in pairs) / n
    num = sum((p - mp) * (o - mo) for p, o in pairs)
    denp = math.sqrt(sum((p - mp) ** 2 for p, _ in pairs))
    deno = math.sqrt(sum((o - mo) ** 2 for _, o in pairs))
    return safe_div(num, denp * deno, float("nan"))


def brier(prob: Iterable[float], event: Iterable[int]) -> float:
    pairs = [(float(p), int(e)) for p, e in zip(prob, event, strict=True) if _finite(p)]
    if not pairs:
        return float("nan")
    return sum((p - e) ** 2 for p, e in pairs) / len(pairs)


def csi(tp: int, fp: int, fn: int) -> float:
    den = tp + fp + fn
    return safe_div(float(tp), float(den), float("nan"))


def crps_ensemble(obs: float, members: Sequence[float]) -> float:
    """Fair CRPS for a discrete ensemble (Hersbach-style simplified)."""
    m = [float(x) for x in members if _finite(x)]
    if not m or not _finite(obs):
        return float("nan")
    m.sort()
    n = len(m)
    s = 0.0
    for i, x in enumerate(m):
        p = (i + 0.5) / n
        s += (x - obs) * (2 * p - 1)  # not exact CRPS; used as demo proxy
    # Standard empirical CRPS:
    term1 = sum(abs(x - obs) for x in m) / n
    term2 = sum(abs(m[i] - m[j]) for i in range(n) for j in range(n)) / (2 * n * n)
    return term1 - term2


def _finite(x: float) -> bool:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return not math.isnan(v) and not math.isinf(v)


def gaussian_smooth(values: dict[str, float], neighbors: dict[str, list[str]], strength: float) -> dict[str, float]:
    if strength <= 0:
        return dict(values)
    out = {}
    for k, v in values.items():
        nbrs = neighbors.get(k, [])
        if not nbrs:
            out[k] = v
            continue
        acc = v
        w = 1.0
        for n in nbrs:
            if n in values:
                acc += strength * values[n]
                w += strength
        out[k] = acc / w
    return out
