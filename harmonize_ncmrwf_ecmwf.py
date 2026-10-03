from pathlib import Path
import xarray as xr
import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import warnings

warnings.filterwarnings("ignore")

# ============================================================
# AERIS COMMON GRID
# ============================================================

LAT_MIN = 5.25
LAT_MAX = 37.75

LON_MIN = 65.25
LON_MAX = 99.75

RESOLUTION = 0.25

TARGET_LAT = np.arange(
    LAT_MIN,
    LAT_MAX + 0.001,
    RESOLUTION
)

TARGET_LON = np.arange(
    LON_MIN,
    LON_MAX + 0.001,
    RESOLUTION
)

TARGET_LON2D, TARGET_LAT2D = np.meshgrid(
    TARGET_LON,
    TARGET_LAT
)

print("=" * 100)
print("AERIS COMMON GRID")
print("=" * 100)

print("Latitude:", TARGET_LAT[0], "to", TARGET_LAT[-1])
print("Longitude:", TARGET_LON[0], "to", TARGET_LON[-1])
print("Resolution:", RESOLUTION)
print("Grid size:", len(TARGET_LAT), "x", len(TARGET_LON))
print("Cells:", len(TARGET_LAT) * len(TARGET_LON))


# ============================================================
# PATHS
# ============================================================

ROOT = Path(
    r"C:\Users\poorv\OneDrive\Desktop\AERIS"
)

NCMRWF_FILE = ROOT / "data" / "processed" / \
    "aeris_ncmrwf_initial_runs.nc"

ECMWF_DIR = ROOT / "GRIB DATASETS" / "ECMWF"

OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# VARIABLES
# ============================================================

VARIABLES = [
    "temperature_2m_C",
    "dewpoint_2m_C",
    "wind_u_10m_ms",
    "wind_v_10m_ms",
    "pressure_msl_hPa",
    "precipitation_total_mm",
]


# ============================================================
# 1. LOAD NCMRWF
# ============================================================

print("\nLoading NCMRWF...")

ncm = xr.open_dataset(NCMRWF_FILE)

print(ncm)


# ============================================================
# NCMRWF -> COMMON 0.25 GRID
# ============================================================

print("\nRegridding NCMRWF...")

ncm_common = {}

for variable in VARIABLES:

    print("  Processing:", variable)

    da = ncm[variable]

    # Regular NCMRWF grid -> regular AERIS grid
    da_interp = da.interp(
        latitude=xr.DataArray(
            TARGET_LAT,
            dims="latitude"
        ),
        longitude=xr.DataArray(
            TARGET_LON,
            dims="longitude"
        ),
        method="linear"
    )

    ncm_common[variable] = da_interp.astype("float32")


ncm_out = xr.Dataset(
    ncm_common
)

ncm_out = ncm_out.assign_coords(
    init_time=ncm.init_time,
    step=ncm.step,
    latitude=TARGET_LAT,
    longitude=TARGET_LON,
)

ncm.close()


# ============================================================
# 2. LOAD ECMWF GRIB FILES
# ============================================================

ecmwf_files = sorted(
    ECMWF_DIR.glob("ecmwf_*.grib")
)

print("\nECMWF files:", len(ecmwf_files))


# ============================================================
# ECMWF variable extraction
# ============================================================

ECMWF_FILTERS = {

    "temperature_2m_C": {
        "shortName": "2t",
        "typeOfLevel": "heightAboveGround",
        "level": 2,
    },

    "dewpoint_2m_C": {
        "shortName": "2d",
        "typeOfLevel": "heightAboveGround",
        "level": 2,
    },

    "wind_u_10m_ms": {
        "shortName": "10u",
        "typeOfLevel": "heightAboveGround",
        "level": 10,
    },

    "wind_v_10m_ms": {
        "shortName": "10v",
        "typeOfLevel": "heightAboveGround",
        "level": 10,
    },

    "pressure_msl_hPa": {
        "shortName": "msl",
        "typeOfLevel": "meanSea",
    },

    "precipitation_total_mm": {
        "shortName": "tp",
        "typeOfLevel": "surface",
    },
}


# ============================================================
# Helper: load one ECMWF variable
# ============================================================

def load_ecmwf_variable(path, variable):

    cfg = ECMWF_FILTERS[variable]

    ds = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": cfg,
            "indexpath": "",
        },
    )

    if len(ds.data_vars) != 1:
        raise RuntimeError(
            f"Unexpected variables: {list(ds.data_vars)}"
        )

    source_name = list(ds.data_vars)[0]

    da = ds[source_name]

    # Convert units
    if variable == "temperature_2m_C":
        da = da - 273.15

    elif variable == "dewpoint_2m_C":
        da = da - 273.15

    elif variable == "pressure_msl_hPa":
        da = da / 100.0

    # Remove scalar coordinates
    for coord in [
        "heightAboveGround",
        "meanSea",
        "surface",
    ]:

        if coord in da.coords:

            try:
                da = da.drop_vars(coord)
            except Exception:
                pass

    return da.astype("float32"), ds


# ============================================================
# Helper: scattered ECMWF -> regular AERIS grid
# ============================================================

