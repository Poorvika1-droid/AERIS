# AERIS Scientific Methodology

## Disclaimer

This is a hackathon prototype. All results presented are from deterministic seeded benchmark data.  
No claim is made regarding deployment at NCMRWF, IMD, or any operational center.  
No claim is made regarding guaranteed improvement over existing operational systems.

---

## Problem framing

Multi-model forecast blending is a well-established field in numerical weather prediction.  
AERIS addresses a specific sub-problem: **context-aware dynamic weight assignment**.

The central hypothesis is that static or climatological weighting is suboptimal because:
- Model skill varies by region (coastal vs. inland, topographic effects)
- Model skill varies by lead time (NWP diverges at longer leads; AI emulators may degrade faster)
- Model skill varies by weather regime (convective systems vs. large-scale circulation)
- Model health varies in real-time (missing runs, degraded initialization)

Therefore, weights should be functions of all these context variables simultaneously.

---

## Weather regime classification

**Classification approach:** Hybrid KMeans (7 clusters) with physics-inspired rule overlay.

**Features:**
- Temperature, rainfall, wind speed
- Pressure, humidity (when available)
- Month, temperature anomaly, rainfall anomaly

**Output:** 9 operational regime classes.

**Important:** These classes are defined for the purpose of adaptive model weighting, not as official meteorological regime definitions. They do not correspond to IMD or WMO regime taxonomies.

**Limitations:**
- Clusters are initialized from synthetic data in the prototype
- Regime boundaries are configurable and should be validated against historical Indian climate data before operational use
- A future transformer-based encoder would improve temporal resolution and regime stability

---

## Model skill metrics

| Metric | Application |
|---|---|
| MAE | Primary skill score for continuous variables |
| RMSE | Variance-sensitive error |
| Bias | Systematic over/under-prediction |
| Pearson correlation | Temporal phase agreement |
| CSI (Critical Success Index) | Event detection (rainfall threshold exceedance) |
| Brier Score | Probabilistic calibration for binary events |
| CRPS (Continuous Ranked Probability Score) | Full distribution reliability (approximated) |
| Precision / Recall | Event detection contingency |

All metrics are computed from `(forecast, observation)` pairs. In the prototype, observations are synthetic.

---

## Dynamic trust engine

**Input:** Context vector + skill snapshots + health scores.

**Strategy CONTEXTUAL_ML (demo):** Heuristic contextual prior applied to inverse-MAE base weights.  
Rule summary:
- AI weight boosted at ≤ 48h lead in CONVECTIVE_RAIN / HEAVY_RAIN
- NWP weight boosted in NORMAL / MONSOON / CYCLONIC_INFLUENCE, penalized in CONVECTIVE_RAIN
- Ensemble weight boosted at high disagreement (> 0.45) and transition probability (> 0.5)
- All weights multiplied by health adjustment (0–1.2)

**Production path:** LightGBM / XGBoost meta-model predicting inverse normalized error from context + recent error features.

**Mathematical guarantee:** All weights satisfy w_i ≥ 0 and Σ w_i = 1 by construction via `normalize_weights`.

---

## Blending

```
blended = Σ (w_i × calibrated_value_i)
```

Bias correction hooks available at harmonization stage (additive correction per location).  
Spatial smoothing (Gaussian neighborhood, k=4) applied to weight fields for coherence.  
Missing model: weight 0, remaining weights renormalized.

---

## Uncertainty quantification

**Ensemble spread:** Standard deviation of member forecast values at a location.

**Prediction interval:** Blended ± 1.28σ (approximately 80%). This is a Gaussian approximation — not a rigorous probabilistic interval. For operational use, replace with proper ensemble quantiles.

**Inter-model disagreement score:** Normalized standard deviation of model values:
```
D = std(values) / max(|mean(values)|, 1.0)  ∈ [0, 1]
```

**Confidence:** HIGH if uncertainty score < 0.22 and disagreement < 0.3; MODERATE if < 0.45; LOW otherwise.

**Forecast Reliability Score (FRS):** Weighted composite:
```
FRS = 0.25 × skill + 0.15 × health + 0.20 × agreement + 0.15 × regime_certainty
    + 0.15 × obs_consistency + 0.10 × stability
```
Range: 0–100. FRS is a **decision-support summary only**, not a scientifically validated universal metric. Component weights are configurable.

**Forecast failure risk:** Logistic combination of disagreement, health, transition probability, lead time, unusual state, and historical error rate. Decision-support indicator — not a claim of certain failure.

---

## Extreme events

Event probability uses a Gaussian tail proxy:
```
P(X > threshold) ≈ 0.5 × erfc((threshold - value) / (sqrt(2) × spread))
```

**Thresholds:** Configurable in `default_thresholds()`. Prototype defaults:
- Heavy rainfall: ≥ 50 mm (24h accumulation)
- Heatwave: ≥ 40°C
- High wind: ≥ 12 m s⁻¹

**These are NOT official IMD/NCMRWF warning thresholds.** They are configurable starting points.

---

## Verification approach

AERIS is compared against:
1. Individual component models (NWP, AI, Ensemble)
2. Static equal-weight ensemble mean
3. AERIS adaptive blend

In the prototype, all comparisons use synthetic benchmark data. The controlled error hierarchy (AI stronger short-lead, NWP stronger large-scale) is designed to demonstrate the adaptive advantage in a reproducible way — it does not represent real-world model performance.

---

## What has NOT been validated

- Actual skill of AERIS over operational NWP at NCMRWF
- Performance on real Indian monsoon / extreme event cases
- Calibration of prediction intervals on real observation networks
- FRS correlation with actual forecast quality on operational data
- Regime classification accuracy against historical Indian climate regimes
- Computational performance at national grid resolution

All of the above require operational data access and are planned for future work.
