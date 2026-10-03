from eccodes import (
    codes_grib_new_from_file,
    codes_get,
    codes_release,
)
from pathlib import Path

path = Path(
    r"C:\Users\poorv\OneDrive\Desktop\AERIS"
    r"\GRIB DATASETS\370713e22141393fc5af4097283a5ecb.grib"
)

print("=" * 100)
print("RAW GRIB MESSAGE METADATA")
print("=" * 100)

with open(path, "rb") as f:

    count = 0

    while True:

        gid = codes_grib_new_from_file(f)

        if gid is None:
            break

        count += 1

        def get(key):
            try:
                return codes_get(gid, key)
            except Exception:
                return "N/A"

        print(
            f"{count:03d} | "
            f"shortName={get('shortName')} | "
            f"paramId={get('paramId')} | "
            f"typeOfLevel={get('typeOfLevel')} | "
            f"level={get('level')} | "
            f"heightAboveGround={get('heightAboveGround')} | "
            f"step={get('step')}"
        )

        codes_release(gid)

print("=" * 100)
print("TOTAL MESSAGES:", count)
print("=" * 100)