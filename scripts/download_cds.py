import cdsapi
from pathlib import Path

# ============================================================
# AERIS - ERA5 CDS Downloader
# Test download: January 2025
# ============================================================

# AERIS project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Output directory
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "cds"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Output file
OUTPUT_FILE = OUTPUT_DIR / "era5_india_2025_01.nc"

# CDS client
client = cdsapi.Client()

# ERA5 dataset
dataset = "reanalysis-era5-single-levels"

# Request
request = {
    "product_type": ["reanalysis"],

    "variable": [
        "2m_temperature",
        "2m_dewpoint_temperature",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "mean_sea_level_pressure",
        "total_precipitation",
    ],

    "year": ["2025"],

    "month": ["01"],

    "day": [
        "01", "02", "03", "04", "05", "06", "07",
        "08", "09", "10", "11", "12", "13", "14",
        "15", "16", "17", "18", "19", "20", "21",
        "22", "23", "24", "25", "26", "27", "28",
        "29", "30", "31"
    ],

    "time": [
        "00:00",
        "01:00",
        "02:00",
        "03:00",
        "04:00",
        "05:00",
        "06:00",
        "07:00",
        "08:00",
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
        "18:00",
        "19:00",
        "20:00",
        "21:00",
        "22:00",
        "23:00"
    ],

    # North, West, South, East
    # Matches the spatial domain of your IMD RF25 dataset.
    "area": [38.5, 66.5, 6.5, 100.0],

    "data_format": "netcdf",
    "download_format": "unarchived",
}

print("=" * 60)
print("AERIS - ERA5 CDS DOWNLOAD")
print("=" * 60)
print(f"Dataset : {dataset}")
print("Period  : January 2025")
print("Region  : India")
print("Output  :", OUTPUT_FILE)
print("=" * 60)

print("\nStarting CDS request...")

client.retrieve(
    dataset,
    request,
    str(OUTPUT_FILE)
)

print("\nDownload completed successfully!")
print(f"Saved to: {OUTPUT_FILE}")