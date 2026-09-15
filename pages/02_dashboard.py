"""Dashboard page."""

import streamlit as st

from core.config import get_config
from storage import (
    count_projects, count_simulations, init_database,
    list_projects, list_simulations,
)
from ui.components import info_box, metric_card, section_header
from ui.theme import apply_theme

config = get_config()
st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
apply_theme()
init_database()

st.title("📊 Dashboard")
st.caption("Overview of your CFD projects")

if config.demo_mode:
    info_box("You are in <b>Demo Mode</b>. Simulations use sample data.", "info")

total_projects = count_projects()
total_sims = count_simulations()
completed = count_simulations("completed")
running = count_simulations("running") + count_simulations("meshing")
failed = count_simulations("failed")

section_header("Overview", "Platform statistics", icon="📈")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("Projects", str(total_projects), icon="📁")
with col2:
    metric_card("Simulations", str(total_sims), icon="⚙️")
with col3:
    metric_card("Completed", str(completed), icon="✅")
with col4:
    metric_card("Running", str(running), icon="⏳")
with col5:
    metric_card("Failed", str(failed), icon="❌")

st.markdown("---")
section_header("Recent Projects", "Your latest projects", icon="📁")

recent_projects = list_projects(limit=5)
if recent_projects:
    for project in recent_projects:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{project['name']}**")
            st.caption(project.get("description", "No description"))
        with col2:
            st.caption(f"Type: {project['cfd_type']}")
        with col3:
            if st.button("Open", key=f"open_{project['project_id']}"):
                st.session_state["current_project_id"] = project["project_id"]
                st.switch_page("pages/05_simulation_setup.py")
        st.markdown("---")
else:
    info_box("No projects yet. Create your first project.", "info")

section_header("Recent Simulations", "Latest runs", icon="⚙️")
recent_sims = list_simulations(limit=5)
if recent_sims:
    for sim in recent_sims:
        status = sim.get("status", "unknown")
        icon = {"completed": "✅", "running": "⏳", "failed": "❌", "queued": "🕐"}.get(status, "❓")
        st.markdown(f"{icon} **{sim['simulation_id'][:25]}** — {status}")
else:
    info_box("No simulations yet.", "info")

st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("➕ New Project", use_container_width=True, type="primary"):
        st.switch_page("pages/03_projects.py")
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()