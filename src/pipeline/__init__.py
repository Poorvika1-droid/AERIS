"""Data pipeline modules for AERIS.

This package contains:
- temporal_alignment: Align forecasts and observations in time
- spatial_alignment: Regrid and align spatial data
- quality_control: Validate and clean weather data
- training_dataset_builder: Build causally valid training datasets
"""

from src.pipeline.temporal_alignment import TemporalAligner, TimeAlignmentConfig, validate_temporal_overlap
from src.pipeline.spatial_alignment import SpatialAligner, GridDefinition, INDIA_025_GRID, INDIA_05_GRID
from src.pipeline.quality_control import QualityController, QCResult, VariableQCConfig, validate_provenance
from src.pipeline.training_dataset_builder import (
    TrainingDataset,
    TrainingDatasetBuilder,
    TrainingDatasetConfig,
    create_default_config,
)

__all__ = [
    "TemporalAligner",
    "TimeAlignmentConfig",
    "validate_temporal_overlap",
    "SpatialAligner",
    "GridDefinition",
    "INDIA_025_GRID",
    "INDIA_05_GRID",
    "QualityController",
    "QCResult",
    "VariableQCConfig",
    "validate_provenance",
    "TrainingDataset",
    "TrainingDatasetBuilder",
    "TrainingDatasetConfig",
    "create_default_config",
]
