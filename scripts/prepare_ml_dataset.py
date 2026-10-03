import xarray as xr
import numpy as np
from pathlib import Path

INPUT = Path("data/processed/aeris_training_2025_01.nc")
OUTPUT = Path("data/processed/aeris_ml_ready_2025_01.nc")

print("=" * 70)
print("AERIS ML DATASET PREPARATION")
print("=" * 70)

# ---------------------------------------------------------
# 1. Load dataset
# ---------------------------------------------------------
print("\n[1/6] Loading dataset...")

ds = xr.open_dataset(INPUT)

print(ds)

# ---------------------------------------------------------
# 2. Identify valid IMD observation mask
# ---------------------------------------------------------
print("\n[2/6] Creating static IMD observation mask...")

rainfall = ds["RAINFALL"]

# Valid wherever IMD has an actual observation
imd_valid_mask = rainfall.isel(TIME=0).notnull()

print("Valid grid points:", int(imd_valid_mask.sum()))
print("Missing grid points:", int((~imd_valid_mask).sum()))

# Verify mask is constant through time
all_same = np.all(
    rainfall.isnull().values ==
    rainfall.isnull().isel(TIME=0).values
)

print("Static mask verified:", all_same)

if not all_same:
    raise ValueError(
        "IMD missing-data mask changes with time. "
        "Cannot use static spatial mask."
    )

# ---------------------------------------------------------
# 3. Apply mask to rainfall target
# ---------------------------------------------------------
print("\n[3/6] Applying IMD observation mask...")

# IMPORTANT:
# Do NOT convert NaN to zero.
# Zero rainfall is a legitimate observation.

rainfall_target = rainfall.where(imd_valid_mask)

ds["rainfall_target_mm"] = rainfall_target

# ---------------------------------------------------------
# 4. Keep only required ML variables
# ---------------------------------------------------------
print("\n[4/6] Selecting ML variables...")

features = [
    "temperature_2m_C",
    "dewpoint_2m_C",
    "wind_u_10m",
    "wind_v_10m",
    "wind_speed_10m",
    "pressure_msl_hPa",
    "precipitation_ERA5_mm",
]

target = "rainfall_target_mm"

ml_ds = ds[features + [target]].copy()

# ---------------------------------------------------------
# 5. Add static observation mask
# ---------------------------------------------------------
print("\n[5/6] Adding IMD observation mask...")

ml_ds["imd_valid_mask"] = imd_valid_mask.astype(np.int8)

ml_ds["imd_valid_mask"].attrs = {
    "description": "Static spatial mask indicating grid cells with valid IMD rainfall observations",
    "valid_value": 1,
    "invalid_value": 0,
}

ml_ds["rainfall_target_mm"].attrs = {
    "description": "IMD observed rainfall used as ML target",
    "units": "mm",
    "missing_value": "NaN outside valid IMD observation domain",
}

# ---------------------------------------------------------
# 6. Save
# ---------------------------------------------------------
print("\n[6/6] Saving ML-ready dataset...")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

ml_ds.to_netcdf(OUTPUT)

print("\n" + "=" * 70)
print("SUCCESS")
print("=" * 70)

print("Output:", OUTPUT)
print("Dimensions:", dict(ml_ds.sizes))

print("\nVariables:")
for name in ml_ds.data_vars:
    print(" -", name)

valid = int(imd_valid_mask.sum())
total = int(imd_valid_mask.size)

print("\nIMD valid grid points:", valid)
print("Total grid points:", total)
print("Coverage: {:.2f}%".format(valid / total * 100))

print("\nRainfall statistics:")
print("Min:", float(rainfall_target.min(skipna=True)))
print("Max:", float(rainfall_target.max(skipna=True)))
print("Mean:", float(rainfall_target.mean(skipna=True)))

print("\nML-ready dataset created successfully.")