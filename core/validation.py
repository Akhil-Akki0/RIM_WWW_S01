"""Input validation utilities."""

from typing import Any, Dict, List, Tuple

from .constants import VALIDATION_LIMITS


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_numeric(
    value: Any,
    name: str,
    min_value: float = None,
    max_value: float = None,
) -> float:
    """Validate a numeric value."""
    if value is None:
        raise ValidationError(f"{name} is required")

    try:
        fval = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be a number")

    if min_value is not None and fval < min_value:
        raise ValidationError(f"{name} must be ≥ {min_value}")

    if max_value is not None and fval > max_value:
        raise ValidationError(f"{name} must be ≤ {max_value}")

    return fval


def validate_velocity(value: Any, name: str = "Velocity") -> float:
    lim = VALIDATION_LIMITS["velocity"]
    return validate_numeric(value, name, lim["min"], lim["max"])


def validate_pressure(value: Any, name: str = "Pressure") -> float:
    lim = VALIDATION_LIMITS["pressure"]
    return validate_numeric(value, name, lim["min"], lim["max"])


def validate_temperature(value: Any, name: str = "Temperature") -> float:
    lim = VALIDATION_LIMITS["temperature"]
    return validate_numeric(value, name, lim["min"], lim["max"])


def validate_density(value: Any, name: str = "Density") -> float:
    lim = VALIDATION_LIMITS["density"]
    return validate_numeric(value, name, lim["min"], lim["max"])


def validate_viscosity(value: Any, name: str = "Viscosity") -> float:
    lim = VALIDATION_LIMITS["dynamic_viscosity"]
    return validate_numeric(value, name, lim["min"], lim["max"])


class SimulationConfigValidator:
    """Validate a complete simulation configuration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations. Returns (is_valid, errors, warnings)."""
        self._validate_fluid()
        self._validate_boundary()
        self._validate_solver()
        self._validate_mesh()
        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_fluid(self):
        fluid = self.config.get("fluid", {})
        try:
            validate_density(fluid.get("density"), "Density")
        except ValidationError as e:
            self.errors.append(str(e))
        try:
            validate_viscosity(fluid.get("dynamic_viscosity"), "Dynamic viscosity")
        except ValidationError as e:
            self.errors.append(str(e))
        try:
            validate_temperature(fluid.get("temperature"), "Temperature")
        except ValidationError as e:
            self.errors.append(str(e))
        try:
            validate_pressure(fluid.get("pressure"), "Pressure")
        except ValidationError as e:
            self.errors.append(str(e))

    def _validate_boundary(self):
        bc = self.config.get("boundary_conditions", {})
        inlet = bc.get("inlet", {})
        outlet = bc.get("outlet", {})

        try:
            validate_velocity(inlet.get("velocity"), "Inlet velocity")
        except ValidationError as e:
            self.errors.append(str(e))

        try:
            validate_pressure(inlet.get("pressure"), "Inlet pressure")
        except ValidationError as e:
            self.errors.append(str(e))

        try:
            validate_pressure(outlet.get("pressure"), "Outlet pressure")
        except ValidationError as e:
            self.errors.append(str(e))

    def _validate_solver(self):
        solver = self.config.get("solver_settings", {})
        lim_iter = VALIDATION_LIMITS["max_iterations"]
        try:
            validate_numeric(
                solver.get("max_iterations"), "Max iterations",
                lim_iter["min"], lim_iter["max"],
            )
        except ValidationError as e:
            self.errors.append(str(e))

    def _validate_mesh(self):
        mesh = self.config.get("mesh_settings", {})
        lim = VALIDATION_LIMITS["base_cell_size"]
        try:
            validate_numeric(
                mesh.get("base_cell_size"), "Base cell size",
                lim["min"], lim["max"],
            )
        except ValidationError as e:
            self.errors.append(str(e))


def estimate_mesh_cells(
    geometry_size: float,
    base_cell_size: float,
    refinement_level: int = 0,
) -> int:
    """
    Roughly estimate total mesh cells for a domain around the geometry.

    Assumes a domain ~15x the geometry size in each dimension,
    with a background mesh of base_cell_size, plus 2^refinement extra cells
    near the geometry surface.
    """
    if base_cell_size <= 0:
        return 0

    # Domain dimensions (cube around geometry)
    domain_extent = max(geometry_size * 15.0, 1.0)

    # Background mesh cells
    cells_per_dim = max(int(domain_extent / base_cell_size), 1)
    background_cells = cells_per_dim ** 3

    # Refinement adds ~2^(2*level) more cells near the surface
    refinement_multiplier = 1 + (2 ** refinement_level) * 0.1

    return int(background_cells * refinement_multiplier)