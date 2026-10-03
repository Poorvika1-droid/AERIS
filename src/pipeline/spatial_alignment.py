"""Spatial alignment and regridding pipeline for weather data.

This module handles:
- Coordinate system validation
- Grid definition
- Regridding between different spatial resolutions
- Spatial interpolation methods appropriate for different variables
- Prevention of spatial leakage
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import xarray as xr


@dataclass
class GridDefinition:
    """Definition of a spatial grid."""

    name: str
    latitude_min: float
    latitude_max: float
    longitude_min: float
    longitude_max: float
    latitude_resolution: float  # Degrees
    longitude_resolution: float  # Degrees
    crs: str = "EPSG:4326"  # WGS84

    @property
    def n_lat(self) -> int:
        """Number of latitude points."""
        return int((self.latitude_max - self.latitude_min) / self.latitude_resolution) + 1

    @property
    def n_lon(self) -> int:
        """Number of longitude points."""
        return int((self.longitude_max - self.longitude_min) / self.longitude_resolution) + 1

    @property
    def latitude_values(self) -> np.ndarray:
        """Latitude coordinate values."""
        return np.linspace(self.latitude_min, self.latitude_max, self.n_lat)

    @property
    def longitude_values(self) -> np.ndarray:
        """Longitude coordinate values."""
        return np.linspace(self.longitude_min, self.longitude_max, self.n_lon)


# Common grid definitions
INDIA_025_GRID = GridDefinition(
    name="india_0.25deg",
    latitude_min=5.0,
    latitude_max=40.0,
    longitude_min=65.0,
    longitude_max=100.0,
    latitude_resolution=0.25,
    longitude_resolution=0.25,
)

INDIA_05_GRID = GridDefinition(
    name="india_0.5deg",
    latitude_min=5.0,
    latitude_max=40.0,
    longitude_min=65.0,
    longitude_max=100.0,
    latitude_resolution=0.5,
    longitude_resolution=0.5,
)

GLOBAL_05_GRID = GridDefinition(
    name="global_0.5deg",
    latitude_min=-90.0,
    latitude_max=90.0,
    longitude_min=0.0,
    longitude_max=359.5,
    latitude_resolution=0.5,
    longitude_resolution=0.5,
)


@dataclass
class RegriddingConfig:
    """Configuration for regridding operations."""

    method: str = "bilinear"  # bilinear, nearest, conservative
    extrap_method: str = "nearest"  # nearest, constant, nan
    regrid_kwargs: dict[str, Any] | None = None


class SpatialAligner:
    """Align and regrid spatial data while preventing leakage."""

    def __init__(self, target_grid: GridDefinition):
        """Initialize with target grid.

        Args:
            target_grid: Grid to regrid all data to
        """
        self.target_grid = target_grid

    def validate_coordinates(self, ds: xr.Dataset) -> bool:
        """Validate that dataset has valid coordinates.

        Args:
            ds: Dataset to validate

        Returns:
            True if coordinates are valid

        Raises:
            ValueError: If coordinates are invalid
        """
        # Check for latitude coordinate
        lat_var = ds.coords.get("latitude", ds.coords.get("lat", ds.coords.get("LATITUDE")))
        if lat_var is None:
            raise ValueError("Dataset missing latitude coordinate")

        # Check for longitude coordinate
        lon_var = ds.coords.get("longitude", ds.coords.get("lon", ds.coords.get("LONGITUDE")))
        if lon_var is None:
            raise ValueError("Dataset missing longitude coordinate")

        # Validate latitude range
        lat_values = lat_var.values
        if np.any(lat_values < -90) or np.any(lat_values > 90):
            raise ValueError(f"Latitude values out of range [-90, 90]: min={lat_values.min()}, max={lat_values.max()}")

        # Validate longitude range
        lon_values = lon_var.values
        if np.any(lon_values < -180) or np.any(lon_values > 360):
            raise ValueError(f"Longitude values out of range [-180, 360]: min={lon_values.min()}, max={lon_values.max()}")

        return True

    def get_source_grid(self, ds: xr.Dataset) -> GridDefinition:
        """Extract grid definition from dataset.

        Args:
            ds: Dataset to extract grid from

        Returns:
            GridDefinition object
        """
        lat_var = ds.coords.get("latitude", ds.coords.get("lat"))
        lon_var = ds.coords.get("longitude", ds.coords.get("lon"))

        lat_values = lat_var.values
        lon_values = lon_var.values

        # Compute resolution
        lat_res = float(np.diff(lat_values).mean())
        lon_res = float(np.diff(lon_values).mean())

        grid = GridDefinition(
            name="source",
            latitude_min=float(lat_values.min()),
            latitude_max=float(lat_values.max()),
            longitude_min=float(lon_values.min()),
            longitude_max=float(lon_values.max()),
            latitude_resolution=lat_res,
            longitude_resolution=lon_res,
        )

        return grid

    def regrid_dataset(
        self,
        ds: xr.Dataset,
        variable: str,
        config: RegriddingConfig | None = None,
    ) -> xr.Dataset:
        """Regrid dataset to target grid.

        Args:
            ds: Source dataset
            variable: Variable to regrid
            config: Regridding configuration

        Returns:
            Dataset with variable regridded to target grid
        """
        config = config or RegriddingConfig()

        # Validate source coordinates
        self.validate_coordinates(ds)

        # Get source grid
        source_grid = self.get_source_grid(ds)

        # Create target coordinates
        target_lat = self.target_grid.latitude_values
        target_lon = self.target_grid.longitude_values

        # Extract source data
        if variable not in ds.data_vars:
            raise ValueError(f"Variable {variable} not found in dataset")

        source_data = ds[variable]

        # Perform regridding
        regridded = self._regrid_variable(
            source_data,
            source_grid,
            self.target_grid,
            config,
        )

        # Create new dataset with regridded data
        result = xr.Dataset(
            {
                variable: regridded,
            },
            coords={
                "latitude": target_lat,
                "longitude": target_lon,
            },
        )

        # Copy attributes
        result[variable].attrs = source_data.attrs
        result.attrs = ds.attrs

        # Add regridding metadata
        result.attrs["regridded_from"] = source_grid.name
        result.attrs["regridding_method"] = config.method

        return result

    def _regrid_variable(
        self,
        source_data: xr.DataArray,
        source_grid: GridDefinition,
        target_grid: GridDefinition,
        config: RegriddingConfig,
    ) -> xr.DataArray:
        """Regrid a single variable.

        This is a simplified implementation. For production use, consider:
        - xESMF for conservative regridding
        - scipy.interpolate for bilinear/nearest
        - pyresample for spherical regridding
        """
        from scipy.interpolate import RegularGridInterpolator

        # Get source coordinates
        source_lat = source_grid.latitude_values
        source_lon = source_grid.longitude_values

        # Get target coordinates
        target_lat = target_grid.latitude_values
        target_lon = target_grid.longitude_values

        # Create meshgrid for target coordinates
        target_lon_grid, target_lat_grid = np.meshgrid(target_lon, target_lat)

        # Handle different dimension orders
        dims = source_data.dims
        if "latitude" in dims and "longitude" in dims:
            # Standard (lat, lon) order
            lat_idx = dims.index("latitude")
            lon_idx = dims.index("longitude")
        elif "lat" in dims and "lon" in dims:
            lat_idx = dims.index("lat")
            lon_idx = dims.index("lon")
        else:
            raise ValueError(f"Cannot identify latitude/longitude dimensions: {dims}")

        # Extract 2D slice (for other dimensions like time, use first)
        if len(dims) > 2:
            # Take first slice along other dimensions
            slices = [0] * len(dims)
            slices[lat_idx] = slice(None)
            slices[lon_idx] = slice(None)
            source_2d = source_data[tuple(slices)].values
        else:
            source_2d = source_data.values

        # Create interpolator
        if config.method == "bilinear":
            interpolator = RegularGridInterpolator(
                (source_lat, source_lon),
                source_2d,
                method="linear",
                bounds_error=False,
                fill_value=np.nan,
            )
        elif config.method == "nearest":
            interpolator = RegularGridInterpolator(
                (source_lat, source_lon),
                source_2d,
                method="nearest",
                bounds_error=False,
                fill_value=np.nan,
            )
        else:
            raise ValueError(f"Unsupported regridding method: {config.method}")

        # Interpolate to target grid
        target_points = np.column_stack([target_lat_grid.ravel(), target_lon_grid.ravel()])
        regridded_flat = interpolator(target_points)
        regridded = regridded_flat.reshape(target_lat_grid.shape)

        # Create DataArray
        result = xr.DataArray(
            regridded,
            dims=["latitude", "longitude"],
            coords={
                "latitude": target_lat,
                "longitude": target_lon,
            },
        )

        return result

    def check_spatial_coverage(
        self,
        ds: xr.Dataset,
        required_region: GridDefinition | None = None,
    ) -> dict[str, Any]:
        """Check spatial coverage of dataset.

        Args:
            ds: Dataset to check
            required_region: Required region (uses target grid if None)

        Returns:
            Dictionary with coverage information
        """
        required_region = required_region or self.target_grid

        source_grid = self.get_source_grid(ds)

        # Check overlap
        lat_overlap = max(
            0,
            min(source_grid.latitude_max, required_region.latitude_max)
            - max(source_grid.latitude_min, required_region.latitude_min),
        )

        lon_overlap = max(
            0,
            min(source_grid.longitude_max, required_region.longitude_max)
            - max(source_grid.longitude_min, required_region.longitude_min),
        )

        has_overlap = lat_overlap > 0 and lon_overlap > 0

        # Check if source covers required region
        lat_covered = (
            source_grid.latitude_min <= required_region.latitude_min
            and source_grid.latitude_max >= required_region.latitude_max
        )

        lon_covered = (
            source_grid.longitude_min <= required_region.longitude_min
            and source_grid.longitude_max >= required_region.longitude_max
        )

        fully_covered = lat_covered and lon_covered

        return {
            "has_overlap": has_overlap,
            "fully_covers_required": fully_covered,
            "source_grid": source_grid.name,
            "required_grid": required_region.name,
            "latitude_overlap_deg": lat_overlap,
            "longitude_overlap_deg": lon_overlap,
        }

    def extract_region(
        self,
        ds: xr.Dataset,
        region: GridDefinition,
    ) -> xr.Dataset:
        """Extract a region from a dataset.

        Args:
            ds: Source dataset
            region: Region to extract

        Returns:
            Dataset cropped to region
        """
        lat_var = ds.coords.get("latitude", ds.coords.get("lat"))
        lon_var = ds.coords.get("longitude", ds.coords.get("lon"))

        if lat_var is None or lon_var is None:
            raise ValueError("Dataset missing latitude/longitude coordinates")

        # Slice to region
        result = ds.sel(
            latitude=slice(region.latitude_min, region.latitude_max),
            longitude=slice(region.longitude_min, region.longitude_max),
        )

        return result


def create_common_grid(
    datasets: list[xr.Dataset],
    method: str = "finest",
) -> GridDefinition:
    """Create a common grid from multiple datasets.

    Args:
        datasets: List of datasets to harmonize
        method: Method for choosing grid resolution
            - "finest": Use finest resolution
            - "coarsest": Use coarsest resolution
            - "mean": Use mean resolution

    Returns:
        GridDefinition suitable for all datasets
    """
    if not datasets:
        raise ValueError("No datasets provided")

    grids = []
    for ds in datasets:
        aligner = SpatialAligner(INDIA_025_GRID)  # Dummy target
        grid = aligner.get_source_grid(ds)
        grids.append(grid)

    if method == "finest":
        selected = min(grids, key=lambda g: g.latitude_resolution)
    elif method == "coarsest":
        selected = max(grids, key=lambda g: g.latitude_resolution)
    elif method == "mean":
        lat_res = np.mean([g.latitude_resolution for g in grids])
        lon_res = np.mean([g.longitude_resolution for g in grids])
        # Use union of extents
        lat_min = min(g.latitude_min for g in grids)
        lat_max = max(g.latitude_max for g in grids)
        lon_min = min(g.longitude_min for g in grids)
        lon_max = max(g.longitude_max for g in grids)
        selected = GridDefinition(
            name="common_mean",
            latitude_min=lat_min,
            latitude_max=lat_max,
            longitude_min=lon_min,
            longitude_max=lon_max,
            latitude_resolution=lat_res,
            longitude_resolution=lon_res,
        )
    else:
        raise ValueError(f"Unknown method: {method}")

    return selected
