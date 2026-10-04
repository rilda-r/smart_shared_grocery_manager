"""
pages/06_Dashboard.py
=====================
GrocEase Dashboard — overview of rooms, grocery items, payments,
personal spending, and budget status.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from collections import defaultdict

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_username
from utils.formatting import format_currency
from components.sidebar import render_sidebar
from components.cards import render_metric_card, render_info_card, render_empty_state
from components.charts import render_category_pie_chart, render_budget_utilization_chart
from mock.mock_api import (
    _init_store,
    get_rooms,
    get_grocery_items,
    get_payments,
    get_personal_expenses,
    get_budgets,
)

st.set_page_config(
    page_title="Dashboard — GrocEase",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id = get_current_user_id()
username = get_username()

# ── Page title ────────────────────────────────────────────────────────────────
st.markdown(f"# 📊 Dashboard")
st.markdown(f"<p style='color:#5B6459; margin-top:-0.8rem;'>Welcome back, <strong>{username}</strong>!</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Pull mock data ────────────────────────────────────────────────────────────
my_rooms   = get_rooms(user_id)
all_items  = []
for room in my_rooms:
    all_items.extend(get_grocery_items(room["id"]))

pending_items = [i for i in all_items if i["status"] == "pending"]

# Payments
all_payments = []
for room in my_rooms:
    all_payments.extend(get_payments(room["id"]))

amount_owe = sum(
    p["amount"] for p in all_payments
    if p["payerUserId"] == user_id and p["paymentStatus"] == "pending"
)
amount_owed_to_me = sum(
    p["amount"] for p in all_payments
    if p["payeeUserId"] == user_id and p["paymentStatus"] == "pending"
)

expenses    = get_personal_expenses(user_id)
total_spent = sum(e["amount"] for e in expenses)

budgets     = get_budgets(user_id)
spending_by_cat = defaultdict(float)
for e in expenses:
    spending_by_cat[e["category"]] += e["amount"]

over_budget_count = sum(
    1 for b in budgets
    if spending_by_cat.get(b["category"], 0) >= b["monthlyLimit"]
)

# ── Metric row ────────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5, m6 = st.columns(6)

with m1:
    render_metric_card("My Rooms", str(len(my_rooms)), "active rooms")
with m2:
    render_metric_card("Pending Items", str(len(pending_items)), "across all rooms")
with m3:
    render_metric_card("I Owe", format_currency(amount_owe), "pending payments", accent="danger")
with m4:
    render_metric_card("Owed to Me", format_currency(amount_owed_to_me), "pending receipts", accent="gold")
with m5:
    render_metric_card("Personal Spend", format_currency(total_spent), "this month total")
with m6:
    render_metric_card(
        "Over Budget",
        str(over_budget_count),
        "categories",
        accent="danger" if over_budget_count > 0 else "default",
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Two-column section ────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.markdown("### 🏠 My Rooms")
    if not my_rooms:
        render_empty_state("🏠", "No rooms yet", "Join or create a room to get started.")
    else:
        for room in my_rooms:
            pending_in_room = sum(1 for i in all_items if i["roomId"] == room["id"] and i["status"] == "pending")
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #D8D0BE; border-left:4px solid #1F4C3D;
                            border-radius:6px; padding:0.9rem 1.2rem; margin-bottom:0.6rem;">
                    <div style="font-weight:600; color:#20261F;">{room['name']}</div>
                    <div style="font-size:0.8rem; color:#5B6459; margin-top:0.2rem;">
                        Code: <code>{room['code']}</code> &nbsp;|&nbsp;
                        {pending_in_room} pending item{"s" if pending_in_room != 1 else ""}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if st.button("Manage Rooms →", key="dash_goto_rooms"):
            st.switch_page("pages/07_Rooms.py")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🛒 Pending Grocery Items")
    if not pending_items:
        render_empty_state("✅", "All clear!", "No pending items across your rooms.")
    else:
        for item in pending_items[:5]:
            room_name = next((r["name"] for r in my_rooms if r["id"] == item["roomId"]), "—")
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center;
                            padding:0.5rem 0.8rem; border-bottom:1px solid #F0F0F0;">
                    <div style="font-size:0.92rem;">🥛 {item['itemName']} ×{item['quantity']}</div>
                    <div style="font-size:0.78rem; color:#5B6459;">{room_name}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if len(pending_items) > 5:
            st.caption(f"… and {len(pending_items) - 5} more items")
        if st.button("View Grocery List →", key="dash_goto_grocery"):
            st.switch_page("pages/08_Grocery_List.py")

with right_col:
    st.markdown("### 📊 Spending by Category")
    render_category_pie_chart(expenses)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Budget Status")
    if not budgets:
        render_empty_state("🎯", "No budgets set", "Set budgets to track your spending limits.")
    else:
        for b in budgets:
            spent = spending_by_cat.get(b["category"], 0.0)
            pct = (spent / b["monthlyLimit"] * 100) if b["monthlyLimit"] > 0 else 0
            color = "#9C4B3E" if pct >= 100 else ("#A97A1F" if pct >= 80 else "#1F4C3D")
            st.markdown(
                f"""
                <div style="margin-bottom:0.6rem;">
                    <div style="display:flex; justify-content:space-between; font-size:0.85rem;
                                color:#20261F; margin-bottom:3px;">
                        <span>{b['category']}</span>
                        <span style="color:{color};">{format_currency(spent)} / {format_currency(b['monthlyLimit'])}</span>
                    </div>
                    <div style="background:#F0F0F0; border-radius:4px; height:7px; overflow:hidden;">
                        <div style="background:{color}; width:{min(pct, 100):.0f}%; height:100%; border-radius:4px;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if st.button("Manage Budget →", key="dash_goto_budget"):
            st.switch_page("pages/13_Budget.py")
