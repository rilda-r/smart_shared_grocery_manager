"""
pages/12_Personal_Expenses.py
==============================
Personal expenses page — private expense log with category/date filters,
add/delete, and spending summary.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import date, timedelta
from collections import defaultdict

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_username
from utils.formatting import format_currency
from components.sidebar import render_sidebar
from components.cards import render_metric_card, render_empty_state
from components.expense_table import render_expense_table
from components.forms import render_add_expense_form
from components.charts import render_category_pie_chart, render_monthly_bar_chart
from mock.mock_api import (
    get_personal_expenses,
    add_personal_expense,
    delete_personal_expense,
)
from mock.mock_data import EXPENSE_CATEGORIES

st.set_page_config(
    page_title="Personal Expenses — GrocEase",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id  = get_current_user_id()
username = get_username()

st.markdown("# 📝 Personal Expenses")
st.markdown(
    f"<p style='color:#5B6459; margin-top:-0.8rem;'>Your private expense log — only visible to you, <strong>{username}</strong>.</p>",
    unsafe_allow_html=True,
)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Add expense form ──────────────────────────────────────────────────────────
new_expense = render_add_expense_form(key_prefix="pe_")
if new_expense:
    add_personal_expense(
        user_id,
        new_expense["amount"],
        new_expense["category"],
        new_expense["expenseDate"],
        new_expense["description"],
    )
    st.success(f"✅ Added expense: {format_currency(new_expense['amount'])} — {new_expense['category']}")
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ── Fetch expenses ────────────────────────────────────────────────────────────
all_expenses = get_personal_expenses(user_id)

# ── Summary metrics ───────────────────────────────────────────────────────────
total_spent = sum(e["amount"] for e in all_expenses)
num_expenses = len(all_expenses)
avg_expense  = (total_spent / num_expenses) if num_expenses > 0 else 0.0

spending_by_cat = defaultdict(float)
for e in all_expenses:
    spending_by_cat[e["category"]] += e["amount"]

top_category = max(spending_by_cat, key=spending_by_cat.get) if spending_by_cat else "—"

m1, m2, m3, m4 = st.columns(4)
with m1:
    render_metric_card("Total Spent", format_currency(total_spent))
with m2:
    render_metric_card("Expenses", str(num_expenses), "transactions")
with m3:
    render_metric_card("Avg per Entry", format_currency(avg_expense))
with m4:
    render_metric_card("Top Category", top_category, accent="gold")

st.markdown("<br>", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filter Expenses", expanded=False):
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        category_options = ["All Categories"] + EXPENSE_CATEGORIES
        selected_category = st.selectbox("Category", category_options, key="selected_expense_category")

    with filter_col2:
        start_date = st.date_input(
            "From date",
            value=date.today() - timedelta(days=30),
            key="selected_expense_start_date",
        )

    with filter_col3:
        end_date = st.date_input(
            "To date",
            value=date.today(),
            key="selected_expense_end_date",
        )

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = all_expenses
if selected_category != "All Categories":
    filtered = [e for e in filtered if e["category"] == selected_category]

filtered = [
    e for e in filtered
    if start_date.isoformat() <= e["expenseDate"] <= end_date.isoformat()
]

# ── Expense table + delete ────────────────────────────────────────────────────
def handle_delete(expense_id):
    delete_personal_expense(expense_id)
    st.success("Expense deleted.")
    st.rerun()

st.markdown(f"### Showing {len(filtered)} expense{'s' if len(filtered) != 1 else ''}")
render_expense_table(filtered, on_delete=handle_delete)

# ── Charts ────────────────────────────────────────────────────────────────────
if all_expenses:
    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("#### 🥧 Spending by Category")
        render_category_pie_chart(all_expenses)
    with chart_col2:
        st.markdown("#### 📅 Monthly Spending")
        render_monthly_bar_chart(all_expenses)
