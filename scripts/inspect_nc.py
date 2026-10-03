"""Quick inspection of the NetCDF dataset."""
from __future__ import annotations
import sys
from pathlib import Path

import netCDF4 as nc
import numpy as np

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("RF25_ind2025_rfp25.nc")
ds = nc.Dataset(path)

print("=== DIMENSIONS ===")
for k, v in ds.dimensions.items():
    print(f"  {k}: {len(v)}")

print("\n=== VARIABLES ===")
for k, v in ds.variables.items():
    units = getattr(v, "units", "?")
    lname = getattr(v, "long_name", getattr(v, "description", "?"))
    fill = getattr(v, "_FillValue", None)
    print(f"  {k:20s}  shape={str(v.shape):20s}  dtype={v.dtype}  units={units}  long_name={lname}")
    if k not in ds.dimensions:
        arr = v[:]
        if hasattr(arr, 'compressed'):
            arr2 = arr.compressed()
        else:
            arr2 = np.array(arr).ravel()
        finite = arr2[np.isfinite(arr2)]
        if len(finite):
            print(f"    → range [{finite.min():.4f}, {finite.max():.4f}]  mean={finite.mean():.4f}  n_valid={len(finite)}")

print("\n=== GLOBAL ATTRIBUTES ===")
for a in ds.ncattrs():
    print(f"  {a}: {getattr(ds, a)}")

ds.close()
