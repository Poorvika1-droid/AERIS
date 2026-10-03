from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "schemas"))
sys.path.insert(0, str(ROOT / "packages" / "shared"))

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import Location
from app.pipeline import seed_universe
from app.routers import router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("aeris")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    log.info("AERIS API started data_mode=%s", settings.aeris_data_mode)

    yield


app = FastAPI(
    title="AERIS API",
    description="Context-Aware Forecast Trust Engine — prototype for SIH 2026 PS 26081. Demonstration data unless operational adapters are configured.",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "core", "description": "Health, forecast intelligence, blending"},
    ],
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id", str(uuid.uuid4()))
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        log.exception("request_failed", extra={"request_id": rid})
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "request_id": rid, "detail": "Prototype error — see logs"},
        )
    ms = round((time.perf_counter() - t0) * 1000, 2)
    log.info(
        json.dumps(
            {
                "msg": "request",
                "request_id": rid,
                "path": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "latency_ms": ms,
            }
        )
    )
    response.headers["x-request-id"] = rid
    response.headers["x-aeris-data-mode"] = settings.aeris_data_mode
    return response


app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": "AERIS", "docs": "/docs", "health": "/api/v1/health"}
