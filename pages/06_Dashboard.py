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

from style import apply_base_style, render_dev_mode_banner
from utils.session import require_auth, get_current_user_id, get_username
from utils.formatting import format_currency
from components.sidebar import render_sidebar
from components.cards import render_metric_card, render_metric_cards_grid, render_info_card, render_empty_state
from components.charts import render_category_pie_chart, render_budget_utilization_chart
from database.database import get_user_joined_rooms, get_live_grocery_items
from services.personal_expense_service import get_personal_expenses as svc_get_personal_expenses
from services.budget_service import get_budgets as svc_get_budgets
from services.payment_service import get_room_payments as svc_get_room_payments

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

# ── Dev mode banner ───────────────────────────────────────────────────────────
render_dev_mode_banner()

# ── Page title ────────────────────────────────────────────────────────────────
st.markdown(f"# 📊 Dashboard")
st.markdown(f"<p style='color:#5C4A3E; margin-top:-0.8rem;'>Welcome back, <strong>{username}</strong>!</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#E3D6BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)


# ── Pull database data ────────────────────────────────────────────────────────
db_rooms = get_user_joined_rooms(user_id) or []
my_rooms = [
    {
        "id": r["id"],
        "name": r["name"],
        "role": r.get("role", "member"),
        "code": r.get("secret_code") or r.get("code", ""),
    }
    for r in db_rooms
]

all_items = []
for room in my_rooms:
    all_items.extend(get_live_grocery_items(room["id"]) or [])

pending_items = [i for i in all_items if i.get("status") == "pending"]

# Payments
all_payments = []
for room in my_rooms:
    res_p = svc_get_room_payments(user_id, room["id"])
    if res_p and res_p.get("success"):
        all_payments.extend(res_p.get("data", []))

amount_owe = sum(
    float(p.get("amount", 0)) for p in all_payments
    if p.get("payer_user_id") == user_id and p.get("payment_status") == "pending"
)
amount_owed_to_me = sum(
    float(p.get("amount", 0)) for p in all_payments
    if p.get("payee_user_id") == user_id and p.get("payment_status") == "pending"
)

exp_res = svc_get_personal_expenses(user_id)
expenses = [
    {
        "id": e["id"],
        "amount": float(e["amount"]),
        "category": e["category"],
        "expenseDate": str(e.get("expense_date") or ""),
    }
    for e in (exp_res.get("data", []) if exp_res and exp_res.get("success") else [])
]
total_spent = sum(e["amount"] for e in expenses)

bg_res = svc_get_budgets(user_id)
budgets = [
    {
        "id": b["id"],
        "category": b["category"],
        "monthlyLimit": float(b.get("monthly_limit", 0)),
    }
    for b in (bg_res.get("data", []) if bg_res and bg_res.get("success") else [])
]

spending_by_cat = defaultdict(float)
for e in expenses:
    spending_by_cat[e["category"]] += e["amount"]

over_budget_count = sum(
    1 for b in budgets
    if spending_by_cat.get(b["category"], 0) >= b["monthlyLimit"]
)

# ── Metric row ────────────────────────────────────────────────────────────────
summary_cards = [
    {"label": "MY ROOMS", "value": str(len(my_rooms)), "sub": "active rooms"},
    {"label": "PENDING ITEMS", "value": str(len(pending_items)), "sub": "across all rooms"},
    {"label": "I OWE", "value": format_currency(amount_owe), "sub": "pending payments", "accent": "danger"},
    {"label": "OWED TO ME", "value": format_currency(amount_owed_to_me), "sub": "pending receipts", "accent": "gold"},
    {"label": "PERSONAL SPEND", "value": format_currency(total_spent), "sub": "this month total"},
    {
        "label": "OVER BUDGET",
        "value": str(over_budget_count),
        "sub": "categories",
        "accent": "danger" if over_budget_count > 0 else "default",
    },
]
render_metric_cards_grid(summary_cards)

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
                <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-left:4px solid #7A1F2B;
                            border-radius:18px; padding:1.1rem 1.3rem; margin-bottom:0.75rem; box-shadow:0 4px 20px -2px rgba(59, 42, 32, 0.08);">
                    <div style="font-weight:700; color:#2A1D16; font-size:1.02rem;">{room['name']}</div>
                    <div style="font-size:0.82rem; color:#5C4A3E; margin-top:0.3rem;">
                        Code: <code style="background:#F7F2E8; border:1px solid #E3D6BE; border-radius:8px; padding:2px 6px; color:#7A1F2B; font-weight:700;">{room.get('code','')}</code> &nbsp;|&nbsp;
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
                <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:14px;
                            padding:0.65rem 1rem; margin-bottom:0.45rem; display:flex; justify-content:space-between; align-items:center;
                            box-shadow:0 2px 6px rgba(59, 42, 32, 0.03);">
                    <div style="font-size:0.92rem; font-weight:600; color:#2A1D16;">🛒 {item['itemName']} <span style="color:#7A1F2B; font-weight:700;">×{item['quantity']}</span></div>
                    <div style="font-size:0.78rem; color:#5C4A3E; background:#F7F2E8; border:1px solid #E3D6BE; border-radius:8px; padding:2px 8px;">{room_name}</div>
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
            color = "#8C1C13" if pct >= 100 else ("#C8963E" if pct >= 80 else "#6B8F71")
            st.markdown(
                f"""
                <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:18px;
                            padding:0.85rem 1.1rem; margin-bottom:0.7rem; box-shadow:0 4px 20px -2px rgba(59, 42, 32, 0.06);">
                    <div style="display:flex; justify-content:space-between; font-size:0.88rem; font-weight:600;
                                color:#2A1D16; margin-bottom:6px;">
                        <span>{b['category']}</span>
                        <span style="color:{color}; font-weight:700;">{format_currency(spent)} / {format_currency(b['monthlyLimit'])}</span>
                    </div>
                    <div style="background:#EADFCB; border:1px solid #E3D6BE; border-radius:8px; height:8px; overflow:hidden;">
                        <div style="background:{color}; width:{min(pct, 100):.0f}%; height:100%; border-radius:8px;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if st.button("Manage Budget →", key="dash_goto_budget"):
            st.switch_page("pages/13_Budget.py")
