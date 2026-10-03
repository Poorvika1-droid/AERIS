from pathlib import Path
import xarray as xr
import pandas as pd
import numpy as np


# ============================================================
# AERIS - NCMRWF TIGGE GRIB -> CLEAN NETCDF
# ============================================================

ROOT = Path(
    r"C:\Users\poorv\OneDrive\Desktop\AERIS\GRIB DATASETS"
)

OUT = Path(
    r"C:\Users\poorv\OneDrive\Desktop\AERIS\data\processed"
)

OUT.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# IMPORTANT:
# These are the ACTUAL GRIB shortNames found in the files.
# ------------------------------------------------------------

VARIABLES = {

    "temperature_2m_C": {
        "filter": {
            "shortName": "2t",
            "typeOfLevel": "heightAboveGround",
            "level": 2,
        },
        "convert": lambda x: x - 273.15,
        "units": "degC",
    },

    "dewpoint_2m_C": {
        "filter": {
            "shortName": "2d",
            "typeOfLevel": "heightAboveGround",
            "level": 2,
        },
        "convert": lambda x: x - 273.15,
        "units": "degC",
    },

    "wind_u_10m_ms": {
        "filter": {
            "shortName": "10u",
            "typeOfLevel": "heightAboveGround",
            "level": 10,
        },
        "convert": lambda x: x,
        "units": "m s-1",
    },

    "wind_v_10m_ms": {
        "filter": {
            "shortName": "10v",
            "typeOfLevel": "heightAboveGround",
            "level": 10,
        },
        "convert": lambda x: x,
        "units": "m s-1",
    },

    "pressure_msl_hPa": {
        "filter": {
            "shortName": "msl",
            "typeOfLevel": "meanSea",
        },
        "convert": lambda x: x / 100.0,
        "units": "hPa",
    },

    "precipitation_total_mm": {
        "filter": {
            "shortName": "tp",
            "typeOfLevel": "surface",
        },
        "convert": lambda x: x,
        "units": "mm",
    },
}


# ------------------------------------------------------------
# Find GRIB files
# ------------------------------------------------------------

files = sorted(ROOT.glob("*.grib"))

print("=" * 100)
print("AERIS NCMRWF TIGGE CONVERTER")
print("=" * 100)
print("GRIB files found:", len(files))


if not files:
    raise RuntimeError("No .grib files found.")


runs = []
manifest = []


# ------------------------------------------------------------
# Process every forecast run
# ------------------------------------------------------------

for i, path in enumerate(files, 1):

    print()
    print("-" * 100)
    print(f"[{i}/{len(files)}] {path.name}")

    # --------------------------------------------------------
    # Read metadata using a known-good field
    # --------------------------------------------------------

    meta = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={
            "filter_by_keys": {
                "shortName": "10u",
                "typeOfLevel": "heightAboveGround",
                "level": 10,
            },
            "indexpath": "",
        },
    )

    init_time = pd.Timestamp(meta["time"].values)

    print("Initialization:", init_time)

    meta.close()


    variables = {}


    # --------------------------------------------------------
    # Extract each meteorological variable independently
    # --------------------------------------------------------

    for output_name, cfg in VARIABLES.items():

        try:

            ds = xr.open_dataset(
                path,
                engine="cfgrib",
                backend_kwargs={
                    "filter_by_keys": cfg["filter"],
                    "indexpath": "",
                },
            )

            if len(ds.data_vars) != 1:
                raise RuntimeError(
                    f"Expected one data variable, found: "
                    f"{list(ds.data_vars)}"
                )

            source_var = list(ds.data_vars)[0]

            da = ds[source_var]

            # Remove the conflicting scalar height coordinate.
            if "heightAboveGround" in da.coords:
                da = da.drop_vars("heightAboveGround")

            da = cfg["convert"](da)

            da.name = output_name
            da.attrs["units"] = cfg["units"]

            # Normalize dimension order.
            da = da.transpose(
                "step",
                "latitude",
                "longitude"
            )

            # Add forecast initialization dimension.
            da = da.expand_dims(
                init_time=[np.datetime64(init_time)]
            )

            variables[output_name] = da

            manifest.append({
                "file": path.name,
                "source": "NCMRWF",
                "initialization_time": init_time,
                "variable": output_name,
                "status": "OK",
            })

            print(f"  OK   {output_name}")

            ds.close()

        except Exception as e:

            print(
                f"  FAIL {output_name}: {type(e).__name__}: {e}"
            )

            manifest.append({
                "file": path.name,
                "source": "NCMRWF",
                "initialization_time": init_time,
                "variable": output_name,
                "status": f"FAILED: {e}",
            })


    # --------------------------------------------------------
    # Build one dataset for this forecast initialization
    # --------------------------------------------------------

    if variables:

        run = xr.Dataset(variables)

        run = run.assign_coords(
            source="NCMRWF"
        )

        runs.append(run)


