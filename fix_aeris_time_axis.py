from pathlib import Path
import xarray as xr
import numpy as np

ROOT = Path(r"C:\Users\poorv\OneDrive\Desktop\AERIS")

NCM = ROOT / "data" / "processed" / "aeris_ncmrwf_common_025deg.nc"
ECM = ROOT / "data" / "processed" / "aeris_ecmwf_common_025deg.nc"
OUT = ROOT / "data" / "processed" / "aeris_multimodel_ready.nc"

# ---------------------------------------------------------
# Load
# ---------------------------------------------------------

ncm = xr.open_dataset(NCM)
ecm = xr.open_dataset(ECM)

# ---------------------------------------------------------
# Keep ONLY initialization times common to BOTH models
# ---------------------------------------------------------

common_times = np.intersect1d(
    ncm.init_time.values,
    ecm.init_time.values
)

print("Common initialization times:")
for t in common_times:
    print(" ", t)

ncm = ncm.sel(init_time=common_times)
ecm = ecm.sel(init_time=common_times)

# ---------------------------------------------------------
# Remove source-specific / misleading scalar coordinates
# ---------------------------------------------------------

DROP_COORDS = [
    "number",
    "time",
    "meanSea",
    "surface",
    "source",
    "valid_time",
]

for c in DROP_COORDS:
    if c in ncm.coords:
        ncm = ncm.drop_vars(c)

    if c in ecm.coords:
        ecm = ecm.drop_vars(c)

# ---------------------------------------------------------
# Ensure same lead times
# ---------------------------------------------------------

common_steps = np.intersect1d(
    ncm.step.values,
    ecm.step.values
)

ncm = ncm.sel(step=common_steps)
ecm = ecm.sel(step=common_steps)

# ---------------------------------------------------------
# Create CORRECT valid_time matrix
# ---------------------------------------------------------

# datetime64[ns] initialization
# + timedelta64[ns] forecast step

valid_times = (
    ncm.init_time.values[:, None]
    +
    ncm.step.values[None, :]
)

ncm = ncm.assign_coords(
    valid_time=(
        ("init_time", "step"),
        valid_times
    )
)

ecm = ecm.assign_coords(
    valid_time=(
        ("init_time", "step"),
        valid_times
    )
)

# ---------------------------------------------------------
# Add explicit model dimension
# ---------------------------------------------------------

ncm = ncm.expand_dims(
    model=["NCMRWF"]
)

ecm = ecm.expand_dims(
    model=["ECMWF"]
)

# ---------------------------------------------------------
# Concatenate models
# ---------------------------------------------------------

multi = xr.concat(
    [ncm, ecm],
    dim="model",
    data_vars="all",
    coords="minimal",
    compat="override",
)

# ---------------------------------------------------------
# Metadata
# ---------------------------------------------------------

multi.attrs = {
    "title":
        "AERIS Multi-Model Forecast Dataset",

    "description":
        "NCMRWF and ECMWF TIGGE forecasts harmonized "
        "to a common 0.25 degree grid.",

    "models":
        "NCMRWF, ECMWF",

    "valid_time_definition":
        "forecast initialization time + lead time",

    "purpose":
        "Input to AERIS dynamic model trust and blending.",

    "warning":
        "Forecast data only; observations must be supplied "
        "separately for verification.",
}

# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

print("\nSaving:")
print(OUT)

multi.to_netcdf(
    OUT,
    engine="netcdf4",
)

print("\n" + "=" * 80)
print("AERIS MULTI-MODEL DATASET READY")
print("=" * 80)

print(multi)

print("\nModels:")
print(multi.model.values)

print("\nInitialization times:")
print(multi.init_time.values)

print("\nLead times:")
print(multi.step.values)

print("\nValid time dimensions:")
print(multi.valid_time.dims)