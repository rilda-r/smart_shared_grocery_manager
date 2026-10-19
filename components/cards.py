"""
components/cards.py
===================
Reusable card components for the GrocEase dashboard and pages.
Shared Kitchen Counter aesthetic design.
"""

import streamlit as st
from utils.formatting import format_currency


_CARD_CSS = """
<style>
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.85rem;
    margin-bottom: 1.5rem;
    align-items: stretch;
}
@media (max-width: 1100px) {
    .metrics-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
    }
}
@media (max-width: 640px) {
    .metrics-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 0.65rem;
    }
}
.metric-card {
    background: #F7FBFA;
    border: 1px solid #CADDD8;
    border-top: 4px solid #0F766E;
    border-radius: 18px;
    padding: 1.15rem 1rem;
    box-shadow: 0 4px 20px -2px rgba(16, 39, 42, 0.08);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    min-height: 128px;
    box-sizing: border-box;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px -4px rgba(16, 39, 42, 0.12);
}
.metric-card .mc-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #9A6A12;
    margin-bottom: 0.35rem;
}
.metric-card .mc-value {
    font-family: 'Fraunces', Georgia, serif;
    font-size: clamp(1.25rem, 1.6vw, 1.65rem);
    font-weight: 700;
    color: #0F766E;
    line-height: 1.15;
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.metric-card .mc-sub {
    font-size: 0.76rem;
    color: #4A6568;
    margin-top: 0.35rem;
}
.metric-card.metric-card-accent {
    border-top-color: #6B8F71;
}
.metric-card.metric-card-accent .mc-value { color: #6B8F71; }
.metric-card.metric-card-danger {
    border-top-color: #8C1C13;
}
.metric-card.metric-card-danger .mc-value { color: #8C1C13; }
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
    sub_html = f'<div class="mc-sub">{sub}</div>' if sub else ''
    html = f'<div class="metric-card {accent_class}"><div><div class="mc-label">{label}</div><div class="mc-value">{value}</div></div>{sub_html}</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_metric_cards_grid(cards: list):
    """
    Render a cohesive, perfectly aligned row or 2x3/3x2 responsive grid of metric cards.
    Each item in cards should be a dict with keys: 'label', 'value', 'sub' (optional), 'accent' (optional).
    """
    st.markdown(_CARD_CSS, unsafe_allow_html=True)
    cards_html = []
    for c in cards:
        label = c.get("label", "")
        val = c.get("value", "")
        sub = c.get("sub", "")
        accent = c.get("accent", "default")
        accent_class = {
            "gold":   "metric-card-accent",
            "danger": "metric-card-danger",
        }.get(accent, "")
        sub_html = f'<div class="mc-sub">{sub}</div>' if sub else ''
        cards_html.append(
            f'<div class="metric-card {accent_class}"><div><div class="mc-label">{label}</div><div class="mc-value">{val}</div></div>{sub_html}</div>'
        )
    joined_cards = "".join(cards_html)
    st.markdown(f'<div class="metrics-grid">{joined_cards}</div>', unsafe_allow_html=True)


def render_info_card(icon: str, title: str, body: str):
    """Render an informational panel card."""
    st.markdown(
        f"""
        <div style="background:#F7FBFA; border:1px solid #CADDD8; border-radius:18px;
                    padding:1.4rem; box-shadow:0 4px 20px -2px rgba(16, 39, 42, 0.08);">
            <div style="font-size:1.6rem; margin-bottom:0.4rem;">{icon}</div>
            <div style="font-family:'Fraunces',Georgia,serif; font-weight:700; color:#0F766E;
                        font-size:1.05rem; margin-bottom:0.3rem;">{title}</div>
            <div style="font-size:0.9rem; color:#10272A; line-height:1.5;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(icon: str, message: str, sub: str = ""):
    """Render a friendly empty-state block."""
    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1.5px dashed #CADDD8; border-radius:18px;
                    text-align:center; padding:2.8rem 1.2rem; color:#4A6568; box-shadow:0 2px 8px rgba(16,39,42,0.03);">
            <div style="font-size:2.8rem; margin-bottom:0.6rem;">{icon}</div>
            <div style="font-family:'Fraunces',Georgia,serif; font-size:1.15rem; font-weight:700; color:#10272A;">{message}</div>
            {"" if not sub else f'<div style="font-size:0.88rem; color:#4A6568; margin-top:0.35rem;">{sub}</div>'}
        </div>
        """,
        unsafe_allow_html=True,
    )
