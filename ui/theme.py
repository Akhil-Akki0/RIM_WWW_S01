"""UI theme with custom CSS."""

import streamlit as st

COLORS = {
    "primary": "#3B82F6",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#06B6D4",
    "dark": "#1F2937",
    "gray": "#6B7280",
    "light": "#F3F4F6",
    "white": "#FFFFFF",
}


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .main .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }
        h1 { color: #1F2937; font-weight: 700; }
        h2 { color: #374151; font-weight: 600; }
        h3 { color: #4B5563; font-weight: 600; }
        
        .hero-container {
            padding: 3rem 2rem;
            background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 50%, #06B6D4 100%);
            border-radius: 16px;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin-bottom: 1rem; line-height: 1.1; color: white; }
        .hero-subtitle { font-size: 1.25rem; font-weight: 400; opacity: 0.95; margin-bottom: 0.5rem; color: white; }
        .hero-tagline { font-size: 1rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.9; color: white; }
        
        .metric-card {
            background: white; border: 1px solid #E5E7EB; border-radius: 12px;
            padding: 1.5rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease; height: 100%;
        }
        .metric-card:hover { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); transform: translateY(-2px); }
        .metric-label { font-size: 0.875rem; font-weight: 500; color: #6B7280; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
        .metric-value { font-size: 2rem; font-weight: 700; color: #1F2937; line-height: 1; }
        
        .feature-card { background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.75rem; height: 100%; transition: all 0.2s ease; }
        .feature-card:hover { border-color: #3B82F6; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15); }
        .feature-icon { font-size: 2rem; margin-bottom: 1rem; }
        .feature-title { font-size: 1.125rem; font-weight: 600; color: #1F2937; margin-bottom: 0.5rem; }
        .feature-description { font-size: 0.925rem; color: #6B7280; line-height: 1.6; }
        
        .status-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        .status-success { background-color: #D1FAE5; color: #065F46; }
        .status-warning { background-color: #FEF3C7; color: #92400E; }
        .status-error { background-color: #FEE2E2; color: #991B1B; }
        .status-info { background-color: #DBEAFE; color: #1E40AF; }
        
        .section-header { display: flex; align-items: center; gap: 0.75rem; margin: 2rem 0 1rem 0; padding-bottom: 0.75rem; border-bottom: 2px solid #E5E7EB; }
        .section-title { font-size: 1.5rem; font-weight: 700; color: #1F2937; }
        .section-subtitle { font-size: 0.95rem; color: #6B7280; margin-top: 0.25rem; }
        
        .info-box { padding: 1rem 1.25rem; border-radius: 8px; border-left: 4px solid; margin: 1rem 0; }
        .info-box-info { background-color: #EFF6FF; border-color: #3B82F6; color: #1E40AF; }
        .info-box-warning { background-color: #FFFBEB; border-color: #F59E0B; color: #92400E; }
        .info-box-error { background-color: #FEF2F2; border-color: #EF4444; color: #991B1B; }
        .info-box-success { background-color: #F0FDF4; border-color: #10B981; color: #065F46; }
        
        .app-footer { text-align: center; padding: 2rem 0 1rem 0; color: #9CA3AF; font-size: 0.875rem; border-top: 1px solid #E5E7EB; margin-top: 3rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )