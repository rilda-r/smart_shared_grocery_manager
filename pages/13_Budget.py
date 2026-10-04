"""
pages/13_Budget.py
==================
Budget page — set, edit, and delete monthly category budgets with
progress indicators and over-budget alerts.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from collections import defaultdict

from style import apply_base_style
from utils.session import require_auth, get_current_user_id
from utils.formatting import format_currency
from components.sidebar import render_sidebar
from components.cards import render_empty_state
from components.budget_progress import render_budget_progress
from components.forms import render_add_budget_form
from components.charts import render_budget_utilization_chart
from mock.mock_api import (
    get_budgets,
    create_budget,
    update_budget,
    delete_budget,
    get_personal_expenses,
)

st.set_page_config(
    page_title="Budget — GrocEase",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id = get_current_user_id()

st.markdown("# 🎯 Budget Manager")
st.markdown("<p style='color:#5B6459; margin-top:-0.8rem;'>Set monthly spending limits per category.</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
budgets  = get_budgets(user_id)
expenses = get_personal_expenses(user_id)

spending_by_cat = defaultdict(float)
for e in expenses:
    spending_by_cat[e["category"]] += e["amount"]

existing_cats = [b["category"] for b in budgets]

# ── Add budget form ───────────────────────────────────────────────────────────
new_budget = render_add_budget_form(existing_cats, key_prefix="bg_")
if new_budget:
    create_budget(user_id, new_budget["category"], new_budget["monthlyLimit"])
    st.success(f"✅ Budget set for **{new_budget['category']}**: {format_currency(new_budget['monthlyLimit'])}/month")
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ── Budget progress rows ──────────────────────────────────────────────────────
if not budgets:
    render_empty_state("🎯", "No budgets set yet", "Add your first budget using the form above.")
else:
    left_col, right_col = st.columns([1.2, 1], gap="large")

    with left_col:
        st.markdown("### Budget Progress")
        for budget in budgets:
            spent = spending_by_cat.get(budget["category"], 0.0)
            render_budget_progress(budget, spent)

            # Inline edit / delete
            edit_key   = f"edit_budget_{budget['id']}"
            delete_key = f"del_confirm_{budget['id']}"

            col_edit, col_del = st.columns(2)
            with col_edit:
                if st.button("✏️ Edit Limit", key=f"edit_btn_{budget['id']}"):
                    st.session_state[edit_key] = True

            with col_del:
                st.markdown('<div class="groc-danger">', unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_btn_{budget['id']}"):
                    st.session_state[delete_key] = True
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get(edit_key, False):
                with st.form(f"edit_budget_form_{budget['id']}"):
                    new_limit = st.number_input(
                        f"New monthly limit for {budget['category']} (₹)",
                        min_value=1.0,
                        value=float(budget["monthlyLimit"]),
                        step=100.0,
                        format="%.2f",
                    )
                    sc, cc = st.columns(2)
                    with sc:
                        if st.form_submit_button("Save", type="primary"):
                            update_budget(budget["id"], new_limit)
                            st.session_state[edit_key] = False
                            st.success("Budget updated.")
                            st.rerun()
                    with cc:
                        if st.form_submit_button("Cancel"):
                            st.session_state[edit_key] = False
                            st.rerun()

            if st.session_state.get(delete_key, False):
                st.warning(f"Delete budget for **{budget['category']}**?")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("Yes, Delete", key=f"yes_del_{budget['id']}", type="primary"):
                        delete_budget(budget["id"])
                        st.session_state[delete_key] = False
                        st.success(f"Budget for {budget['category']} deleted.")
                        st.rerun()
                with dc2:
                    if st.button("Cancel", key=f"no_del_{budget['id']}"):
                        st.session_state[delete_key] = False
                        st.rerun()

            st.markdown("<hr style='border-color:#EEE; margin:0.3rem 0 1rem 0;'>", unsafe_allow_html=True)

    with right_col:
        st.markdown("### Budget Utilization Chart")
        render_budget_utilization_chart(budgets, dict(spending_by_cat))

        # Summary table
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Summary")
        total_limit = sum(b["monthlyLimit"] for b in budgets)
        total_spent = sum(spending_by_cat.get(b["category"], 0.0) for b in budgets)
        total_remaining = total_limit - total_spent

        sc1, sc2 = st.columns(2)
        sc1.metric("Total Budget", format_currency(total_limit))
        sc2.metric("Total Spent",  format_currency(total_spent))
        st.metric("Remaining",     format_currency(max(total_remaining, 0)))
