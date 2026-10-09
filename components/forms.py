"""
components/forms.py
===================
Reusable form components for GrocEase.
"""

import streamlit as st
from mock.mock_data import EXPENSE_CATEGORIES, MOCK_USERS


def render_add_grocery_form(room_id: int, key_prefix: str = "") -> dict | None:
    """
    Render the add-grocery-item form.

    Returns a dict {itemName, quantity} on submit, None otherwise.
    """
    with st.form(key=f"{key_prefix}add_grocery_form", clear_on_submit=True):
        st.markdown("#### ➕ Add Grocery Item")
        col_name, col_qty = st.columns([3, 1])
        with col_name:
            item_name = st.text_input("Item name", placeholder="e.g. Milk")
        with col_qty:
            quantity = st.number_input("Qty", min_value=1, max_value=999, value=1, step=1)
        submitted = st.form_submit_button("Add Item", type="primary", use_container_width=True)
        if submitted:
            if not item_name.strip():
                st.error("Item name cannot be empty.")
                return None
            return {"itemName": item_name.strip(), "quantity": int(quantity)}
    return None


def render_add_expense_form(key_prefix: str = "") -> dict | None:
    """
    Render the add-personal-expense form.

    Returns a dict {amount, category, expenseDate, description} on submit.
    """
    from datetime import date
    with st.form(key=f"{key_prefix}add_expense_form", clear_on_submit=True):
        st.markdown("#### ➕ Add Expense")
        col_amount, col_cat = st.columns(2)
        with col_amount:
            amount = st.number_input("Amount (₹)", min_value=0.01, value=100.0, step=10.0, format="%.2f")
        with col_cat:
            category = st.selectbox("Category", EXPENSE_CATEGORIES)
        col_date, col_desc = st.columns(2)
        with col_date:
            expense_date = st.date_input("Date", value=date.today(), max_value=date.today())
        with col_desc:
            description = st.text_input("Description", placeholder="e.g. Lunch")
        submitted = st.form_submit_button("Add Expense", type="primary", use_container_width=True)
        if submitted:
            if expense_date > date.today():
                st.error("Expense date cannot be in the future.")
                return None
            return {
                "amount": float(amount),
                "category": category,
                "expenseDate": expense_date.isoformat(),
                "description": description.strip(),
            }
    return None


def render_add_budget_form(existing_categories: list, key_prefix: str = "") -> dict | None:
    """
    Render the add-budget form.

    existing_categories: list of category strings already budgeted (to exclude from dropdown).
    Returns {category, monthlyLimit} on submit.
    """
    available = [c for c in EXPENSE_CATEGORIES if c not in existing_categories]
    if not available:
        st.info("You have set budgets for all available categories.")
        return None

    with st.form(key=f"{key_prefix}add_budget_form", clear_on_submit=True):
        st.markdown("#### ➕ Add Budget")
        col_cat, col_limit = st.columns(2)
        with col_cat:
            category = st.selectbox("Category", available)
        with col_limit:
            monthly_limit = st.number_input("Monthly Limit (₹)", min_value=1.0, value=1000.0, step=100.0, format="%.2f")
        submitted = st.form_submit_button("Set Budget", type="primary", use_container_width=True)
        if submitted:
            return {"category": category, "monthlyLimit": float(monthly_limit)}
    return None
