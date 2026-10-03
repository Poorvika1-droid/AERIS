import os
import numpy as np
import pandas as pd
import xarray as xr

FORECAST_FILE = r"data\processed\aeris_multimodel_ready.nc"
OBS_FILE = r"data\observations\IMD\imd_rain_june_2020.nc"

OUT_NC = r"data\processed\aeris_rainfall_verification_june2020.nc"
OUT_CSV = r"data\processed\aeris_rainfall_metrics_june2020.csv"

# Forecast 24-hour windows:
# 12h -> 36h   ends 00 UTC
# 36h -> 60h   ends 00 UTC
# 60h -> 84h   ends 00 UTC
# 84h -> 108h  ends 00 UTC
START_H = np.array([12, 36, 60, 84])
END_H   = np.array([36, 60, 84, 108])

print("=" * 80)
print("AERIS RAINFALL VERIFICATION")
print("=" * 80)

# ---------------------------------------------------------------------
# 1. Load datasets
# ---------------------------------------------------------------------
fcst = xr.open_dataset(FORECAST_FILE)
obs = xr.open_dataset(OBS_FILE)

print("\nForecast models:", fcst.model.values)
print("Forecast init times:", fcst.init_time.values)

# ---------------------------------------------------------------------
# 2. Find exact common grid
# ---------------------------------------------------------------------
common_lat = np.intersect1d(fcst.latitude.values, obs.lat.values)
common_lon = np.intersect1d(fcst.longitude.values, obs.lon.values)

print("\nCommon grid:")
print("Latitude:", common_lat.min(), "to", common_lat.max(), "count:", len(common_lat))
print("Longitude:", common_lon.min(), "to", common_lon.max(), "count:", len(common_lon))

fcst = fcst.sel(latitude=common_lat, longitude=common_lon)
obs = obs.sel(lat=common_lat, lon=common_lon)

# ---------------------------------------------------------------------
# 3. Containers
# ---------------------------------------------------------------------
models = [str(x) for x in fcst.model.values]
init_times = fcst.init_time.values

forecast_arrays = []
observation_arrays = []

metrics = []

# ---------------------------------------------------------------------
# 4. Process each model / initialization / 24h window
# ---------------------------------------------------------------------
for model in models:

    for i, init_time in enumerate(init_times):

        model_window_fields = []

        for w, (start_h, end_h) in enumerate(zip(START_H, END_H)):

            start_step = np.timedelta64(int(start_h), "h")
            end_step = np.timedelta64(int(end_h), "h")

            # Cumulative precipitation from initialization.
            start_tp = fcst.precipitation_total_mm.sel(
                model=model,
                init_time=init_time,
                step=start_step
            )

            end_tp = fcst.precipitation_total_mm.sel(
                model=model,
                init_time=init_time,
                step=end_step
            )

            # 24-hour accumulation
            precip_24h = end_tp - start_tp

            # Prevent tiny numerical negatives from propagating.
            negative_count = int((precip_24h < 0).sum().values)

            precip_24h = precip_24h.clip(min=0)

            # Valid forecast time = initialization + end lead
            valid_time = np.datetime64(init_time) + end_step

            valid_date = pd.Timestamp(valid_time).normalize()

            # IMD daily rainfall for matching calendar date
            if valid_date < pd.Timestamp("2020-06-01") or valid_date > pd.Timestamp("2020-06-30"):
                continue

            obs_day = obs.rain.sel(
                time=np.datetime64(valid_date)
            )

            p = precip_24h.values.astype(np.float64).ravel()
            o = obs_day.values.astype(np.float64).ravel()

            # Exclude missing/masked IMD cells
            mask = np.isfinite(p) & np.isfinite(o)

            p = p[mask]
            o = o[mask]

            if len(p) == 0:
                continue

            error = p - o

            bias = float(np.mean(error))
            mae = float(np.mean(np.abs(error)))
            rmse = float(np.sqrt(np.mean(error ** 2)))

            if np.std(p) > 0 and np.std(o) > 0:
                correlation = float(np.corrcoef(p, o)[0, 1])
            else:
                correlation = np.nan

            # -----------------------------------------------------------------
            # Rain-event verification
            # -----------------------------------------------------------------
            row = {
                "model": model,
                "init_time": str(pd.Timestamp(init_time)),
                "valid_date": str(valid_date.date()),
                "start_lead_h": int(start_h),
                "end_lead_h": int(end_h),
                "n_valid_cells": int(len(p)),
                "forecast_mean_mm": float(np.mean(p)),
                "observed_mean_mm": float(np.mean(o)),
                "bias_mm": bias,
                "mae_mm": mae,
                "rmse_mm": rmse,
                "correlation": correlation,
                "negative_raw_cells": negative_count,
            }

            for threshold in [1.0, 15.6, 64.5]:

                forecast_event = p >= threshold
                obs_event = o >= threshold

                hits = int(np.sum(forecast_event & obs_event))
                misses = int(np.sum(~forecast_event & obs_event))
                false_alarms = int(np.sum(forecast_event & ~obs_event))

                pod_den = hits + misses
                far_den = hits + false_alarms
                csi_den = hits + misses + false_alarms

                pod = hits / pod_den if pod_den > 0 else np.nan
                far = false_alarms / far_den if far_den > 0 else np.nan
                csi = hits / csi_den if csi_den > 0 else np.nan

                suffix = str(threshold).replace(".", "_")

                row[f"POD_{suffix}mm"] = pod
                row[f"FAR_{suffix}mm"] = far
                row[f"CSI_{suffix}mm"] = csi
                row[f"hits_{suffix}mm"] = hits
                row[f"misses_{suffix}mm"] = misses
                row[f"false_alarms_{suffix}mm"] = false_alarms

            metrics.append(row)

