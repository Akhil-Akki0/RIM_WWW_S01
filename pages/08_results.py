"""CFD Results — interactive 3D visualization."""

import tempfile
from pathlib import Path

import streamlit as st

from core.config import get_config
from core.logging import get_logger
from storage import (
    get_logs,
    get_simulation,
    init_database,
    list_simulations,
)
from ui.components import info_box, metric_card, section_header
from ui.theme import apply_theme
from visualization import (
    CAMERA_PRESETS,
    COLORMAPS,
    DISPLAY_MODES,
    detect_fields,
    load_demo_result,
    render_plotter,
    render_to_png,
    save_mesh_as_vtk,
)

logger = get_logger(__name__)
config = get_config()

st.set_page_config(page_title="Results", page_icon="📈", layout="wide")
apply_theme()
init_database()

st.title("📈 CFD Results")
st.caption("Interactive 3D visualization of your simulation")

# ============================================================
# SIMULATION SELECTION
# ============================================================

sim_id = st.session_state.get("current_simulation_id")

# If a simulation is in session state, verify it actually exists in DB
if sim_id:
    existing = get_simulation(sim_id)
    if not existing or existing.get("status") != "completed":
        # Stale session state — clear it
        st.session_state.pop("current_simulation_id", None)
        sim_id = None

# No valid simulation selected — show picker
if not sim_id:
    completed_sims = list_simulations(status="completed", limit=20)
    if not completed_sims:
        info_box(
            "No completed simulations yet. Run a simulation first.",
            "warning",
        )
        if st.button("▶️ Go to Simulation Runner", type="primary"):
            st.switch_page("pages/07_simulation_runner.py")
        st.stop()

    section_header("Select Simulation", "Choose a completed simulation to view", icon="📋")

    opts = {
        s["simulation_id"]: f"{s['simulation_id'][:25]}... — {s.get('solver', 'N/A')}"
        for s in completed_sims
    }
    selected = st.selectbox("Simulation", list(opts.keys()), format_func=lambda x: opts[x])
    if st.button("Load Results", type="primary"):
        st.session_state["current_simulation_id"] = selected
        st.rerun()
    st.stop()
# Load simulation
sim = get_simulation(sim_id)
if not sim:
    # Session state is stale — clear it and show the selection UI
    st.session_state.pop("current_simulation_id", None)
    st.warning(
        f"The previously selected simulation is no longer available. "
        f"Please choose one below."
    )
    st.rerun()

# ============================================================
# HEADER
# ============================================================

section_header(
    f"Simulation: {sim_id[:30]}...",
    f"Solver: {sim.get('solver', 'N/A')} | "
    f"Execution: {sim.get('execution_time', 0):.1f}s",
    icon="📈",
)

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Change Simulation"):
        st.session_state.pop("current_simulation_id", None)
        st.rerun()

if sim.get("is_demo"):
    info_box("🔵 <b>Demo Data</b> — These results are from a simulated run.", "info")

# ============================================================
# LOAD MESH
# ============================================================

@st.cache_data(show_spinner="Loading result data...")
def load_mesh_cached(sim_id: str, is_demo: bool):
    """Cache the loaded mesh so it doesn't re-render on every interaction."""
    if is_demo:
        return load_demo_result()
    else:
        # Future: load real OpenFOAM results
        return load_demo_result()  # Fallback for now

try:
    mesh = load_mesh_cached(sim_id, bool(sim.get("is_demo")))
except Exception as e:
    st.error(f"Failed to load result mesh: {e}")
    st.stop()

available_fields = detect_fields(mesh)

if not available_fields:
    st.warning("No fields detected in this result.")
    st.stop()

# ============================================================
# METRICS SUMMARY
# ============================================================

import json

try:
    metrics = json.loads(sim.get("metrics") or "{}")
except Exception:
    metrics = {}

if metrics:
    section_header("Summary Metrics", "Key numbers from the simulation", icon="📊")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Max Velocity", f"{metrics.get('max_velocity', 0):.3f} m/s")
    with col2:
        st.metric("Max Pressure", f"{metrics.get('max_pressure', 0):.0f} Pa")
    with col3:
        st.metric("Cells", f"{metrics.get('mesh_cells', 0):,}")
    with col4:
        st.metric("Runtime", f"{sim.get('execution_time', 0):.1f} s")

# ============================================================
# VISUALIZATION CONTROLS
# ============================================================

st.markdown("---")
section_header("3D Visualization", "Configure and explore your results", icon="🎨")

# Sidebar-like controls panel
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)

