"""Visualization module for the AI CFD Platform."""

from .viewer import (
    CAMERA_PRESETS,
    COLORMAPS,
    DISPLAY_MODES,
    FIELD_MAP,
    detect_fields,
    load_demo_result,
    prepare_mesh_for_field,
    render_contour,
    render_plotter,
    render_slice,
    render_streamlines,
    render_surface,
    render_to_png,
    render_vectors,
    save_mesh_as_vtk,
)

__all__ = [
    "FIELD_MAP",
    "DISPLAY_MODES",
    "COLORMAPS",
    "CAMERA_PRESETS",
    "load_demo_result",
    "detect_fields",
    "prepare_mesh_for_field",
    "render_surface",
    "render_slice",
    "render_streamlines",
    "render_vectors",
    "render_contour",
    "render_plotter",
    "render_to_png",
    "save_mesh_as_vtk",
]