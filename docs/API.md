# AERIS API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs` (Swagger UI)  
ReDoc: `http://localhost:8000/redoc`

All responses include:
```json
{ "data_mode": "demonstration", "banner": "Demonstration / Benchmark Data", "disclaimer": "..." }
```

---

## Health & meta

### `GET /api/v1/health`
API + database + Redis health with latency.

### `GET /api/v1/meta`
Product metadata, PS number, core messages.

### `GET /`
Root redirect info.

---

## Models & sources

### `GET /api/v1/models`
List all registered forecast sources.

### `GET /api/v1/models/{model_id}`
Single model: health score, skill summary, metadata.

### `GET /api/v1/locations`
All locations. Query: `?q=<search>`.

---

## Forecast intelligence

### `GET /api/v1/forecast`
Blended AERIS forecast for a location.

**Query params:** `location_id`, `variable` (RAINFALL/TEMPERATURE/WIND_SPEED), `lead_time_hours`, `model`

**Response includes:** `value`, `units`, `weights`, `dominant_model`, `regime`, `uncertainty`, `explanation`, `members`

**Weight invariant:** `Σ weights = 1`, all `≥ 0`.

### `POST /api/v1/forecast/blend`
Trigger blend for a specific request.

```json
{ "location_id": "IN-DL-DEL", "variable": "RAINFALL", "lead_time_hours": 48, "strategy": "CONTEXTUAL_ML", "smoothing": "MEDIUM" }
```

### `GET /api/v1/forecast/skill-lead`
MAE vs lead time per model. Query: `variable`, `region`.

### `GET /api/v1/forecast/uncertainty-series`
Uncertainty interval across lead times. Query: `location_id`, `variable`.

---

## Weights & reliability

### `GET /api/v1/weights`
Dynamic trust weights for all locations. Query: `variable`, `lead_time_hours`.

### `GET /api/v1/weights/history`
Weight evolution across lead times (chart data). Query: `location_id`, `variable`.

### `GET /api/v1/reliability`
FRS for locations. Query: `location_id`, `variable`, `lead_time_hours`.

### `GET /api/v1/disagreement`
Inter-model disagreement scores. Query: `variable`, `lead_time_hours`.

---

## Skill & verification

### `GET /api/v1/skill`
Rolling skill memory. Query: `model_id`.

### `GET /api/v1/skill/heatmap`
MAE grid: model × lead time. Query: `variable`.

### `GET /api/v1/verification`
Overall verification metrics per model. Query: `variable`, `region`.

### `GET /api/v1/verification/by-lead`
MAE by lead time per model. Query: `variable`.

---

## Domain

### `GET /api/v1/extremes`
Extreme weather events. Query: `event_type` (heavy_rainfall/heatwave/high_wind).

```json
{
  "items": [{
    "event_id": "...", "event_type": "heavy_rainfall", "location_name": "Mumbai",
    "probability": 0.82, "intensity_range": [45.1, 68.3],
    "confidence": "HIGH", "forecast_failure_risk": "LOW"
  }],
  "thresholds_note": "Configurable prototype thresholds — not official IMD/NCMRWF warnings."
}
```

### `GET /api/v1/regimes`
Weather regime per location + transition probability.

```json
{
  "items": [{ "current_regime": "MONSOON", "transition_probability": 0.23, ... }],
  "note": "Operational regime classes for adaptive model weighting — not official classifications."
}
```

### `GET /api/v1/model-health`
Health score, status, reasons, weight adjustment per model.

---

## Simulation & provenance

### `POST /api/v1/simulations/counterfactual`
Run a counterfactual scenario. **Never modifies production state.**

```json
{
  "forecast_id": "...",
  "remove_models": ["nwp-mock-gfs-like"],
  "weight_boosts": {"ai-mock-emulator": 0.3},
  "strategy": "SKILL_WEIGHTED"
}
```

Response: `baseline_forecast`, `scenario_forecast`, `forecast_delta`, `scenario_weights`, `production_mutated: false`.

### `GET /api/v1/provenance/{forecast_id}`
Full data lineage: input models, timestamps, versions, weights, calibration/blending versions.

---

## Overview & system

### `GET /api/v1/overview`
KPIs: active models, blended locations, FRS, disagreement, models degraded, highest-risk event.

### `GET /api/v1/timeseries`
Multi-model time series at a location. Query: `location_id`, `variable`.

### `GET /api/v1/system`
Infrastructure health, pipeline jobs, alerts, queue status.

### `GET /api/v1/data-hub`
Forecast source status, variables, quality, coverage.

### `POST /api/v1/data-hub/import`
Import hook (prototype stub). Body: `{ "format": "CSV", "payload": ... }`.

### `GET /api/v1/ml/registry`
Trust meta-model registry (MLflow integration).

---

## Admin (demo only)

### `POST /api/v1/admin/seed`
Seed / re-seed the demonstration benchmark database.

### `POST /api/v1/admin/learn`
Trigger a synchronous continuous learning step (skill + health + blend + verification).

---

## WebSocket

### `WS /api/v1/ws`
Live channel for forecast updates, health changes, event alerts, pipeline status.

```js
const ws = new WebSocket("ws://localhost:8000/api/v1/ws");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## Error format

```json
{ "detail": "forecast not found — seed demo data first" }
```

HTTP 404 for missing resources. HTTP 500 with `request_id` for server errors.

## Headers

| Header | Direction | Value |
|---|---|---|
| `x-request-id` | Response | UUID per request |
| `x-aeris-data-mode` | Response | `demonstration` or `operational` |