with ctrl_col1:
    st.markdown("##### Data")
    selected_field = st.selectbox(
        "Variable",
        available_fields,
        index=0,
        key="results_variable",
    )
    display_mode = st.selectbox(
        "Display Mode",
        DISPLAY_MODES,
        index=0,
        key="results_mode",
    )
    cmap = st.selectbox(
        "Color Map",
        COLORMAPS,
        index=0,
        key="results_cmap",
    )

with ctrl_col2:
    st.markdown("##### Appearance")
    opacity = st.slider("Opacity", 0.1, 1.0, 0.9, 0.05, key="results_opacity")
    show_edges = st.checkbox("Show Mesh Edges", value=False, key="results_edges")

    st.markdown("##### Camera")
    camera_preset = st.selectbox(
        "View",
        list(CAMERA_PRESETS.keys()),
        index=0,
        key="results_camera",
    )

with ctrl_col3:
    st.markdown("##### Mode-Specific")
    slice_normal = "z"
    slice_position = 0.5
    streamline_density = 1.0
    vector_scale = 1.0
    contour_levels = 10

    if display_mode == "Slice":
        slice_normal = st.selectbox("Slice Plane", ["x", "y", "z"], index=2)
        slice_position = st.slider("Slice Position", 0.0, 1.0, 0.5, 0.05)
    elif display_mode == "Streamlines":
        streamline_density = st.slider("Streamline Density", 0.5, 3.0, 1.0, 0.1)
    elif display_mode == "Vectors":
        vector_scale = st.slider("Vector Scale", 0.1, 5.0, 1.0, 0.1)
    elif display_mode == "Contour":
        contour_levels = st.slider("Contour Levels", 3, 20, 10, 1)
    else:
        st.caption("No mode-specific controls for Surface")

# ============================================================
# RENDER
# ============================================================

st.markdown("---")

render_col1, render_col2 = st.columns([4, 1])

with render_col2:
    st.markdown("##### Actions")
    refresh = st.button("🔄 Re-render", use_container_width=True)
    reset_view = st.button("🎯 Reset View", use_container_width=True)
    download_vtk = st.button("💾 Download VTK", use_container_width=True)
    download_png = st.button("🖼️ Download PNG", use_container_width=True)

with render_col1:
    try:
        plotter = render_plotter(
            mesh=mesh,
            mode=display_mode,
            field=selected_field,
            cmap=cmap,
            opacity=opacity,
            show_edges=show_edges,
            slice_normal=slice_normal,
            slice_position=slice_position,
            streamline_density=streamline_density,
            vector_scale=vector_scale,
            contour_levels=contour_levels,
        )

        # Set camera
        preset = CAMERA_PRESETS.get(camera_preset, "iso")
        if preset == "iso":
            plotter.camera_position = "iso"
        else:
            plotter.view_xy() if preset == "xy" else None
            if preset == "xz":
                plotter.view_xz()
            elif preset == "yz":
                plotter.view_yz()

        # Try interactive stpyvista first
        preview_shown = False
        try:
            from stpyvista import stpyvista

            stpyvista(plotter, key=f"viewer_{display_mode}_{selected_field}")
            preview_shown = True
        except Exception as e:
            logger.warning(f"Interactive viewer failed: {e}")

        # Fallback: static PNG
        if not preview_shown:
            png_path = render_to_png(plotter)
            st.image(
                str(png_path),
                caption=f"{display_mode} — {selected_field}",
                use_container_width=True,
            )
            try:
                png_path.unlink()
            except Exception:
                pass

        # Handle downloads
        if download_vtk:
            vtk_path = save_mesh_as_vtk(mesh)
            with open(vtk_path, "rb") as f:
                st.download_button(
                    "⬇️ Click to Download VTK",
                    data=f.read(),
                    file_name=f"{sim_id}.vtk",
                    mime="application/octet-stream",
                )

        if download_png:
            png_path = render_to_png(plotter)
            with open(png_path, "rb") as f:
                st.download_button(
                    "⬇️ Click to Download PNG",
                    data=f.read(),
                    file_name=f"{sim_id}_{display_mode}.png",
                    mime="image/png",
                )

    except Exception as e:
        logger.error(f"Rendering failed: {e}")
        st.error(f"❌ Rendering failed: {e}")

# ============================================================
# LOGS
# ============================================================

st.markdown("---")
with st.expander("📜 Simulation Logs"):
    logs = get_logs(sim_id)
    if logs:
        log_text = "\n".join(log["content"] for log in logs)
        st.code(log_text, language="text")
    else:
        st.caption("No logs available.")