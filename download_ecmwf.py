import cdsapi
from pathlib import Path
import time

# ============================================================
# AERIS - ECMWF TIGGE DOWNLOADER
# Proven MARS-style TIGGE request
# ============================================================

client = cdsapi.Client(
    url="https://ecds.ecmwf.int/api"
)

OUT = Path(
    r"C:\Users\poorv\OneDrive\Desktop\AERIS"
    r"\GRIB DATASETS\ECMWF"
)

OUT.mkdir(parents=True, exist_ok=True)

# These are the 2020 NCMRWF initialization dates we are
# currently matching.
DATES = [
    "2020-06-01",
    "2020-06-05",
    "2020-06-10",
    "2020-06-11",
    "2020-06-15",
    "2020-06-20",
    "2020-06-21",
]

# TIGGE/MARS parameter IDs
PARAMS = "165/166/167/168/151/228228"

# 6-hourly lead times from 6h to 120h
STEPS = "6/12/18/24/30/36/42/48/54/60/66/72/78/84/90/96/102/108/114/120"

for date in DATES:

    compact_date = date.replace("-", "")

    target = OUT / f"ecmwf_{compact_date}_1200.grib"

    if target.exists() and target.stat().st_size > 1000:
        print("SKIP:", target.name)
        continue

    request = {
        "class": "ti",
        "date": date,
        "expver": "prod",
        "levtype": "sfc",

        "origin": "ecmf",

        "param": PARAMS,

        "step": STEPS,

        "stream": "enfo",

        "time": "12:00:00",

        "type": "cf",

        # North / West / South / East
        "area": "38/65/5/100",
    }

    print()
    print("=" * 90)
    print("ECMWF TIGGE")
    print("Date:", date)
    print("Target:", target.name)
    print("=" * 90)

    try:

        client.retrieve(
            "tigge-forecasts",
            request,
            str(target)
        )

        print("SUCCESS:", target.name)

    except Exception as e:

        print("FAILED:", date)
        print(type(e).__name__)
        print(e)

    time.sleep(2)

print()
print("=" * 90)
print("ECMWF DOWNLOAD COMPLETE")
print("=" * 90)