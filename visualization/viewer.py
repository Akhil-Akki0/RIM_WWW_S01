"""PyVista-based CFD visualization service."""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pyvista as pv

from core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# FIELD MAPPING
# ============================================================

FIELD_MAP = {
    "Velocity": "U",
    "Velocity Magnitude": "U_magnitude",
    "Pressure": "p",
    "Temperature": "T",
    "Turbulent Kinetic Energy": "k",
    "Turbulent Dissipation": "epsilon",
    "Turbulent Viscosity": "nut",
}


DISPLAY_MODES = [
    "Surface",
    "Slice",
    "Streamlines",
    "Vectors",
    "Contour",
]


COLORMAPS = [
    "viridis",
    "plasma",
    "coolwarm",
    "jet",
    "turbo",
    "rainbow",
    "magma",
    "inferno",
]


CAMERA_PRESETS = {
    "Iso": "iso",
    "Front": "xy",
    "Top": "xz",
    "Side": "yz",
}


# ============================================================
# DATA LOADING
# ============================================================

def load_demo_result() -> pv.ImageData:
    """Load the pre-generated demo flow field."""
    from storage.demo_data import load_demo_flow_field

    return load_demo_flow_field()


def detect_fields(mesh: pv.DataSet) -> List[str]:
    """Detect which fields are actually available in the mesh."""
    available = []
    point_data = mesh.point_data

    for display_name, internal_name in FIELD_MAP.items():
        if internal_name in point_data:
            available.append(display_name)

    # Also add "Velocity Magnitude" if U exists but U_magnitude doesn't
    if "U" in point_data and "Velocity Magnitude" not in available:
        available.append("Velocity Magnitude")

    return available


# ============================================================
# FIELD PREPARATION
# ============================================================

def prepare_mesh_for_field(mesh: pv.DataSet, field_name: str) -> Tuple[pv.DataSet, str]:
    """
    Prepare a mesh with the requested field as an active scalar.

    Returns:
        (mesh, actual_field_key)
    """
    internal = FIELD_MAP.get(field_name, field_name)

    # Compute magnitude if requested
    if field_name == "Velocity Magnitude" and "U" in mesh.point_data:
        vectors = mesh.point_data["U"]
        mesh.point_data["U_magnitude"] = np.linalg.norm(vectors, axis=1)
        internal = "U_magnitude"

    return mesh, internal


# ============================================================
# RENDER FUNCTIONS
# ============================================================

def render_surface(
    mesh: pv.DataSet,
    field: str,
    cmap: str = "viridis",
    opacity: float = 1.0,
    show_edges: bool = False,
    n_colors: int = 256,
) -> pv.Plotter:
    """Render a colored surface."""
    plotter = pv.Plotter(window_size=(1000, 700))
    plotter.add_mesh(
        mesh,
        scalars=field,
        cmap=cmap,
        opacity=opacity,
        show_edges=show_edges,
        n_colors=n_colors,
        show_scalar_bar=True,
        scalar_bar_args={
            "title": field,
            "title_font_size": 16,
            "label_font_size": 12,
            "color": "black",
        },
    )
    plotter.background_color = "#F9FAFB"
    plotter.add_axes()
    return plotter


def render_slice(
    mesh: pv.DataSet,
    field: str,
    normal: str = "z",
    position: float = 0.5,
    cmap: str = "viridis",
) -> pv.Plotter:
    """Render a slice through the domain."""
    # Compute bounds to place slice
    bounds = mesh.bounds
    axis_idx = {"x": 0, "y": 1, "z": 2}.get(normal.lower(), 2)
    low = bounds[axis_idx * 2]
    high = bounds[axis_idx * 2 + 1]
    origin_pos = low + (high - low) * position

    origin = list(mesh.center)
    origin[axis_idx] = origin_pos

    # Perform slice
    slice_mesh = mesh.slice(normal=normal, origin=origin)

    plotter = pv.Plotter(window_size=(1000, 700))
    if slice_mesh.n_points > 0:
        plotter.add_mesh(
            slice_mesh,
            scalars=field,
            cmap=cmap,
            show_scalar_bar=True,
            scalar_bar_args={"title": field},
        )
    else:
        plotter.add_text("No data at this slice position", position="upper_left")

    plotter.background_color = "#F9FAFB"
    plotter.add_axes()
    return plotter


def render_streamlines(
    mesh: pv.DataSet,
    vector_field: str = "U",
    color_field: Optional[str] = None,
    density: float = 1.0,
    n_points: int = 100,
) -> pv.Plotter:
    """Render streamlines through the vector field."""
    plotter = pv.Plotter(window_size=(1000, 700))

    if vector_field not in mesh.point_data:
        plotter.add_text(
            f"Vector field '{vector_field}' not available",
            position="upper_left",
        )
        plotter.background_color = "#F9FAFB"
        return plotter

    # Create source points for streamlines
    bounds = mesh.bounds
    source = pv.Plane(
        center=(bounds[0], mesh.center[1], mesh.center[2]),
        direction=(1, 0, 0),
        i_size=(bounds[3] - bounds[2]) * 0.8,
        j_size=(bounds[5] - bounds[4]) * 0.8,
        i_resolution=int(10 * density),
        j_resolution=int(10 * density),
    )

    # Generate streamlines
    try:
        streamlines = mesh.streamlines_from_source(
            source,
            vectors=vector_field,
            integration_direction="forward",
            max_steps=2000,
            initial_step_length=0.01,
            terminal_speed=1e-5,
        )
    except Exception as e:
        logger.warning(f"Streamlines failed: {e}")
        streamlines = pv.PolyData()

    if streamlines.n_points > 0:
        if color_field and color_field in mesh.point_data:
            # Color by field
            plotter.add_mesh(
                streamlines,
                line_width=2,
                scalars=color_field,
                cmap="plasma",
                show_scalar_bar=True,
            )
        else:
            # Color by velocity magnitude
            mag = np.linalg.norm(mesh.point_data[vector_field], axis=1)
            plotter.add_mesh(
                streamlines,
                line_width=2,
                color="#3B82F6",
            )
    else:
        plotter.add_text("No streamlines generated", position="upper_left")

    # Add outline
    plotter.add_mesh(
        mesh.outline(),
        color="black",
        line_width=2,
        opacity=0.3,
    )

    plotter.background_color = "#F9FAFB"
    plotter.add_axes()
    return plotter


