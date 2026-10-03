# Existing website audit

## Current state

The existing application is retained: Next.js frontend in `apps/web`, FastAPI API in `apps/api`, and blending/verification services in `services`. It is a demonstration application by design, not an operational forecast product.

## Production-path findings

- `services/ingestion/adapters.py` contains `MockNWPAdapter`, `MockAIAdapter`, `MockEnsembleAdapter`, and `MockObservationAdapter`; each synthesizes values with random noise and marks payloads as demo.
- `apps/api/app/pipeline.py` seeds these adapters and marks forecast provenance and event payloads as demonstration.
- `scripts/train_aeris_real.py` was unsafe: its feature schema included observations and verification error fields, and it selected via `GroupKFold`. It is now hard-blocked.
- `RUN_AERIS_REAL.cmd` no longer starts the API in `real_IMD` mode. It starts explicit `demonstration` mode until a validated frozen model and real ingestion source are registered.

## Decision

No current dashboard value, confidence score, source weight, event probability, or verification metric may be represented as live or operational. The user interface can remain useful as a clearly labelled demo/replay shell, but real API integration is blocked pending validated source contracts, provenance, and a frozen causal model.
