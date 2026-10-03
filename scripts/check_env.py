"""Check which scientific packages are available."""
mods = ["numpy", "pandas", "scipy", "sklearn", "xgboost", "lightgbm", "mlflow", "netCDF4", "zarr", "xarray"]
for m in mods:
    try:
        mod = __import__(m)
        v = getattr(mod, "__version__", "?")
        print(f"OK   {m} {v}")
    except ImportError:
        print(f"MISS {m}")
