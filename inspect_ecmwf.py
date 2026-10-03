from pathlib import Path
import xarray as xr

ROOT = Path(r"C:\Users\poorv\OneDrive\Desktop\AERIS\GRIB DATASETS\ECMWF")

files = sorted(ROOT.glob("*.grib"))

print("=" * 90)
print("ECMWF AERIS DATA CHECK")
print("=" * 90)
print("Files:", len(files))

for f in files:

    print("\n", "-" * 90)
    print(f.name)

    # Open individual parameter groups because t2m/d2m and
    # 10m fields use different height levels.

    for short_name in ["10u", "10v", "2d", "2t", "msl", "tp"]:

        try:

            ds = xr.open_dataset(
                f,
                engine="cfgrib",
                backend_kwargs={
                    "filter_by_keys": {
                        "shortName": short_name
                    },
                    "indexpath": ""
                }
            )

            print(
                short_name,
                "OK",
                "shape=", dict(ds.sizes)
            )

            if "step" in ds.coords:
                print(
                    "  lead count:",
                    len(ds.step)
                )

            ds.close()

        except Exception as e:

            print(
                short_name,
                "FAIL",
                type(e).__name__
            )

print("\nDONE")