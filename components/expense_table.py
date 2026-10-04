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
            <div style="text-align:center; padding:2rem; color:#5B6459;">
                <div style="font-size:2.5rem;">📝</div>
                <div style="font-weight:600; color:#20261F; margin-top:0.5rem;">No expenses found</div>
                <div style="font-size:0.88rem; margin-top:0.3rem;">Add your first expense using the form above.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Header
    header_cols = st.columns([2, 2, 2, 3, 1])
    for col, h in zip(header_cols, ["Date", "Category", "Amount", "Description", "Delete"]):
        col.markdown(f"**{h}**")
    st.markdown("<hr style='margin:0.3rem 0 0.5rem 0; border-color:#D8D0BE;'>", unsafe_allow_html=True)

    for exp in sorted(expenses, key=lambda e: e["expenseDate"], reverse=True):
        row = st.columns([2, 2, 2, 3, 1])
        row[0].write(format_date(exp["expenseDate"]))
        row[1].markdown(badge_html(exp["category"].lower()) if exp["category"] else "—", unsafe_allow_html=True)
        row[2].write(format_currency(exp["amount"]))
        row[3].write(exp.get("description") or "—")
        with row[4]:
            if on_delete and st.button("🗑️", key=f"del_exp_{exp['id']}"):
                on_delete(exp["id"])
