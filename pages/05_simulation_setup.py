"""Simulation configuration page."""

import json

import streamlit as st

from core.constants import (
    CFD_TYPE_SOLVER_MAP,
    DEFAULT_BOUNDARY_CONDITIONS,
    DEFAULT_MESH_SETTINGS,
    DEFAULT_SOLVER_SETTINGS,
    FLUID_PROPERTIES,
    SOLVERS,
)
from core.logging import get_logger
from core.validation import (
    SimulationConfigValidator,
    estimate_mesh_cells,
)
from storage import (
    get_geometry,
    get_project,
    init_database,
    list_projects,
)
from ui.components import info_box, metric_card, section_header
from ui.theme import apply_theme

logger = get_logger(__name__)

st.set_page_config(page_title="Simulation Setup", page_icon="⚙️", layout="wide")
apply_theme()
init_database()

st.title("⚙️ Simulation Setup")
st.caption("Configure the parameters for your CFD simulation")

# ============================================================
# PROJECT SELECTION
# ============================================================

projects = list_projects(limit=100)
if not projects:
    info_box("Create a project first.", "warning")
    if st.button("📁 Go to Projects", type="primary"):
        st.switch_page("pages/03_projects.py")
    st.stop()

current_project_id = st.session_state.get("current_project_id")

if not current_project_id:
    section_header("Select Project", "Which project are you configuring?", icon="📁")
    opts = {
        p["project_id"]: f"{p['name']} ({p['project_id'][:12]}...)" for p in projects
    }
    selected = st.selectbox("Project", list(opts.keys()), format_func=lambda x: opts[x])
    if st.button("Select Project", type="primary"):
        st.session_state["current_project_id"] = selected
        st.rerun()
    st.stop()

project = get_project(current_project_id)
if not project:
    st.error(f"Project not found: {current_project_id}")
    st.session_state.pop("current_project_id", None)
    st.stop()

# Check geometry exists
geometry = get_geometry(current_project_id)
if not geometry:
    info_box(
        f"No geometry uploaded for project <b>{project['name']}</b>. "
        f"Upload one first.",
        "warning",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔷 Upload Geometry", type="primary", use_container_width=True):
            st.switch_page("pages/04_geometry.py")
    with col2:
        if st.button("🔄 Change Project", use_container_width=True):
            st.session_state.pop("current_project_id", None)
            st.rerun()
    st.stop()

# ============================================================
# HEADER
# ============================================================

section_header(
    f"Project: {project['name']}",
    f"Geometry: {geometry['filename']} | CFD Type: {project['cfd_type']}",
    icon="📁",
)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔄 Change Project"):
        st.session_state.pop("current_project_id", None)
        st.rerun()
with col2:
    if st.button("🔷 Change Geometry"):
        st.switch_page("pages/04_geometry.py")

# ============================================================
# LOAD DEFAULTS
# ============================================================

default_fluid_name = project.get("fluid_type", "Air") or "Air"
if default_fluid_name not in FLUID_PROPERTIES:
    default_fluid_name = "Air"

fluid_defaults = FLUID_PROPERTIES[default_fluid_name]
suggested_solver = CFD_TYPE_SOLVER_MAP.get(project["cfd_type"], "simpleFoam")

# ============================================================
# CONFIGURATION TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "💧 Fluid Properties",
        "🌊 Boundary Conditions",
        "⚙️ Solver Settings",
        "🔷 Mesh Settings",
    ]
)

# ------------------------------------------------------------
# TAB 1: FLUID PROPERTIES
# ------------------------------------------------------------

with tab1:
    section_header(
        "Fluid Properties", "Physical properties of your working fluid", icon="💧"
    )

    col1, col2 = st.columns(2)

    with col1:
        fluid_name = st.selectbox(
            "Fluid *",
            ["Air", "Water", "Custom"],
            index=["Air", "Water", "Custom"].index(default_fluid_name),
        )
        density = st.number_input(
            "Density (kg/m³) *",
            value=float(fluid_defaults["density"]),
            min_value=0.001,
            max_value=25000.0,
            format="%.4f",
        )
        viscosity = st.number_input(
            "Dynamic Viscosity (Pa·s) *",
            value=float(fluid_defaults["dynamic_viscosity"]),
            min_value=1e-8,
            max_value=1e6,
            format="%.8f",
        )

    with col2:
        temperature = st.number_input(
            "Temperature (K)",
            value=float(fluid_defaults["temperature"]),
            min_value=1.0,
            max_value=5000.0,
            format="%.2f",
        )
        pressure = st.number_input(
            "Reference Pressure (Pa)",
            value=float(fluid_defaults["pressure"]),
            min_value=1.0,
            max_value=1e9,
            format="%.2f",
        )

    # Show computed kinematic viscosity
    if density > 0:
        nu = viscosity / density
        st.caption(f"→ Kinematic viscosity: ν = μ/ρ = {nu:.6e} m²/s")

