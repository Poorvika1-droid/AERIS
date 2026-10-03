# AERIS Deployment Guide

## Mode A — Docker Compose (recommended for demo/prototype)

### Prerequisites
- Docker Desktop ≥ 24 with Compose plugin
- 4 GB RAM, 10 GB disk

### Start

```bash
git clone <repo> aeris && cd aeris
cp .env.example .env
docker compose -f infra/docker/docker-compose.yml up --build
```

Services:

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | Next.js |
| API | http://localhost:8000 | FastAPI |
| API docs | http://localhost:8000/docs | Swagger UI |
| MLflow | http://localhost:5001 | Experiment tracking |
| MySQL | localhost:3306 | MySQL 8.4 |
| Redis | localhost:6379 | Cache + Celery broker |

### First-run behavior

On first startup, if the database is empty, the API auto-seeds the demonstration benchmark.  
This generates ~2,000 locations × 8 history days × 3 variables × 6 lead times of synthetic data — typically 30–90 seconds.

### Stop / reset

```bash
docker compose -f infra/docker/docker-compose.yml down
# Full reset (drops volumes):
docker compose -f infra/docker/docker-compose.yml down -v
```

---

## Mode B — Local development

### Backend

```bash
cd apps/api
pip install -r requirements.txt

# Start infra only
docker compose -f ../../infra/docker/docker-compose.yml up mysql redis mlflow -d

# Run API
DATABASE_URL=mysql+pymysql://aeris:aeris@localhost:3306/aeris \
REDIS_URL=redis://localhost:6379/0 \
AERIS_DATA_MODE=demonstration \
MLFLOW_TRACKING_URI=http://localhost:5001 \
uvicorn app.main:app --reload --port 8000
```

### Celery worker (optional in demo)

```bash
cd apps/api
celery -A app.celery_app.celery_app worker --loglevel=info
```

### Frontend

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## Mode C — Zero-dependency SQLite demo

```bash
cd apps/api
pip install -r requirements.txt

DATABASE_URL="sqlite:///$(pwd)/../../data/demo/aeris.db" \
AERIS_DATA_MODE=demonstration \
uvicorn app.main:app --port 8000
```

No Docker, no MySQL, no Redis needed. Redis features (Celery, WebSocket pub/sub) are unavailable.

---

## MySQL

For a MySQL server, install the API requirements (which include the PyMySQL
driver) and set `DATABASE_URL` before starting the API:

```bash
cd apps/api
DATABASE_URL="mysql+pymysql://aeris:password@localhost:3306/aeris" \
AERIS_DATA_MODE=demonstration \
uvicorn app.main:app --port 8000
```

Replace the example credentials, hostname, and database name. SQLite remains
available through its SQLAlchemy URL.

## Environment variables

Copy `.env.example` → `.env`. Never commit `.env`.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///.../data/aeris.db` | SQLite or MySQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery results |
| `AERIS_DATA_MODE` | `demonstration` | `demonstration` or `operational` |
| `MLFLOW_TRACKING_URI` | `http://localhost:5001` | MLflow server |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated frontend origins |
| `SECRET_KEY` | `change-me-in-any-non-demo-environment` | JWT secret (change for production) |
| `AUTH_DISABLED` | `true` | Set `false` to enable auth |
| `NWP_BASE_URL` | `` | Operational NWP endpoint |
| `NWP_API_KEY` | `` | Operational NWP key |

---

## Health checks

```bash
# API
curl http://localhost:8000/api/v1/health

# Frontend
curl http://localhost:3000

# Trigger demo data seed
curl -X POST http://localhost:8000/api/v1/admin/seed

# Run learning step
curl -X POST http://localhost:8000/api/v1/admin/learn
```

---

## Production considerations (future)

For a real operational deployment at NCMRWF scale:

1. **Use MySQL in production** — Docker Compose uses MySQL; SQLite is suitable for local/demo use only
2. **Configure auth** — set `AUTH_DISABLED=false`, configure RBAC roles
3. **Replace mock adapters** — implement `RealNWPAdapter` with `NWP_BASE_URL` + `NWP_API_KEY`
4. **Kubernetes** — each service is stateless and horizontally scalable; Docker Compose → Helm chart
5. **Celery beat scheduling** — replace manual `POST /admin/learn` with timed `continuous_learning` task
6. **MLflow server** — use a persistent artifact store (S3-compatible or NFS)
7. **Monitoring** — wire structured JSON logs to ELK / Grafana; expose `/metrics` endpoint for Prometheus

---

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` runs:
- `AERIS_SKIP_SEED_TESTS=1 python -m pytest tests/ -q` — fast tests only
- Frontend typecheck: `cd apps/web && npm ci && npm run typecheck`

Full seed tests require a database (SQLite is sufficient) and are run separately.
