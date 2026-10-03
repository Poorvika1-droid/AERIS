"""Deterministic demo universe: observations, three models, skill, blend, events."""

from __future__ import annotations

import hashlib
import logging
import math
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from aeris_schemas import CANONICAL_UNITS, HealthStatus, LocationPoint, ModelType, RegimeClass, Variable, WeightingStrategy
from aeris_shared.metrics import normalize_weights
from services.blending import (
    CounterfactualRequest,
    DynamicTrustEngine,
    FRSComponents,
    ForecastFailureRiskEngine,
    SkillSnapshot,
    TrustInput,
    blend_value,
    disagreement_score,
    event_probability,
    run_counterfactual,
    smooth_weight_fields,
    uncertainty_from_members,
)
from services.extreme_events import detect_events
from services.ingestion import DEMO_ADAPTERS, MockObservationAdapter, harmonize
from services.model_health import ModelHealthEngine, inject_demo_degradation
from services.regime import RegimeDetector, RegimeTransitionDetector, season_from_month
from services.verification import compute_skill

from app.config import get_settings
from app.geo import all_locations, neighbors_map
from app.models import (
    Alert,
    BlendedForecast,
    DynamicWeight,
    ExtremeEvent,
    ForecastExplanation,
    ForecastProvenance,
    ForecastRun,
    ForecastSource,
    ForecastValue,
    Location,
    MLModelRecord,
    ModelHealth,
    ModelSkill,
    Observation,
    PipelineRun,
    RegimeTransition,
    SimulationRun,
    SystemMetric,
    UncertaintyMetric,
    VerificationResult,
    WeatherRegime,
)

log = logging.getLogger("aeris.pipeline")
LEADS = [6, 12, 24, 48, 72, 120]
VARIABLES = [Variable.RAINFALL, Variable.TEMPERATURE, Variable.WIND_SPEED]
HISTORY_DAYS = 8
CURRENT_INIT = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
# Demonstration thresholds are deliberately calibrated to the seeded data's
# range so the event-intelligence map always has meaningful candidate points.
# They are not IMD/NCMRWF operational warning thresholds.
DEMO_EVENT_THRESHOLDS = {
    "RAINFALL": {"heavy": 10.0},
    "TEMPERATURE": {"heat": 27.0},
    "WIND_SPEED": {"high_wind": 6.0},
}

_engine = DynamicTrustEngine()
_health = ModelHealthEngine()
_regimes = RegimeDetector()
_trans = RegimeTransitionDetector()
_fail = ForecastFailureRiskEngine()
_obs = MockObservationAdapter()


