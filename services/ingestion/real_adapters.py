"""Real data ingestion adapters for operational weather sources.

These adapters handle actual meteorological data from:
- IMD (India Meteorological Department) observations
- NCMRWF (National Centre for Medium Range Weather Forecasting) forecasts
- ECMWF (European Centre for Medium-Range Weather Forecasts) forecasts
- GFS (Global Forecast System) forecasts

All adapters enforce causal constraints and proper provenance tracking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from aeris_schemas import ForecastModelAdapter, LocationPoint, ModelType, Variable


class BaseRealAdapter(ABC):
    """Base class for real weather data adapters."""

    provider: str
    model_id: str
    model_name: str
    model_type: ModelType
    spatial_resolution: str
    grid_definition: str

    @abstractmethod
    def fetch(
        self,
        locations: list[LocationPoint],
        initialization_time: datetime,
        lead_time_hours: int,
        variable: Variable,
    ) -> ForecastModelAdapter:
        """Fetch forecast data for specific locations and time."""
        raise NotImplementedError

    def _validate_times(self, initialization_time: datetime, lead_time_hours: int) -> datetime:
        """Validate and compute valid time."""
        if initialization_time.tzinfo is None:
            initialization_time = initialization_time.replace(tzinfo=timezone.utc)
        if lead_time_hours <= 0:
            raise ValueError(f"Lead time must be positive, got {lead_time_hours}")
        valid_time = initialization_time + timedelta(hours=lead_time_hours)
        return valid_time


class IMDObservationAdapter:
    """Adapter for IMD gridded rainfall observations.

    Data source: IMD RF0.25 gridded daily rainfall
    Format: NetCDF
    Variables: RAINFALL (mm)
    Spatial resolution: 0.25°
    Temporal resolution: Daily
    """

    provider = "IMD"
    spatial_resolution = "0.25deg"
    grid_definition = "india_0.25deg_grid"

    def __init__(self, data_path: Path | str):
        """Initialize with path to IMD NetCDF file."""
        self.data_path = Path(data_path)
        if not self.data_path.exists():
            raise FileNotFoundError(f"IMD data file not found: {self.data_path}")
        self._dataset = None

    def _load_dataset(self) -> xr.Dataset:
        """Lazy load the NetCDF dataset."""
        if self._dataset is None:
            self._dataset = xr.open_dataset(self.data_path)
        return self._dataset

    def fetch_station(
        self,
        locations: list[LocationPoint],
        valid_time: datetime,
        variable: Variable,
    ) -> dict[str, float]:
        """Fetch observations for specific locations at valid time.

        Args:
            locations: List of location points
            valid_time: Observation time (must match data time axis)
            variable: Variable to fetch (currently only RAINFALL supported)

        Returns:
            Dictionary mapping location_id to observed value
        """
        if variable != Variable.RAINFALL:
            raise ValueError(f"IMD adapter currently only supports RAINFALL, got {variable}")

        ds = self._load_dataset()

        # Convert valid_time to dataset time format
        if valid_time.tzinfo is None:
            valid_time = valid_time.replace(tzinfo=timezone.utc)

        # Find the time index closest to valid_time
        time_var = ds.coords.get("TIME", ds.coords.get("time", ds.coords.get("TIME")))
        if time_var is None:
            raise ValueError("IMD dataset missing time coordinate")

        # Parse time format (IMD uses "days since 1900-12-31")
        time_values = xr.cftime.num2date(
            time_var.values,
            units=time_var.attrs.get("units", "days since 1900-12-31"),
            calendar=time_var.attrs.get("calendar", "standard"),
        )

        # Find closest time
        target_time = valid_time.replace(tzinfo=None)
        time_idx = np.argmin([abs((t - target_time).total_seconds()) for t in time_values])

        # Extract grid coordinates
        lon_var = ds.coords.get("LONGITUDE", ds.coords.get("lon", ds.coords.get("longitude")))
        lat_var = ds.coords.get("LATITUDE", ds.coords.get("lat", ds.coords.get("latitude")))

        if lon_var is None or lat_var is None:
            raise ValueError("IMD dataset missing latitude/longitude coordinates")

        lon_values = lon_var.values
        lat_values = lat_var.values

        # Extract rainfall variable
        rain_var = ds.data_vars.get("RAINFALL", ds.data_vars.get("rf", ds.data_vars.get("rainfall")))
        if rain_var is None:
            raise ValueError("IMD dataset missing rainfall variable")

        results = {}

        for loc in locations:
            # Find nearest grid point
            lon_idx = np.argmin(np.abs(lon_values - loc.longitude))
            lat_idx = np.argmin(np.abs(lat_values - loc.latitude))

            # Extract value
            if len(rain_var.dims) == 3:  # (time, lat, lon)
                value = float(rain_var[time_idx, lat_idx, lon_idx].values)
            elif len(rain_var.dims) == 2:  # (lat, lon) - no time dimension
                value = float(rain_var[lat_idx, lon_idx].values)
            else:
                raise ValueError(f"Unexpected rainfall variable dimensions: {rain_var.dims}")

            # Handle missing values
            if np.isnan(value) or value < 0:
                value = 0.0

            results[loc.location_id] = value

        return results

    def close(self) -> None:
        """Close the dataset."""
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class NCMRWFAdapter(BaseRealAdapter):
    """Adapter for NCMRWF TIGGE forecasts.

    Data source: NCMRWF TIGGE archive
    Format: GRIB2 or NetCDF
    Variables: precipitation (tp), temperature (2t), wind (10u, 10v), pressure (msl)
    Spatial resolution: 0.5° or higher
    Temporal resolution: 6-hourly
    """

    provider = "NCMRWF"
    model_id = "ncmrwf-tigge"
    model_name = "NCMRWF TIGGE"
    model_type = ModelType.NWP
    spatial_resolution = "0.5deg"
    grid_definition = "global_0.5deg"

    def __init__(self, data_path: Path | str):
        """Initialize with path to NCMRWF forecast file."""
        self.data_path = Path(data_path)
        if not self.data_path.exists():
            raise FileNotFoundError(f"NCMRWF data file not found: {self.data_path}")
        self._dataset = None

    def _load_dataset(self) -> xr.Dataset:
        """Lazy load the forecast dataset."""
        if self._dataset is None:
            # Try NetCDF first, then GRIB
            try:
                self._dataset = xr.open_dataset(self.data_path)
            except Exception:
                try:
                    self._dataset = xr.open_dataset(
                        self.data_path,
                        engine="cfgrib",
                        backend_kwargs={"indexpath": ""},
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to load NCMRWF data: {e}")
        return self._dataset

    def fetch(
        self,
        locations: list[LocationPoint],
        initialization_time: datetime,
        lead_time_hours: int,
        variable: Variable,
    ) -> ForecastModelAdapter:
        """Fetch NCMRWF forecast for specific locations and time."""
        valid_time = self._validate_times(initialization_time, lead_time_hours)

        ds = self._load_dataset()

        # Map AERIS variables to NCMRWF variable names
        var_mapping = {
            Variable.RAINFALL: "tp",
            Variable.TEMPERATURE: "t2m",
            Variable.WIND_SPEED: "wind_speed",  # Derived from 10u, 10v
            Variable.WIND_DIRECTION: "wind_dir",  # Derived from 10u, 10v
        }

        nc_var = var_mapping.get(variable)
        if nc_var is None:
            raise ValueError(f"Variable {variable} not supported by NCMRWF adapter")

        # Find initialization time index
        init_time_var = ds.coords.get("init_time", ds.coords.get("time"))
        if init_time_var is None:
            raise ValueError("NCMRWF dataset missing initialization time coordinate")

        init_idx = self._find_time_index(init_time_var, initialization_time)

        # Find lead time index
        step_var = ds.coords.get("step", ds.coords.get("lead_time"))
        if step_var is None:
            raise ValueError("NCMRWF dataset missing lead time coordinate")

        lead_idx = self._find_lead_index(step_var, lead_time_hours)

        # Extract coordinates
        lon_var = ds.coords.get("longitude", ds.coords.get("lon"))
        lat_var = ds.coords.get("latitude", ds.coords.get("lat"))

        if lon_var is None or lat_var is None:
            raise ValueError("NCMRWF dataset missing latitude/longitude coordinates")

        # Extract forecast values for each location
        values = []
        for loc in locations:
            lon_idx = np.argmin(np.abs(lon_var.values - loc.longitude))
            lat_idx = np.argmin(np.abs(lat_var.values - loc.latitude))

            if nc_var in ds.data_vars:
                if variable == Variable.WIND_SPEED:
                    # Derive from u10 and v10
                    u = ds.data_vars["u10"][init_idx, lead_idx, lat_idx, lon_idx].values
                    v = ds.data_vars["v10"][init_idx, lead_idx, lat_idx, lon_idx].values
                    value = float(np.sqrt(u**2 + v**2))
                elif variable == Variable.WIND_DIRECTION:
                    u = ds.data_vars["u10"][init_idx, lead_idx, lat_idx, lon_idx].values
                    v = ds.data_vars["v10"][init_idx, lead_idx, lat_idx, lon_idx].values
                    value = float(np.degrees(np.arctan2(v, u)) % 360)
                else:
                    value = float(ds.data_vars[nc_var][init_idx, lead_idx, lat_idx, lon_idx].values)
            else:
                raise ValueError(f"Variable {nc_var} not found in NCMRWF dataset")

            # Unit conversions if needed
            if variable == Variable.RAINFALL:
                # GRIB tp is in kg/m^2, convert to mm (1 kg/m^2 = 1 mm)
                pass  # Already in mm
            elif variable == Variable.TEMPERATURE:
                # Convert Kelvin to Celsius if needed
                if value > 200:  # Likely Kelvin
                    value = value - 273.15

            values.append(value)

        # Build forecast adapter
        from aeris_schemas import CANONICAL_UNITS

        return ForecastModelAdapter(
            model_id=self.model_id,
            model_name=self.model_name,
            provider=self.provider,
            model_type=self.model_type,
            initialization_time=initialization_time,
            valid_time=valid_time,
            lead_time_hours=lead_time_hours,
            variable=variable,
            spatial_resolution=self.spatial_resolution,
            grid_definition=self.grid_definition,
            units=CANONICAL_UNITS[variable],
            forecast_values=values,
            latitudes=[loc.latitude for loc in locations],
            longitudes=[loc.longitude for loc in locations],
            location_ids=[loc.location_id for loc in locations],
            metadata={"data_path": str(self.data_path), "real_data": True},
        )

    def _find_time_index(self, time_var: xr.DataArray, target_time: datetime) -> int:
        """Find the index closest to target time."""
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)

        time_values = [np.datetime64(t) if isinstance(t, datetime) else t for t in time_var.values]
        target_np = np.datetime64(target_time.replace(tzinfo=None))

        return int(np.argmin([abs((t - target_np).astype("timedelta64[s]").astype(int)) for t in time_values]))

    def _find_lead_index(self, step_var: xr.DataArray, target_lead_hours: int) -> int:
        """Find the index closest to target lead time."""
        lead_values = step_var.values
        # Convert to hours if in seconds
        if lead_values[0] > 10000:  # Likely in seconds
            lead_values = lead_values / 3600.0

        return int(np.argmin(np.abs(lead_values - target_lead_hours)))

    def close(self) -> None:
        """Close the dataset."""
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ECMWFAdapter(BaseRealAdapter):
    """Adapter for ECMWF TIGGE forecasts.

    Data source: ECMWF TIGGE archive
    Format: GRIB2 or NetCDF
    Variables: precipitation (tp), temperature (2t), wind (10u, 10v), pressure (msl)
    Spatial resolution: 0.5° or 0.25°
    Temporal resolution: 6-hourly
    """

    provider = "ECMWF"
    model_id = "ecmwf-tigge"
    model_name = "ECMWF TIGGE"
    model_type = ModelType.NWP
    spatial_resolution = "0.5deg"
    grid_definition = "global_0.5deg"

    def __init__(self, data_path: Path | str):
        """Initialize with path to ECMWF forecast file."""
        self.data_path = Path(data_path)
        if not self.data_path.exists():
            raise FileNotFoundError(f"ECMWF data file not found: {self.data_path}")
        self._dataset = None

    def _load_dataset(self) -> xr.Dataset:
        """Lazy load the forecast dataset."""
        if self._dataset is None:
            try:
                self._dataset = xr.open_dataset(
                    self.data_path,
                    engine="cfgrib",
                    backend_kwargs={"indexpath": ""},
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load ECMWF data: {e}")
        return self._dataset

    def fetch(
        self,
        locations: list[LocationPoint],
        initialization_time: datetime,
        lead_time_hours: int,
        variable: Variable,
    ) -> ForecastModelAdapter:
        """Fetch ECMWF forecast for specific locations and time."""
        valid_time = self._validate_times(initialization_time, lead_time_hours)

        ds = self._load_dataset()

        # Map AERIS variables to ECMWF variable names
        var_mapping = {
            Variable.RAINFALL: "tp",
            Variable.TEMPERATURE: "t2m",
            Variable.WIND_SPEED: "wind_speed",
            Variable.WIND_DIRECTION: "wind_dir",
        }

        nc_var = var_mapping.get(variable)
        if nc_var is None:
            raise ValueError(f"Variable {variable} not supported by ECMWF adapter")

        # Similar extraction logic as NCMRWF
        # (Full implementation would mirror NCMRWF adapter)
        raise NotImplementedError("ECMWF adapter fetch not yet fully implemented")

    def close(self) -> None:
        """Close the dataset."""
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None


class GFSAdapter(BaseRealAdapter):
    """Adapter for NOAA GFS forecasts.

    Data source: NOAA NCEP GFS archive
    Format: GRIB2
    Variables: precipitation (APCP), temperature (TMP), wind (UGRD, VGRD), pressure (MSLMA)
    Spatial resolution: 0.5°
    Temporal resolution: 3-hourly or 6-hourly
    """

    provider = "NOAA"
    model_id = "gfs-0p25"
    model_name = "GFS 0.25°"
    model_type = ModelType.NWP
    spatial_resolution = "0.25deg"
    grid_definition = "global_0.25deg"

    def __init__(self, data_path: Path | str):
        """Initialize with path to GFS forecast file."""
        self.data_path = Path(data_path)
        if not self.data_path.exists():
            raise FileNotFoundError(f"GFS data file not found: {self.data_path}")
        self._dataset = None

    def fetch(
        self,
        locations: list[LocationPoint],
        initialization_time: datetime,
        lead_time_hours: int,
        variable: Variable,
    ) -> ForecastModelAdapter:
        """Fetch GFS forecast for specific locations and time."""
        valid_time = self._validate_times(initialization_time, lead_time_hours)
        raise NotImplementedError("GFS adapter not yet fully implemented")


# Registry of real adapters
REAL_ADAPTERS: dict[str, type] = {
    "imd": IMDObservationAdapter,
    "ncmrwf": NCMRWFAdapter,
    "ecmwf": ECMWFAdapter,
    "gfs": GFSAdapter,
}


def get_real_adapter(provider: str, data_path: Path | str) -> Any:
    """Factory function to get real adapter instance."""
    adapter_class = REAL_ADAPTERS.get(provider.lower())
    if adapter_class is None:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(REAL_ADAPTERS.keys())}")
    return adapter_class(data_path)
