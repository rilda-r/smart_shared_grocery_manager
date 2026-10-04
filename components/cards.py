"""
components/cards.py
===================
Reusable card components for the GrocEase dashboard and pages.
"""

import streamlit as st
from utils.formatting import format_currency


_CARD_CSS = """
<style>
.metric-card {
    background: #FFFFFF;
    border: 1px solid #D8D0BE;
    border-top: 3px solid #1F4C3D;
    border-radius: 6px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.5rem;
}
.metric-card .mc-label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #5B6459;
    margin-bottom: 0.3rem;
}
.metric-card .mc-value {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.8rem;
    font-weight: 600;
    color: #1F4C3D;
    line-height: 1.1;
}
.metric-card .mc-sub {
    font-size: 0.8rem;
    color: #5B6459;
    margin-top: 0.3rem;
}
.metric-card-accent {
    border-top-color: #A97A1F;
}
.metric-card-accent .mc-value { color: #A97A1F; }
.metric-card-danger {
    border-top-color: #9C4B3E;
}
.metric-card-danger .mc-value { color: #9C4B3E; }
</style>
"""


def render_metric_card(label: str, value: str, sub: str = "", accent: str = "default"):
    """
    Render a single metric card.

    accent: 'default' | 'gold' | 'danger'
    """
    st.markdown(_CARD_CSS, unsafe_allow_html=True)
    accent_class = {
        "gold":   "metric-card-accent",
        "danger": "metric-card-danger",
    }.get(accent, "")
    st.markdown(
        f"""
        <div class="metric-card {accent_class}">
            <div class="mc-label">{label}</div>
            <div class="mc-value">{value}</div>
            {"" if not sub else f'<div class="mc-sub">{sub}</div>'}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_card(icon: str, title: str, body: str):
    """Render an informational panel card."""
    st.markdown(
        f"""
        <div style="background:#E7EFE6; border:1px solid #C3D6C6; border-radius:6px; padding:1.2rem;">
            <div style="font-size:1.5rem; margin-bottom:0.5rem;">{icon}</div>
            <div style="font-family:'Fraunces',serif; font-weight:600; color:#1F4C3D;
                        font-size:1rem; margin-bottom:0.3rem;">{title}</div>
            <div style="font-size:0.88rem; color:#5B6459;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(icon: str, message: str, sub: str = ""):
    """Render a friendly empty-state block."""
    st.markdown(
        f"""
        <div style="text-align:center; padding:3rem 1rem; color:#5B6459;">
            <div style="font-size:3rem; margin-bottom:0.8rem;">{icon}</div>
            <div style="font-size:1.05rem; font-weight:600; color:#20261F;">{message}</div>
            {"" if not sub else f'<div style="font-size:0.88rem; margin-top:0.4rem;">{sub}</div>'}
        </div>
        """,
        unsafe_allow_html=True,
    )
