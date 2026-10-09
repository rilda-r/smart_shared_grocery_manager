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
    border: 1px solid rgba(163, 150, 112, 0.35);
    border-top: 4px solid #5C0203;
    border-radius: 18px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 6px 18px rgba(55, 39, 19, 0.05), 0 1px 3px rgba(55, 39, 19, 0.03);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 22px rgba(55, 39, 19, 0.08);
}
.metric-card .mc-label {
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #A39670;
    margin-bottom: 0.35rem;
}
.metric-card .mc-value {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.95rem;
    font-weight: 700;
    color: #5C0203;
    line-height: 1.1;
    letter-spacing: -0.01em;
}
.metric-card .mc-sub {
    font-size: 0.8rem;
    color: #6B5A47;
    margin-top: 0.35rem;
}
.metric-card-accent {
    border-top-color: #A39670;
}
.metric-card-accent .mc-value { color: #4D4828; }
.metric-card-danger {
    border-top-color: #5C0203;
}
.metric-card-danger .mc-value { color: #5C0203; }
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
        <div style="background:#FCFBF8; border:1px solid rgba(163, 150, 112, 0.4); border-radius:18px;
                    padding:1.4rem; box-shadow:0 4px 14px rgba(55, 39, 19, 0.04);">
            <div style="font-size:1.6rem; margin-bottom:0.4rem;">{icon}</div>
            <div style="font-family:'Fraunces',Georgia,serif; font-weight:700; color:#5C0203;
                        font-size:1.05rem; margin-bottom:0.3rem;">{title}</div>
            <div style="font-size:0.9rem; color:#372713; line-height:1.5;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(icon: str, message: str, sub: str = ""):
    """Render a friendly empty-state block."""
    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1.5px dashed rgba(163, 150, 112, 0.45); border-radius:20px;
                    text-align:center; padding:2.8rem 1.2rem; color:#6B5A47; box-shadow:0 2px 8px rgba(55,39,19,0.02);">
            <div style="font-size:2.8rem; margin-bottom:0.6rem;">{icon}</div>
            <div style="font-family:'Fraunces',Georgia,serif; font-size:1.15rem; font-weight:700; color:#372713;">{message}</div>
            {"" if not sub else f'<div style="font-size:0.88rem; color:#6B5A47; margin-top:0.35rem;">{sub}</div>'}
        </div>
        """,
        unsafe_allow_html=True,
    )