def _fid(loc: str, var: str, lead: int, valid: datetime) -> str:
    raw = f"{loc}|{var}|{lead}|{valid.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def seed_universe(db: Session) -> dict[str, Any]:
    if get_settings().aeris_data_mode == "real_IMD":
        raise RuntimeError("seed_universe is disabled in real_IMD mode")
    t0 = time.perf_counter()
    settings = get_settings()
    locations = all_locations()
    db.query(ForecastValue).delete()
    db.query(ForecastRun).delete()
    db.query(Observation).delete()
    db.query(ModelSkill).delete()
    db.query(ModelHealth).delete()
    db.query(WeatherRegime).delete()
    db.query(RegimeTransition).delete()
    db.query(DynamicWeight).delete()
    db.query(UncertaintyMetric).delete()
    db.query(ForecastExplanation).delete()
    db.query(ForecastProvenance).delete()
    db.query(ExtremeEvent).delete()
    db.query(BlendedForecast).delete()
    db.query(VerificationResult).delete()
    db.query(SimulationRun).delete()
    db.query(Alert).delete()
    db.query(SystemMetric).delete()
    db.query(PipelineRun).delete()
    db.query(MLModelRecord).delete()
    db.query(ForecastSource).delete()
    db.query(Location).delete()
    db.commit()

    for loc in locations:
        db.add(
            Location(
                id=loc.location_id,
                name=loc.name,
                latitude=loc.latitude,
                longitude=loc.longitude,
                region=loc.region,
                elevation_m=loc.elevation_m,
                admin_level=loc.admin_level,
            )
        )
    for mid, ad in DEMO_ADAPTERS.items():
        db.add(
            ForecastSource(
                id=ad.model_id,
                model_name=ad.model_name,
                provider=ad.provider,
                model_type=ad.model_type.value,
                spatial_resolution=ad.spatial_resolution,
                status="ACTIVE",
                variables=[v.value for v in VARIABLES],
                metadata_json={"demo": True, "adapter": ad.__class__.__name__},
            )
        )
    db.add(
        ForecastSource(
            id="aeris-blend",
            model_name="AERIS Trust Blend",
            provider="AERIS",
            model_type=ModelType.BLENDED.value,
            spatial_resolution="harmonized",
            status="ACTIVE",
            variables=[v.value for v in VARIABLES],
            metadata_json={"demo": True},
        )
    )
    db.commit()

    # Observations + model forecasts over history (valid times daily at 00Z)
    for day in range(HISTORY_DAYS):
        valid = CURRENT_INIT.date()
        vt = CURRENT_INIT - timedelta(days=HISTORY_DAYS - 1 - day)
        for var in VARIABLES:
            obs = _obs.fetch_station(locations, vt, var)
            for loc in locations:
                db.add(
                    Observation(
                        location_id=loc.location_id,
                        valid_time=vt,
                        variable=var.value,
                        value=obs[loc.location_id],
                        source="demo-station",
                        data_mode="demonstration",
                    )
                )
            for lead in LEADS:
                init = vt - timedelta(hours=lead)
                for ad in DEMO_ADAPTERS.values():
                    payload = ad.fetch(locations, init, lead, var)
                    field = harmonize(payload)
                    run_id = f"{ad.model_id}:{var.value}:{lead}:{init.isoformat()}"
                    db.add(
                        ForecastRun(
                            id=run_id,
                            model_id=ad.model_id,
                            initialization_time=init,
                            lead_time_hours=lead,
                            variable=var.value,
                            valid_time=vt,
                            units=CANONICAL_UNITS[var],
                            data_mode="demonstration",
                        )
                    )
                    db.flush()
                    for loc_id, val in field.values.items():
                        # Controlled error hierarchy vs observation
                        err = _controlled_error(ad.model_id, loc_id, var, lead, vt, locations)
                        db.add(
                            ForecastValue(
                                run_id=run_id,
                                location_id=loc_id,
                                value=val + err,
                                qc_flags=field.qc_flags.get(loc_id, []),
                            )
                        )
        db.commit()

    _fit_regimes(db, locations)
    compute_and_store_skill(db)
    refresh_health(db)
    produce_current_blend(db, locations, smoothing="MEDIUM")
    store_verification(db)
    register_ml_model(db)
    db.add(
        PipelineRun(
            id=str(uuid.uuid4())[:12],
            job_name="seed_demo",
            status="SUCCESS",
            started_at=CURRENT_INIT,
            finished_at=datetime.now(timezone.utc),
            detail="Demonstration benchmark seeded",
        )
    )
    db.add(
        SystemMetric(
            name="seed_seconds",
            value=time.perf_counter() - t0,
            captured_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        Alert(
            level="INFO",
            message="AERIS running in Demonstration / Benchmark Data mode. Not operational NCMRWF skill.",
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    maybe_mlflow()
    return {
        "locations": len(locations),
        "mode": settings.aeris_data_mode,
        "init": CURRENT_INIT.isoformat(),
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }


def _controlled_error(model_id: str, loc_id: str, var: Variable, lead: int, vt: datetime, locations: list[LocationPoint]) -> float:
    loc = next(x for x in locations if x.location_id == loc_id)
    rng = np.random.default_rng(abs(hash((model_id, loc_id, var.value, lead, vt.date().isoformat()))) % (2**32))
    regime, _, _ = _regimes.detect(
        temperature=32,
        rainfall=10,
        wind=5,
        pressure=1008,
        humidity=70,
        month=vt.month,
        temp_anomaly=0,
        rain_anomaly=0,
    )
    # Hierarchy: NWP better NORMAL/MONSOON & long lead; AI better convective & short lead; ENS robust in transition
    scale = 1.8 if var == Variable.RAINFALL else 0.55 if var == Variable.TEMPERATURE else 0.4
    if model_id.startswith("nwp"):
        if vt.month in {6, 7, 8, 9} and lead >= 48:
            scale *= 0.65
        if loc.region in {"Northeast", "South"} and lead <= 24:
            scale *= 1.25
    if model_id.startswith("ai"):
        if lead <= 48:
            scale *= 0.7
        else:
            scale *= 1.35
        if loc.latitude < 16:
            scale *= 0.85
    if model_id.startswith("ens"):
        scale *= 0.9
    return float(rng.normal(0, scale))


def _fit_regimes(db: Session, locations: list[LocationPoint]) -> None:
    rows = db.query(Observation).filter(Observation.variable == Variable.RAINFALL.value).limit(400).all()
    feats = []
    for _ in rows[:80]:
        feats.append([30, 10, 5, 1010, 70, 7, 0, 0])
    if feats:
        _regimes.fit(np.array(feats, dtype=float))
    prev: dict[str, str] = {}
    vt = CURRENT_INIT
    rain = {o.location_id: o.value for o in db.query(Observation).filter(Observation.valid_time == vt, Observation.variable == "RAINFALL")}
    temp = {o.location_id: o.value for o in db.query(Observation).filter(Observation.valid_time == vt, Observation.variable == "TEMPERATURE")}
    wind = {o.location_id: o.value for o in db.query(Observation).filter(Observation.valid_time == vt, Observation.variable == "WIND_SPEED")}
    for loc in locations:
        r = rain.get(loc.location_id, 5.0)
        t = temp.get(loc.location_id, 30.0)
        w = wind.get(loc.location_id, 4.0)
        label, cid, feat = _regimes.detect(
            temperature=t,
            rainfall=r,
            wind=w,
            pressure=1005 if r > 40 else 1010,
            humidity=80 if r > 10 else 55,
            month=vt.month,
            temp_anomaly=t - 30,
            rain_anomaly=r - 8,
        )
        # Simulate previous regime for demo data to generate transition probabilities
        regime_options = [RegimeClass.NORMAL, RegimeClass.MONSOON, RegimeClass.CONVECTIVE_RAIN, RegimeClass.HEAVY_RAIN, RegimeClass.HEATWAVE, RegimeClass.HIGH_WIND, RegimeClass.DRY_EXTREME]
        if loc.location_id not in prev:
            # Randomly assign a previous regime different from current for ~30% of locations
            if random.random() < 0.3:
                prev[loc.location_id] = random.choice([r for r in regime_options if r != label]).value
            else:
                prev[loc.location_id] = label.value
        p_prev_str = prev.get(loc.location_id)
        p_prev = RegimeClass(p_prev_str) if p_prev_str else None
        # Amplify trends for demo data to ensure transition probabilities exceed threshold
        rain_trend = (r - 8) * 2.5
        temp_trend = (t - 30) * 2.5
        tp, tc = _trans.estimate(p_prev, label, rain_trend, temp_trend)
        db.add(
            WeatherRegime(
                location_id=loc.location_id,
                valid_time=vt,
                current_regime=label.value,
                previous_regime=p_prev_str,
                cluster_id=cid,
                features=feat,
            )
        )
        if tp > 0.2:
            db.add(
                RegimeTransition(
                    location_id=loc.location_id,
                    valid_time=vt,
                    from_regime=p_prev_str or label.value,
                    to_regime=label.value,
                    transition_probability=tp,
                    transition_confidence=tc,
                )
            )


def compute_and_store_skill(db: Session) -> None:
    if get_settings().aeris_data_mode == "real_IMD":
        log.info("Skipping destructive skill recomputation in real_IMD mode.")
        return
    db.query(ModelSkill).delete()
    models = [s.id for s in db.query(ForecastSource).all() if s.id != "aeris-blend"]
    now = datetime.now(timezone.utc)
    for model_id in models:
        for var in VARIABLES:
            for lead in LEADS:
                for region in ["North", "South", "East", "West", "Central", "Northeast", "ALL"]:
                    q = (
                        db.query(ForecastValue, Observation, Location, ForecastRun)
                        .join(ForecastRun, ForecastRun.id == ForecastValue.run_id)
                        .join(Observation, (Observation.location_id == ForecastValue.location_id) & (Observation.variable == ForecastRun.variable) & (Observation.valid_time == ForecastRun.valid_time))
                        .join(Location, Location.id == ForecastValue.location_id)
                        .filter(ForecastRun.model_id == model_id, ForecastRun.variable == var.value, ForecastRun.lead_time_hours == lead)
                    )
                    if region != "ALL":
                        q = q.filter(Location.region == region)
                    rows = q.all()
                    if len(rows) < 5:
                        continue
                    preds = [r[0].value for r in rows]
                    obs = [r[1].value for r in rows]
                    sk = compute_skill(preds, obs, event_threshold=50.0 if var == Variable.RAINFALL else None)
                    season = season_from_month(CURRENT_INIT.month)
                    db.add(
                        ModelSkill(
                            model_id=model_id,
                            region=region,
                            variable=var.value,
                            lead_time_bin=lead,
                            season=season,
                            regime="ALL",
                            window="historical",
                            mae=sk["mae"] or 0,
                            rmse=sk["rmse"] or 0,
                            bias=sk["bias"] or 0,
                            correlation=sk["correlation"],
                            brier=sk["brier"],
                            crps=sk["crps"],
                            csi=sk["csi"],
                            precision=sk["precision"],
                            recall=sk["recall"],
                            sample_count=int(sk["sample_count"] or 0),
                            computed_at=now,
                        )
                    )
    db.commit()


def refresh_health(db: Session) -> None:
    db.query(ModelHealth).delete()
    now = datetime.now(timezone.utc)
    nloc = db.query(Location).count()
    for src in db.query(ForecastSource).filter(ForecastSource.id != "aeris-blend"):
        runs = db.query(ForecastRun).filter(ForecastRun.model_id == src.id, ForecastRun.valid_time == CURRENT_INIT).all()
        rec = 0
        outliers = 0
        if runs:
            vals = db.query(ForecastValue).filter(ForecastValue.run_id == runs[0].id).all()
            rec = len(vals)
            outliers = sum(1 for v in vals if abs(v.value) > 500)
        skill = (
            db.query(ModelSkill)
            .filter(ModelSkill.model_id == src.id, ModelSkill.region == "ALL")
            .first()
        )
        deg = inject_demo_degradation(src.id, CURRENT_INIT)
        report = _health.evaluate(
            model_id=src.id,
            expected_locations=nloc,
            received_locations=rec or nloc,
            initialization_time=CURRENT_INIT,
            now=CURRENT_INIT + timedelta(hours=3),
            value_outlier_rate=outliers / max(rec, 1),
            recent_mae=(skill.mae * (2.0 if deg < 1 else 1.0)) if skill else None,
            baseline_mae=skill.mae if skill else None,
        )
        if deg < 1:
            report.health_reasons.append("scheduled demo degradation probe")
            report.recommended_weight_adjustment *= deg
            report.health_score *= deg
            if report.health_score < 80:
                report.health_status = HealthStatus.WARNING
        db.add(
            ModelHealth(
                model_id=src.id,
                health_score=report.health_score,
                health_status=report.health_status.value,
                health_reasons=report.health_reasons,
                recommended_weight_adjustment=report.recommended_weight_adjustment,
                checked_at=now,
            )
        )
        src.status = report.health_status.value if report.health_status.value != "HEALTHY" else "ACTIVE"
    db.commit()


def _skill_map(db: Session, var: str, lead: int, region: str) -> dict[str, SkillSnapshot]:
    out: dict[str, SkillSnapshot] = {}
    rows = db.query(ModelSkill).filter(ModelSkill.variable == var, ModelSkill.lead_time_bin == lead)
    for r in rows:
        if r.region not in {region, "ALL"}:
            continue
        if r.model_id in out and r.region != region:
            continue
        key = r.model_id
        if r.region == region or key not in out:
            out[key] = SkillSnapshot(r.model_id, r.mae, r.rmse, r.bias, r.sample_count, r.csi, r.brier, r.crps)
    return out


def produce_current_blend(db: Session, locations: list[LocationPoint], smoothing: str = "MEDIUM") -> None:
    db.query(BlendedForecast).delete()
    db.query(DynamicWeight).delete()
    db.query(UncertaintyMetric).delete()
    db.query(ForecastExplanation).delete()
    db.query(ForecastProvenance).delete()
    db.query(ExtremeEvent).delete()
    health_adj = {h.model_id: h.recommended_weight_adjustment for h in db.query(ModelHealth).all()}
    health_score = {h.model_id: h.health_score for h in db.query(ModelHealth).all()}
    regimes = {r.location_id: r for r in db.query(WeatherRegime).filter(WeatherRegime.valid_time == CURRENT_INIT)}
    trans = {t.location_id: t for t in db.query(RegimeTransition).all()}
    nbrs = neighbors_map(locations)
    model_ids = list(DEMO_ADAPTERS.keys())

    for var in VARIABLES:
        for lead in LEADS:
            raw_w: dict[str, dict[str, float]] = {}
            payloads: dict[str, dict[str, float]] = {m: {} for m in model_ids}
            for m in model_ids:
                run = (
                    db.query(ForecastRun)
                    .filter(
                        ForecastRun.model_id == m,
                        ForecastRun.variable == var.value,
                        ForecastRun.lead_time_hours == lead,
                        ForecastRun.valid_time == CURRENT_INIT,
                    )
                    .first()
                )
                if not run:
                    continue
                for fv in db.query(ForecastValue).filter(ForecastValue.run_id == run.id):
                    payloads[m][fv.location_id] = fv.value

            for loc in locations:
                members = {m: payloads[m][loc.location_id] for m in model_ids if loc.location_id in payloads[m]}
                if not members:
                    continue
                disag = disagreement_score(members)
                rg = regimes.get(loc.location_id)
                from aeris_schemas import RegimeClass

                regime = RegimeClass(rg.current_regime) if rg else RegimeClass.NORMAL
                tp = trans.get(loc.location_id).transition_probability if loc.location_id in trans else 0.15
                skills = _skill_map(db, var.value, lead, loc.region)
                ti = TrustInput(
                    model_ids=model_ids,
                    skill=skills,
                    health_adjustment=health_adj,
                    regime=regime,
                    transition_probability=tp,
                    lead_time_hours=lead,
                    variable=var,
                    disagreement=disag,
                    season=season_from_month(CURRENT_INIT.month),
                    region=loc.region,
                    event_mode=var == Variable.RAINFALL and members.get(next(iter(members), ""), 0) > 40,
                )
                tout = _engine.compute(ti, WeightingStrategy.CONTEXTUAL_ML)
                raw_w[loc.location_id] = tout.weights

            sm = smooth_weight_fields(raw_w, nbrs, smoothing)
            for loc in locations:
                if loc.location_id not in sm:
                    continue
                members = {m: payloads[m][loc.location_id] for m in model_ids if loc.location_id in payloads[m]}
                w = sm[loc.location_id]
                val = blend_value(w, members)
                fid = _fid(loc.location_id, var.value, lead, CURRENT_INIT)
                dominant = max(w, key=w.get)
                db.add(
                    BlendedForecast(
                        id=fid,
                        location_id=loc.location_id,
                        variable=var.value,
                        lead_time_hours=lead,
                        valid_time=CURRENT_INIT,
                        initialization_time=CURRENT_INIT - timedelta(hours=lead),
                        value=val,
                        units=CANONICAL_UNITS[var],
                        dominant_model=dominant,
                        data_mode="demonstration",
                    )
                )
                db.add(DynamicWeight(forecast_id=fid, location_id=loc.location_id, variable=var.value, lead_time_hours=lead, weights=w, strategy="CONTEXTUAL_ML", regime=regimes.get(loc.location_id).current_regime if loc.location_id in regimes else "NORMAL"))
                u = uncertainty_from_members(val, members)
                health_mean = float(np.mean(list(health_score.values()) or [80]))
                frs_c = FRSComponents(
                    historical_skill=clamp01(1 / (1 + (skills_mae_mean(db, var.value, lead)))) * 100,
                    model_health=health_mean,
                    inter_model_agreement=(1 - u.disagreement_score) * 100,
                    regime_certainty=85 - 40 * (trans.get(loc.location_id).transition_probability if loc.location_id in trans else 0.1),
                    observation_consistency=78,
                    forecast_stability=82,
                )
                frs = frs_c.score()
                risk, rex = _fail.assess(
                    disagreement=u.disagreement_score,
                    health_min=min(health_adj.values() or [1]),
                    transition_probability=trans.get(loc.location_id).transition_probability if loc.location_id in trans else 0.1,
                    lead_time_hours=lead,
                    unusual_state=0.2 if val > 40 else 0.05,
                    historical_error_rate=0.15,
                )
                db.add(
                    UncertaintyMetric(
                        forecast_id=fid,
                        ensemble_spread=u.ensemble_spread,
                        inter_model_spread=u.inter_model_spread,
                        interval_low=u.prediction_interval_low,
                        interval_high=u.prediction_interval_high,
                        confidence=u.confidence,
                        uncertainty_score=u.uncertainty_score,
                        disagreement_score=u.disagreement_score,
                        disagreement_label=u.disagreement_label,
                        frs=frs,
                        frs_label=frs_c.label(frs),
                        frs_components=frs_c.__dict__,
                        failure_risk=risk,
                        failure_explanation=rex,
                    )
                )
                rg = regimes.get(loc.location_id)
                reasons = {
                    m: [
                        f"Contribution {w.get(m, 0):.0%}",
                        f"Regime {rg.current_regime if rg else 'NORMAL'} (operational class for weighting)",
                    ]
                    for m in w
                }
                top = dominant
                summary = (
                    f"AERIS blended {var.value} at {loc.name}: {val:.1f} {CANONICAL_UNITS[var]}. "
                    f"Dominant source {top} ({w.get(top, 0):.0%}). "
                    f"Uncertainty is not the same as confidence (confidence={u.confidence}, disagreement={u.disagreement_label})."
                )
                db.add(ForecastExplanation(forecast_id=fid, summary=summary, reasons=reasons, shap_like={"note": "Rule-based attribution; SHAP optional when meta-model is trained."}))
                db.add(
                    ForecastProvenance(
                        forecast_id=fid,
                        input_models=list(members.keys()),
                        timestamps={"valid_time": CURRENT_INIT.isoformat(), "generated_at": datetime.now(timezone.utc).isoformat()},
                        model_versions={m: "demo-v1" for m in members},
                        weights=w,
                        generated_at=datetime.now(timezone.utc),
                        data_mode="demonstration",
                    )
                )
                if lead == 48:
                    rain_v = val if var == Variable.RAINFALL else None
                    # events assembled after all variables — handled below per loc at 48h rainfall pass
                    if var == Variable.RAINFALL:
                        evs = detect_events(
                            location_id=loc.location_id,
                            location_name=loc.name,
                            latitude=loc.latitude,
                            longitude=loc.longitude,
                            valid_time=CURRENT_INIT,
                            lead_time_hours=lead,
                            rainfall=val,
                            temperature=None,
                            wind=None,
                            rain_spread=u.ensemble_spread,
                            temp_spread=1.0,
                            wind_spread=1.0,
                            weights=w,
                            disagreement=u.disagreement_score,
                            failure_risk=risk,
                            confidence=u.confidence,
                            thresholds=DEMO_EVENT_THRESHOLDS,
                        )
                        for e in evs:
                            db.add(
                                ExtremeEvent(
                                    id=e.event_id,
                                    event_type=e.event_type,
                                    location_id=e.location_id,
                                    location_name=e.location_name,
                                    latitude=e.latitude,
                                    longitude=e.longitude,
                                    start_time=e.start_time,
                                    end_time=e.end_time,
                                    probability=e.probability,
                                    intensity_low=e.intensity_range[0],
                                    intensity_high=e.intensity_range[1],
                                    confidence=e.confidence,
                                    affected_grid_area=e.affected_grid_area,
                                    primary_model=e.primary_model,
                                    supporting_models=e.supporting_models,
                                    disagreement=e.disagreement,
                                    forecast_failure_risk=e.forecast_failure_risk,
                                    variable=e.variable,
                                    lead_time_hours=e.lead_time_hours,
                                    payload={"demo": True},
                                )
                            )
            db.commit()
    # heat/wind events
    _extra_events(db, locations)


def _extra_events(db: Session, locations: list[LocationPoint]) -> None:
    for loc in locations:
        for var, etype in [(Variable.TEMPERATURE, "heatwave"), (Variable.WIND_SPEED, "high_wind")]:
            bf = (
                db.query(BlendedForecast)
                .filter(BlendedForecast.location_id == loc.location_id, BlendedForecast.variable == var.value, BlendedForecast.lead_time_hours == 48)
                .first()
            )
            if not bf:
                continue
            um = db.query(UncertaintyMetric).filter(UncertaintyMetric.forecast_id == bf.id).first()
            dw = db.query(DynamicWeight).filter(DynamicWeight.forecast_id == bf.id).first()
            evs = detect_events(
                location_id=loc.location_id,
                location_name=loc.name,
                latitude=loc.latitude,
                longitude=loc.longitude,
                valid_time=CURRENT_INIT,
                lead_time_hours=48,
                rainfall=None,
                temperature=bf.value if var == Variable.TEMPERATURE else None,
                wind=bf.value if var == Variable.WIND_SPEED else None,
                rain_spread=1,
                temp_spread=um.ensemble_spread if um else 1,
                wind_spread=um.ensemble_spread if um else 1,
                weights=dw.weights if dw else {},
                disagreement=um.disagreement_score if um else 0.2,
                failure_risk=um.failure_risk if um else "LOW",
                confidence=um.confidence if um else "MODERATE",
                thresholds=DEMO_EVENT_THRESHOLDS,
            )
            for e in evs:
                db.add(
                    ExtremeEvent(
                        id=e.event_id,
                        event_type=e.event_type,
                        location_id=e.location_id,
                        location_name=e.location_name,
                        latitude=e.latitude,
                        longitude=e.longitude,
                        start_time=e.start_time,
                        end_time=e.end_time,
                        probability=e.probability,
                        intensity_low=e.intensity_range[0],
                        intensity_high=e.intensity_range[1],
                        confidence=e.confidence,
                        affected_grid_area=e.affected_grid_area,
                        primary_model=e.primary_model,
                        supporting_models=e.supporting_models,
                        disagreement=e.disagreement,
                        forecast_failure_risk=e.forecast_failure_risk,
                        variable=e.variable,
                        lead_time_hours=e.lead_time_hours,
                        payload={"demo": True},
                    )
                )
    db.commit()


def store_verification(db: Session) -> None:
    db.query(VerificationResult).delete()
    for model_id in list(DEMO_ADAPTERS.keys()) + ["aeris-blend", "static-equal"]:
        for var in VARIABLES:
            mae_s, n = _verify_model(db, model_id, var)
            if n < 3:
                continue
            db.add(
                VerificationResult(
                    model_id=model_id,
                    variable=var.value,
                    region="ALL",
                    lead_time_hours=0,
                    regime="ALL",
                    mae=mae_s["mae"],
                    rmse=mae_s["rmse"],
                    bias=mae_s["bias"],
                    crps=mae_s.get("crps"),
                    brier=mae_s.get("brier"),
                    csi=mae_s.get("csi"),
                    f1=_f1(mae_s.get("precision"), mae_s.get("recall")),
                    precision=mae_s.get("precision"),
                    recall=mae_s.get("recall"),
                    sample_count=n,
                    note="DEMONSTRATION BENCHMARK — not operational accuracy",
                )
            )
    db.commit()


def _verify_model(db: Session, model_id: str, var: Variable) -> tuple[dict, int]:
    if model_id == "aeris-blend":
        # score blend vs obs at current init only (small) + reconstruct historical equal is separate
        rows = (
            db.query(BlendedForecast, Observation)
            .join(Observation, (Observation.location_id == BlendedForecast.location_id) & (Observation.variable == BlendedForecast.variable) & (Observation.valid_time == BlendedForecast.valid_time))
            .filter(BlendedForecast.variable == var.value)
            .all()
        )
        if len(rows) < 3:
            return {"mae": 0, "rmse": 0, "bias": 0}, 0
        preds = [r[0].value for r in rows]
        obs = [r[1].value for r in rows]
        return compute_skill(preds, obs, event_threshold=50 if var == Variable.RAINFALL else None), len(rows)
    if model_id == "static-equal":
        # approximate: mean of three models vs obs for current init
        return _equal_weight_skill(db, var)
    rows = (
        db.query(ForecastValue, Observation, ForecastRun)
        .join(ForecastRun, ForecastRun.id == ForecastValue.run_id)
        .join(Observation, (Observation.location_id == ForecastValue.location_id) & (Observation.valid_time == ForecastRun.valid_time) & (Observation.variable == ForecastRun.variable))
        .filter(ForecastRun.model_id == model_id, ForecastRun.variable == var.value)
        .all()
    )
    preds = [r[0].value for r in rows]
    obs = [r[1].value for r in rows]
    if len(preds) < 3:
        return {"mae": 0, "rmse": 0, "bias": 0}, 0
    return compute_skill(preds, obs, event_threshold=50 if var == Variable.RAINFALL else None), len(preds)


def _equal_weight_skill(db: Session, var: Variable) -> tuple[dict, int]:
    # current valid time equal mean
    locs = db.query(Location).all()
    preds, obs = [], []
    for loc in locs:
        members = []
        for m in DEMO_ADAPTERS:
            run = (
                db.query(ForecastRun)
                .filter(ForecastRun.model_id == m, ForecastRun.variable == var.value, ForecastRun.valid_time == CURRENT_INIT, ForecastRun.lead_time_hours == 48)
                .first()
            )
            if not run:
                continue
            fv = db.query(ForecastValue).filter(ForecastValue.run_id == run.id, ForecastValue.location_id == loc.id).first()
            if fv:
                members.append(fv.value)
        o = db.query(Observation).filter(Observation.location_id == loc.id, Observation.variable == var.value, Observation.valid_time == CURRENT_INIT).first()
        if members and o:
            preds.append(sum(members) / len(members))
            obs.append(o.value)
    if len(preds) < 3:
        return {"mae": 0, "rmse": 0, "bias": 0}, 0
    return compute_skill(preds, obs, event_threshold=50 if var == Variable.RAINFALL else None), len(preds)


def _f1(p, r):
    if not p or not r:
        return None
    return 2 * p * r / (p + r) if (p + r) else None


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def skills_mae_mean(db: Session, var: str, lead: int) -> float:
    rows = db.query(ModelSkill).filter(ModelSkill.variable == var, ModelSkill.lead_time_bin == lead, ModelSkill.region == "ALL").all()
    if not rows:
        return 2.0
    return float(np.mean([r.mae for r in rows]))


def register_ml_model(db: Session) -> None:
    db.add(
        MLModelRecord(
            id="trust-meta-v0.1",
            name="AERIS contextual trust meta-model",
            version="0.1.0",
            stage="Staging",
            blending_strategy="CONTEXTUAL_ML",
            metrics={"note": "heuristic+skill until sufficient labeled ops data"},
            hyperparameters={"fallback": "heuristic_context", "smoother": "MEDIUM"},
            dataset_version="demo-grid-v1",
            feature_version="context-v1",
            mlflow_run_id=None,
            trained_at=datetime.now(timezone.utc),
            validation_status="demonstration-benchmark",
        )
    )
    db.commit()


def maybe_mlflow() -> None:
    try:
        import mlflow

        settings = get_settings()
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment)
        with mlflow.start_run(run_name="demo-trust-engine"):
            mlflow.log_param("strategy", "CONTEXTUAL_ML")
            mlflow.log_param("data_mode", "demonstration")
            mlflow.log_metric("seed_complete", 1)
    except Exception as exc:  # noqa: BLE001
        log.info("MLflow not reachable (expected in local-only): %s", exc)


def simulate(db: Session, forecast_id: str, request: dict) -> dict:
    bf = db.query(BlendedForecast).filter(BlendedForecast.id == forecast_id).first()
    if not bf:
        raise ValueError("forecast not found")
    dw = db.query(DynamicWeight).filter(DynamicWeight.forecast_id == forecast_id).first()
    members = {}
    for m in DEMO_ADAPTERS:
        run = (
            db.query(ForecastRun)
            .filter(
                ForecastRun.model_id == m,
                ForecastRun.variable == bf.variable,
                ForecastRun.lead_time_hours == bf.lead_time_hours,
                ForecastRun.valid_time == bf.valid_time,
            )
            .first()
        )
        if run:
            fv = db.query(ForecastValue).filter(ForecastValue.run_id == run.id, ForecastValue.location_id == bf.location_id).first()
            if fv:
                members[m] = fv.value
    loc = db.query(Location).filter(Location.id == bf.location_id).first()
    rg = db.query(WeatherRegime).filter(WeatherRegime.location_id == bf.location_id).first()
    from aeris_schemas import RegimeClass

    skills = _skill_map(db, bf.variable, bf.lead_time_hours, loc.region if loc else "ALL")
    health_adj = {h.model_id: h.recommended_weight_adjustment for h in db.query(ModelHealth).all()}
    ti = TrustInput(
        model_ids=list(DEMO_ADAPTERS.keys()),
        skill=skills,
        health_adjustment=health_adj,
        regime=RegimeClass(rg.current_regime) if rg else RegimeClass.NORMAL,
        transition_probability=0.2,
        lead_time_hours=bf.lead_time_hours,
        variable=Variable(bf.variable),
        disagreement=disagreement_score(members),
        season=season_from_month(bf.valid_time.month),
        region=loc.region if loc else "ALL",
    )
    req = CounterfactualRequest(
        remove_models=request.get("remove_models", []),
        weight_boosts=request.get("weight_boosts", {}),
        lead_time_hours=request.get("lead_time_hours"),
        strategy=request.get("strategy"),
        simulate_outage=request.get("simulate_outage", []),
    )
    result = run_counterfactual(dw.weights if dw else {}, members, req, _engine, ti)
    sid = str(uuid.uuid4())[:12]
    db.add(SimulationRun(id=sid, request=request, result=result, created_at=datetime.now(timezone.utc), production_mutated=False))
    db.commit()
    result["simulation_id"] = sid
    result["production_mutated"] = False
    return result


def learning_step(db: Session) -> dict:
    """Update rolling skill + health; do not retrain huge models."""
    t0 = time.perf_counter()
    if get_settings().aeris_data_mode == "real_IMD":
        return {
            "status": "blocked",
            "message": "Continuous learning is disabled in real_IMD mode. The real database and model artifact are preserved.",
            "elapsed_s": round(time.perf_counter() - t0, 2),
        }
    compute_and_store_skill(db)
    refresh_health(db)
    produce_current_blend(db, all_locations())
    store_verification(db)
    db.add(
        PipelineRun(
            id=str(uuid.uuid4())[:12],
            job_name="continuous_learning",
            status="SUCCESS",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            detail="Skill memory + health + blend recalibrated from verified observations (demo).",
        )
    )
    db.commit()
    return {"status": "ok", "elapsed_s": round(time.perf_counter() - t0, 2)}
