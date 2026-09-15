"""Geometry upload, validation, and 3D preview."""
from pathlib import Path
import streamlit as st

from cfd import (
    create_preview_plotter,
    get_project_geometry_dir,
    load_geometry,
    save_uploaded_geometry,
    validate_geometry,
)
from core.logging import get_logger
from storage import (
    get_geometry,
    get_project,
    init_database,
    list_projects,
    save_geometry_record,
)
from ui.components import info_box, metric_card, section_header
from ui.theme import apply_theme

logger = get_logger(__name__)

st.set_page_config(page_title="Geometry", page_icon="🔷", layout="wide")
apply_theme()
init_database()

st.title("🔷 Geometry")
st.caption("Upload and validate your CFD geometry")

# ============================================================
# PROJECT SELECTION
# ============================================================

projects = list_projects(limit=100)

if not projects:
    info_box(
        "You need to create a project first. "
        "Go to <b>Projects</b> page and create one.",
        "warning",
    )
    if st.button("📁 Go to Projects", type="primary"):
        st.switch_page("pages/03_projects.py")
    st.stop()

# Get current project from session
current_project_id = st.session_state.get("current_project_id")

if not current_project_id:
    section_header("Select Project", "Choose which project to upload geometry for", icon="📁")

    project_options = {p["project_id"]: f"{p['name']} ({p['project_id'][:12]}...)" for p in projects}
    selected = st.selectbox(
        "Project",
        options=list(project_options.keys()),
        format_func=lambda x: project_options[x],
    )

    if st.button("Select Project", type="primary"):
        st.session_state["current_project_id"] = selected
        st.rerun()
    st.stop()

# We have a project selected
project = get_project(current_project_id)

if not project:
    st.error(f"Project {current_project_id} not found")
    st.session_state.pop("current_project_id", None)
    st.stop()

section_header(
    f"Project: {project['name']}",
    f"Type: {project['cfd_type']} | Fluid: {project.get('fluid_type', 'N/A')}",
    icon="📁",
)

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Change Project"):
        st.session_state.pop("current_project_id", None)
        st.rerun()

# ============================================================
# CHECK EXISTING GEOMETRY
# ============================================================

existing = get_geometry(current_project_id)

tab1, tab2 = st.tabs(["📤 Upload New", "📋 Existing Geometries"])

# ============================================================
# TAB 1: UPLOAD
# ============================================================

