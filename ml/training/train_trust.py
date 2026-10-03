"""Train a lightweight trust meta-model on demonstration features. Benchmark only."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=(200, 8))
    # fake reliability of 3 models from features — illustration only
    y = np.abs(np.stack([x[:, 0] * 0.1 + 0.4, x[:, 1] * 0.05 + 0.35, 0.25 - 0.02 * x[:, 2]], axis=1))
    y = y / y.sum(axis=1, keepdims=True)
    try:
        from xgboost import XGBRegressor

        model = XGBRegressor(n_estimators=40, max_depth=3, random_state=42)
        model.fit(x, y)
        print("Trained XGBRegressor on synthetic meta features (demonstration).")
    except Exception as exc:  # noqa: BLE001
        print("XGBoost unavailable, skipped:", exc)
    out = ROOT / "ml" / "registry" / "last_train.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"status": "demonstration", "n": 200}, indent=2))


if __name__ == "__main__":
    main()
