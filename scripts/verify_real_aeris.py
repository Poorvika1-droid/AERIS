#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    ROOT / "data" / "processed" / "aeris_multimodel_ready.nc",
    ROOT / "data" / "processed" / "aeris_rainfall_verification_june2020.nc",
    ROOT / "data" / "processed" / "aeris_rainfall_metrics_june2020.csv",
    ROOT / "models" / "aeris_trust_engine.joblib",
    ROOT / "models" / "aeris_trust_engine_metadata.json",
    ROOT / "data" / "aeris.db",
]


def main() -> int:
    missing = [str(p) for p in REQUIRED if not p.exists()]
    if missing:
        print("Missing required AERIS real-data artifacts:")
        for item in missing:
            print(f" - {item}")
        return 1

    try:
        report = json.loads((ROOT / "data" / "processed" / "aeris_training_report.json").read_text())
        if "trust_engine_metrics" not in report:
            raise ValueError("Training report missing trust_engine_metrics")
    except Exception as exc:
        print(f"Training report invalid: {exc}")
        return 1

    api_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    print(f"API base URL: {api_url}")
    print("AERIS REAL PIPELINE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
