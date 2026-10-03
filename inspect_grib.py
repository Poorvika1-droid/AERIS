from pathlib import Path
import xarray as xr

ROOT = Path(r"C:\Users\poorv\OneDrive\Desktop\AERIS\GRIB DATASETS")

files = sorted(ROOT.glob("*.grib"))

print("=" * 100)
print("AERIS TIGGE GRIB MANIFEST")
print("=" * 100)
print("Files:", len(files))

for i, file in enumerate(files, 1):
    print("\n" + "-" * 100)
    print(f"{i}. {file.name}")
    print("Size:", round(file.stat().st_size / 1024 / 1024, 2), "MB")

    try:
        ds = xr.open_dataset(
            file,
            engine="cfgrib",
            backend_kwargs={"indexpath": ""}
        )

        print("Variables:", list(ds.data_vars))
        print("Dimensions:", dict(ds.sizes))

        for coord in ["time", "step", "valid_time"]:
            if coord in ds.coords:
                print(f"{coord}:", ds[coord].values)

        print("Centre:", ds.attrs.get("GRIB_centre"))
        print("Description:", ds.attrs.get("GRIB_centreDescription"))

        for var in ds.data_vars:
            da = ds[var]

            print(f"\nVariable: {var}")
            print("  shortName:", da.attrs.get("GRIB_shortName"))
            print("  paramId:", da.attrs.get("GRIB_paramId"))
            print("  units:", da.attrs.get("GRIB_units"))
            print("  level:", da.attrs.get("GRIB_typeOfLevel"))
            print("  shape:", da.shape)

        ds.close()

    except Exception as e:
        print("ERROR:", repr(e))

print("\n" + "=" * 100)
print("DONE")
print("=" * 100)