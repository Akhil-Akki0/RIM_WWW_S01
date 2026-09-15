"""Geometry processing, validation, and storage."""

import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pyvista as pv
import trimesh

from core.config import get_config
from core.exceptions import GeometryError
from core.logging import get_logger
from core.utils import format_file_size

logger = get_logger(__name__)


# ============================================================
# GEOMETRY LOADING
# ============================================================

def load_geometry(file_path: Path) -> pv.PolyData:
    """
    Load a geometry file (STL or OBJ) as a PyVista PolyData object.

    Args:
        file_path: Path to the geometry file.

    Returns:
        PyVista PolyData mesh.

    Raises:
        GeometryError: If the file cannot be read or is invalid.
    """
    if not file_path.exists():
        raise GeometryError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in (".stl", ".obj"):
        raise GeometryError(
            f"Unsupported format: {suffix}. Supported formats: .stl, .obj"
        )

    try:
        mesh = pv.read(str(file_path))
    except Exception as e:
        raise GeometryError(f"Failed to read geometry: {e}")

    if not isinstance(mesh, pv.PolyData):
        # Convert UnstructuredGrid to PolyData if necessary
        mesh = mesh.extract_surface()

    if mesh.n_points == 0 or mesh.n_cells == 0:
        raise GeometryError("Geometry is empty (no points or cells)")

    logger.info(f"Loaded geometry: {file_path.name} ({mesh.n_points} points, {mesh.n_cells} cells)")
    return mesh


# ============================================================
# GEOMETRY VALIDATION
# ============================================================

def validate_geometry(mesh: pv.PolyData) -> Dict[str, Any]:
    """
    Validate a geometry mesh.

    Checks:
        - Has points and cells
        - Has reasonable bounds (not zero, not gigantic)
        - Is manifold (if triangulated)
        - No NaN values

    Returns:
        Dict with 'valid' (bool), 'errors' (list), 'warnings' (list),
        and metadata like bounds, size, number of points/cells.
    """
    errors: list = []
    warnings: list = []

    # Basic checks
    if mesh.n_points == 0:
        errors.append("Geometry has no points")
    if mesh.n_cells == 0:
        errors.append("Geometry has no cells")

    # Bounds check
    if mesh.n_points > 0:
        bounds = mesh.bounds  # (xmin, xmax, ymin, ymax, zmin, zmax)
        size = (
            bounds[1] - bounds[0],
            bounds[3] - bounds[2],
            bounds[5] - bounds[4],
        )
        max_dim = max(size)
        min_dim = min(size)

        if max_dim == 0:
            errors.append("Geometry has zero extent")
        elif max_dim < 1e-6:
            errors.append("Geometry is too small (< 1 micron)")
        elif max_dim > 1000:
            warnings.append(f"Geometry is very large ({max_dim:.1f} m) — check units")

        if min_dim == 0:
            warnings.append("Geometry appears flat (one dimension is zero)")
    else:
        bounds = (0, 0, 0, 0, 0, 0)
        size = (0, 0, 0)

    # Check for NaN values
    points = mesh.points
    if np.any(np.isnan(points)):
        errors.append("Geometry contains NaN coordinates")

    # Manifold check (only if triangulated)
    try:
        if mesh.n_cells > 0 and mesh.is_all_triangles:
            # Use trimesh for a proper manifold check
            faces = mesh.faces.reshape(-1, 4)[:, 1:]
            tm = trimesh.Trimesh(vertices=points, faces=faces, process=False)
            if not tm.is_watertight:
                warnings.append("Geometry is not watertight (may affect simulation)")
    except Exception as e:
        logger.warning(f"Manifold check failed: {e}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "bounds": {
            "x": [bounds[0], bounds[1]],
            "y": [bounds[2], bounds[3]],
            "z": [bounds[4], bounds[5]],
        },
        "size": {"x": size[0], "y": size[1], "z": size[2], "max": max(size)},
        "n_points": mesh.n_points,
        "n_cells": mesh.n_cells,
        "is_triangulated": bool(mesh.is_all_triangles) if mesh.n_cells > 0 else False,
    }


# ============================================================
# GEOMETRY STORAGE
# ============================================================

def get_project_geometry_dir(project_id: str) -> Path:
    """Return the geometry directory for a project, creating it if needed."""
    config = get_config()
    geom_dir = config.data_directory / "projects" / project_id / "geometry"
    geom_dir.mkdir(parents=True, exist_ok=True)
    return geom_dir


def save_uploaded_geometry(
    project_id: str,
    uploaded_file_bytes: bytes,
    original_filename: str,
) -> Dict[str, Any]:
    """
    Save an uploaded geometry file to the project folder.

    Args:
        project_id: The project this geometry belongs to.
        uploaded_file_bytes: Raw file content.
        original_filename: The original filename from the upload.

    Returns:
        Dict with file metadata (path, size, format, validation).
    """
    # Sanitize filename
    safe_name = Path(original_filename).name
    suffix = Path(safe_name).suffix.lower()

    if suffix not in (".stl", ".obj"):
        raise GeometryError(f"Unsupported file type: {suffix}")

    # Save to project geometry directory
    geom_dir = get_project_geometry_dir(project_id)
    dest_path = geom_dir / safe_name

    # Handle duplicate names
    counter = 1
    while dest_path.exists():
        stem = Path(safe_name).stem
        dest_path = geom_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    with open(dest_path, "wb") as f:
        f.write(uploaded_file_bytes)

    file_size = dest_path.stat().st_size

    # Load and validate
    try:
        mesh = load_geometry(dest_path)
        validation = validate_geometry(mesh)
    except GeometryError as e:
        validation = {"valid": False, "errors": [str(e)], "warnings": []}

    logger.info(f"Saved geometry for project {project_id}: {dest_path.name}")

    return {
        "filename": dest_path.name,
        "original_filename": original_filename,
        "file_path": str(dest_path),
        "file_size": file_size,
        "file_size_display": format_file_size(file_size),
        "format": suffix.lstrip(".").upper(),
        "validation": validation,
    }


def delete_geometry(file_path: Path) -> bool:
    """Delete a geometry file."""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted geometry: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete geometry: {e}")
        return False


# ============================================================
# GEOMETRY PREVIEW
# ============================================================

def create_preview_plotter(
    mesh: pv.PolyData,
    window_size: Tuple[int, int] = (800, 600),
    color: str = "#3B82F6",
):
    """
    Create a PyVista Plotter for previewing geometry in Streamlit.

    Args:
        mesh: The geometry mesh.
        window_size: Plotter window size.
        color: Mesh color.

    Returns:
        Configured PyVista Plotter.
    """
    plotter = pv.Plotter(window_size=window_size)
    plotter.add_mesh(
        mesh,
        color=color,
        show_edges=True,
        edge_color="#1F2937",
        opacity=0.9,
        smooth_shading=True,
    )
    plotter.add_axes()
    plotter.add_bounding_box(color="#6B7280", line_width=1)
    plotter.camera_position = "iso"
    plotter.background_color = "#F9FAFB"

    return plotter