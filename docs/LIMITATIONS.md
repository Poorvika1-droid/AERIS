# AERIS Limitations

## Data

- **No real operational data.** All forecasts, observations, and metrics are from seeded synthetic ensembles. The error hierarchy (AI stronger short-lead, NWP stronger large-scale) is deliberately injected to demonstrate adaptive blending — it does not represent real NWP vs AI model performance.
- **No real NCMRWF archives.** Comparison metrics are from a deterministic benchmark, not actual archive data.
- **Limited location coverage.** Prototype uses ~20 major Indian cities + a coarse ~100-point grid. Production would require full India grid at ≥ 0.25° resolution.
- **Single valid time.** The prototype blends at a single initialization time (2026-07-15 00Z). Multi-cycle rolling blending requires additional pipeline work.

## Models

- **Mock adapters only.** `MockNWPAdapter`, `MockAIAdapter`, `MockEnsembleAdapter` generate synthetic forecasts from a climatological function with injected noise. They are not real NWP model outputs.
- **No real AI model.** No foundation weather model (Pangu, GraphCast, FourCastNet) is integrated. The AI adapter is a placeholder demonstrating the adapter pattern.
- **3 models only.** Production deployment would require at minimum: GFS, ECMWF, NCMRWF-TIGGE, and one or more AI models.

## Algorithms

- **KMeans regime clustering on synthetic data.** The regime detector is fit on features derived from synthetic observations, not on historical Indian meteorological records. Cluster boundaries are not validated.
- **Heuristic contextual prior (not a trained meta-model).** `CONTEXTUAL_ML` strategy uses a hand-coded heuristic, not a trained XGBoost/LightGBM model. Sufficient labeled operational data does not exist in this prototype.
- **Gaussian interval approximation.** Prediction intervals use a Gaussian spread approximation, not rigorous ensemble quantiles. Intervals are indicative only.
- **FRS component weights are uncalibrated.** The (0.25, 0.15, 0.20, 0.15, 0.15, 0.10) weights in FRS are prototype defaults, not validated by observational studies.
- **No bias correction.** Bias correction hooks exist in the harmonization layer but are populated with zero corrections in the prototype.
- **CRPS approximation.** The CRPS implementation is a simplified empirical proxy, not exact Hersbach-style CRPS.

## Infrastructure

- **Celery worker optional in demo.** The continuous learning loop runs synchronously via `POST /api/v1/admin/learn`. Asynchronous job scheduling requires a running Celery worker.
- **MLflow optional.** MLflow logging is attempted at seed time and gracefully skipped if unreachable. No artifacts are stored in the prototype.
- **No spatial SQL queries.** The schema has latitude/longitude columns with indexes, but radius, polygon, and raster queries are not implemented.
- **Single-node only.** No sharding, no distributed Dask processing, no GPU inference.
- **SQLite for demo.** SQLite has limited concurrent-write support. Use MySQL for any multi-user or multi-worker deployment.

## Security

- **Auth disabled by default.** `AUTH_DISABLED=true` in `.env.example`. RBAC architecture exists but authentication middleware is a placeholder.
- **Rate limiting not wired.** Hook point exists; needs Redis-backed implementation for production.
- **No secrets management.** Environment variables used directly. Production requires a secrets manager (Vault, AWS Secrets Manager, etc.).

## Verification

- **No independent validation.** All verification metrics are computed on the same synthetic dataset used for training the heuristic. Independent holdout validation on real data has not been performed.
- **No statistical significance testing.** MAE differences between AERIS and individual models are not tested for statistical significance.

## What this prototype IS designed for

- Demonstrating the **architecture and interface design** for operational integration
- Showing the **adaptive weighting concept** with a controlled synthetic benchmark
- Providing a **clean codebase** that can be extended with real data adapters without architectural changes
- Facilitating **scientific discussion** of hybrid AI–NWP blending approaches
