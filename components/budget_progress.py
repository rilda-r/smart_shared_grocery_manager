"""
components/budget_progress.py
==============================
Budget progress bar component.
"""

import streamlit as st
from utils.formatting import format_currency, percentage_color


def render_budget_progress(budget: dict, current_spending: float):
    """
    Render a single budget row with progress bar.

    Args:
        budget: Budget dict with monthlyLimit, category, id
        current_spending: total spent in this category this month
    """
    monthly_limit = budget["monthlyLimit"]
    remaining = monthly_limit - current_spending
    pct = (current_spending / monthly_limit * 100) if monthly_limit > 0 else 0.0
    color = percentage_color(pct)
    clamped_pct = min(pct, 100)

    is_over = pct >= 100
    status_text = "⚠️ Over budget!" if is_over else f"{pct:.0f}% used"

    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1px solid #D8D0BE; border-radius:6px;
                    padding:1rem 1.2rem; margin-bottom:0.8rem;">
            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-bottom:0.5rem;">
                <div style="font-weight:600; color:#20261F;">{budget['category']}</div>
                <div style="font-size:0.82rem; color:{color}; font-weight:600;">{status_text}</div>
            </div>
            <div style="background:#F0F0F0; border-radius:4px; height:8px; overflow:hidden;">
                <div style="background:{color}; width:{clamped_pct}%; height:100%;
                            border-radius:4px; transition:width 0.3s ease;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:0.5rem;
                        font-size:0.8rem; color:#5B6459;">
                <div>Spent: <strong style="color:#20261F;">{format_currency(current_spending)}</strong></div>
                <div>Limit: <strong style="color:#20261F;">{format_currency(monthly_limit)}</strong></div>
                <div>Remaining: <strong style="color:{color};">{format_currency(max(remaining, 0))}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if is_over:
        st.error(f"🚨 You are over budget for **{budget['category']}** by {format_currency(abs(remaining))}!")
