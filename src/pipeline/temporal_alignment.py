"""Temporal alignment pipeline for forecast and observation data.

This module ensures:
- Forecast initialization times are correctly represented
- Valid times are computed from initialization + lead time
- Observations are aligned to forecast valid times
- No future information leaks into features
- Causal ordering is enforced
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr


@dataclass
class TimeAlignmentConfig:
    """Configuration for temporal alignment."""

    forecast_init_frequency: str = "12H"  # 00Z and 12Z
    forecast_lead_times: list[int] | None = None  # Hours, e.g., [6, 12, 24, 48, 72, 96, 120]
    observation_frequency: str = "1D"  # Daily
    observation_hour: int = 0  # UTC hour for daily observation
    timezone: str = "UTC"
    max_forecast_age_hours: int = 24  # Maximum age of forecast before considered stale


class TemporalAligner:
    """Align forecasts and observations in time while preventing leakage."""

    def __init__(self, config: TimeAlignmentConfig | None = None):
        self.config = config or TimeAlignmentConfig()
        if self.config.forecast_lead_times is None:
            self.config.forecast_lead_times = [6, 12, 24, 48, 72, 96, 120]

    def align_forecast_observation(
        self,
        forecast_ds: xr.Dataset,
        observation_ds: xr.Dataset,
        variable: str,
    ) -> xr.Dataset:
        """Align forecast and observation datasets.

        Args:
            forecast_ds: Forecast dataset with init_time, step, latitude, longitude
            observation_ds: Observation dataset with time, latitude, longitude
            variable: Variable name to align

        Returns:
            Aligned dataset with forecast and observation values

        Raises:
            ValueError: If temporal overlap cannot be found
        """
        # Extract time coordinates
        forecast_init_times = self._parse_time_coord(forecast_ds, "init_time")
        forecast_lead_times = self._parse_lead_coord(forecast_ds, "step")
        observation_times = self._parse_time_coord(observation_ds, "time")

        # Compute forecast valid times
        forecast_valid_times = []
        for init_time in forecast_init_times:
            for lead_hours in forecast_lead_times:
                valid_time = init_time + timedelta(hours=lead_hours)
                forecast_valid_times.append(valid_time)

        # Find overlapping time period
        obs_min = min(observation_times)
        obs_max = max(observation_times)
        fcst_min = min(forecast_valid_times)
        fcst_max = max(forecast_valid_times)

        overlap_start = max(obs_min, fcst_min)
        overlap_end = min(obs_max, fcst_max)

        if overlap_start >= overlap_end:
            raise ValueError(
                f"No temporal overlap between forecasts ({fcst_min} to {fcst_max}) "
                f"and observations ({obs_min} to {obs_max})"
            )

        # Filter to overlapping period
        valid_times = [t for t in forecast_valid_times if overlap_start <= t <= overlap_end]
        obs_times = [t for t in observation_times if overlap_start <= t <= overlap_end]

        # Build aligned dataset
        aligned = xr.Dataset()

        # Add forecast values
        if variable in forecast_ds.data_vars:
            aligned["forecast"] = forecast_ds[variable]

        # Add observation values
        if variable in observation_ds.data_vars:
            aligned["observation"] = observation_ds[variable]

        # Add metadata
        aligned.attrs["overlap_start"] = overlap_start.isoformat()
        aligned.attrs["overlap_end"] = overlap_end.isoformat()
        aligned.attrs["n_forecast_times"] = len(valid_times)
        aligned.attrs["n_observation_times"] = len(obs_times)

        return aligned

    def compute_valid_time(
        self,
        initialization_time: datetime,
        lead_hours: int,
    ) -> datetime:
        """Compute forecast valid time from initialization and lead time.

        Args:
            initialization_time: Forecast initialization time
            lead_hours: Lead time in hours

        Returns:
            Valid time (initialization + lead time)
        """
        if initialization_time.tzinfo is None:
            initialization_time = initialization_time.replace(tzinfo=timezone.utc)

        if lead_hours < 0:
            raise ValueError(f"Lead time must be non-negative, got {lead_hours}")

        valid_time = initialization_time + timedelta(hours=lead_hours)
        return valid_time

    def check_causal_ordering(
        self,
        feature_time: datetime,
        forecast_init_time: datetime,
        target_time: datetime,
    ) -> bool:
        """Check that causal ordering is maintained.

        Must satisfy: feature_time <= forecast_init_time < target_time

        Args:
            feature_time: Time when feature information is available
            forecast_init_time: Forecast initialization time
            target_time: Target observation time

        Returns:
            True if causal ordering is maintained

        Raises:
            ValueError: If causal ordering is violated
        """
        if feature_time.tzinfo is None:
            feature_time = feature_time.replace(tzinfo=timezone.utc)
        if forecast_init_time.tzinfo is None:
            forecast_init_time = forecast_init_time.replace(tzinfo=timezone.utc)
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)

        if feature_time > forecast_init_time:
            raise ValueError(
                f"CAUSAL VIOLATION: feature_time ({feature_time}) > "
                f"forecast_init_time ({forecast_init_time})"
            )

        if forecast_init_time >= target_time:
            raise ValueError(
                f"CAUSAL VIOLATION: forecast_init_time ({forecast_init_time}) >= "
                f"target_time ({target_time})"
            )

        return True

    def find_observation_for_forecast(
        self,
        forecast_valid_time: datetime,
        observation_times: list[datetime],
        observation_values: list[float],
        max_delta_hours: int = 3,
    ) -> tuple[datetime, float] | None:
        """Find observation closest to forecast valid time.

        Args:
            forecast_valid_time: Forecast valid time
            observation_times: List of observation times
            observation_values: Corresponding observation values
            max_delta_hours: Maximum allowed time difference

        Returns:
            Tuple of (observation_time, observation_value) or None if no match
        """
        if forecast_valid_time.tzinfo is None:
            forecast_valid_time = forecast_valid_time.replace(tzinfo=timezone.utc)

        # Find closest observation
        deltas = [abs((t - forecast_valid_time).total_seconds() / 3600) for t in observation_times]
        min_delta_idx = int(np.argmin(deltas))
        min_delta = deltas[min_delta_idx]

        if min_delta > max_delta_hours:
            return None

        return observation_times[min_delta_idx], observation_values[min_delta_idx]

    def build_training_sample(
        self,
        forecast_init_time: datetime,
        lead_hours: int,
        forecast_value: float,
        observation_value: float,
        feature_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Build a single training sample with causal validation.

        Args:
            forecast_init_time: Forecast initialization time
            lead_hours: Lead time in hours
            forecast_value: Forecast value
            observation_value: Observation value
            feature_time: Time when feature information is available (defaults to init_time)

        Returns:
            Dictionary representing a training sample
        """
        if feature_time is None:
            feature_time = forecast_init_time

        valid_time = self.compute_valid_time(forecast_init_time, lead_hours)

        # Validate causal ordering
        self.check_causal_ordering(feature_time, forecast_init_time, valid_time)

        sample = {
            "initialization_time": forecast_init_time,
            "valid_time": valid_time,
            "lead_hours": lead_hours,
            "forecast_value": forecast_value,
            "observation_value": observation_value,
            "feature_information_time": feature_time,
            "sample_id": f"{forecast_init_time.isoformat()}_{lead_hours}h",
        }

        return sample

    def create_training_dataframe(
        self,
        forecast_ds: xr.Dataset,
        observation_ds: xr.Dataset,
        variable: str,
    ) -> pd.DataFrame:
        """Create a training DataFrame from aligned forecast and observation data.

        Args:
            forecast_ds: Forecast dataset
            observation_ds: Observation dataset
            variable: Variable name

        Returns:
            DataFrame with training samples
        """
        samples = []

        # Get forecast initialization times
        init_times = self._parse_time_coord(forecast_ds, "init_time")
        lead_times = self._parse_lead_coord(forecast_ds, "step")

        # Get observation times and values
        obs_times = self._parse_time_coord(observation_ds, "time")
        obs_values = observation_ds[variable].values if variable in observation_ds.data_vars else []

        # For each forecast run
        for init_time in init_times:
            for lead_hours in lead_times:
                valid_time = self.compute_valid_time(init_time, lead_hours)

                # Find matching observation
                obs_match = self.find_observation_for_forecast(
                    valid_time,
                    obs_times,
                    obs_values,
                    max_delta_hours=12,  # Allow 12-hour tolerance for daily data
                )

                if obs_match is None:
                    continue

                obs_time, obs_value = obs_match

                # Get forecast value (simplified - would need actual grid extraction)
                forecast_value = 0.0  # Placeholder

                sample = self.build_training_sample(
                    init_time,
                    lead_hours,
                    forecast_value,
                    obs_value,
                    feature_time=init_time,
                )

                samples.append(sample)

        if not samples:
            raise ValueError("No training samples could be created - check temporal alignment")

        return pd.DataFrame(samples)

    def _parse_time_coord(self, ds: xr.Dataset, coord_name: str) -> list[datetime]:
        """Parse time coordinate from dataset."""
        time_var = ds.coords.get(coord_name)
        if time_var is None:
            raise ValueError(f"Dataset missing coordinate: {coord_name}")

        times = []
        for t in time_var.values:
            if isinstance(t, np.datetime64):
                dt = pd.Timestamp(t).to_pydatetime()
            elif isinstance(t, datetime):
                dt = t
            else:
                # Try parsing as cftime
                try:
                    import cftime

                    if isinstance(t, cftime.datetime):
                        dt = datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
                    else:
                        dt = pd.Timestamp(t).to_pydatetime()
                except ImportError:
                    dt = pd.Timestamp(t).to_pydatetime()

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            times.append(dt)

        return times

    def _parse_lead_coord(self, ds: xr.Dataset, coord_name: str) -> list[int]:
        """Parse lead time coordinate from dataset."""
        lead_var = ds.coords.get(coord_name)
        if lead_var is None:
            raise ValueError(f"Dataset missing coordinate: {coord_name}")

        leads = []
        for lead in lead_var.values:
            # Convert to hours if in seconds
            if lead > 10000:
                lead_hours = int(lead / 3600)
            else:
                lead_hours = int(lead)
            leads.append(lead_hours)

        return leads


