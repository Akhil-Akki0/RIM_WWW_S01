"""Landing page."""

import streamlit as st

from core import __version__
from ui.components import feature_card, info_box, section_header
from ui.theme import apply_theme

st.set_page_config(page_title="Landing", page_icon="🌐", layout="wide")
apply_theme()

st.markdown(
    """
    <div class="hero-container">
        <div class="hero-tagline">AI CFD PLATFORM</div>
        <div class="hero-title">AI-Powered Computational<br>Fluid Dynamics</div>
        <div class="hero-subtitle">Simulate. Analyze. Predict.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🚀 Start Simulation", use_container_width=True, type="primary"):
        st.switch_page("pages/03_projects.py")
with col2:
    if st.button("📊 View Dashboard", use_container_width=True):
        st.switch_page("pages/02_dashboard.py")
with col3:
    if st.button("📖 Documentation", use_container_width=True):
        st.info("Documentation coming soon.")

section_header("What is CFD?", "The science behind the platform", icon="🔬")

st.markdown("""
**Computational Fluid Dynamics (CFD)** is the science of using computers to solve 
the equations that govern how fluids — liquids and gases — flow, transfer heat, and react.

Instead of building expensive prototypes, engineers simulate flow digitally using the 
**Navier-Stokes equations**.
""")

section_header("Core Capabilities", "Everything you need", icon="⚡")

col1, col2, col3, col4 = st.columns(4)
with col1:
    feature_card("🔬", "CFD Simulation", "Run OpenFOAM simulations for aerodynamics, internal flow, and heat transfer.")
with col2:
    feature_card("🎨", "3D Visualization", "Interactive 3D visualization of velocity, pressure, and temperature fields.")
with col3:
    feature_card("🧠", "AI Analysis", "Physics-informed neural networks for fast flow prediction.")
with col4:
    feature_card("📊", "Automated Reports", "Professional Excel reports with metrics and insights.")

st.markdown(f'<div class="app-footer">AI CFD Platform v{__version__} | Free & Open Source</div>',
            unsafe_allow_html=True)