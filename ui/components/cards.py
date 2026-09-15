"""Reusable UI card components."""

from typing import Optional

import streamlit as st


def metric_card(label: str, value: str, delta: Optional[str] = None, icon: Optional[str] = None) -> None:
    icon_html = f'<div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>' if icon else ""
    st.markdown(
        f"""
        <div class="metric-card">
            {icon_html}
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(icon: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="feature-card">
            <div class="feature-icon">{icon}</div>
            <div class="feature-title">{title}</div>
            <div class="feature-description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(text: str, status: str = "info") -> str:
    return f'<span class="status-badge status-{status}">{text}</span>'


def info_box(message: str, box_type: str = "info") -> None:
    icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}
    icon = icons.get(box_type, "ℹ️")
    st.markdown(
        f'<div class="info-box info-box-{box_type}">{icon} {message}</div>',
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: Optional[str] = None, icon: Optional[str] = None) -> None:
    icon_html = f'<span style="font-size: 1.75rem;">{icon}</span>' if icon else ""
    subtitle_html = f'<div class="section-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-header">
            {icon_html}
            <div>
                <div class="section-title">{title}</div>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )