"""Physical constants and simulation defaults."""

from typing import Any, Dict


# ============================================================
# FLUID PROPERTIES DATABASE
# ============================================================

FLUID_PROPERTIES: Dict[str, Dict[str, float]] = {
    "Air": {
        "density": 1.225,              # kg/m³
        "dynamic_viscosity": 1.81e-5,  # Pa·s
        "temperature": 293.15,         # K (20°C)
        "pressure": 101325.0,          # Pa
    },
    "Water": {
        "density": 998.2,              # kg/m³
        "dynamic_viscosity": 1.002e-3,  # Pa·s
        "temperature": 293.15,
        "pressure": 101325.0,
    },
    "Custom": {
        "density": 1.0,
        "dynamic_viscosity": 1e-5,
        "temperature": 293.15,
        "pressure": 101325.0,
    },
}


# ============================================================
# SOLVERS
# ============================================================

SOLVERS: Dict[str, Dict[str, Any]] = {
    "simpleFoam": {
        "label": "simpleFoam",
        "description": "Steady-state incompressible flow",
        "type": "Steady",
        "supports_heat": False,
    },
    "pimpleFoam": {
        "label": "pimpleFoam",
        "description": "Transient incompressible flow",
        "type": "Transient",
        "supports_heat": False,
    },
    "buoyantSimpleFoam": {
        "label": "buoyantSimpleFoam",
        "description": "Steady buoyant flow (heat transfer)",
        "type": "Steady",
        "supports_heat": True,
    },
    "buoyantPimpleFoam": {
        "label": "buoyantPimpleFoam",
        "description": "Transient buoyant flow (heat transfer)",
        "type": "Transient",
        "supports_heat": True,
    },
}


# ============================================================
# VALIDATION LIMITS
# ============================================================

VALIDATION_LIMITS: Dict[str, Dict[str, float]] = {
    "density":             {"min": 1e-3, "max": 25000.0},
    "dynamic_viscosity":   {"min": 1e-8, "max": 1e6},
    "temperature":         {"min": 1.0, "max": 5000.0},
    "pressure":            {"min": 1.0, "max": 1e9},
    "velocity":            {"min": 0.0, "max": 1000.0},
    "max_iterations":      {"min": 10, "max": 1_000_000},
    "convergence_tol":     {"min": 1e-12, "max": 1e-1},
    "time_step":           {"min": 1e-8, "max": 1000.0},
    "base_cell_size":      {"min": 1e-6, "max": 100.0},
    "refinement_level":    {"min": 0, "max": 5},
    "boundary_layers":     {"min": 0, "max": 20},
}


# ============================================================
# DEFAULTS
# ============================================================

DEFAULT_BOUNDARY_CONDITIONS = {
    "inlet": {
        "velocity": 10.0,      # m/s
        "pressure": 101325.0,  # Pa
        "temperature": 293.15, # K
    },
    "outlet": {
        "pressure": 101325.0,  # Pa
    },
    "walls": {
        "type": "no-slip",
    },
}


DEFAULT_SOLVER_SETTINGS = {
    "solver": "simpleFoam",
    "max_iterations": 500,
    "convergence_tolerance": 1e-4,
    "time_step": 0.001,
}


DEFAULT_MESH_SETTINGS = {
    "base_cell_size": 0.1,      # m
    "refinement_level": 2,       # 0-5
    "boundary_layers": 3,        # 0-20
}


# ============================================================
# CFD TYPE → SOLVER SUGGESTIONS
# ============================================================

CFD_TYPE_SOLVER_MAP: Dict[str, str] = {
    "External Aerodynamics": "simpleFoam",
    "Internal Flow": "simpleFoam",
    "Pipe Flow": "simpleFoam",
    "Airflow": "simpleFoam",
    "Heat Transfer": "buoyantSimpleFoam",
    "Custom": "simpleFoam",
}


# ============================================================
# RESULT FIELDS
# ============================================================

RESULT_FIELDS: Dict[str, Dict[str, str]] = {
    "U":       {"name": "Velocity",              "unit": "m/s",   "type": "vector"},
    "p":       {"name": "Pressure",              "unit": "Pa",    "type": "scalar"},
    "T":       {"name": "Temperature",           "unit": "K",     "type": "scalar"},
    "k":       {"name": "Turbulent Kinetic Energy", "unit": "m²/s²", "type": "scalar"},
    "epsilon": {"name": "Turbulent Dissipation",  "unit": "m²/s³", "type": "scalar"},
    "nut":     {"name": "Turbulent Viscosity",   "unit": "m²/s",  "type": "scalar"},
}