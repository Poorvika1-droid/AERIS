# AERIS ML Pipeline

## Overview

The ML pipeline has two distinct concerns:

1. **Skill memory** — rolling statistics computed from verified observations (runs every learning cycle)
2. **Trust meta-model** — lightweight model predicting per-model reliability from context features (trained on schedule, not per observation)

---

## Feature engineering (`ml/features/context_v1.json`)

Context features used by the trust engine:

| Feature | Type | Description |
|---|---|---|
| `latitude` | float | Location latitude |
| `longitude` | float | Location longitude |
| `region` | categorical | North/South/East/West/Central/Northeast |
| `elevation_m` | float | Elevation (0 if unavailable) |
| `season` | categorical | DJF / MAM / JJAS / ON |
| `month` | int | 1–12 |
| `day_of_year` | int | 1–365 |
| `lead_time_hours` | int | 6/12/24/48/72/120 |
| `variable` | categorical | RAINFALL/TEMPERATURE/WIND_SPEED |
| `weather_regime` | categorical | 9 operational classes |
| `regime_transition_probability` | float | 0–1 |
| `model_disagreement` | float | 0–1 normalized spread |
| `model_health_mean` | float | Mean health score 0–100 |

Per-model error features (for meta-model training, populated after sufficient operational data):
- `recent_mae_{model_id}` — rolling 30d MAE
- `recent_rmse_{model_id}` — rolling 30d RMSE
- `recent_bias_{model_id}` — rolling 30d bias
- `recent_csi_{model_id}` — rolling 30d CSI (rainfall events)

---

## Weighting strategies

### Current demo: CONTEXTUAL_ML (heuristic prior)

In the absence of sufficient labeled operational data, `DynamicTrustEngine` uses `_heuristic_context()`:

- **AI model**: weight boosted ×1.25 at lead ≤ 48h, ×1.3 in CONVECTIVE_RAIN / HEAVY_RAIN regimes
- **NWP model**: weight boosted ×1.2 in NORMAL / MONSOON / CYCLONIC_INFLUENCE, ×0.75 in CONVECTIVE_RAIN
- **Ensemble**: weight boosted ×1.05–1.25 at high disagreement or transition probability
- All multiplied by health adjustment (0–1.2) and observation consistency

### Production path: LightGBM / XGBoost meta-model

```python
# Training target: inverse normalized MAE (higher = more reliable)
y = 1 / (1 + mae_normalized)

# Feature matrix: context + recent errors per model
X = build_feature_matrix(context_features, recent_error_features)

# Train
model = LGBMRegressor(n_estimators=200, learning_rate=0.05, ...)
model.fit(X_train, y_train)

# Predict reliability scores → normalize to weights
scores = model.predict(X)
weights = scores / scores.sum()  # guaranteed ≥ 0, sum = 1
```

The meta-model is registered in MLflow with:
- `dataset_version`, `feature_version`, `hyperparameters`, `metrics`
- Validation: benchmark-only until operational data available

### SHAP attribution

When the meta-model is trained, `shap.TreeExplainer` provides per-feature contributions to the weight decision. These populate the `shap_like` field in `ForecastExplanation`. In the demo prototype, rule-based attribution is used instead.

---

## Skill memory update

Triggered by `compute_and_store_skill()` (called by `learning_step()`):

```
For each model × region × variable × lead × season:
  1. Fetch (forecast, observation) pairs from DB
  2. Compute: MAE, RMSE, bias, correlation, CSI, Brier, CRPS
  3. Upsert ModelSkill row (window = "historical" in demo)
```

Rolling windows supported: 7d, 30d, 90d, seasonal, historical.  
In production, add a `WHERE valid_time >= NOW() - INTERVAL '{window}'` filter.

---

## Model health evaluation

`ModelHealthEngine.evaluate()` inputs:
- Expected vs received location count (completeness)
- Initialization time vs now (delay detection)
- Value outlier rate (range check)
- Distribution shift score
- Recent MAE vs baseline MAE (degradation detection)

Output: `health_score` (0–100), `health_status` (HEALTHY/WARNING/DEGRADED/UNAVAILABLE), `recommended_weight_adjustment` (0–1.2).

---

## Continuous learning loop

```
POST /api/v1/admin/learn  →  learning_step(db)
  1. compute_and_store_skill(db)       # update rolling metrics
  2. refresh_health(db)                # re-evaluate health
  3. produce_current_blend(db)         # recompute weights + blend
  4. store_verification(db)            # update verification table
  5. PipelineRun record written
```

In production, schedule via Celery beat every N hours:
```python
celery_app.conf.beat_schedule = {
    "learning-step": {
        "task": "aeris.jobs.continuous_learning",
        "schedule": crontab(hour="*/6"),
    }
}
```

---

## MLflow tracking

```python
mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
mlflow.set_experiment("aeris-trust-engine")

with mlflow.start_run(run_name="demo-trust-engine"):
    mlflow.log_param("strategy", "CONTEXTUAL_ML")
    mlflow.log_param("data_mode", "demonstration")
    mlflow.log_metric("seed_complete", 1)
    # On real training: log model artifact
    # mlflow.sklearn.log_model(lgbm_model, "trust_meta_model")
```

MLflow is optional — gracefully skipped if the server is unreachable.

---

## Hyperparameter optimization

Optuna hooks are designed into the training pipeline (`ml/training/train_trust.py`).  
In the prototype, default hyperparameters are used.  
For production: `optuna.create_study(direction="minimize")` on validation CRPS.

---

## Regime detection

`RegimeDetector` uses a **hybrid approach**:

1. `KMeans(n_clusters=7)` on standardized anomaly features
2. Cluster centers mapped to `RegimeClass` via `_label_center()` (physics-inspired rules)
3. For extreme regimes (HEAVY_RAIN, HEATWAVE, HIGH_WIND, etc.), rule overlay takes precedence over cluster assignment to maintain interpretability

Future: transformer-based regime encoder for higher-resolution temporal patterns.

---

## Drift detection

`inject_demo_degradation()` simulates deterministic degradation on specific days.  
In production, implement:
- KS-test on forecast distribution vs rolling baseline
- MAE trend detection (CUSUM or Exponential Smoothing)
- Flag → reduce weight → quarantine after persistent degradation → recovery after verification improves
