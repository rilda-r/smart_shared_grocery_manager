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
        <div style="background:#FFFFFF; border:1px solid rgba(163, 150, 112, 0.35); border-radius:16px;
                    padding:1.15rem 1.35rem; margin-bottom:0.85rem; box-shadow:0 4px 14px rgba(55, 39, 19, 0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-bottom:0.6rem;">
                <div style="font-size:1.02rem; font-weight:700; color:#372713;">{budget['category']}</div>
                <div style="font-size:0.82rem; color:{color}; font-weight:700; background:#FAF6F0; border:1px solid rgba(163,150,112,0.3); border-radius:12px; padding:2px 8px;">{status_text}</div>
            </div>
            <div style="background:#FAF6F0; border:1px solid rgba(163, 150, 112, 0.25); border-radius:8px; height:9px; overflow:hidden;">
                <div style="background:{color}; width:{clamped_pct}%; height:100%;
                            border-radius:8px; transition:width 0.3s ease;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:0.65rem;
                        font-size:0.84rem; color:#6B5A47;">
                <div>Spent: <strong style="color:#372713;">{format_currency(current_spending)}</strong></div>
                <div>Limit: <strong style="color:#372713;">{format_currency(monthly_limit)}</strong></div>
                <div>Remaining: <strong style="color:{color}; font-weight:700;">{format_currency(max(remaining, 0))}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if is_over:
        st.error(f"🚨 You are over budget for **{budget['category']}** by {format_currency(abs(remaining))}!")