# ------------------------------------------------------------
# Stop if nothing was extracted
# ------------------------------------------------------------

if not runs:
    raise RuntimeError("No valid forecast runs were extracted.")


# ------------------------------------------------------------
# Combine all initialization dates
# ------------------------------------------------------------

print()
print("=" * 100)
print("COMBINING FORECAST RUNS")
print("=" * 100)

combined = xr.concat(
    runs,
    dim="init_time",
    data_vars="all",
    coords="minimal",
    compat="override",
    combine_attrs="drop_conflicts",
)

combined = combined.sortby("init_time")


# ------------------------------------------------------------
# Derived wind feature
# ------------------------------------------------------------

print("Creating derived wind speed...")

combined["wind_speed_10m_ms"] = np.sqrt(
    combined["wind_u_10m_ms"] ** 2
    +
    combined["wind_v_10m_ms"] ** 2
)


# ------------------------------------------------------------
# Derived dewpoint depression
# ------------------------------------------------------------

print("Creating dewpoint depression...")

combined["dewpoint_depression_C"] = (
    combined["temperature_2m_C"]
    -
    combined["dewpoint_2m_C"]
)


# ------------------------------------------------------------
# Convert cumulative precipitation to 6-hour increment
# ------------------------------------------------------------

print("Creating 6-hour precipitation...")

tp = combined["precipitation_total_mm"]

tp_increment = tp.diff(
    dim="step",
    label="upper"
)

# First lead is already the accumulation from forecast start.
first = tp.isel(step=0)

first = first.expand_dims(
    step=[tp.step.values[0]]
)

tp_increment = xr.concat(
    [first, tp_increment],
    dim="step"
)

# Numerical safety.
tp_increment = tp_increment.clip(min=0)

combined["precipitation_6h_mm"] = tp_increment


# ------------------------------------------------------------
# Metadata
# ------------------------------------------------------------

combined.attrs.update({
    "title":
        "AERIS NCMRWF TIGGE Harmonized Forecast Dataset",

    "forecast_source":
        "NCMRWF via TIGGE",

    "purpose":
        "Prototype input for AERIS dynamic forecast trust and blending",

    "note":
        "This dataset contains forecast fields, not observations.",

    "variables":
        "2t, 2d, 10u, 10v, msl, tp",
})


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

output_file = OUT / "aeris_ncmrwf_initial_runs.nc"

print()
print("Saving:")
print(output_file)

encoding = {}

for variable in combined.data_vars:

    encoding[variable] = {
        "zlib": True,
        "complevel": 4,
        "dtype": "float32",
    }


combined.to_netcdf(
    output_file,
    engine="netcdf4",
    encoding=encoding,
)


# ------------------------------------------------------------
# Manifest
# ------------------------------------------------------------

manifest_df = pd.DataFrame(manifest)

manifest_file = OUT / "ncmrwf_manifest.csv"

manifest_df.to_csv(
    manifest_file,
    index=False
)


# ------------------------------------------------------------
# Final report
# ------------------------------------------------------------

print()
print("=" * 100)
print("AERIS DATASET CREATED SUCCESSFULLY")
print("=" * 100)

print()
print("Output:")
print(output_file)

print()
print("Manifest:")
print(manifest_file)

print()
print("DATASET SUMMARY")
print(combined)

print()
print("VARIABLES")
for v in combined.data_vars:
    print("  ", v)

print()
print("INITIALIZATION TIMES")
for t in combined.init_time.values:
    print("  ", t)

print()
print("LEAD TIMES")
for s in combined.step.values:
    print("  ", s)

print()
print("SOURCE")
print(combined.attrs.get("forecast_source"))

print()
print("=" * 100)
print("DONE")
print("=" * 100)