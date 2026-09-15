"""Simulation runner page with live progress and logs."""

from datetime import datetime
from pathlib import Path

import streamlit as st

from cfd import CaseGenerator, run_simulation
from core.config import get_config
from core.logging import get_logger
from storage import (
    append_log,
    create_simulation,
    get_geometry,
    get_project,
    init_database,
    update_simulation_results,
    update_simulation_status,
)
from ui.components import info_box, metric_card, section_header
from ui.theme import apply_theme

logger = get_logger(__name__)
config = get_config()

st.set_page_config(page_title="Simulation Runner", page_icon="▶️", layout="wide")
apply_theme()
init_database()

st.title("▶️ Simulation Runner")
st.caption("Execute and monitor your CFD simulation")

# ============================================================
# PRECHECKS
# ============================================================

project_id = st.session_state.get("current_project_id")
sim_config = st.session_state.get("simulation_config")

if not project_id:
    info_box("No project selected. Go to Setup first.", "warning")
    if st.button("⚙️ Go to Setup", type="primary"):
        st.switch_page("pages/05_simulation_setup.py")
    st.stop()

if not sim_config:
    info_box("No simulation configured. Go to Setup first.", "warning")
    if st.button("⚙️ Go to Setup", type="primary"):
        st.switch_page("pages/05_simulation_setup.py")
    st.stop()

project = get_project(project_id)
if not project:
    st.error(f"Project not found: {project_id}")
    st.stop()

geometry = get_geometry(project_id)
if not geometry:
    info_box("No geometry uploaded. Go to Geometry first.", "warning")
    if st.button("🔷 Upload Geometry", type="primary"):
        st.switch_page("pages/04_geometry.py")
    st.stop()

# ============================================================
# HEADER
# ============================================================

section_header(
    f"Project: {project['name']}",
    f"Solver: {sim_config['solver_settings']['solver']} | "
    f"Fluid: {sim_config['fluid']['name']} | "
    f"Demo: {'Yes' if config.demo_mode else 'No'}",
    icon="📁",
)