def validate_temporal_overlap(
    forecast_ds: xr.Dataset,
    observation_ds: xr.Dataset,
) -> dict[str, Any]:
    """Validate that forecast and observation datasets have temporal overlap.

    Args:
        forecast_ds: Forecast dataset
        observation_ds: Observation dataset

    Returns:
        Dictionary with overlap information
    """
    aligner = TemporalAligner()

    try:
        # Parse time coordinates
        forecast_init_times = aligner._parse_time_coord(forecast_ds, "init_time")
        forecast_lead_times = aligner._parse_lead_coord(forecast_ds, "step")
        observation_times = aligner._parse_time_coord(observation_ds, "time")

        # Compute forecast valid times
        forecast_valid_times = []
        for init_time in forecast_init_times:
            for lead_hours in forecast_lead_times:
                valid_time = init_time + timedelta(hours=lead_hours)
                forecast_valid_times.append(valid_time)

        # Check overlap
        obs_min = min(observation_times)
        obs_max = max(observation_times)
        fcst_min = min(forecast_valid_times)
        fcst_max = max(forecast_valid_times)

        overlap_start = max(obs_min, fcst_min)
        overlap_end = min(obs_max, fcst_max)

        has_overlap = overlap_start < overlap_end

        return {
            "has_overlap": has_overlap,
            "forecast_period": (fcst_min.isoformat(), fcst_max.isoformat()),
            "observation_period": (obs_min.isoformat(), obs_max.isoformat()),
            "overlap_period": (overlap_start.isoformat(), overlap_end.isoformat()) if has_overlap else None,
            "n_forecast_init_times": len(forecast_init_times),
            "n_forecast_lead_times": len(forecast_lead_times),
            "n_forecast_valid_times": len(forecast_valid_times),
            "n_observation_times": len(observation_times),
        }

    except Exception as e:
        return {
            "has_overlap": False,
            "error": str(e),
        }
