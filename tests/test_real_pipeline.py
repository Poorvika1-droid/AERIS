from __future__ import annotations

import os
import sys
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'aeris.db'}")
os.environ.setdefault("AERIS_DATA_MODE", "real_IMD")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_model_artifact_exists_and_loads():
    path = ROOT / "models" / "aeris_trust_engine.joblib"
    assert path.exists(), f"Missing trained model artifact at {path}"
    payload = joblib.load(path)
    assert "model" in payload
    assert "feature_names" in payload
    assert payload["model_names"] == ["NCMRWF", "ECMWF"]


def test_real_training_report_exists():
    report_path = ROOT / "data" / "processed" / "aeris_training_report.json"
    assert report_path.exists(), f"Missing training report at {report_path}"


def test_database_and_summary_present():
    db_path = ROOT / "data" / "aeris.db"
    assert db_path.exists(), "Database is missing"
    metadata = ROOT / "models" / "aeris_trust_engine_metadata.json"
    assert metadata.exists(), "Metadata is missing"


def test_system_endpoint_reports_real_mode(client):
    response = client.get("/api/v1/system")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_mode"] == "real_IMD"
    assert body["database"] == "connected"
    assert body["trained_model"] in {"available", "unavailable"}
    assert "dataset_summary" in body
    assert body["verification_status"] in {"ok", "missing"}


def test_seed_endpoint_is_disabled_in_real_mode(client):
    response = client.post("/api/v1/admin/seed")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert "Demo seeding is disabled" in body["message"]


def test_learn_endpoint_is_disabled_in_real_mode(client):
    response = client.post("/api/v1/admin/learn")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert "real_IMD mode" in body["message"]


def test_real_weights_sum_to_one():
    report = ROOT / "data" / "processed" / "aeris_training_report.json"
    data = __import__("json").loads(report.read_text())
    assert "trust_engine_metrics" in data
    assert isinstance(data["feature_list"], list)
    assert data["model_names"] == ["NCMRWF", "ECMWF"]


def test_no_seed_invocation_in_real_mode():
    src = (ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    assert "not intended for real runtime" not in src.lower()
