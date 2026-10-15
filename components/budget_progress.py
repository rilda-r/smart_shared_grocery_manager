"""
components/budget_progress.py
==============================
Budget progress bar component.
Shared Kitchen Counter aesthetic design.
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
        <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:18px;
                    padding:1.15rem 1.35rem; margin-bottom:0.85rem; box-shadow:0 4px 20px -2px rgba(59, 42, 32, 0.08);">
            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-bottom:0.6rem;">
                <div style="font-size:1.02rem; font-weight:700; color:#2A1D16;">{budget['category']}</div>
                <div style="font-size:0.82rem; color:{color}; font-weight:700; background:#F7F2E8; border:1px solid #E3D6BE; border-radius:12px; padding:2px 8px;">{status_text}</div>
            </div>
            <div style="background:#EADFCB; border:1px solid #E3D6BE; border-radius:8px; height:9px; overflow:hidden;">
                <div style="background:{color}; width:{clamped_pct}%; height:100%;
                            border-radius:8px; transition:width 0.3s ease;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:0.65rem;
                        font-size:0.84rem; color:#5C4A3E;">
                <div>Spent: <strong style="color:#2A1D16;">{format_currency(current_spending)}</strong></div>
                <div>Limit: <strong style="color:#2A1D16;">{format_currency(monthly_limit)}</strong></div>
                <div>Remaining: <strong style="color:{color}; font-weight:700;">{format_currency(max(remaining, 0))}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if is_over:
        st.error(f"🚨 You are over budget for **{budget['category']}** by {format_currency(abs(remaining))}!")
