"""Core application modules."""

from .config import Config, get_config, reset_config
from .exceptions import (
    AIError,
    CFDPlatformError,
    GeometryError,
    MeshError,
    ModulusNotAvailableError,
    NoModelConfiguredError,
    OpenFOAMError,
    OpenFOAMExecutionError,
    OpenFOAMNotFoundError,
    ProjectNotFoundError,
    SimulationError,
    SimulationNotFoundError,
    StorageError,
    ValidationError,
)
from .logging import get_logger, setup_logging

__version__ = "0.1.0"

__all__ = [
    "Config", "get_config", "reset_config",
    "get_logger", "setup_logging",
    "CFDPlatformError", "ValidationError", "GeometryError", "MeshError",
    "OpenFOAMError", "OpenFOAMNotFoundError", "OpenFOAMExecutionError",
    "SimulationError", "AIError", "NoModelConfiguredError",
    "ModulusNotAvailableError", "StorageError",
    "ProjectNotFoundError", "SimulationNotFoundError",
    "__version__",
]