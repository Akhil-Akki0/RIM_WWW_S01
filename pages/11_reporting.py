"""Reports — generate and download Excel reports."""

import json
from datetime import datetime

import streamlit as st

from core.config import get_config
from core.logging import get_logger
from reports import generate_report_for_simulation
from storage import (
    get_geometry,
    get_logs,
    get_project,
    get_simulation,
    init_database,
    list_simulations,
)
from ui.components import info_box, metric_card, section_header
from ui.theme import apply_theme

logger = get_logger(__name__)
config = get_config()

st.set_page_config(page_title="Reports", page_icon="📄", layout="wide")
apply_theme()
init_database()

st.title("📄 Reports")
st.caption("Generate professional Excel reports for your simulations")

# ============================================================
# SIMULATION SELECTION
# ============================================================

sim_id = st.session_state.get("current_simulation_id")

# Validate session state
if sim_id:
    existing = get_simulation(sim_id)
    if not existing or existing.get("status") != "completed":
        st.session_state.pop("current_simulation_id", None)
        sim_id = None

if not sim_id:
    completed_sims = list_simulations(status="completed", limit=20)
    if not completed_sims:
        info_box("No completed simulations to report on yet.", "warning")
        if st.button("▶️ Go to Simulation Runner", type="primary"):
            st.switch_page("pages/07_simulation_runner.py")
        st.stop()

    section_header("Select Simulation", "Choose a simulation to report on", icon="📋")

    opts = {
        s["simulation_id"]: f"{s['simulation_id'][:30]}... — {s.get('solver', 'N/A')}"
        for s in completed_sims
    }
    selected = st.selectbox(
        "Simulation", list(opts.keys()), format_func=lambda x: opts[x]
    )
    if st.button("Load", type="primary"):
        st.session_state["current_simulation_id"] = selected
        st.rerun()
    st.stop()

# ============================================================
# LOAD SIMULATION
# ============================================================

sim = get_simulation(sim_id)
project = get_project(sim["project_id"]) if sim else None
geometry = get_geometry(sim["project_id"]) if sim else None
logs = get_logs(sim_id)

if not sim or not project:
    st.error("Simulation or project not found.")
    st.stop()

section_header(
    f"Report for: {sim_id[:30]}...",
    f"Project: {project['name']} | Solver: {sim.get('solver')}",
    icon="📄",
)

# ============================================================
# REPORT PREVIEW
# ============================================================

st.markdown("### Report Contents")

try:
    metrics = json.loads(sim.get("metrics") or "{}")
except Exception:
    metrics = {}

try:
    config_data = json.loads(sim.get("config") or "{}")
except Exception:
    config_data = {}

# Metrics summary
col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Max Velocity", f"{metrics.get('max_velocity', 0):.2f} m/s", icon="🚀")
with col2:
    metric_card("Max Pressure", f"{metrics.get('max_pressure', 0):.0f} Pa", icon="🔺")
with col3:
    metric_card("Cells", f"{metrics.get('mesh_cells', 0):,}", icon="🔷")
with col4:
    metric_card("Runtime", f"{sim.get('execution_time', 0):.1f} s", icon="⏱️")

st.markdown("---")

# Report contents
with st.expander("📋 What's in the report?", expanded=True):
    st.markdown("""
    The Excel report contains **9 worksheets**:
    
    | # | Sheet | Contents |
    |---|-------|----------|
    | 1 | **Summary** | Project info, simulation ID, key results |
    | 2 | **Geometry** | File details, validation status |
    | 3 | **Fluid Properties** | Density, viscosity, temperature, pressure |
    | 4 | **Boundary Conditions** | Inlet/outlet/wall conditions |
    | 5 | **Solver** | Solver name, iterations, tolerance |
    | 6 | **Mesh** | Cell size, refinement, layer count |
    | 7 | **Results** | All computed metrics + available fields |
    | 8 | **AI Analysis** | Model status (placeholder for now) |
    | 9 | **Simulation Logs** | Full chronological log |
    
    All sheets include professional formatting, headers, and units.
    """)

# ============================================================
# GENERATE BUTTON
# ============================================================

st.markdown("---")
section_header("Generate Report", "Create the Excel file", icon="⚙️")

col1, col2 = st.columns([1, 3])

with col1:
    generate_clicked = st.button(
        "📊 Generate Excel Report",
        type="primary",
        use_container_width=True,
    )

with col2:
    st.caption("The report will include all data from this simulation.")

# ============================================================
# GENERATE
# ============================================================

if generate_clicked:
    with st.spinner("Generating Excel report..."):
        try:
            report_path = generate_report_for_simulation(sim_id)

            if report_path and report_path.exists():
                st.success("✅ Report generated successfully!")

                # Read file for download
                with open(report_path, "rb") as f:
                    report_bytes = f.read()

                size_kb = len(report_bytes) / 1024
                st.info(f"📄 Report size: {size_kb:.1f} KB")

                # Download button
                st.download_button(
                    label="⬇️ Download Excel Report",
                    data=report_bytes,
                    file_name=f"cfd_report_{sim_id[:20]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                )

                # Cleanup temp file
                try:
                    report_path.unlink()
                except Exception:
                    pass

            else:
                st.error("❌ Report generation returned no file.")

        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            st.error(f"❌ Failed to generate report: {e}")

# ============================================================
# LOG VIEWER
# ============================================================

st.markdown("---")
with st.expander("📜 Simulation Logs Preview"):
    if logs:
        log_text = "\n".join(
            f"[{str(log.get('timestamp', ''))[:19]}] {log.get('content', '')}"
            for log in logs
        )
        st.code(log_text, language="text")
    else:
        st.caption("No logs available.")
