"""Unit tests for trust/blend invariants."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "schemas"))
sys.path.insert(0, str(ROOT / "packages" / "shared"))

from aeris_schemas import RegimeClass, Variable, WeightingStrategy
from aeris_shared.metrics import normalize_weights
from services.blending import DynamicTrustEngine, SkillSnapshot, TrustInput, blend_value, run_counterfactual
from services.blending.engine import CounterfactualRequest
from services.ingestion.harmonize import convert_units, harmonize
from services.ingestion.adapters import MockNWPAdapter
from aeris_schemas import ForecastModelAdapter, ModelType
from datetime import datetime, timezone


def test_normalize_weights_sum_and_nonneg():
    w = normalize_weights({"a": 2, "b": 3, "c": 5})
    assert abs(sum(w.values()) - 1) < 1e-9
    assert all(v >= 0 for v in w.values())


def test_normalize_rejects_nan_negative():
    w = normalize_weights({"a": float("nan"), "b": -4, "c": 2})
    assert abs(sum(w.values()) - 1) < 1e-9
    assert w["a"] == 0 or w["a"] >= 0
    assert all(v >= 0 for v in w.values())


def test_equal_when_all_zero():
    w = normalize_weights({"a": 0, "b": 0})
    assert abs(w["a"] - 0.5) < 1e-9


def test_redistribute_missing():
    w = normalize_weights({"a": 1, "b": 1, "c": 1}, available=["a", "b"])
    assert "c" not in w
    assert abs(sum(w.values()) - 1) < 1e-9


def test_trust_engine_invariants():
    eng = DynamicTrustEngine()
    inp = TrustInput(
        model_ids=["nwp-x", "ai-x", "ens-x"],
        skill={
            "nwp-x": SkillSnapshot("nwp-x", 2.0, 3.0, 0.1, 40),
            "ai-x": SkillSnapshot("ai-x", 1.2, 2.0, 0.0, 40),
            "ens-x": SkillSnapshot("ens-x", 1.5, 2.2, 0.0, 40),
        },
        health_adjustment={"nwp-x": 1.0, "ai-x": 0.7, "ens-x": 1.0},
        regime=RegimeClass.CONVECTIVE_RAIN,
        transition_probability=0.4,
        lead_time_hours=24,
        variable=Variable.RAINFALL,
        disagreement=0.3,
        season="JJAS",
        region="South",
    )
    for strat in WeightingStrategy:
        out = eng.compute(inp, strat)
        assert abs(sum(out.weights.values()) - 1) < 1e-8
        assert all(v >= 0 and not math.isnan(v) for v in out.weights.values())


def test_unavailable_model_zero_health():
    eng = DynamicTrustEngine()
    inp = TrustInput(
        model_ids=["nwp-x", "ai-x"],
        skill={"nwp-x": SkillSnapshot("nwp-x", 1.0, 1.2, 0, 10), "ai-x": SkillSnapshot("ai-x", 1.0, 1.2, 0, 10)},
        health_adjustment={"nwp-x": 0.0, "ai-x": 1.0},
        regime=RegimeClass.NORMAL,
        transition_probability=0.1,
        lead_time_hours=48,
        variable=Variable.TEMPERATURE,
        disagreement=0.1,
        season="MAM",
        region="North",
    )
    out = eng.compute(inp)
    assert out.weights.get("nwp-x", 0) == 0 or "nwp-x" not in out.weights
    assert abs(sum(out.weights.values()) - 1) < 1e-8


def test_blend_and_nan_rejected():
    v = blend_value({"a": 0.5, "b": 0.5}, {"a": 10.0, "b": float("nan")})
    assert abs(v - 10.0) < 1e-9


def test_counterfactual_does_not_share_mutation():
    eng = DynamicTrustEngine()
    base_w = {"nwp-x": 0.4, "ai-x": 0.4, "ens-x": 0.2}
    frozen = dict(base_w)
    inp = TrustInput(
        model_ids=["nwp-x", "ai-x", "ens-x"],
        skill={m: SkillSnapshot(m, 1.0, 1.2, 0, 10) for m in base_w},
        health_adjustment={m: 1.0 for m in base_w},
        regime=RegimeClass.NORMAL,
        transition_probability=0.1,
        lead_time_hours=48,
        variable=Variable.RAINFALL,
        disagreement=0.2,
        season="JJAS",
        region="West",
    )
    res = run_counterfactual(base_w, {"nwp-x": 20, "ai-x": 30, "ens-x": 25}, CounterfactualRequest(remove_models=["nwp-x"]), eng, inp)
    assert res["simulation"] is True
    assert "nwp-x" not in res["scenario_weights"] or res["scenario_weights"].get("nwp-x", 0) == 0
    assert frozen == base_w


def test_unit_normalization_kelvin():
    assert abs(convert_units(300.15, "K", Variable.TEMPERATURE) - 27.0) < 1e-6


def test_harmonize_range_flags():
    payload = ForecastModelAdapter(
        model_id="x",
        model_name="x",
        provider="t",
        model_type=ModelType.NWP,
        initialization_time=datetime.now(timezone.utc),
        valid_time=datetime.now(timezone.utc),
        lead_time_hours=6,
        variable=Variable.RAINFALL,
        spatial_resolution="x",
        grid_definition="x",
        units="mm",
        forecast_values=[10.0, 9000.0],
        latitudes=[20.0, 21.0],
        longitudes=[77.0, 78.0],
        location_ids=["a", "b"],
    )
    field = harmonize(payload)
    assert "range" in field.qc_flags.get("b", [])
