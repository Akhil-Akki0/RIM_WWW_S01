"""Projects page."""

import streamlit as st

from storage import create_project, init_database, list_projects
from ui.components import info_box, section_header
from ui.theme import apply_theme

st.set_page_config(page_title="Projects", page_icon="📁", layout="wide")
apply_theme()
init_database()

st.title("📁 Projects")
st.caption("Create and manage your CFD projects")

tab1, tab2 = st.tabs(["➕ Create New Project", "📋 All Projects"])

with tab1:
    section_header("New Project", "Define your CFD simulation goals", icon="✨")

    with st.form("create_project_form"):
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Project Name *", placeholder="e.g., Car Aerodynamics")
            cfd_type = st.selectbox("CFD Type *", [
                "External Aerodynamics", "Internal Flow", "Pipe Flow",
                "Airflow", "Heat Transfer", "Custom",
            ])
            fluid_type = st.selectbox("Fluid *", ["Air", "Water", "Custom"])
        with col2:
            simulation_type = st.selectbox("Simulation Type *", ["Steady State", "Transient"])
            description = st.text_area("Description", height=100)

        submitted = st.form_submit_button("✅ Create Project", use_container_width=True, type="primary")

        if submitted:
            if not project_name.strip():
                st.error("❌ Project name is required")
            elif len(project_name.strip()) < 3:
                st.error("❌ Project name must be at least 3 characters")
            else:
                project = create_project(
                    name=project_name.strip(),
                    description=description.strip(),
                    cfd_type=cfd_type,
                    fluid_type=fluid_type,
                    simulation_type=simulation_type,
                )
                st.success(f"✅ Project **{project['name']}** created!")
                st.session_state["current_project_id"] = project["project_id"]

with tab2:
    section_header("All Projects", "Browse existing projects", icon="📂")
    projects = list_projects(limit=100)
    if not projects:
        info_box("No projects yet.", "info")
    else:
        for project in projects:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"### {project['name']}")
                st.caption(project.get("description") or "No description")
            with col2:
                st.markdown(f"**Type:** {project['cfd_type']}")
                st.markdown(f"**Fluid:** {project.get('fluid_type', 'N/A')}")
            with col3:
                if st.button("Open", key=f"open_{project['project_id']}", use_container_width=True):
                    st.session_state["current_project_id"] = project["project_id"]
                    st.switch_page("pages/05_simulation_setup.py")
            st.markdown("---")