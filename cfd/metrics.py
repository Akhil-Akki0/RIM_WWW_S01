"""Compute CFD metrics from OpenFOAM results."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from core.logging import get_logger

logger = get_logger(__name__)


class MetricsCalculator:
    """Calculate numerical metrics from a mesh with field data."""

    # Default air density (kg/m³) if we can't read from config
    DEFAULT_DENSITY = 1.225

    def calculate_from_case(self, case_path: Path) -> Dict[str, Any]:
        """Compute metrics from an OpenFOAM case directory.

        Note on pressure units:
        - simpleFoam (incompressible) stores KINEMATIC pressure = p / rho
        - We multiply by density to get ACTUAL pressure in Pa
        """
        metrics: Dict[str, Any] = {
            "max_velocity": 0.0,
            "min_velocity": 0.0,
            "avg_velocity": 0.0,
            "max_pressure": 0.0,
            "min_pressure": 0.0,
            "pressure_drop": 0.0,
            "mesh_cells": 0,
            "converged": True,
            "iterations": 0,
        }

        # Read density from case config if available
        density = self._read_density(case_path)

        vtk_dir = case_path / "VTK"
        if not vtk_dir.exists():
            logger.warning(f"No VTK directory at {vtk_dir}")
            return metrics

        # Prefer the LAST timestep (most converged)
        vtk_files = sorted(vtk_dir.rglob("internal.vtu"))
        if not vtk_files:
            vtk_files = sorted(vtk_dir.rglob("internal.vtk"))
        if not vtk_files:
            logger.warning(f"No internal VTK files in {vtk_dir}")
            return metrics

        try:
            import pyvista as pv

            mesh = pv.read(str(vtk_files[-1]))
            logger.info(
                f"Loaded mesh for metrics: {mesh.n_points} points, {mesh.n_cells} cells"
            )

            metrics["mesh_cells"] = mesh.n_cells

            # -------- Velocity --------
            U = self._get_field(mesh, "U")
            if U is not None:
                U = np.asarray(U)
                if U.ndim > 1 and U.shape[1] == 3:
                    mag = np.linalg.norm(U, axis=1)
                else:
                    mag = np.abs(U)
                metrics["max_velocity"] = float(np.max(mag))
                metrics["min_velocity"] = float(np.min(mag))
                metrics["avg_velocity"] = float(np.mean(mag))
                logger.info(
                    f"Velocity: max={metrics['max_velocity']:.4f}, "
                    f"avg={metrics['avg_velocity']:.4f} m/s"
                )

            # -------- Pressure (kinematic → actual Pa) --------
            p = self._get_field(mesh, "p")
            if p is not None:
                p = np.asarray(p).flatten()
                # Multiply by density to get Pa (from kinematic p/rho)
                p_actual = p * density

                metrics["max_pressure"] = float(np.max(p_actual))
                metrics["min_pressure"] = float(np.min(p_actual))
                metrics["pressure_drop"] = float(np.max(p_actual) - np.min(p_actual))

                logger.info(
                    f"Pressure (Pa, density={density}): "
                    f"max={metrics['max_pressure']:.2f}, "
                    f"min={metrics['min_pressure']:.2f}, "
                    f"drop={metrics['pressure_drop']:.2f}"
                )

        except Exception as e:
            logger.warning(f"Failed to compute metrics: {e}")

        return metrics

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _get_field(mesh, name: str) -> Optional[np.ndarray]:
        """Look for a field in point_data or cell_data (with common suffixes)."""
        candidates = [name, f"{name}_1", f"{name}_0"]

        # Check point_data first (higher resolution)
        for cand in candidates:
            if cand in mesh.point_data:
                return mesh.point_data[cand]

        # Fall back to cell_data
        for cand in candidates:
            if cand in mesh.cell_data:
                return mesh.cell_data[cand]

        return None

    def _read_density(self, case_path: Path) -> float:
        """Try to read fluid density from a saved config file.

        The runner saves the simulation config as JSON when the case is created.
        Falls back to DEFAULT_DENSITY if not found.
        """
        # Look for config in a few likely locations
        candidates = [
            case_path / "case_config.json",
            case_path.parent / "case_config.json",
            case_path.parent.parent / "case_config.json",
        ]

        for candidate in candidates:
            if candidate.exists():
                try:
                    cfg = json.loads(candidate.read_text())
                    density = cfg.get("fluid", {}).get("density")
                    if density and density > 0:
                        logger.info(f"Read density from config: {density} kg/m³")
                        return float(density)
                except Exception as e:
                    logger.warning(f"Failed to read density from {candidate}: {e}")

        logger.info(f"Using default density: {self.DEFAULT_DENSITY} kg/m³")
        return self.DEFAULT_DENSITY