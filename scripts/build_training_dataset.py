from pathlib import Path
import xarray as xr

# ============================================================
# AERIS - ERA5 + IMD TRAINING DATA BUILDER
# January 2025
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ERA5_DIR = PROJECT_ROOT / "data" / "raw" / "cds" / "era5_india_2025_01"

INSTANT_FILE = ERA5_DIR / "data_stream-oper_stepType-instant.nc"
ACCUM_FILE = ERA5_DIR / "data_stream-oper_stepType-accum.nc"

IMD_FILE = PROJECT_ROOT / "RF25_ind2025_rfp25.nc"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "aeris_training_2025_01.nc"


print("=" * 70)
print("AERIS - BUILDING TRAINING DATASET")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load ERA5
# ------------------------------------------------------------

print("\n[1/6] Loading ERA5 instantaneous data...")

instant = xr.open_dataset(
    INSTANT_FILE,
    engine="netcdf4"
)

print("Variables:", list(instant.data_vars))

print("\n[2/6] Loading ERA5 accumulated data...")

accum = xr.open_dataset(
    ACCUM_FILE,
    engine="netcdf4"
)

print("Variables:", list(accum.data_vars))

# ------------------------------------------------------------
# 2. Rename ERA5 coordinates
# ------------------------------------------------------------

instant = instant.rename({
    "valid_time": "TIME",
    "latitude": "LATITUDE",
    "longitude": "LONGITUDE",
})

accum = accum.rename({
    "valid_time": "TIME",
    "latitude": "LATITUDE",
    "longitude": "LONGITUDE",
})

# ------------------------------------------------------------
# 3. Select required variables
# ------------------------------------------------------------

instant = instant[
    [
        "t2m",
        "d2m",
        "u10",
        "v10",
        "msl",
    ]
]

accum = accum[
    ["tp"]
]

# ------------------------------------------------------------
# 4. Convert hourly ERA5 → daily features
# ------------------------------------------------------------

print("\n[3/6] Converting hourly ERA5 to daily features...")

# Temperature / dew point
t2m_daily = instant["t2m"].resample(TIME="1D").mean()
d2m_daily = instant["d2m"].resample(TIME="1D").mean()

# Wind components
u10_daily = instant["u10"].resample(TIME="1D").mean()
v10_daily = instant["v10"].resample(TIME="1D").mean()

# Mean sea-level pressure
msl_daily = instant["msl"].resample(TIME="1D").mean()

# Total precipitation
tp_daily = accum["tp"].resample(TIME="1D").sum()

# ------------------------------------------------------------
# 5. Convert units
# ------------------------------------------------------------

print("\n[4/6] Engineering weather features...")

# Kelvin → Celsius
t2m_daily = t2m_daily - 273.15
d2m_daily = d2m_daily - 273.15

# Pa → hPa
msl_daily = msl_daily / 100.0

# ERA5 precipitation is metres → millimetres
tp_daily = tp_daily * 1000.0

# Wind speed from U/V components
wind_speed_daily = (u10_daily ** 2 + v10_daily ** 2) ** 0.5

# ------------------------------------------------------------
# 6. Combine ERA5 features
# ------------------------------------------------------------

era5_daily = xr.Dataset(
    {
        "temperature_2m_C": t2m_daily,
        "dewpoint_2m_C": d2m_daily,
        "wind_u_10m": u10_daily,
        "wind_v_10m": v10_daily,
        "wind_speed_10m": wind_speed_daily,
        "pressure_msl_hPa": msl_daily,
        "precipitation_ERA5_mm": tp_daily,
    }
)

print("ERA5 daily dataset:")
print(era5_daily)

# ------------------------------------------------------------
# 7. Load IMD rainfall
# ------------------------------------------------------------

print("\n[5/6] Loading IMD rainfall...")

imd = xr.open_dataset(
    IMD_FILE,
    engine="netcdf4"
)

imd = imd[
    ["RAINFALL"]
]

# Select January 2025
imd = imd.sel(
    TIME=slice("2025-01-01", "2025-01-31")
)

print("IMD dataset:")
print(imd)

# ------------------------------------------------------------
# 8. Align ERA5 and IMD
# ------------------------------------------------------------

print("\n[6/6] Aligning ERA5 + IMD...")

# Make coordinates identical in orientation.
imd = imd.sortby("LATITUDE")
imd = imd.sortby("LONGITUDE")

era5_daily = era5_daily.sortby("LATITUDE")
era5_daily = era5_daily.sortby("LONGITUDE")

# Exact spatial alignment
era5_daily = era5_daily.sel(
    LATITUDE=imd.LATITUDE,
    LONGITUDE=imd.LONGITUDE
)

# Match dates
era5_daily = era5_daily.sel(
    TIME=imd.TIME
)

# Combine predictors + target
training = xr.merge(
    [
        era5_daily,
        imd
    ]
)

print("\nFinal training dataset:")
print(training)

# ------------------------------------------------------------
# 9. Save
# ------------------------------------------------------------

training.to_netcdf(
    OUTPUT_FILE,
    engine="netcdf4"
)

print("\n" + "=" * 70)
print("SUCCESS")
print("=" * 70)
print("Saved:")
print(OUTPUT_FILE)
print("=" * 70)