# ---------------------------------------------------------------------
# 5. Build compact verification NetCDF
# ---------------------------------------------------------------------
print("\nCreating verification NetCDF...")

# Rebuild arrays in a clean deterministic order:
# model x init_time x window x latitude x longitude

model_data = []
obs_data_by_window = []
valid_time_matrix = []

for i, init_time in enumerate(init_times):

    init_obs_windows = []
    init_valid_times = []

    for start_h, end_h in zip(START_H, END_H):

        start_step = np.timedelta64(int(start_h), "h")
        end_step = np.timedelta64(int(end_h), "h")

        valid_time = np.datetime64(init_time) + end_step
        init_valid_times.append(valid_time)

        if pd.Timestamp(valid_time).normalize() >= pd.Timestamp("2020-06-01") and \
           pd.Timestamp(valid_time).normalize() <= pd.Timestamp("2020-06-30"):

            obs_day = obs.rain.sel(
                time=np.datetime64(pd.Timestamp(valid_time).normalize())
            )
            init_obs_windows.append(obs_day.values.astype(np.float32))
        else:
            init_obs_windows.append(
                np.full((len(common_lat), len(common_lon)), np.nan, dtype=np.float32)
            )

    obs_data_by_window.append(init_obs_windows)
    valid_time_matrix.append(init_valid_times)

# Forecast array
for model in models:

    model_windows = []

    for i, init_time in enumerate(init_times):

        init_windows = []

        for start_h, end_h in zip(START_H, END_H):

            start_step = np.timedelta64(int(start_h), "h")
            end_step = np.timedelta64(int(end_h), "h")

            start_tp = fcst.precipitation_total_mm.sel(
                model=model,
                init_time=init_time,
                step=start_step
            )

            end_tp = fcst.precipitation_total_mm.sel(
                model=model,
                init_time=init_time,
                step=end_step
            )

            precip_24h = (end_tp - start_tp).clip(min=0)

            init_windows.append(precip_24h.values.astype(np.float32))

        model_windows.append(init_windows)

    model_data.append(model_windows)

forecast_24h = np.asarray(model_data, dtype=np.float32)
obs_daily = np.asarray(obs_data_by_window, dtype=np.float32)

verification_ds = xr.Dataset(
    {
        "forecast_24h_mm": (
            ("model", "init_time", "window", "latitude", "longitude"),
            forecast_24h
        ),
        "imd_daily_rain_mm": (
            ("init_time", "window", "latitude", "longitude"),
            obs_daily
        ),
    },
    coords={
        "model": models,
        "init_time": init_times,
        "window": [0, 1, 2, 3],
        "start_lead_h": ("window", START_H),
        "end_lead_h": ("window", END_H),
        "valid_time": (
            ("init_time", "window"),
            np.asarray(valid_time_matrix)
        ),
        "latitude": common_lat,
        "longitude": common_lon,
    },
    attrs={
        "title": "AERIS Rainfall Verification Dataset",
        "description": "24-hour NCMRWF and ECMWF forecast rainfall compared against IMD daily gridded rainfall.",
        "forecast_accumulation_method": "TP(end_lead) - TP(start_lead)",
        "temporal_alignment": "Forecast windows ending at 00 UTC compared with IMD daily rainfall date.",
        "observation_source": "IMD 0.25 degree daily gridded rainfall",
        "note": "IMD missing/masked cells are excluded from verification metrics."
    }
)

os.makedirs(os.path.dirname(OUT_NC), exist_ok=True)
verification_ds.to_netcdf(OUT_NC)

# ---------------------------------------------------------------------
# 6. Save metrics
# ---------------------------------------------------------------------
metrics_df = pd.DataFrame(metrics)
metrics_df.to_csv(OUT_CSV, index=False)

print("\nSaved:")
print(OUT_NC)
print(OUT_CSV)

print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

summary = (
    metrics_df
    .groupby(["model", "end_lead_h"], as_index=False)
    .agg(
        RMSE_mm=("rmse_mm", "mean"),
        MAE_mm=("mae_mm", "mean"),
        Bias_mm=("bias_mm", "mean"),
        Correlation=("correlation", "mean"),
        CSI_1mm=("CSI_1_0mm", "mean"),
        CSI_15_6mm=("CSI_15_6mm", "mean"),
        CSI_64_5mm=("CSI_64_5mm", "mean"),
    )
)

print(summary.to_string(index=False))

print("\nNumber of verification cases:", len(metrics_df))
print("\nDone.")