# ------------------------------------------------------------
# TAB 2: BOUNDARY CONDITIONS
# ------------------------------------------------------------

with tab2:
    section_header(
        "Boundary Conditions", "Inlet, outlet, and wall conditions", icon="🌊"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Inlet")
        inlet_velocity = st.number_input(
            "Inlet Velocity (m/s) *",
            value=DEFAULT_BOUNDARY_CONDITIONS["inlet"]["velocity"],
            min_value=0.0,
            max_value=1000.0,
            format="%.2f",
        )
        inlet_pressure = st.number_input(
            "Inlet Pressure (Pa)",
            value=DEFAULT_BOUNDARY_CONDITIONS["inlet"]["pressure"],
            min_value=1.0,
            max_value=1e9,
            format="%.2f",
        )
        inlet_temp = st.number_input(
            "Inlet Temperature (K)",
            value=DEFAULT_BOUNDARY_CONDITIONS["inlet"]["temperature"],
            min_value=1.0,
            max_value=5000.0,
            format="%.2f",
        )

    with col2:
        st.markdown("#### Outlet")
        outlet_pressure = st.number_input(
            "Outlet Pressure (Pa) *",
            value=DEFAULT_BOUNDARY_CONDITIONS["outlet"]["pressure"],
            min_value=1.0,
            max_value=1e9,
            format="%.2f",
        )

        st.markdown("#### Walls")
        wall_type = st.selectbox(
            "Wall Boundary Type",
            ["no-slip", "slip", "partial-slip"],
            help="no-slip = zero velocity at wall (default)",
        )

    # Info about pressure drop
    st.markdown("---")
    pressure_drop = inlet_pressure - outlet_pressure
    st.caption(f"→ Pressure drop (ΔP): {pressure_drop:.2f} Pa")

# ------------------------------------------------------------
# TAB 3: SOLVER SETTINGS
# ------------------------------------------------------------

with tab3:
    section_header("Solver Settings", "Numerical solver configuration", icon="⚙️")

    solver_options = list(SOLVERS.keys())
    solver_index = (
        solver_options.index(suggested_solver)
        if suggested_solver in solver_options
        else 0
    )

    col1, col2 = st.columns(2)

    with col1:
        solver_name = st.selectbox(
            "Solver *",
            solver_options,
            index=solver_index,
            format_func=lambda x: f"{SOLVERS[x]['label']} — {SOLVERS[x]['description']}",
        )
        max_iterations = st.number_input(
            "Max Iterations *",
            value=DEFAULT_SOLVER_SETTINGS["max_iterations"],
            min_value=10,
            max_value=1_000_000,
            step=50,
        )

    with col2:
        convergence_tol = st.number_input(
            "Convergence Tolerance",
            value=DEFAULT_SOLVER_SETTINGS["convergence_tolerance"],
            min_value=1e-12,
            max_value=1e-1,
            format="%.1e",
            help="Lower = more accurate but slower. Typical: 1e-4 to 1e-6",
        )

        is_transient = SOLVERS[solver_name]["type"] == "Transient"
        time_step = st.number_input(
            "Time Step (s)",
            value=DEFAULT_SOLVER_SETTINGS["time_step"],
            min_value=1e-8,
            max_value=1000.0,
            format="%.6f",
            disabled=not is_transient,
            help=(
                "Only used for transient solvers"
                if is_transient
                else "N/A for steady solver"
            ),
        )

    st.caption(f"→ Solver type: **{SOLVERS[solver_name]['type']}**")

# ------------------------------------------------------------
# TAB 4: MESH SETTINGS
# ------------------------------------------------------------

with tab4:
    section_header("Mesh Settings", "Grid resolution for your simulation", icon="🔷")

    col1, col2 = st.columns(2)

    with col1:
        base_cell_size = st.number_input(
            "Base Cell Size (m) *",
            value=DEFAULT_MESH_SETTINGS["base_cell_size"],
            min_value=1e-6,
            max_value=100.0,
            format="%.4f",
            help="Smaller = finer mesh = more accurate but slower",
        )
        refinement_level = st.slider(
            "Refinement Level (0-5)",
            min_value=0,
            max_value=5,
            value=DEFAULT_MESH_SETTINGS["refinement_level"],
            help="Higher = more cells near the geometry",
        )

    with col2:
        boundary_layers = st.slider(
            "Boundary Layers (0-20)",
            min_value=0,
            max_value=20,
            value=DEFAULT_MESH_SETTINGS["boundary_layers"],
            help="Extra layers near walls for accurate boundary layer capture",
        )

    # Estimate mesh size
    geom_size = 1.0  # default
    try:
        if geometry.get("file_path"):
            from pathlib import Path

            from cfd.geometry import load_geometry, validate_geometry

            gpath = Path(geometry["file_path"])
            if gpath.exists():
                mesh = load_geometry(gpath)
                validation = validate_geometry(mesh)
                geom_size = validation["size"]["max"]
    except Exception as e:
        logger.warning(f"Could not read geometry size: {e}")

    est_cells = estimate_mesh_cells(geom_size, base_cell_size, refinement_level)

    st.markdown("---")
    st.markdown("#### Estimated Mesh Size")

    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Geometry Size", f"{geom_size:.3f} m", icon="📏")
    with col2:
        metric_card("Base Cell", f"{base_cell_size:.4f} m", icon="🔹")
    with col3:
        metric_card("Est. Cells", f"{est_cells:,}", icon="🔷")

    if est_cells > 5_000_000:
        info_box(
            f"⚠️ Estimated <b>{est_cells:,}</b> cells — this simulation may take a long time. "
            f"Consider increasing cell size or reducing refinement.",
            "warning",
        )
    elif est_cells > 1_000_000:
        info_box(
            f"Estimated <b>{est_cells:,}</b> cells — expected runtime: moderate.",
            "info",
        )
    else:
        info_box(f"Estimated <b>{est_cells:,}</b> cells — reasonable size.", "success")

# ============================================================
# BUILD CONFIGURATION
# ============================================================

config = {
    "fluid": {
        "name": fluid_name,
        "density": float(density),
        "dynamic_viscosity": float(viscosity),
        "temperature": float(temperature),
        "pressure": float(pressure),
    },
    "boundary_conditions": {
        "inlet": {
            "velocity": float(inlet_velocity),
            "pressure": float(inlet_pressure),
            "temperature": float(inlet_temp),
        },
        "outlet": {
            "pressure": float(outlet_pressure),
        },
        "walls": {
            "type": wall_type,
        },
    },
    "solver_settings": {
        "solver": solver_name,
        "max_iterations": int(max_iterations),
        "convergence_tolerance": float(convergence_tol),
        "time_step": float(time_step),
    },
    "mesh_settings": {
        "base_cell_size": float(base_cell_size),
        "refinement_level": int(refinement_level),
        "boundary_layers": int(boundary_layers),
        "estimated_cells": est_cells,
    },
}

# ============================================================
# VALIDATION & ACTIONS
# ============================================================

st.markdown("---")
section_header("Validation & Save", "Check and save your configuration", icon="✅")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔍 Validate Configuration", use_container_width=True):
        validator = SimulationConfigValidator(config)
        is_valid, errors, warnings = validator.validate()

        if is_valid:
            st.success("✅ Configuration is valid!")
            for w in warnings:
                st.warning(f"⚠️ {w}")
        else:
            st.error("❌ Configuration has errors:")
            for e in errors:
                st.markdown(f"- {e}")

with col2:
    if st.button("💾 Save & Continue →", type="primary", use_container_width=True):
        validator = SimulationConfigValidator(config)
        is_valid, errors, warnings = validator.validate()

        if not is_valid:
            st.error("❌ Please fix errors before saving:")
            for e in errors:
                st.markdown(f"- {e}")
        else:
            # Save to session
            st.session_state["simulation_config"] = config
            st.session_state["current_project_id"] = current_project_id
            st.success("✅ Configuration saved!")
            st.info("→ Next: Go to **Simulation Runner** to run the simulation")
            if st.button("▶️ Go to Simulation Runner"):
                st.switch_page("pages/07_simulation_runner.py")
