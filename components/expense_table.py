"""
components/expense_table.py
===========================
Personal expense list table component.
"""

import streamlit as st
from utils.formatting import format_currency, format_date, badge_html


def render_expense_table(expenses: list, on_delete=None):
    """
    Render personal expenses as an interactive table.

    Args:
        expenses: list of PersonalExpense dicts
        on_delete: optional callback(expense_id)
    """
    if not expenses:
        st.markdown(
            """
            <div style="background:#FFFFFF; border:1.5px dashed rgba(163, 150, 112, 0.45); border-radius:18px;
                        text-align:center; padding:2.5rem 1rem; color:#6B5A47; box-shadow:0 2px 8px rgba(55,39,19,0.02);">
                <div style="font-size:2.8rem; margin-bottom:0.4rem;">📝</div>
                <div style="font-family:'Fraunces',Georgia,serif; font-size:1.1rem; font-weight:700; color:#372713;">No expenses found</div>
                <div style="font-size:0.88rem; color:#6B5A47; margin-top:0.3rem;">Add your first expense using the form above.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Header
    header_cols = st.columns([2, 2, 2, 3, 1])
    for col, h in zip(header_cols, ["Date", "Category", "Amount", "Description", "Delete"]):
        col.markdown(f"<span style='font-size:0.82rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#A39670;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:0.4rem 0 0.8rem 0; border:none; border-top:1.5px solid rgba(163, 150, 112, 0.35);'>", unsafe_allow_html=True)

    for exp in sorted(expenses, key=lambda e: e["expenseDate"], reverse=True):
        row = st.columns([2, 2, 2, 3, 1])
        row[0].write(format_date(exp["expenseDate"]))
        row[1].markdown(badge_html(exp["category"].lower()) if exp["category"] else "—", unsafe_allow_html=True)
        row[2].write(format_currency(exp["amount"]))
        row[3].write(exp.get("description") or "—")
        with row[4]:
            if on_delete and st.button("🗑️", key=f"del_exp_{exp['id']}"):
                on_delete(exp["id"])