with tab1:
    section_header("Upload Geometry", "Supported formats: STL, OBJ", icon="📤")

    uploaded_file = st.file_uploader(
        "Choose a geometry file",
        type=["stl", "obj"],
        help="Drag and drop a .stl or .obj file here",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("### File Info")
            st.markdown(f"**Name:** {uploaded_file.name}")
            st.markdown(f"**Size:** {len(file_bytes) / 1024:.1f} KB")

        with col2:
            st.markdown("### Actions")
            analyze_clicked = st.button("🔍 Analyze Geometry", type="primary", use_container_width=True)
            save_clicked = st.button("💾 Save to Project", use_container_width=True)

        # Analyze geometry (preview + validation)
        if analyze_clicked or save_clicked:
            with st.spinner("Analyzing geometry..."):
                try:
                    # Save temporarily for analysis
                    temp_dir = get_project_geometry_dir(current_project_id) / "_temp"
                    temp_dir.mkdir(exist_ok=True)
                    temp_file = temp_dir / uploaded_file.name

                    with open(temp_file, "wb") as f:
                        f.write(file_bytes)

                    # Load and validate
                    mesh = load_geometry(temp_file)
                    validation = validate_geometry(mesh)

                    # Store in session for later use
                    st.session_state["_pending_geometry"] = {
                        "file_bytes": file_bytes,
                        "filename": uploaded_file.name,
                        "mesh": mesh,
                        "validation": validation,
                    }

                except Exception as e:
                    logger.error(f"Geometry analysis failed: {e}")
                    st.error(f"❌ Failed to analyze geometry: {e}")
                    st.stop()

        # Display analysis results
        if "_pending_geometry" in st.session_state:
            pending = st.session_state["_pending_geometry"]
            mesh = pending["mesh"]
            validation = pending["validation"]

            st.markdown("---")
            section_header("Geometry Analysis", "Preview and validation results", icon="🔬")

            # Validation status
            if validation["valid"]:
                info_box("✅ Geometry is valid and ready for simulation.", "success")
            else:
                errors = " | ".join(validation["errors"])
                info_box(f"❌ <b>Validation errors:</b> {errors}", "error")

            if validation["warnings"]:
                for warn in validation["warnings"]:
                    info_box(f"⚠️ {warn}", "warning")

            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                metric_card("Points", f"{validation['n_points']:,}", icon="🔵")
            with col2:
                metric_card("Cells", f"{validation['n_cells']:,}", icon="🔷")
            with col3:
                max_size = validation["size"]["max"]
                metric_card("Max Size", f"{max_size:.4f} m", icon="📏")
            with col4:
                tri = "Yes" if validation["is_triangulated"] else "No"
                metric_card("Triangulated", tri, icon="△")

                        # 3D Preview — Static PNG (works everywhere on Windows)
            st.markdown("### 3D Preview")

            try:
                import tempfile
                from pathlib import Path as _Path

                # Create plotter with off-screen rendering
                plotter = create_preview_plotter(mesh, window_size=(900, 600))
                plotter.off_screen = True

                # Render to temporary PNG
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = _Path(tmp.name)

                plotter.screenshot(str(tmp_path), transparent_background=False)
                plotter.close()

                # Display the rendered image
                st.image(
                    str(tmp_path),
                    caption=(
                        f"Geometry Preview — "
                        f"{mesh.n_points:,} points, {mesh.n_cells:,} cells"
                    ),
                    use_container_width=True,
                )

                # Optional: allow interactive stpyvista as a bonus
                with st.expander("🔍 Try interactive viewer (may not work on all systems)"):
                    try:
                        from stpyvista import stpyvista

                        interactive_plotter = create_preview_plotter(mesh)
                        stpyvista(interactive_plotter, key="geometry_preview_interactive")
                    except Exception as e:
                        st.caption(f"Interactive viewer unavailable: {e}")

                # Clean up temp file
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

            except Exception as e:
                logger.warning(f"3D preview failed: {e}")
                info_box(
                    f"3D preview could not be generated: {e}. "
                    f"Geometry validation above is still accurate.",
                    "warning",
                )

            # Save button
            st.markdown("---")

            if save_clicked or st.button("💾 Confirm Save", type="primary"):
                try:
                    with st.spinner("Saving geometry to project..."):
                        # Save the actual file
                        result = save_uploaded_geometry(
                            current_project_id,
                            file_bytes,
                            uploaded_file.name,
                        )

                        # Save to DB
                        save_geometry_record(
                            project_id=current_project_id,
                            filename=result["filename"],
                            original_filename=result["original_filename"],
                            file_path=result["file_path"],
                            file_size=result["file_size"],
                            file_format=result["format"],
                            validation_status="valid" if validation["valid"] else "invalid",
                            validation_message=" | ".join(validation["errors"]),
                        )

                        # Clean temp file
                        try:
                            temp_file.unlink()
                        except Exception:
                            pass

                        # Clear session
                        st.session_state.pop("_pending_geometry", None)

                    st.success(f"✅ Geometry saved: **{result['filename']}**")
                    st.balloons()

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("⚙️ Configure Simulation →", type="primary", use_container_width=True):
                            st.switch_page("pages/05_simulation_setup.py")
                    with col_b:
                        if st.button("📋 View Geometries", use_container_width=True):
                            st.rerun()

                except Exception as e:
                    logger.error(f"Failed to save geometry: {e}")
                    st.error(f"❌ Failed to save: {e}")

# ============================================================
# TAB 2: EXISTING GEOMETRIES
# ============================================================

with tab2:
    section_header("Existing Geometries", "Geometries saved for this project", icon="📋")

    from storage import list_geometries

    geometries = list_geometries(current_project_id)

    if not geometries:
        info_box("No geometries saved for this project yet.", "info")
    else:
        for geom in geometries:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

            with col1:
                st.markdown(f"**{geom['filename']}**")
                st.caption(geom.get("original_filename", ""))

            with col2:
                size_kb = geom.get("file_size", 0) / 1024
                st.caption(f"Size: {size_kb:.1f} KB")
                st.caption(f"Format: {geom.get('format', 'N/A')}")

            with col3:
                status = geom.get("validation_status", "unknown")
                icon = "✅" if status == "valid" else "❌"
                st.caption(f"{icon} {status}")

            with col4:
                if st.button("View", key=f"view_{geom['id']}"):
                    try:
                        mesh = load_geometry(Path(geom["file_path"]))
                        st.session_state["_pending_geometry"] = {
                            "mesh": mesh,
                            "validation": validate_geometry(mesh),
                            "filename": geom["filename"],
                        }
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load: {e}")

            st.markdown("---")