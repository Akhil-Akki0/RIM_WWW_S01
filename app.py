"""AI CFD Platform - Main Entry Point."""

import streamlit as st

from core import __version__
from core.config import get_config
from core.logging import get_logger, setup_logging
from storage import init_database
from ui.theme import apply_theme

config = get_config()
setup_logging(debug=config.debug)
logger = get_logger(__name__)

logger.info(f"AI CFD Platform v{__version__} starting...")

st.set_page_config(
    page_title="AI CFD Platform",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
init_database()

# Sidebar
with st.sidebar:
    st.markdown("## 🌊 AI CFD Platform")
    st.caption(f"v{__version__}")
    st.markdown("---")

    st.markdown("### 🧭 Navigation")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/01_landing.py", label="Landing", icon="🌐")
    st.page_link("pages/02_dashboard.py", label="Dashboard", icon="📊")
    st.page_link("pages/03_projects.py", label="Projects", icon="📁")
    st.page_link("pages/04_geometry.py", label="Geometry", icon="🔷")
    st.page_link("pages/05_simulation_setup.py", label="Setup", icon="⚙️")
    st.page_link("pages/07_simulation_runner.py", label="Run", icon="▶️")
    st.page_link("pages/08_results.py", label="Results", icon="📈")
    st.page_link("pages/10_ai_analysis.py", label="AI", icon="🧠")
    st.page_link("pages/11_reporting.py", label="Reports", icon="📄")

    st.markdown("---")
    if config.demo_mode:
        st.info("🔵 Demo Mode")
    else:
        st.success("🟢 Live Mode")

# Main content
st.title("🌊 AI CFD Platform")
st.markdown("### AI-Powered Computational Fluid Dynamics")
st.markdown("")

col1, col2 = st.columns(2)
with col1:
    if st.button("🌐 Landing Page", use_container_width=True, type="primary"):
        st.switch_page("pages/01_landing.py")
with col2:
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/02_dashboard.py")

st.markdown("---")
st.markdown(f'<div class="app-footer">AI CFD Platform v{__version__}</div>',
            unsafe_allow_html=True)