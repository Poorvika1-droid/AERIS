#!/usr/bin/env python3
"""Create the initial scientific gate reports; it never trains a model."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "81datas"
LINEAGE = DATA / "DATA_LINEAGE.csv"

FIELDS = ["dataset_id", "repository", "repository_url", "original_path", "file", "source_provider", "source_dataset", "source_type", "data_role", "real_demo_synthetic", "observation_forecast_reanalysis_derived", "variables", "units", "spatial_resolution", "temporal_resolution", "initialization_time", "valid_time", "forecast_lead", "creation_time", "license", "download_url", "parent_dataset", "processing_history", "sha256", "training_eligibility", "exclusion_reason"]

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def classify(path: Path) -> tuple[str, str, str, str]:
    text = str(path).lower()
    if path.suffix.lower() == ".grib":
        return "NWP_FORECAST", "real", "forecast", "ECMWF or NCMRWF metadata must be inspected"
    if path.suffix.lower() == ".nc" and "era5" in text:
        return "REANALYSIS", "real", "reanalysis", "ERA5 excluded as forecast member"
    if path.suffix.lower() == ".nc" and ("imd" in text or "rf25" in text):
        return "OBSERVATION", "real", "observation", "target candidate; availability metadata required"
    if any(x in text for x in ("demo", "mock", "fixture", "synthetic", "seed")):
        return "DEMO", "demo", "derived", "demo/synthetic artifact"
    if path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".md", ".txt", ".yml", ".yaml", ".toml", ".lock"}:
        return "METADATA", "unknown", "metadata", "repository implementation/documentation; not a data source"
    return "UNKNOWN", "unknown", "unknown", "unverified provenance/timing"

def main() -> int:
    # Every collected file gets a lineage row. Repository code and dependencies
    # are explicitly METADATA/UNKNOWN rather than silently treated as weather data.
    candidates = [p for p in DATA.rglob("*") if p.is_file() and p != LINEAGE]
    known_hashes: dict[str, str] = {}
    source_hashes = DATA / "FILE_HASHES.csv"
    if source_hashes.exists():
        with source_hashes.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                known_hashes[row.get("collected_path", "").lower()] = row.get("sha256", "").lower()
    rows = []
    for path in candidates:
        role, reality, kind, reason = classify(path)
        sha = known_hashes.get(str(path).lower()) or digest(path)
        relative = path.relative_to(DATA)
        repository = relative.parts[0] if len(relative.parts) > 1 else "AERIS_DATA_CATALOG"
        rows.append({"dataset_id": f"local-{sha[:16]}", "repository": repository, "repository_url": "", "original_path": str(path), "file": path.name, "source_provider": "UNVERIFIED", "source_dataset": "", "source_type": kind, "data_role": role, "real_demo_synthetic": reality, "observation_forecast_reanalysis_derived": kind, "variables": "", "units": "", "spatial_resolution": "", "temporal_resolution": "", "initialization_time": "", "valid_time": "", "forecast_lead": "", "creation_time": "", "license": "", "download_url": "", "parent_dataset": "", "processing_history": "discovery only", "sha256": sha, "training_eligibility": "NO", "exclusion_reason": reason})
    with LINEAGE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    report = ROOT / "TRAINING_DATA_READINESS_REPORT.md"
    report.write_text("# Training-data readiness\n\n## Status: INSUFFICIENT TRAINING DATA — TRAINING BLOCKED\n\nThe local inventory contains IMD observation candidates, ERA5 reanalysis, and limited ECMWF/NCMRWF forecast artifacts. Forecast issuance/availability metadata, a multi-year overlapping archive, and source/grid/units verification have not been established for every candidate. ERA5 is classified only as REANALYSIS and cannot be a forecast blend member. The existing 2020 forecast sample has seven initialization times; it cannot support valid chronological train/validation/test selection.\n\nNo model was trained by this audit. `DATA_LINEAGE.csv` records every collected file; all are ineligible until their provenance and timing are resolved.\n", encoding="utf-8")
    (ROOT / "LEAKAGE_AUDIT_REPORT.md").write_text("# Leakage audit\n\n## Status: FAIL — production training prohibited\n\nThe prior `scripts/train_aeris_real.py` includes `observed_mean_mm`, `bias_mm`, `mae_mm`, `rmse_mm`, and a target-derived rain indicator as model features, and uses `GroupKFold`, which is not a chronological split. Its artifact and its reported metrics are therefore contaminated and must not be deployed. The new `src/validation/leakage.py` provides fail-closed causal, split, duplicate, compatibility, and rolling-skill checks.\n", encoding="utf-8")
    (ROOT / "DATA_SPLIT_REPORT.md").write_text("# Data split report\n\n## Status: NOT CREATED\n\nNo valid split is possible from the currently verified overlap. The available real forecast evaluation period has only seven 2020 initialization times. Obtain a sufficiently long, versioned overlap of ECMWF/NCMRWF issued forecasts and IMD observations before creating chronological partitions.\n", encoding="utf-8")
    (ROOT / "DATA_QUALITY_REPORT.md").write_text(f"# Data quality report\n\nDiscovery catalogued {len(rows)} data-bearing artifacts. Unit, coordinate, temporal coverage, missingness, and provider provenance are intentionally unverified until file-level inspection completes; every record is excluded from training.\n", encoding="utf-8")
    print(f"Wrote {LINEAGE} ({len(rows)} records) and fail-closed readiness reports.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
