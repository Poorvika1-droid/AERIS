# AERIS Demo Guide

## 5-minute demonstration flow

This is the recommended sequence for a live presentation or judging session.

---

### Step 1 — Start services

```bash
docker compose -f infra/docker/docker-compose.yml up --build
# Wait ~60 seconds for services to become healthy
# Open http://localhost:3000
```

Or if already running:
```
http://localhost:3000/overview
```

---

### Step 2 — Overview (1 min)

**Page:** `/overview`

Show:
- Demo data banner (bottom of screen) — proof of scientific honesty
- 8 KPI cards: active models, blended locations, FRS, disagreement, models degraded
- India rainfall 48h map — dots color-coded by dominant model (cyan=NWP, green=AI, violet=ensemble, red=high risk)
- Model contribution pie chart — dynamic weights, sum always = 1
- Weight evolution area chart — how NWP/AI/ensemble weights shift across 6h → 120h lead time
- Current major events list with risk colors

Click **"Load / refresh demo data"** if the page shows no data.

**Key message:** "One forecast is not always enough. The best model changes with context."

---

### Step 3 — Forecast Explorer (1 min)

**Page:** `/forecast`

Show:
- Select: RAINFALL / 48h / New Delhi
- AERIS blended value with dominant model and regime
- FRS (Forecast Reliability Score), confidence, disagreement, failure risk
- **"WHY THIS FORECAST?"** panel — model contribution bars with reasons
- Member comparison bar chart (NWP vs AI vs Ensemble vs AERIS)

Switch tab to **"Skill vs lead"** → shows MAE growing with lead time (NWP stronger long-lead, AI stronger short-lead — controlled error hierarchy).

**Key message:** "AI is historically stronger at short lead times under convective regimes."

---

### Step 4 — Weather Regimes (30 sec)

**Page:** `/regimes`

Show:
- India regime map — 9 operational classes color-coded
- Regime distribution pie
- Transition probability bar chart — locations with high transition probability

**Note:** "These are operational weighting classes, not official IMD/NCMRWF classifications."

---

### Step 5 — Model Health (30 sec)

**Page:** `/model-health`

Show:
- Three radial gauge charts (NWP, AI, Ensemble) — health scores
- One model showing WARNING or DEGRADED (deterministic demo degradation)
- Weight adjustment ×0.72 for the degraded model

**Key message:** "A degraded model's weight is automatically reduced before the blend."

---

### Step 6 — Dynamic Weight Maps (30 sec)

**Page:** `/weights`

Show:
- India map with dominant model color-coding
- Select: NWP dominant filter → see NWP regions
- Weight evolution line chart for New Delhi — NWP increases at 72h+, AI decreases

---

### Step 7 — Extreme Events (1 min)

**Page:** `/events`

Show:
- Heavy rainfall, heatwave, high wind summary cards with probabilities
- Event map — blue=rain, red=heat, yellow=wind
- Click a map point → see detail panel: probability, intensity range, primary model, failure risk

**Note:** "Prototype thresholds — not official warning thresholds. Configurable."

---

### Step 8 — Uncertainty & FRS (30 sec)

**Page:** `/uncertainty`

Show:
- FRS radial gauge (0–100, color-coded)
- Forecast value + 80% interval
- Failure risk panel with explanation
- FRS components horizontal bar chart

**Key message:** "Uncertainty is not confidence. FRS is a decision-support summary, not a universal scientific metric."

---

### Step 9 — Counterfactual Lab (1 min)

**Page:** `/lab`

Show:
- Baseline forecast for New Delhi rainfall 48h
- Click **Remove NWP** → click **Run simulation**
- See: scenario forecast changes, weights redistributed to AI + ensemble
- Weight comparison bar chart (baseline vs scenario)
- `production_mutated: false` in response

**Key message:** "What if NWP is unavailable? AERIS automatically redistributes weights. This is a simulation — production state is never changed."

Also show: Add AI boost +0.3 → run simulation → forecast shifts.

---

### Step 10 — Verification (30 sec)

**Page:** `/verification`

Show:
- MAE bar chart — AERIS blend vs individual models vs static equal-weight
- Radar chart — multi-metric comparison
- Full metrics table

**Show the banner:** "DEMONSTRATION BENCHMARK — not operational accuracy."

---

### Step 11 — Model Registry (30 sec)

**Page:** `/registry`

Show:
- Trust meta-model card: strategy CONTEXTUAL_ML, stage Staging, dataset demo-grid-v1
- Skill heatmap table (MAE by model × lead)
- Click **"Run continuous learning step"** → see elapsed time → learning loop demonstration

---

### Step 12 — Close with core messages

Return to `/about` for the closing slide:

1. One forecast is not always enough.
2. The best model changes with context.
3. AERIS learns when, where and why each model should be trusted.
4. Forecast uncertainty is information, not a failure.
5. Every verified forecast improves future model trust.

---

## Resetting demo data

```bash
# From the Overview page: click "Load / refresh demo data"
# Or via API:
curl -X POST http://localhost:8000/api/v1/admin/seed
```

## Triggering the learning loop

```bash
curl -X POST http://localhost:8000/api/v1/admin/learn
# Or from the Registry page: "Run continuous learning step"
```

## What to say about demo data

> "Everything you see is generated from seeded synthetic ensembles with a controlled error hierarchy — NWP stronger in large-scale regimes, AI stronger at short lead times, ensemble robust in transitions. This is not NCMRWF operational data. The architecture is designed for operational integration with real data adapters."
