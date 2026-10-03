from pathlib import Path
import xarray as xr
import pandas as pd

ROOT = Path(r"C:\Users\poorv\OneDrive\Desktop\AERIS\GRIB DATASETS")
OUT = Path(r"C:\Users\poorv\OneDrive\Desktop\AERIS\data\interim\ncmrwf")

OUT.mkdir(parents=True, exist_ok=True)

FILES = sorted(ROOT.glob("*.grib"))

VARIABLES = {
    "t2m": {"shortName": "t2m"},
    "d2m": {"shortName": "d2m"},
    "u10": {"shortName": "10u"},
    "v10": {"shortName": "10v"},
    "msl": {"shortName": "msl"},
    "tp": {"shortName": "tp"},
}

manifest = []

for file in FILES:
    print("=" * 80)
    print("Processing:", file.name)

    for name, filter_keys in VARIABLES.items():

        try:
            ds = xr.open_dataset(
                file,
                engine="cfgrib",
                backend_kwargs={
                    "filter_by_keys": filter_keys,
                    "indexpath": ""
                }
            )

            if name not in ds.data_vars:
                actual = list(ds.data_vars)[0]
            else:
                actual = name

            data = ds[actual]

            output = OUT / f"{file.stem}_{name}.nc"

            data.to_netcdf(output)

            init_time = ds.coords["time"].values if "time" in ds.coords else None

            if "step" in ds.coords:
                steps = ds["step"].values
                lead_hours = [
                    int(pd.Timedelta(s).total_seconds() / 3600)
                    for s in steps
                ]
            else:
                lead_hours = []

            manifest.append({
                "file": file.name,
                "source": "NCMRWF",
                "variable": name,
                "output": str(output),
                "initialization_time": str(init_time),
                "lead_hours": ",".join(map(str, lead_hours)),
                "centre": ds.attrs.get("GRIB_centre"),
                "centre_description": ds.attrs.get(
                    "GRIB_centreDescription"
                ),
            })

            print(f"  OK: {name}")

            ds.close()

        except Exception as e:
            print(f"  SKIP: {name} -> {e}")

manifest_df = pd.DataFrame(manifest)

manifest_file = OUT / "manifest.csv"
manifest_df.to_csv(manifest_file, index=False)

print()
print("=" * 80)
print("EXTRACTION COMPLETE")
print("Files:", len(manifest_df))
print("Manifest:", manifest_file)
print("=" * 80)