def render_vectors(
    mesh: pv.DataSet,
    vector_field: str = "U",
    subsample: int = 20,
    scale: float = 1.0,
    color_field: Optional[str] = None,
) -> pv.Plotter:
    """Render vector arrows."""
    plotter = pv.Plotter(window_size=(1000, 700))

    if vector_field not in mesh.point_data:
        plotter.add_text(
            f"Vector field '{vector_field}' not available",
            position="upper_left",
        )
        plotter.background_color = "#F9FAFB"
        return plotter

    # Subsample the mesh
    try:
        glyph_source = mesh.point_data_to_cell_data() if mesh.n_cells > 0 else mesh
        # Sample points
        sampled = mesh.sample(mesh)  # Keep all points for now
    except Exception:
        sampled = mesh

    # Create arrows
    try:
        arrows = mesh.glyph(
            orient=vector_field,
            scale=vector_field,
            factor=scale * 0.05,
            geom=pv.Arrow(),
        )
    except Exception as e:
        logger.warning(f"Glyph failed: {e}")
        arrows = mesh

    if color_field and color_field in mesh.point_data:
        plotter.add_mesh(
            arrows,
            scalars=color_field,
            cmap="coolwarm",
            show_scalar_bar=True,
        )
    else:
        plotter.add_mesh(arrows, color="#3B82F6")

    plotter.background_color = "#F9FAFB"
    plotter.add_axes()
    return plotter


def render_contour(
    mesh: pv.DataSet,
    field: str,
    levels: int = 10,
    cmap: str = "viridis",
) -> pv.Plotter:
    """Render contour lines of a scalar field."""
    plotter = pv.Plotter(window_size=(1000, 700))

    if field not in mesh.point_data:
        plotter.add_text(
            f"Field '{field}' not available",
            position="upper_left",
        )
        plotter.background_color = "#F9FAFB"
        return plotter

    try:
        contours = mesh.contour(
            scalars=field,
            isosurfaces=levels,
        )
        plotter.add_mesh(
            contours,
            scalars=field,
            cmap=cmap,
            show_scalar_bar=True,
            opacity=0.8,
        )
    except Exception as e:
        logger.warning(f"Contour failed: {e}")
        plotter.add_text(f"Contour failed: {e}", position="upper_left")

    plotter.add_mesh(
        mesh.outline(),
        color="black",
        line_width=1,
        opacity=0.3,
    )
    plotter.background_color = "#F9FAFB"
    plotter.add_axes()
    return plotter


# ============================================================
# MAIN DISPATCHER
# ============================================================

def render_plotter(
    mesh: pv.DataSet,
    mode: str,
    field: str,
    cmap: str = "viridis",
    opacity: float = 1.0,
    show_edges: bool = False,
    slice_normal: str = "z",
    slice_position: float = 0.5,
    streamline_density: float = 1.0,
    vector_scale: float = 1.0,
    contour_levels: int = 10,
) -> pv.Plotter:
    """
    Main entry point — routes to the correct render function.
    """
    internal_field = FIELD_MAP.get(field, field)

    # Prepare mesh if needed
    mesh, internal_field = prepare_mesh_for_field(mesh, field)

    if mode == "Surface":
        return render_surface(mesh, internal_field, cmap, opacity, show_edges)
    elif mode == "Slice":
        return render_slice(mesh, internal_field, slice_normal, slice_position, cmap)
    elif mode == "Streamlines":
        return render_streamlines(mesh, "U", internal_field, streamline_density)
    elif mode == "Vectors":
        return render_vectors(mesh, "U", 20, vector_scale, internal_field)
    elif mode == "Contour":
        return render_contour(mesh, internal_field, contour_levels, cmap)
    else:
        return render_surface(mesh, internal_field, cmap, opacity)


# ============================================================
# RENDER TO IMAGE (fallback)
# ============================================================

def render_to_png(
    plotter: pv.Plotter,
    output_path: Optional[Path] = None,
) -> Path:
    """Render a plotter to a PNG file (off-screen)."""
    plotter.off_screen = True

    if output_path is None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output_path = Path(tmp.name)

    plotter.screenshot(str(output_path), transparent_background=False)
    plotter.close()

    return output_path


# ============================================================
# DOWNLOAD HELPERS
# ============================================================

def save_mesh_as_vtk(mesh: pv.DataSet) -> Path:
    """Save a mesh to a temporary VTK file for download."""
    with tempfile.NamedTemporaryFile(suffix=".vtk", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    mesh.save(str(tmp_path))
    return tmp_path