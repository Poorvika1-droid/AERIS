<div align="center">

```
 █████╗ ███████╗██████╗ ██╗███████╗
██╔══██╗██╔════╝██╔══██╗██║██╔════╝
███████║█████╗  ██████╔╝██║███████╗
██╔══██║██╔══╝  ██╔══██╗██║╚════██║
██║  ██║███████╗██║  ██║██║███████║
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚══════╝
```

### Adaptive Ensemble & Regime Intelligence System
### *When weather changes, trust must adapt.*

[![SIH 2026](https://img.shields.io/badge/SIH_2026-PS_26081-cyan?style=for-the-badge)](.)
[![MoES · NCMRWF](https://img.shields.io/badge/MoES-NCMRWF-blue?style=for-the-badge)](.)
[![Disaster Management](https://img.shields.io/badge/Theme-Disaster_Management-red?style=for-the-badge)](.)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square)](.)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square)](.)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)](.)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?style=flat-square)](.)

</div>

---

## The Problem No One Is Solving

Operational weather forecasting in India generates **competing signals from multiple NWP models, AI emulators, and ensemble systems** — each with different strengths across regions, seasons, lead times, and atmospheric regimes. Decision-makers today must either:

- Pick one model and ignore the others, or
- Average them blindly, hiding disagreement

Both approaches fail silently. A confident-looking forecast can still be **fragile** — not because the value is wrong, but because the underlying trust is misplaced.

> **AERIS answers the question no existing system does:**  
> *"Which forecast source should be trusted, by how much, for which place, lead time, and atmospheric regime — right now?"*

---

## What AERIS Actually Does

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTEXT-AWARE FORECAST TRUST ENGINE                      │
│                                                                             │
│  INPUTS          INTELLIGENCE LAYER              DECISION PRODUCTS          │
│                                                                             │
│  NWP models ──►  ┌──────────────────┐  ──────►  Blended forecast value     │
│  AI models  ──►  │  Harmonise &     │           Forecast Reliability Score  │
│  Ensembles  ──►  │  Quality Control │  ──────►  Uncertainty interval        │
│  Stations   ──►  └────────┬─────────┘           Model disagreement flag     │
│  Satellite  ──►           │                     Extreme event intelligence  │
│  Radar      ──►  ┌────────▼─────────┐  ──────►  Explainability (WHY)       │
│                  │  Context Engine  │           Counterfactual simulation   │
│                  │  Regime · Season │                                       │
│                  │  Lead · Region   │  ──────►  Continuous learning loop    │
│                  └────────┬─────────┘           (skill → weights → better)  │
│                           │                                                 │
│                  ┌────────▼─────────┐                                       │
│                  │  Skill Memory    │  Rolling 7d · 30d · 90d · seasonal    │
│                  │  + Health Mon.   │  MAE · RMSE · CSI · Brier · CRPS      │
│                  └────────┬─────────┘                                       │
│                           │                                                 │
│                  ┌────────▼─────────┐                                       │
│                  │  Dynamic Trust   │  Non-negative weights · sum = 1       │
│                  │  Engine          │  Gaussian spatial smoothing           │
│                  └────────┬─────────┘                                       │
│                           │                                                 │
│                  ┌────────▼─────────┐                                       │
│                  │  Adaptive Blend  │  CONTEXTUAL_ML · SKILL_WEIGHTED       │
│                  │  + FRS + Events  │  BAYESIAN_AVERAGE · EVENT_SPECIFIC    │
│                  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### End-to-End Intelligence Pipeline

```mermaid
flowchart TD
    subgraph INPUTS["📡 Forecast Inputs"]
        A1[NWP · GFS / ECMWF / NCMRWF]
        A2[AI / ML Emulators]
        A3[Ensemble Systems]
        A4[Station Observations]
        A5[Satellite · Radar]
    end

    subgraph INGEST["🔄 Harmonisation & QC"]
        B1[Unit & grid alignment]
        B2[Quality control flags]
        B3[Bias correction hooks]
        B4[Adapter pattern — plug any source]
    end

    subgraph CONTEXT["🧠 Context Engine"]
        C1[Weather regime classifier]
        C2[Season · lead time · region]
        C3[Transition probability]
        C4[Anomaly detection]
    end

    subgraph TRUST["⚖️ Trust Engine"]
        D1[Skill memory — rolling MAE/RMSE/CSI]
        D2[Model health monitor]
        D3[Inter-model disagreement]
        D4[Dynamic weight solver]
    end

    subgraph BLEND["🌀 Adaptive Blending"]
        E1[Contextual ML blend]
        E2[Spatial smoothing]
        E3[Uncertainty quantification]
        E4[FRS computation]
    end

    subgraph OUTPUT["📊 Decision Products"]
        F1[Blended forecast + interval]
        F2[Forecast Reliability Score]
        F3[Extreme event cards]
        F4[Explainable attribution]
        F5[Counterfactual lab]
    end

    subgraph LEARN["🔁 Learning Loop"]
        G1[Verification · obs vs forecast]
        G2[Skill update]
        G3[Weight recalibration]
    end

    INPUTS --> INGEST
    INGEST --> CONTEXT
    INGEST --> TRUST
    CONTEXT --> TRUST
    TRUST --> BLEND
    BLEND --> OUTPUT
    OUTPUT --> LEARN
    LEARN --> TRUST
```

### Technical Stack Architecture

```mermaid
flowchart LR
    subgraph WEB["🖥️ Next.js Console"]
        W1[15 dashboard pages]
        W2[MapLibre GL India GIS]
        W3[Recharts visualizations]
        W4[TanStack Query]
        W5[Auth guard · session]
    end

    subgraph API["⚡ FastAPI Backend"]
        A1[27 REST endpoints]
        A2[WebSocket live feed]
        A3[Pydantic v2 validation]
        A4[Structured JSON logging]
        A5[Request tracing]
    end

    subgraph ENGINE["🔬 Intelligence Engines"]
        E1[Trust engine · pipeline.py]
        E2[Regime classifier]
        E3[Health monitor]
        E4[Verification engine]
        E5[Extreme event detector]
        E6[Counterfactual simulator]
    end

    subgraph STORE["💾 Persistence"]
        S1[(SQLite — demo)]
        S2[(MySQL — production)]
        S3[Redis · Celery queue]
        S4[MLflow artifacts]
    end

    WEB -->|HTTP / WS| API
    API --> ENGINE
    ENGINE --> STORE
    STORE --> ENGINE
```

### Decision Flow for Every Forecast

```mermaid
flowchart TD
    START([Location · Variable · Lead time]) --> SOURCES

    SOURCES[Collect all forecast sources] --> REGIME

    REGIME{What is the\natmospheric regime?}
    REGIME -->|MONSOON| M1[Boost NWP synoptic skill\nMonitor heavy-rain CSI]
    REGIME -->|CONVECTIVE| M2[Boost AI short-lead weight\nCSI + Brier objective]
    REGIME -->|TRANSITION| M3[Boost ensemble ×1.15\nReduce FRS regime certainty]
    REGIME -->|NORMAL| M4[Standard contextual weights]

    M1 & M2 & M3 & M4 --> HEALTH

    HEALTH{Model health check}
    HEALTH -->|HEALTHY ≥ 80| H1[Full weight contribution]
    HEALTH -->|WARNING 60–79| H2[Reduced multiplier applied]
    HEALTH -->|DEGRADED < 60| H3[Significant weight reduction\nOthers compensate]

    H1 & H2 & H3 --> WEIGHTS

    WEIGHTS[Dynamic non-negative weights\nsum = 1 · spatially smoothed] --> BLEND

    BLEND[Weighted blend\n+ uncertainty quantification] --> FRS

    FRS[Compute Forecast Reliability Score\nSkill · health · agreement ·\nregime certainty · obs consistency] --> OUTPUT

    OUTPUT([Forecast value · interval · FRS\nDisagreement · failure risk · WHY])
```

### Continuous Learning Loop

```mermaid
sequenceDiagram
    participant T as Trust Engine
    participant B as Blending Engine
    participant O as Observations
    participant S as Skill Memory
    participant W as Weight Solver

    T->>B: Dynamic weights (t=0)
    B->>B: Produce blended forecast
    Note over B: Forecast value + FRS + uncertainty

    O->>S: Observed weather arrives
    S->>S: Compute MAE · RMSE · bias · CSI\nper model × region × lead × regime

    S->>W: Updated skill scores
    W->>W: Recalibrate weights\n(rolling 7d · 30d · 90d)
    W->>T: New trust weights (t+1)

    Note over T,W: Cycle repeats every learning step\nNo huge model retraining per obs
```

---

## Why AERIS Is Different

| Capability | AERIS | Static average | Single model |
|---|:---:|:---:|:---:|
| Context-aware trust weights | ✅ | ❌ | ❌ |
| Regime-adaptive blending | ✅ | ❌ | ❌ |
| Model health monitoring | ✅ | ❌ | ❌ |
| Forecast Reliability Score | ✅ | ❌ | ❌ |
| Explainable weight attribution | ✅ | ❌ | ❌ |
| Counterfactual simulation lab | ✅ | ❌ | ❌ |
| Continuous skill learning loop | ✅ | ❌ | ❌ |
| Extreme-event-aware objectives | ✅ | ❌ | ❌ |
| Spatially coherent weight fields | ✅ | ❌ | ❌ |
| Plug-and-play adapter pattern | ✅ | ❌ | ❌ |
| Forecast uncertainty ≠ confidence ≠ FRS | ✅ | ❌ | ❌ |

---

## 6 Core Differentiators

### 01 · Context-Aware Dynamic Weighting
Trust is not static. Every weight is a function of:

```
weight(model, location, lead, t) = f(
    region,           # NE India ≠ peninsular coast
    season,           # monsoon dynamics differ
    lead_time,        # AI leads short, NWP leads long
    weather_regime,   # MONSOON · CONVECTIVE · HEATWAVE · …
    skill_history,    # rolling MAE / CSI over 30d
    model_health,     # completeness · delay · outlier rate
    disagreement      # inter-model spread signal
)
```

### 02 · Model Health Monitoring

```
Health score (0–100) tracks:
  ├── Field completeness ratio
  ├── Run delay (minutes late)
  ├── Value outlier rate (z-score threshold)
  ├── Distribution shift (KL divergence proxy)
  └── Verification degradation (rolling RMSE trend)

→ HEALTHY (≥ 80): full weight pass-through
→ WARNING  (60–79): weight × 0.85 adjustment
→ DEGRADED (< 60):  weight × 0.50, others compensate
```

### 03 · Forecast Disagreement Intelligence

```
Inter-model disagreement score ∈ [0, 1]

  0.0 ──────────────────────────── 1.0
  Full agreement           Maximum spread

When disagreement > threshold:
  → Ensemble weight boosted
  → FRS regime certainty component reduced
  → Disagreement surfaced as visible signal (not hidden)
```

### 04 · Extreme-Event-Aware Blending

```
Normal weather objective:  minimize MAE + RMSE
Extreme event objective:   maximize CSI + recall + Brier score

Thresholds (configurable):
  Heavy rainfall  ≥ 50 mm / 24h
  Heatwave        ≥ 40°C
  High wind       ≥ 12 m s⁻¹
```

### 05 · Forecast Reliability Score (FRS)

```
FRS = weighted combination of 6 components (0–100)

  Historical skill        0.25  ←── Rolling MAE/CSI
  Inter-model agreement   0.20  ←── Disagreement score
  Model health            0.15  ←── Health monitor
  Regime certainty        0.15  ←── Regime confidence
  Observation consistency 0.15  ←── Bias stability
  Forecast stability      0.10  ←── Run-to-run change

FRS ≥ 80 → HIGH reliability
FRS 60–79 → MODERATE
FRS < 60  → LOW — decision support strongly advised
```

### 06 · Continuous Self-Learning

```
Forecast ──► Observation ──► Error analysis ──► Skill update
   ▲                                                  │
   └──────────── Weight recalibration ◄───────────────┘

Windows: 7d (recent) · 30d (rolling) · 90d (seasonal) · historical
No retraining per observation — meta-model retrained on schedule
```

---

## Console Walkthrough

| Page | URL | What it demonstrates |
|---|---|---|
| 🏠 Landing | `/` | Mission, system story, sign-in |
| 🔐 Login | `/login` | Office-style auth with demo credentials |
| ⚡ AERIS Flow | `/architecture` | Full input-to-decision visual story |
| 📊 Overview | `/overview` | National KPIs, map, model contribution pie |
| 🌧 Forecast Explorer | `/forecast` | NWP vs AI vs ensemble vs AERIS comparison |
| 🗺 India GIS | `/gis` | 5 spatial layers: value · FRS · disagreement · risk · dominant |
| ⚖️ Weight Maps | `/weights` | Spatially smoothed trust weight fields |
| 💚 Model Health | `/model-health` | Health gauges, skill heatmap, weight adjustment |
| 🌀 Regimes | `/regimes` | 9 regime classes, transition probabilities |
| 🚨 Extreme Events | `/events` | Heavy rain · heatwave · high wind intelligence |
| 📉 Uncertainty & FRS | `/uncertainty` | FRS gauge, components, interval across leads |
| 🧪 Counterfactual Lab | `/lab` | Remove model · adjust weights · compare strategies |
| ✅ Verification | `/verification` | MAE/RMSE bar, lead chart, multi-metric radar |
| 🗄 Data Hub | `/data` | Source registry, adapter status, import hook |
| 📦 Model Registry | `/registry` | MLflow integration, skill table, meta-model |
| 🖥 System Health | `/system` | API · DB · Redis · pipeline jobs · alerts |
| 🔌 API / Integration | `/integration` | 27 REST endpoints, Swagger, WebSocket |
| ℹ About | `/about` | Methodology, differentiators, honest limitations |

---

## 🚀 Live Demo

| Service | URL |
|---|---|
| **Frontend (Web Console)** | https://aeris-1-iy0y.onrender.com |
| **Backend (API)** | https://aeris-t3ji.onrender.com |
| **API Docs (Swagger)** | https://aeris-t3ji.onrender.com/docs |

**Login:** `demo@aeris.local` / `aeris-demo-2026`

> After login, go to **Overview** and click **"Load / refresh demo data"** to seed all benchmark data.

> ⚠️ Free tier — first load may take 30–60 seconds to wake up.

---

## Quick Start

### Option 1 — Local SQLite (no services needed)

**Terminal 1 — Backend API:**
```bash
cd apps/api

# Install dependencies
pip install fastapi uvicorn[standard] sqlalchemy pymysql pydantic pydantic-settings \
    numpy pandas scikit-learn scipy xgboost xarray netCDF4 python-multipart httpx

# Start API (SQLite auto-created at data/aeris.db)
DATABASE_URL="sqlite:///../../data/aeris.db" \
AERIS_DATA_MODE=demonstration \
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd apps/web
npm install
npm run dev
```

**Open:** http://localhost:3000  
**Login:** `demo@aeris.local` / `aeris-demo-2026`  
**API docs:** http://127.0.0.1:8000/docs

> **First step after login:** go to **Overview** and click **"Load / refresh demo data"** to seed the benchmark universe.

---

### Option 2 — Full stack with Docker Compose

```bash
cp .env.example .env
docker compose -f infra/docker/docker-compose.yml up --build
```

| Service | URL |
|---|---|
| Web console | http://localhost:3000 |
| API + Swagger | http://localhost:8000 / http://localhost:8000/docs |
| MLflow | http://localhost:5001 |
| MySQL | localhost:3306 |
| Redis | localhost:6379 |

---

### Option 3 — MySQL (production-style)

**MySQL setup (run as admin):**
```sql
CREATE DATABASE aeris CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aeris'@'localhost' IDENTIFIED BY 'aeris';
GRANT ALL PRIVILEGES ON aeris.* TO 'aeris'@'localhost';
FLUSH PRIVILEGES;
```

**Start API with MySQL:**
```bash
DATABASE_URL="mysql+pymysql://aeris:aeris@localhost:3306/aeris" \
AERIS_DATA_MODE=demonstration \
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Both SQLite and MySQL are fully supported. Tables are auto-created on first start.

---

## Database Schema

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ forecast_sources│    │   forecast_runs   │    │  forecast_values   │
│─────────────────│    │──────────────────│    │────────────────────│
│ id (PK)         │◄───│ model_id (FK)    │◄───│ run_id (FK)        │
│ model_name      │    │ initialization_t  │    │ location_id (FK)   │
│ provider        │    │ lead_time_hours   │    │ value              │
│ model_type      │    │ variable          │    │ qc_flags           │
│ status          │    │ valid_time        │    └────────────────────┘
│ variables JSON  │    └──────────────────┘
└─────────────────┘
        │
        ▼
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   locations     │    │ blended_forecasts │    │uncertainty_metrics │
│─────────────────│    │──────────────────│    │────────────────────│
│ id (PK)         │◄───│ location_id (FK) │◄───│ forecast_id (FK)   │
│ name            │    │ variable          │    │ frs                │
│ latitude        │    │ lead_time_hours   │    │ ensemble_spread    │
│ longitude       │    │ value             │    │ disagreement_score │
│ region          │    │ dominant_model    │    │ failure_risk       │
│ elevation_m     │    │ data_mode         │    │ frs_components JSON│
└─────────────────┘    └──────────────────┘    └────────────────────┘

┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  dynamic_weights│    │   model_skill    │    │   model_health     │
│─────────────────│    │──────────────────│    │────────────────────│
│ forecast_id     │    │ model_id          │    │ model_id           │
│ location_id     │    │ region            │    │ health_score 0–100 │
│ weights JSON    │    │ variable          │    │ health_status      │
│ strategy        │    │ lead_time_bin     │    │ health_reasons JSON│
│ regime          │    │ season / regime   │    │ weight_adjustment  │
└─────────────────┘    │ mae/rmse/csi/bias │    └────────────────────┘
                       └──────────────────┘

┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ weather_regimes │    │  extreme_events  │    │verification_results│
│─────────────────│    │──────────────────│    │────────────────────│
│ location_id     │    │ event_type        │    │ model_id           │
│ current_regime  │    │ location_id       │    │ variable           │
│ cluster_id      │    │ probability       │    │ lead_time_hours    │
│ features JSON   │    │ confidence        │    │ mae/rmse/bias/crps │
└─────────────────┘    │ failure_risk      │    │ csi/brier/f1       │
                       └──────────────────┘    └────────────────────┘

Total: 23 tables · Full SQLAlchemy ORM · WAL-mode SQLite · MySQL 8.0+
```

---

## API Surface

```
Method  Endpoint                              Description
──────  ────────────────────────────────────  ─────────────────────────────────────
GET     /api/v1/health                        API + DB + Redis health + latency
GET     /api/v1/meta                          Product identity + core messages
GET     /api/v1/overview                      KPIs · contribution · highest-risk event
GET     /api/v1/models                        All registered forecast sources
GET     /api/v1/models/{id}                   Single model: health + skill + metadata
GET     /api/v1/locations                     All locations (filterable)
GET     /api/v1/forecast                      Blended forecast for location+var+lead
POST    /api/v1/forecast/blend                Trigger blend for specific request
GET     /api/v1/forecast/skill-lead           MAE vs lead time per model (chart)
GET     /api/v1/forecast/uncertainty-series   Uncertainty interval across lead times
GET     /api/v1/weights                       Dynamic trust weights — all locations
GET     /api/v1/weights/history               Weight evolution across lead times
GET     /api/v1/reliability                   FRS for all locations
GET     /api/v1/disagreement                  Inter-model disagreement scores
GET     /api/v1/extremes                      Extreme events (rain/heat/wind)
GET     /api/v1/regimes                       Regime per location + transition prob
GET     /api/v1/verification                  Overall verification metrics per model
GET     /api/v1/verification/by-lead          MAE by lead time per model
GET     /api/v1/skill                         Rolling skill memory — full table
GET     /api/v1/skill/heatmap                 MAE grid: model × lead time
GET     /api/v1/model-health                  Health score + status + reasons
POST    /api/v1/simulations/counterfactual    Counterfactual: remove · boost · compare
GET     /api/v1/provenance/{id}               Full data lineage for a forecast
GET     /api/v1/timeseries                    Multi-model time series at location
GET     /api/v1/ml/registry                   Trust meta-model registry (MLflow)
GET     /api/v1/system                        Infrastructure · jobs · alerts
GET     /api/v1/data-hub                      Source status · variables · quality
POST    /api/v1/data-hub/import               Import hook (CSV · JSON · NetCDF)
POST    /api/v1/admin/seed                    Seed demonstration benchmark data
POST    /api/v1/admin/learn                   Trigger continuous learning step
WS      /api/v1/ws                            Live forecast / health / event feed
```

Interactive docs: **http://localhost:8000/docs** (Swagger UI) · **http://localhost:8000/redoc** (ReDoc)

---

## Technology Stack

### Backend
| Library | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime |
| FastAPI | 0.115 | REST API + WebSocket |
| SQLAlchemy | 2.0 | ORM + migrations |
| Pydantic v2 | 2.7 | Validation + serialization |
| PyMySQL | 1.1 | MySQL driver |
| NumPy | 1.26 | Numerical core |
| pandas | 2.2 | Data manipulation |
| scikit-learn | 1.5 | ML utilities |
| XGBoost | 2.1 | Meta-model trust learner |
| SciPy | 1.13 | Statistical methods |
| xarray | 2024.6 | NetCDF / gridded data |
| MLflow | 2.14 | Experiment tracking + model registry |
| Redis | 5.0 | Cache + Celery broker |
| Celery | 5.4 | Async pipeline jobs |

### Frontend
| Library | Version | Role |
|---|---|---|
| Next.js | 16 | React framework + routing |
| React | 19 | UI runtime |
| TypeScript | 5.7 | Type safety |
| Tailwind CSS | 3.4 | Styling |
| MapLibre GL | 6.11 | India GIS map |
| Recharts | 2.15 | Charts + visualizations |
| TanStack Query | 5.62 | Data fetching + cache |
| Framer Motion | 11 | Animations |
| Lucide React | 0.468 | Icons |
| Zod | 3.24 | Schema validation |

### Infrastructure
| Component | Role |
|---|---|
| SQLite | Local development (WAL mode, no services needed) |
| MySQL 8.0 | Production / Docker Compose deployment |
| Redis | Celery broker + result backend |
| MLflow | Model versioning + artifact registry |
| Docker Compose | Full-stack containerised deployment |
| GitHub Actions | CI pipeline (typecheck + lint) |

---

## Repository Map

```
AERIS/
├── apps/
│   ├── api/                    FastAPI backend
│   │   └── app/
│   │       ├── main.py         App factory, lifespan, middleware
│   │       ├── config.py       Settings (SQLite / MySQL, env vars)
│   │       ├── db.py           SQLAlchemy engine (WAL-mode SQLite fix)
│   │       ├── models.py       23 ORM table definitions
│   │       ├── routers.py      30 API endpoints + WebSocket
│   │       └── pipeline.py     Trust engine: seed · blend · verify · learn
│   │
│   └── web/                    Next.js frontend
│       └── src/
│           ├── app/            15 pages (overview · forecast · gis · …)
│           ├── components/     Shell · IndiaMap · Providers (auth guard)
│           └── lib/            API client · cn utility
│
├── services/
│   ├── blending/               Context-aware dynamic weighting
│   ├── regime/                 Weather regime intelligence
│   ├── model_health/           Health scoring
│   ├── verification/           Forecast verification + skill memory
│   └── extreme_events/         Event object generation
│
├── packages/
│   ├── schemas/                Shared Pydantic / TypeScript types
│   └── shared/                 Common metric utilities
│
├── infra/docker/               Docker Compose + Dockerfiles
├── ml/                         Training scripts + model artifacts
├── data/                       SQLite DB + processed datasets
├── docs/                       Architecture · methodology · deployment
├── tests/                      pytest test suite
└── .github/workflows/          CI (typecheck · lint · test)
```

---

## Verification & Honesty

### What the benchmark numbers mean

The seeded demonstration uses **deterministic synthetic ensembles** with a controlled error hierarchy:

```
Short lead (6–24h):    AI emulator skill  > NWP  > ensemble mean
Long lead  (48–120h):  NWP skill          > AI   > ensemble mean
Monsoon regime:        NWP synoptic       > AI convective
Convective regime:     AI                 > NWP  > ensemble

AERIS blend consistently below all individuals → adaptive weighting advantage
Static equal-weight blend is the comparison baseline
```

These are **reproducible, deterministic benchmark numbers** — not operational NCMRWF forecast accuracy claims.

### Scientific honesty

| What AERIS IS | What AERIS IS NOT |
|---|---|
| ✅ A prototype blending framework for NCMRWF integration | ❌ Not deployed at NCMRWF or any operational centre |
| ✅ Demonstration of context-aware dynamic weighting | ❌ Not trained on real NCMRWF operational archives |
| ✅ Architecture designed for operational-scale extension | ❌ Not endorsed by MoES or IMD |
| ✅ Open, reproducible benchmark for ensemble blending | ❌ Benchmark metrics are not real operational accuracy |
| ✅ Horizontally scalable: Docker → Kubernetes path | ❌ FRS is not a universal scientific metric |

---

## 5-Minute Demonstration Path

```
1. Visit http://localhost:3000
2. Sign in → demo@aeris.local / aeris-demo-2026
3. Overview  ──► Click "Load demo data" ──► watch map populate
4. Forecast Explorer ──► Select Chennai · RAINFALL · 48h
                     ──► See NWP vs AI vs Ensemble vs AERIS
                     ──► Note disagreement, dominant model, WHY panel
5. India GIS ──► Switch layers: FRS · disagreement · failure risk
6. Regimes   ──► See MONSOON vs CONVECTIVE regime map
7. Extreme Events ──► Click a heavy rainfall event ──► see model attribution
8. Lab ──► Remove NWP ──► run simulation ──► weight delta chart
9. Verification ──► Radar chart ──► AERIS clearly below all individuals
10. System ──► Click "Run learning step" ──► pipeline completes in ~250ms
```

---

## Running Tests

```bash
# Backend tests (no seed required)
AERIS_SKIP_SEED_TESTS=1 python -m pytest tests -q

# Frontend typecheck
cd apps/web && npm run typecheck

# Frontend lint
cd apps/web && npm run lint
```

---

## Operational Path

AERIS is architecture-ready for real deployment:

```
Demo (now)                  Production extension
────────────────────────    ──────────────────────────────────────────
MockNWPAdapter          ──► RealNWPAdapter  (NWP_BASE_URL + API_KEY)
MockAIAdapter           ──► RealAIAdapter   (model endpoint)
MockEnsembleAdapter     ──► RealEnsAdapter  (TIGGE / ECMWF ENS)
MockObservationAdapter  ──► RealObsAdapter  (IMD station feed)
SQLite                  ──► MySQL / PostgreSQL
Celery demo mode        ──► Celery + Redis + Airflow DAG schedule
Docker Compose          ──► Kubernetes Helm chart
Single node             ──► Horizontally scaled (stateless workers)

No blending engine change required.
Every adapter implements BaseForecastAdapter.
New models auto-register and are evaluated before production use.
```

---

## Environment Variables

```bash
# Core
AERIS_ENV=demo
AERIS_DATA_MODE=demonstration          # demonstration | real_IMD | operational
SECRET_KEY=change-me-in-production
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Database (choose one)
DATABASE_URL=sqlite:///./data/aeris.db
DATABASE_URL=mysql+pymysql://aeris:aeris@localhost:3306/aeris

# Queue (optional in demo)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# MLflow (optional)
MLFLOW_TRACKING_URI=http://localhost:5001
MLFLOW_EXPERIMENT=aeris-trust-engine

# Operational adapters (leave empty in demo)
NWP_BASE_URL=
NWP_API_KEY=
OBS_BASE_URL=
OBS_API_KEY=

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_DATA_MODE=demonstration
```

---

## Acknowledgements

Built for **Smart India Hackathon 2026 · Problem Statement 26081**  
Organisation: **Ministry of Earth Sciences (MoES) · NCMRWF**  
Theme: **Disaster Management**

> *"One forecast is not always enough. The best model changes with context.  
> AERIS learns when, where, and why each model should be trusted.  
> Forecast uncertainty is information, not a failure.  
> Every verified forecast improves future model trust."*

---

<div align="center">

**Prototype · Demonstration / Benchmark Data · Not NCMRWF operational deployment**

</div>
