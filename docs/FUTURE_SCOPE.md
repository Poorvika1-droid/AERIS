# AERIS Future Scope

The architecture is designed so all extensions below can be integrated without changing the core blending engine.

---

## Data sources

| Extension | Implementation path |
|---|---|
| NCMRWF operational NWP | Implement `RealNWPAdapter(base_url, api_key)` → wire `NWP_BASE_URL` + `NWP_API_KEY` |
| ECMWF HRES / ENS | New adapter class; register in `DEMO_ADAPTERS` equivalent |
| GFS, ICON, CFS | Same adapter pattern |
| AI weather models (Pangu, GraphCast, FourCastNet) | `MockAIAdapter` → real inference adapter |
| IMD station observations | Replace `MockObservationAdapter` with real station ingest |
| INSAT-3D satellite | Wire `SatelliteAdapter` stub |
| DWR radar | Wire `RadarAdapter` stub |
| Soil moisture (SMAP, GRACE) | Add `SoilMoistureAdapter`; extend context features |
| Ocean SST | Add SST context variable to `context_features()` |
| Topography (SRTM) | Add elevation-aware bias correction in harmonize layer |

---

## ML pipeline

| Extension | Notes |
|---|---|
| Trained XGBoost/LightGBM meta-model | Replace heuristic prior once operational labeled data available |
| SHAP attribution | Replace rule-based `shap_like` with `shap.TreeExplainer` |
| Online learning | Extend `learning_step()` with streaming weight updates (Vowpal Wabbit, River) |
| Transformer regime encoder | Replace KMeans with temporal attention model for regime detection |
| Calibration (Platt scaling, isotonic regression) | Improve probabilistic output reliability |
| Ensemble dressing | Convert deterministic model output to ensemble via statistical dressing |
| Neural blending | Replace linear weighted sum with shallow neural combiner |
| Optuna hyperparameter optimization | Wire `ml/training/train_trust.py` tuning loop |
| Automated retraining trigger | Detect drift → trigger retraining workflow (MLflow + Celery) |

---

## Infrastructure

| Extension | Notes |
|---|---|
| Kubernetes | Docker Compose → Helm chart; all services stateless |
| HPA (Horizontal Pod Autoscaler) | API and Celery workers scale independently |
| S3-compatible object storage | Zarr gridded data, MLflow artifacts, large forecast grids |
| Kafka / NATS streaming | Replace Celery ingestion tasks with streaming consumer |
| GPU inference | For AI weather model integration; requires NVIDIA container runtime |
| Dask distributed processing | Enable when grid resolution → 0.1° (large arrays) |
| Prometheus + Grafana | Export structured metrics from existing logging |
| CDN / edge cache | Serve static forecast tiles from PMTiles / COG |

---

## Geospatial

| Extension | Notes |
|---|---|
| Full India grid (0.25° × 0.25°) | ~10,000 grid points; requires Zarr + xarray chunking |
| PostGIS spatial queries | ST_DWithin for location-aware queries; raster support |
| PMTiles / COG | Pre-rendered map tiles for large grids |
| District-level aggregation | Spatial JOIN with admin boundaries shapefile |
| Cyclone track overlay | Add cyclone track GeoJSON layer to GIS page |
| Flood inundation proxy | Combine rainfall + DEM for simple inundation indicator |

---

## Decision support

| Extension | Notes |
|---|---|
| Automated alert API | Push event objects to disaster management systems via webhook |
| District-level impact assessment | Combine extreme event probability with exposure/vulnerability data |
| Forecast PDF / report export | Generate operational briefing PDFs from dashboard |
| Multi-language UI | Hindi + regional languages for district-level users |
| Mobile-responsive dashboard | Current layout is desktop-first |
| Offline-capable PWA | Service worker for field use without connectivity |

---

## Governance & operations

| Extension | Notes |
|---|---|
| Full authentication | Enable JWT-based auth; implement RBAC roles |
| Audit trail | Every weight decision logged with full provenance |
| Model validation workflow | New model → benchmark evaluation → staged rollout |
| A/B testing framework | Compare blending strategies in production splits |
| National Weather Intelligence Fabric | Regional AERIS instances federated under a national API gateway |
| Digital twin integration | AERIS as the forecast intelligence layer in a broader climate digital twin |

---

## Academic future work

- Validation on historical Indian extreme events (1979–present reanalysis)
- Comparison of AERIS blending vs. BMA (Bayesian Model Averaging) and EMOS
- Statistical significance testing of skill improvements
- Evaluation of FRS as a forecast quality proxy on real observations
- Regime classification accuracy vs. established Indian climate indices (ISMR, IOD, ENSO)
- Publication of the adaptive weighting methodology
