# AERIS Data Model

Database: SQLAlchemy supports MySQL for deployed environments and SQLite for zero-dependency demos.  
ORM: SQLAlchemy 2 mapped columns.

---

## Table reference

### `forecast_sources`
Registered forecast model sources.

| Column | Type | Notes |
|---|---|---|
| `id` (PK) | String(64) | e.g. `nwp-mock-gfs-like` |
| `model_name` | String(128) | Human-readable name |
| `provider` | String(64) | DEMO / ECMWF / NCMRWF / etc. |
| `model_type` | String(32) | NWP / AI / ENSEMBLE / BLENDED |
| `spatial_resolution` | String(64) | e.g. `0.5deg-equiv` |
| `status` | String(32) | ACTIVE / DEGRADED / OFFLINE |
| `variables` | JSON | List of Variable enum values |
| `metadata_json` | JSON | Adapter class, demo flag, extra |

---

### `locations`
City and grid point registry.

| Column | Type | Notes |
|---|---|---|
| `id` (PK) | String(64) | e.g. `IN-DL-DEL` or `GRID-042` |
| `name` | String(128) | Display name |
| `latitude` | Float | Indexed |
| `longitude` | Float | Indexed |
| `region` | String(64) | North/South/East/West/Central/Northeast |
| `elevation_m` | Float? | Optional |
| `admin_level` | String(32) | city / grid |

Composite index: `(latitude, longitude)`.

---

### `forecast_runs`
One row per model × variable × lead × initialization time.

| Column | Type | Notes |
|---|---|---|
| `id` (PK) | String(64) | Composite key string |
| `model_id` (FK) | String | → `forecast_sources.id` |
| `initialization_time` | DateTime(tz) | Indexed |
| `lead_time_hours` | Integer | 6/12/24/48/72/120 |
| `variable` | String(32) | Indexed |
| `valid_time` | DateTime(tz) | Indexed |
| `units` | String(32) | Canonical unit |
| `data_mode` | String(32) | demonstration / operational |

---

### `forecast_values`
One row per run × location.

| Column | Type | Notes |
|---|---|---|
| `id` (PK) | Integer | Autoincrement |
| `run_id` (FK) | String | → `forecast_runs.id` |
| `location_id` (FK) | String | → `locations.id` |
| `value` | Float | In canonical units |
| `qc_flags` | JSON | List of flag strings |

---

### `observations`
Station or synthetic observations.

| Column | Type | Notes |
|---|---|---|
| `id` (PK) | Integer | Autoincrement |
| `location_id` (FK) | String | → `locations.id` |
| `valid_time` | DateTime(tz) | Indexed |
| `variable` | String(32) | Indexed |
| `value` | Float | Canonical unit |
| `source` | String(64) | `demo-station` / real station ID |
| `data_mode` | String(32) | |

---

### `model_skill`
Rolling skill statistics per model × region × variable × lead × season × regime.

| Column | Type | Notes |
|---|---|---|
| `model_id` | String(64) | Indexed |
| `region` | String(64) | Indexed |
| `variable` | String(32) | Indexed |
| `lead_time_bin` | Integer | |
| `season` | String(16) | DJF/MAM/JJAS/ON |
| `regime` | String(32) | Indexed |
| `window` | String(16) | 7d/30d/90d/historical |
| `mae`, `rmse`, `bias` | Float | Error metrics |
| `correlation` | Float? | Pearson r |
| `brier`, `crps`, `csi` | Float? | Probabilistic metrics |
| `precision`, `recall` | Float? | Event detection |
| `sample_count` | Integer | |
| `computed_at` | DateTime(tz) | |

---

### `model_health`
Health evaluation snapshot per model.

| Column | Type | Notes |
|---|---|---|
| `model_id` | String(64) | Indexed |
| `health_score` | Float | 0–100 |
| `health_status` | String(32) | HEALTHY/WARNING/DEGRADED/UNAVAILABLE |
| `health_reasons` | JSON | List of reason strings |
| `recommended_weight_adjustment` | Float | 0–1.2 |
| `checked_at` | DateTime(tz) | |

---

### `weather_regimes`
Regime classification per location × valid time.

| Column | Type | Notes |
|---|---|---|
| `location_id` | String(64) | Indexed |
| `valid_time` | DateTime(tz) | Indexed |
| `current_regime` | String(32) | RegimeClass value |
| `previous_regime` | String(32)? | |
| `cluster_id` | Integer? | KMeans cluster |
| `features` | JSON | Raw feature values |

---

### `regime_transitions`

