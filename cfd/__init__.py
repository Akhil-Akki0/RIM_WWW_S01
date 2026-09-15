"""CFD service layer."""

from .case_generator import CaseGenerator
from .geometry import (
    create_preview_plotter,
    delete_geometry,
    get_project_geometry_dir,
    load_geometry,
    save_uploaded_geometry,
    validate_geometry,
)
from .runner import (
    OPENFOAM_VERSION,
    SimulationState,
    WSLBridge,
    run_simulation,
)

__all__ = [
    # Geometry
    "load_geometry",
    "validate_geometry",
    "save_uploaded_geometry",
    "delete_geometry",
    "get_project_geometry_dir",
    "create_preview_plotter",
    # Case generator
    "CaseGenerator",
    # Runner
    "run_simulation",
    "SimulationState",
    "WSLBridge",
    "OPENFOAM_VERSION",
]