def regrid_ecmwf(da):

    # ECMWF uses:
    # step × values
    #
    # latitude(values)
    # longitude(values)

    source_lat = da["latitude"].values
    source_lon = da["longitude"].values

    points = np.column_stack([
        source_lon,
        source_lat
    ])

    target_points = np.column_stack([
        TARGET_LON2D.ravel(),
        TARGET_LAT2D.ravel()
    ])

    output = []

    for i in range(len(da.step)):

        print(
            f"      lead {i + 1}/{len(da.step)}",
            end="\r"
        )

        values = da.isel(step=i).values

        # Linear interpolation
        result = griddata(
            points,
            values,
            target_points,
            method="linear"
        )

        # Fill small exterior holes using nearest neighbour
        missing = np.isnan(result)

        if np.any(missing):

            nearest = griddata(
                points,
                values,
                target_points[missing],
                method="nearest"
            )

            result[missing] = nearest

        output.append(
            result.reshape(
                len(TARGET_LAT),
                len(TARGET_LON)
            ).astype("float32")
        )

    print()

    output = np.stack(output)

    return xr.DataArray(
        output,
        dims=[
            "step",
            "latitude",
            "longitude",
        ],
        coords={
            "step": da.step.values,
            "latitude": TARGET_LAT,
            "longitude": TARGET_LON,
        }
    )


# ============================================================
# 3. ECMWF PROCESSING
# ============================================================

ecmwf_runs = []

for idx, path in enumerate(ecmwf_files, 1):

    print("\n" + "-" * 90)
    print(
        f"ECMWF RUN {idx}/{len(ecmwf_files)}:",
        path.name
    )

    # Metadata from 10u
    meta, meta_ds = load_ecmwf_variable(
        path,
        "wind_u_10m_ms"
    )

    init_time = pd.Timestamp(
        meta_ds["time"].values
    )

    print("Initialization:", init_time)

    meta_ds.close()

    variables = {}

    for variable in VARIABLES:

        print("\n  Variable:", variable)

        da, ds = load_ecmwf_variable(
            path,
            variable
        )

        regridded = regrid_ecmwf(da)

        regridded.name = variable

        # Add init dimension
        regridded = regridded.expand_dims(
            init_time=[
                np.datetime64(init_time)
            ]
        )

        variables[variable] = regridded

        ds.close()

    run = xr.Dataset(variables)

    ecmwf_runs.append(run)


# ============================================================
# 4. COMBINE ECMWF
# ============================================================

print("\nCombining ECMWF runs...")

ecmwf_common = xr.concat(
    ecmwf_runs,
    dim="init_time",
    data_vars="all",
    coords="minimal",
    compat="override",
)

ecmwf_common = ecmwf_common.sortby(
    "init_time"
)


# ============================================================
# 5. DERIVED VARIABLES
# ============================================================

def add_derived(ds):

    ds["wind_speed_10m_ms"] = np.sqrt(
        ds["wind_u_10m_ms"] ** 2
        +
        ds["wind_v_10m_ms"] ** 2
    )

    ds["dewpoint_depression_C"] = (
        ds["temperature_2m_C"]
        -
        ds["dewpoint_2m_C"]
    )

    return ds


ncm_common = add_derived(ncm_out)
ecmwf_common = add_derived(ecmwf_common)


# ============================================================
# 6. SAVE INDIVIDUAL COMMON-GRID DATASETS
# ============================================================

ncm_output = OUT_DIR / "aeris_ncmrwf_common_025deg.nc"
ecmwf_output = OUT_DIR / "aeris_ecmwf_common_025deg.nc"

print("\nSaving NCMRWF:")
print(ncm_output)

ncm_common.to_netcdf(
    ncm_output,
    engine="netcdf4"
)

print("\nSaving ECMWF:")
print(ecmwf_output)

ecmwf_common.to_netcdf(
    ecmwf_output,
    engine="netcdf4"
)


# ============================================================
# 7. ADD MODEL DIMENSION
# ============================================================

print("\nCreating multi-model dataset...")

ncm_common = ncm_common.expand_dims(
    model=["NCMRWF"]
)

ecmwf_common = ecmwf_common.expand_dims(
    model=["ECMWF"]
)

multimodel = xr.concat(
    [
        ncm_common,
        ecmwf_common,
    ],
    dim="model"
)


# ============================================================
# METADATA
# ============================================================

multimodel.attrs.update({

    "title":
        "AERIS Multi-Model Common Grid Forecast Dataset",

    "grid":
        "0.25 degree regular latitude-longitude",

    "models":
        "NCMRWF, ECMWF",

    "purpose":
        "Common-grid input for adaptive multi-model forecast blending",

    "warning":
        "Forecast data only; not observations.",

})


# ============================================================
# 8. SAVE MULTI-MODEL DATASET
# ============================================================

multimodel_output = OUT_DIR / \
    "aeris_multimodel_common_025deg.nc"

print("\nSaving:")
print(multimodel_output)

encoding = {}

for variable in multimodel.data_vars:

    encoding[variable] = {
        "zlib": True,
        "complevel": 4,
        "dtype": "float32",
    }

multimodel.to_netcdf(
    multimodel_output,
    engine="netcdf4",
    encoding=encoding,
)


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 100)
print("AERIS COMMON-GRID HARMONIZATION COMPLETE")
print("=" * 100)

print("\nOutput files:")
print(ncm_output)
print(ecmwf_output)
print(multimodel_output)

print("\nMulti-model dataset:")
print(multimodel)

print("\nModels:")
print(multimodel.model.values)

print("\nVariables:")
for variable in multimodel.data_vars:
    print(" -", variable)

print("\nGrid:")
print(
    len(TARGET_LAT),
    "x",
    len(TARGET_LON)
)

print("\nInitialization times:")
print(multimodel.init_time.values)

print("\nLead times:")
print(multimodel.step.values)

print("\nDONE")