| Column | Type | Notes |
|---|---|---|
| `location_id` | String(64) | Indexed |
| `valid_time` | DateTime(tz) | |
| `from_regime` | String(32) | |
| `to_regime` | String(32) | |
| `transition_probability` | Float | 0–1 |
| `transition_confidence` | Float | 0–1 |

---

### `dynamic_weights`
Trust weights per forecast.

| Column | Type | Notes |
|---|---|---|
| `forecast_id` | String(64) | Indexed |
| `location_id` | String(64) | Indexed |
| `variable` | String(32) | Indexed |
| `lead_time_hours` | Integer | |
| `weights` | JSON | `{model_id: weight}` — sum to 1 |
| `strategy` | String(32) | WeightingStrategy value |
| `regime` | String(32) | Regime at blend time |

---

### `blended_forecasts`
Final AERIS blended output.

| Column | Type | Notes |
|---|---|---|
| `id` (PK) | String(64) | SHA256 of location+var+lead+valid_time |
| `location_id` | String(64) | Indexed |
| `variable` | String(32) | Indexed |
| `lead_time_hours` | Integer | Indexed |
| `valid_time` | DateTime(tz) | Indexed |
| `initialization_time` | DateTime(tz) | |
| `value` | Float | Blended value in canonical unit |
| `units` | String(32) | |
| `dominant_model` | String(64) | Model with highest weight |
| `data_mode` | String(32) | |

---

### `uncertainty_metrics`
Uncertainty + FRS per blended forecast.

| Column | Type | Notes |
|---|---|---|
| `forecast_id` | String(64) | Indexed |
| `ensemble_spread` | Float | Standard deviation of members |
| `inter_model_spread` | Float | |
| `interval_low`, `interval_high` | Float | 80%-ish prediction interval |
| `confidence` | String(16) | HIGH/MODERATE/LOW |
| `uncertainty_score` | Float | 0–1 |
| `disagreement_score` | Float | 0–1 |
| `disagreement_label` | String(16) | |
| `frs` | Float | 0–100 |
| `frs_label` | String(32) | HIGH/MODERATE/LOW RELIABILITY |
| `frs_components` | JSON | Breakdown by component |
| `failure_risk` | String(16) | LOW/MODERATE/HIGH |
| `failure_explanation` | Text | Human-readable explanation |

---

### `extreme_events`

| Column | Type | Notes |
|---|---|---|
| `id` (PK) | String(64) | UUID |
| `event_type` | String(32) | heavy_rainfall/heatwave/high_wind |
| `location_id`, `location_name` | String | |
| `latitude`, `longitude` | Float | |
| `start_time`, `end_time` | DateTime(tz) | |
| `probability` | Float | 0–1 |
| `intensity_low`, `intensity_high` | Float | Range |
| `confidence` | String(16) | |
| `affected_grid_area` | Float | km² proxy |
| `primary_model` | String(64) | |
| `supporting_models` | JSON | List |
| `disagreement` | Float | |
| `forecast_failure_risk` | String(16) | |
| `variable`, `lead_time_hours` | | |
| `payload` | JSON | Extra metadata |

---

### `verification_results`

Aggregated verification per model × variable × region × lead × regime.  
Includes MAE, RMSE, bias, CRPS, Brier, CSI, F1, precision, recall.  
`note` always contains `"DEMONSTRATION BENCHMARK"` in demo mode.

---

### `forecast_explanations`

| Column | Type | Notes |
|---|---|---|
| `forecast_id` | String(64) | Indexed |
| `summary` | Text | Human-readable explanation |
| `reasons` | JSON | `{model_id: [reason_strings]}` |
| `shap_like` | JSON | Rule-based or SHAP attribution |

---

### `forecast_provenance`

Full data lineage per blended forecast:  
`input_models`, `timestamps`, `model_versions`, `weights`, `calibration_version`, `blending_version`, `generated_at`, `data_mode`.

---

### `simulation_runs`

Counterfactual results stored for audit.  
`production_mutated: false` is always written and enforced in tests.

---

### `ml_models`

Trust meta-model registry:  
`id`, `name`, `version`, `stage`, `blending_strategy`, `metrics`, `hyperparameters`, `dataset_version`, `feature_version`, `mlflow_run_id`, `trained_at`, `validation_status`.

---

### `pipeline_runs`

Job execution records: `job_name`, `status`, `started_at`, `finished_at`, `detail`.

---

### `alerts`, `system_metrics`

Lightweight event log and numeric metric snapshots for the System Health dashboard.
