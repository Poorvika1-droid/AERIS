from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "schemas"))
sys.path.insert(0, str(ROOT / "packages" / "shared"))

from aeris_schemas import LocationPoint, Variable
from services.ingestion.adapters import MockAIAdapter, MockEnsembleAdapter, MockNWPAdapter
from services.model_health import ModelHealthEngine
from services.regime import RegimeDetector


def test_mock_adapters_same_interface():
    loc = [LocationPoint(location_id="x", name="x", latitude=19.0, longitude=72.8, region="West")]
    init = datetime(2026, 7, 1, tzinfo=timezone.utc)
    for Ad in (MockNWPAdapter, MockAIAdapter, MockEnsembleAdapter):
        p = Ad().fetch(loc, init, 24, Variable.RAINFALL)
        assert p.model_id
        assert len(p.forecast_values) == 1
        assert p.lead_time_hours == 24


def test_health_unavailable():
    h = ModelHealthEngine().evaluate(
        model_id="x",
        expected_locations=10,
        received_locations=0,
        initialization_time=datetime.now(timezone.utc),
    )
    assert h.health_status.value == "UNAVAILABLE"
    assert h.recommended_weight_adjustment == 0


def test_regime_heavy_rain():
    d = RegimeDetector()
    label, _, _ = d.detect(
        temperature=28,
        rainfall=90,
        wind=6,
        pressure=1008,
        humidity=90,
        month=7,
        temp_anomaly=0,
        rain_anomaly=50,
    )
    assert label.value == "HEAVY_RAIN"
