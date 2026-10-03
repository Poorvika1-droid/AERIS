# Leakage audit

## Status: FAIL — production training prohibited

The prior `scripts/train_aeris_real.py` includes `observed_mean_mm`, `bias_mm`, `mae_mm`, `rmse_mm`, and a target-derived rain indicator as model features, and uses `GroupKFold`, which is not a chronological split. Its artifact and its reported metrics are therefore contaminated and must not be deployed. The new `src/validation/leakage.py` provides fail-closed causal, split, duplicate, compatibility, and rolling-skill checks.