with st.expander("📋 Configuration Summary", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Fluid**")
        st.caption(f"Density: {sim_config['fluid']['density']:.4f} kg/m³")
        st.caption(f"Viscosity: {sim_config['fluid']['dynamic_viscosity']:.3e} Pa·s")
        st.caption(f"Temperature: {sim_config['fluid']['temperature']:.2f} K")
    with col2:
        st.markdown("**Boundary Conditions**")
        bc = sim_config["boundary_conditions"]
        st.caption(f"Inlet velocity: {bc['inlet']['velocity']:.2f} m/s")
        st.caption(f"Inlet pressure: {bc['inlet']['pressure']:.0f} Pa")
        st.caption(f"Outlet pressure: {bc['outlet']['pressure']:.0f} Pa")
    with col3:
        st.markdown("**Solver & Mesh**")
        sol = sim_config["solver_settings"]
        mesh = sim_config["mesh_settings"]
        st.caption(f"Max iterations: {sol['max_iterations']}")
        st.caption(f"Base cell size: {mesh['base_cell_size']:.4f} m")
        st.caption(f"Est. cells: {mesh.get('estimated_cells', 0):,}")

if config.demo_mode:
    info_box(
        "🔵 <b>Demo Mode</b> — Simulations use sample data. "
        "Set <code>DEMO_MODE=false</code> in <code>.env</code> for real runs.",
        "info",
    )
else:
    info_box(
        "🟢 <b>Real Mode</b> — Simulations run OpenFOAM via WSL. "
        "This may take several minutes.",
        "warning",
    )

# ============================================================
# SESSION STATE
# ============================================================

if "runner_state" not in st.session_state:
    st.session_state["runner_state"] = {
        "running": False,
        "completed": False,
        "simulation_id": None,
        "result": None,
    }

runner = st.session_state["runner_state"]

# ============================================================
# RUN CONTROLS
# ============================================================

col1, col2 = st.columns([1, 3])

with col1:
    run_clicked = st.button(
        "🚀 RUN SIMULATION",
        type="primary",
        use_container_width=True,
        disabled=runner["running"],
    )

with col2:
    if runner["completed"] and runner["simulation_id"]:
        if st.button("📈 View Results", use_container_width=True):
            st.session_state["current_simulation_id"] = runner["simulation_id"]
            st.switch_page("pages/08_results.py")

# ============================================================
# EXECUTION
# ============================================================

if run_clicked and not runner["running"]:
    runner["running"] = True
    runner["completed"] = False
    runner["result"] = None

    # Create DB record
    sim_record = create_simulation(
        project_id=project_id,
        solver=sim_config["solver_settings"]["solver"],
        config=sim_config,
        is_demo=config.demo_mode,
    )
    simulation_id = sim_record["simulation_id"]
    runner["simulation_id"] = simulation_id
    logger.info(f"Simulation created: {simulation_id}")

    # UI placeholders
    st.markdown("---")
    section_header("Progress", f"Simulation ID: {simulation_id}", icon="⚡")

    progress_bar = st.progress(0)
    status_text = st.empty()

    def on_progress(step_name: str, pct: int, log_msg: str = None):
        progress_bar.progress(pct / 100.0)
        status_text.markdown(f"**{step_name}** — {pct}%")

    # Prepare case path (real mode only)
    case_path = None
    if not config.demo_mode:
        try:
            from core.config import get_config as _get_config
            app_cfg = _get_config()
            case_dir = (
                app_cfg.data_directory / "projects" / project_id
                / "simulations" / simulation_id / "case"
            )
            case_dir.mkdir(parents=True, exist_ok=True)

            status_text.info("📁 Preparing OpenFOAM case...")
            generator = CaseGenerator()
            generator.generate(
                case_path=case_dir,
                geometry_path=Path(geometry["file_path"]),
                config=sim_config,
            )
            case_path = case_dir
            logger.info(f"Case generated at {case_path}")

        except Exception as e:
            logger.error(f"Case generation failed: {e}", exc_info=True)
            update_simulation_status(simulation_id, "failed", str(e))
            runner["running"] = False
            st.error(f"❌ Failed to generate OpenFOAM case: {e}")
            st.stop()

    # Run it
    try:
        result = run_simulation(
            project_id=project_id,
            config=sim_config,
            case_path=case_path,
            progress_callback=on_progress,
        )
        runner["result"] = result

        # Save to DB
        update_simulation_status(simulation_id, result.status)
        if result.status == "completed":
            update_simulation_results(
                simulation_id=simulation_id,
                metrics=result.metrics,
                available_fields=result.available_fields,
                execution_time=result.execution_time,
            )

        # Save logs
        for log_entry in result.logs:
            append_log(
                simulation_id=simulation_id,
                content=f"[{log_entry['timestamp']}] {log_entry['message']}",
                log_type=log_entry["type"],
            )

        runner["running"] = False
        runner["completed"] = result.status == "completed"

        if result.status == "completed":
            st.success(f"✅ Simulation completed in {result.execution_time:.1f}s")
            st.balloons()
        else:
            st.error(f"❌ Simulation failed: {result.error_message}")

    except Exception as e:
        logger.error(f"Simulation runner error: {e}", exc_info=True)
        update_simulation_status(simulation_id, "failed", str(e))
        runner["running"] = False
        st.error(f"❌ Error: {e}")

# ============================================================
# SHOW RESULT
# ============================================================

if runner.get("result") and runner["result"].status == "completed":
    result = runner["result"]

    st.markdown("---")
    section_header("Results Summary", "Metrics from the simulation", icon="📊")

    col1, col2, col3, col4 = st.columns(4)
    m = result.metrics
    with col1:
        metric_card("Max Velocity", f"{m.get('max_velocity', 0):.3f} m/s", icon="🚀")
    with col2:
        metric_card("Max Pressure", f"{m.get('max_pressure', 0):.0f} Pa", icon="🔺")
    with col3:
        metric_card("Cells", f"{m.get('mesh_cells', 0):,}", icon="🔷")
    with col4:
        metric_card("Runtime", f"{result.execution_time:.1f} s", icon="⏱️")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📈 View 3D Results", type="primary", use_container_width=True):
            st.session_state["current_simulation_id"] = result.simulation_id
            st.switch_page("pages/08_results.py")
    with col2:
        if st.button("🔄 Run Again", use_container_width=True):
            st.session_state["runner_state"] = {
                "running": False,
                "completed": False,
                "simulation_id": None,
                "result": None,
            }
            st.rerun()

# ============================================================
# LOG VIEWER
# ============================================================

if runner.get("result") and runner["result"].logs:
    st.markdown("---")
    with st.expander("📜 Simulation Logs", expanded=False):
        log_text = "\n".join(
            f"[{e['timestamp']}] {e['message']}" for e in runner["result"].logs
        )
        st.code(log_text, language="text")