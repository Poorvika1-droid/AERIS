"""Quality control pipeline for weather data.

This module handles:
- Range checks for meteorological variables
- Missing value detection and handling
- Outlier detection
- Temporal consistency checks
- Spatial consistency checks
- Data provenance validation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr


@dataclass
class VariableQCConfig:
    """Quality control configuration for a variable."""

    name: str
    units: str
    min_value: float | None = None
    max_value: float | None = None
    missing_value: float | None = None
    outlier_std_threshold: float = 5.0  # Number of standard deviations
    allow_negative: bool = True
    check_temporal_consistency: bool = True
    check_spatial_consistency: bool = True


# Common QC configurations
QC_CONFIGS = {
    "RAINFALL": VariableQCConfig(
        name="RAINFALL",
        units="mm",
        min_value=0.0,
        max_value=1000.0,  # Daily maximum realistic
        missing_value=-999.0,
        allow_negative=False,
        outlier_std_threshold=5.0,
    ),
    "TEMPERATURE": VariableQCConfig(
        name="TEMPERATURE",
        units="degC",
        min_value=-50.0,
        max_value=60.0,
        missing_value=-999.0,
        allow_negative=True,
        outlier_std_threshold=5.0,
    ),
    "WIND_SPEED": VariableQCConfig(
        name="WIND_SPEED",
        units="m/s",
        min_value=0.0,
        max_value=100.0,
        missing_value=-999.0,
        allow_negative=False,
        outlier_std_threshold=5.0,
    ),
    "PRESSURE": VariableQCConfig(
        name="PRESSURE",
        units="hPa",
        min_value=800.0,
        max_value=1100.0,
        missing_value=-999.0,
        allow_negative=True,
        outlier_std_threshold=5.0,
    ),
}


@dataclass
class QCResult:
    """Result of quality control check."""

    passed: bool
    n_total: int
    n_valid: int
    n_missing: int
    n_out_of_range: int
    n_outliers: int
    flags: np.ndarray  # Same shape as data, 0=valid, 1=missing, 2=out_of_range, 3=outlier
    messages: list[str]


class QualityController:
    """Perform quality control on weather data."""

    def __init__(self, configs: dict[str, VariableQCConfig] | None = None):
        """Initialize with QC configurations.

        Args:
            configs: Dictionary of variable names to QC configs
        """
        self.configs = configs or QC_CONFIGS

    def check_dataset(
        self,
        ds: xr.Dataset,
        variable: str,
    ) -> QCResult:
        """Run all QC checks on a dataset variable.

        Args:
            ds: Dataset to check
            variable: Variable name to check

        Returns:
            QCResult with check results
        """
        if variable not in ds.data_vars:
            raise ValueError(f"Variable {variable} not found in dataset")

        config = self.configs.get(variable.upper())
        if config is None:
            # Use default config
            config = VariableQCConfig(name=variable, units="unknown")

        data = ds[variable].values
        flags = np.zeros_like(data, dtype=int)
        messages = []

        # Check for missing values
        if config.missing_value is not None:
            missing_mask = np.abs(data - config.missing_value) < 1e-6
            flags[missing_mask] = 1
            n_missing = int(np.sum(missing_mask))
            if n_missing > 0:
                messages.append(f"Found {n_missing} missing values")
        else:
            missing_mask = np.isnan(data)
            flags[missing_mask] = 1
            n_missing = int(np.sum(missing_mask))
            if n_missing > 0:
                messages.append(f"Found {n_missing} NaN values")

        # Check range
        if config.min_value is not None or config.max_value is not None:
            valid_mask = ~np.isnan(data) & (flags == 0)
            if config.min_value is not None:
                out_of_range_min = valid_mask & (data < config.min_value)
                flags[out_of_range_min] = 2
                n_min = int(np.sum(out_of_range_min))
                if n_min > 0:
                    messages.append(f"Found {n_min} values below minimum ({config.min_value})")

            if config.max_value is not None:
                out_of_range_max = valid_mask & (data > config.max_value)
                flags[out_of_range_max] = 2
                n_max = int(np.sum(out_of_range_max))
                if n_max > 0:
                    messages.append(f"Found {n_max} values above maximum ({config.max_value})")

        # Check for outliers using standard deviation
        if config.outlier_std_threshold is not None:
            valid_mask = ~np.isnan(data) & (flags == 0)
            if np.sum(valid_mask) > 10:  # Need enough data points
                valid_data = data[valid_mask]
                mean = np.mean(valid_data)
                std = np.std(valid_data)
                if std > 0:
                    outlier_mask = valid_mask & (np.abs(data - mean) > config.outlier_std_threshold * std)
                    flags[outlier_mask] = 3
                    n_outliers = int(np.sum(outlier_mask))
                    if n_outliers > 0:
                        messages.append(f"Found {n_outliers} statistical outliers (> {config.outlier_std_threshold} std)")

        # Count results
        n_total = int(data.size)
        n_valid = int(np.sum(flags == 0))
        n_missing = int(np.sum(flags == 1))
        n_out_of_range = int(np.sum(flags == 2))
        n_outliers = int(np.sum(flags == 3))

        passed = n_valid > 0

        return QCResult(
            passed=passed,
            n_total=n_total,
            n_valid=n_valid,
            n_missing=n_missing,
            n_out_of_range=n_out_of_range,
            n_outliers=n_outliers,
            flags=flags,
            messages=messages,
        )

    def apply_qc_flags(
        self,
        ds: xr.Dataset,
        variable: str,
        qc_result: QCResult,
        action: str = "mask",
    ) -> xr.Dataset:
        """Apply QC flags to dataset.

        Args:
            ds: Dataset to modify
            variable: Variable to modify
            qc_result: QC result with flags
            action: Action to take on flagged values
                - "mask": Set to NaN
                - "fill": Fill with fill value
                - "remove": Remove from dataset (not recommended for gridded data)

        Returns:
            Dataset with QC applied
        """
        result = ds.copy()

        if variable not in result.data_vars:
            raise ValueError(f"Variable {variable} not found in dataset")

        data = result[variable].values
        flags = qc_result.flags

        if action == "mask":
            data[flags > 0] = np.nan
        elif action == "fill":
            # Fill with mean of valid values
            valid_data = data[flags == 0]
            if len(valid_data) > 0:
                fill_value = np.nanmean(valid_data)
                data[flags > 0] = fill_value
            else:
                data[flags > 0] = 0.0
        elif action == "remove":
            raise NotImplementedError("Remove action not implemented for gridded data")
        else:
            raise ValueError(f"Unknown action: {action}")

        result[variable].values = data

        # Add QC metadata
        result[variable].attrs["qc_applied"] = True
        result[variable].attrs["qc_action"] = action
        result[variable].attrs["qc_flags"] = flags.tolist() if flags.size < 1000 else "too_large_to_store"

        return result

    def check_temporal_consistency(
        self,
        ds: xr.Dataset,
        variable: str,
        max_delta: float | None = None,
    ) -> dict[str, Any]:
        """Check temporal consistency of time series.

        Args:
            ds: Dataset with time dimension
            variable: Variable to check
            max_delta: Maximum allowed change between consecutive time steps

        Returns:
            Dictionary with consistency check results
        """
        if variable not in ds.data_vars:
            raise ValueError(f"Variable {variable} not found in dataset")

        data = ds[variable].values

        # Check if time dimension exists
        time_dim = None
        for dim in data.shape:
            if dim in ds.dims and any(t in ds.dims[dim] for t in ["time", "TIME", "init_time"]):
                time_dim = dim
                break

        if time_dim is None:
            return {"has_time_dimension": False, "message": "No time dimension found"}

        # Compute differences along time axis
        if len(data.shape) == 1:
            diffs = np.abs(np.diff(data))
        else:
            # Compute along first dimension
            diffs = np.abs(np.diff(data, axis=0))

        # Find large jumps
        if max_delta is None:
            # Use 3x standard deviation as threshold
            mean_diff = np.nanmean(diffs)
            std_diff = np.nanstd(diffs)
            max_delta = mean_diff + 3 * std_diff

        large_jumps = diffs > max_delta
        n_jumps = int(np.sum(large_jumps))

        return {
            "has_time_dimension": True,
            "n_large_jumps": n_jumps,
            "max_delta_threshold": max_delta,
            "max_observed_delta": float(np.nanmax(diffs)) if len(diffs) > 0 else 0.0,
            "passed": n_jumps == 0,
        }

    def check_spatial_consistency(
        self,
        ds: xr.Dataset,
        variable: str,
        max_gradient: float | None = None,
    ) -> dict[str, Any]:
        """Check spatial consistency of gridded data.

        Args:
            ds: Dataset with spatial dimensions
            variable: Variable to check
            max_gradient: Maximum allowed spatial gradient

        Returns:
            Dictionary with consistency check results
        """
        if variable not in ds.data_vars:
            raise ValueError(f"Variable {variable} not found in dataset")

        data = ds[variable].values

        # Check if spatial dimensions exist
        has_lat = any("lat" in d.lower() for d in ds.dims)
        has_lon = any("lon" in d.lower() for d in ds.dims)

        if not (has_lat and has_lon):
            return {"has_spatial_dimensions": False, "message": "No spatial dimensions found"}

        # Compute spatial gradients
        # Simplified - use numpy gradient
        if len(data.shape) == 2:
            grad_lat, grad_lon = np.gradient(data)
            max_grad = np.nanmax(np.sqrt(grad_lat**2 + grad_lon**2))
        else:
            # For multi-dimensional data, check first 2D slice
            if len(data.shape) >= 2:
                grad_lat, grad_lon = np.gradient(data[0, :, :])
                max_grad = np.nanmax(np.sqrt(grad_lat**2 + grad_lon**2))
            else:
                return {"has_spatial_dimensions": True, "message": "Unexpected data shape"}

        if max_gradient is None:
            # Use 3x mean gradient as threshold
            mean_grad = np.nanmean(np.sqrt(grad_lat**2 + grad_lon**2))
            max_gradient = mean_grad * 3

        has_large_gradients = max_grad > max_gradient

        return {
            "has_spatial_dimensions": True,
            "max_spatial_gradient": float(max_grad),
            "max_gradient_threshold": max_gradient,
            "passed": not has_large_gradients,
        }

    def generate_qc_report(
        self,
        ds: xr.Dataset,
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive QC report for dataset.

        Args:
            ds: Dataset to check
            variables: Variables to check (all if None)

        Returns:
            Dictionary with QC report
        """
        if variables is None:
            variables = list(ds.data_vars.keys())

        report = {
            "dataset": str(ds),
            "variables_checked": [],
            "overall_passed": True,
        }

        for var in variables:
            try:
                qc_result = self.check_dataset(ds, var)
                temporal_check = self.check_temporal_consistency(ds, var)
                spatial_check = self.check_spatial_consistency(ds, var)

                var_report = {
                    "variable": var,
                    "qc_passed": qc_result.passed,
                    "n_total": qc_result.n_total,
                    "n_valid": qc_result.n_valid,
                    "n_missing": qc_result.n_missing,
                    "n_out_of_range": qc_result.n_out_of_range,
                    "n_outliers": qc_result.n_outliers,
                    "messages": qc_result.messages,
                    "temporal_consistency": temporal_check,
                    "spatial_consistency": spatial_check,
                }

                report["variables_checked"].append(var_report)

                if not qc_result.passed:
                    report["overall_passed"] = False

            except Exception as e:
                report["variables_checked"].append(
                    {
                        "variable": var,
                        "error": str(e),
                    }
                )
                report["overall_passed"] = False

        return report


def validate_provenance(ds: xr.Dataset, required_attrs: list[str]) -> dict[str, Any]:
    """Validate that dataset has required provenance metadata.

    Args:
        ds: Dataset to validate
        required_attrs: List of required attribute names

    Returns:
        Dictionary with validation results
    """
    missing = []
    present = []

    for attr in required_attrs:
        if attr in ds.attrs:
            present.append(attr)
        else:
            missing.append(attr)

    return {
        "has_all_required": len(missing) == 0,
        "present_attributes": present,
        "missing_attributes": missing,
    }
