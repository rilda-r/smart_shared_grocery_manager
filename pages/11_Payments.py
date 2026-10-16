"""
pages/11_Payments.py
====================
Payments page — view payment obligations, settle payments, report issues,
and view payment history. Also shows expense split preview from bill scanning.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_current_room_id, get_current_room_name
from utils.formatting import format_currency, format_datetime, badge_html
from components.sidebar import render_sidebar, render_room_selector
from components.cards import render_metric_card, render_empty_state
from components.payment_table import render_payment_table
from database.database import (
    get_room_payments_live,
    settle_payment_live,
    report_payment_live,
)
from mock.mock_api import (
    get_payments as mock_get_payments,
    settle_payment as mock_settle_payment,
    report_payment as mock_report_payment,
    get_bill,
    get_bill_items,
    calculate_bill_split,
    calculate_equal_split,
    get_room_members,
)
from mock.mock_data import get_username

def get_payments(room_id):
    live = get_room_payments_live(room_id)
    if live:
        return live
    return mock_get_payments(room_id)

def settle_payment(payment_id):
    try:
        settle_payment_live(payment_id)
    except Exception:
        mock_settle_payment(payment_id)

def report_payment(payment_id):
    try:
        report_payment_live(payment_id)
    except Exception:
        mock_report_payment(payment_id)


st.set_page_config(
    page_title="Payments — GrocEase",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

# ── Select Room Component at top ──────────────────────────────────────────────
col_title, col_sel = st.columns([1.6, 1], gap="medium")
with col_title:
    st.markdown("# 💳 Payments")
with col_sel:
    st.write("")
    render_room_selector(key_prefix="payments_page")

user_id   = get_current_user_id()
room_id   = get_current_room_id()
room_name = get_current_room_name()

if not room_id:
    render_empty_state("🏠", "No room selected", "Please select a room from the dropdown above to view and settle payments.")
    st.stop()

st.markdown(
    f"""
    <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:14px; padding:0.6rem 1rem; margin-bottom:1.2rem;">
        <span style="color:#5C4A3E; font-size:0.95rem;">Active Room: <strong style="color:#2A1D16;">{room_name}</strong></span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Expense split preview (from bill scanning flow) ───────────────────────────
split_bill_id = st.session_state.pop("split_bill_id", None)
if split_bill_id:
    bill = get_bill(split_bill_id)
    if bill:
        st.markdown("### 🧾 Expense Split Preview")
        st.markdown(
            f"""
            <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:18px;
                        padding:1rem 1.4rem; margin-bottom:1rem; box-shadow:0 4px 20px -2px rgba(59,42,32,0.08);">
                <strong>{bill['fileName']}</strong> — Total:
                <span style="font-family:'Fraunces',serif; font-weight:700; color:#7A1F2B;">
                    {format_currency(bill['totalAmount'])}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        split_tab, equal_tab = st.tabs(["📌 Assigned Split", "⚖️ Equal Split"])

        with split_tab:
            assigned_split = calculate_bill_split(split_bill_id)
            if assigned_split:
                for uid, amt in assigned_split.items():
                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:space-between;
                                    padding:0.6rem 0.8rem; border-bottom:1px solid #E3D6BE;">
                            <div>👤 {get_username(uid)}</div>
                            <div style="font-weight:700; color:#7A1F2B; font-variant-numeric:tabular-nums;">{format_currency(amt)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No items assigned yet. Go back to Bill Scanning to assign items.")

        with equal_tab:
            member_ids = [m["userId"] for m in get_room_members(room_id)]
            equal_split = calculate_equal_split(split_bill_id, member_ids)
            for uid, amt in equal_split.items():
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between;
                                padding:0.6rem 0.8rem; border-bottom:1px solid #E3D6BE;">
                        <div>👤 {get_username(uid)}</div>
                        <div style="font-weight:700; color:#7A1F2B; font-variant-numeric:tabular-nums;">{format_currency(amt)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if st.button("✅ Confirm & Record Payments", type="primary"):
            st.success("Payments recorded! (Mock — no real DB change)")
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

# ── Payment summaries ─────────────────────────────────────────────────────────
payments = get_payments(room_id)

amount_owe = sum(
    p["amount"] for p in payments
    if p["payerUserId"] == user_id and p["paymentStatus"] == "pending"
)
amount_owed_to_me = sum(
    p["amount"] for p in payments
    if p["payeeUserId"] == user_id and p["paymentStatus"] == "pending"
)

m1, m2 = st.columns(2)
with m1:
    render_metric_card("I Owe (Pending)", format_currency(amount_owe), accent="danger")
with m2:
    render_metric_card("Owed to Me (Pending)", format_currency(amount_owed_to_me), accent="gold")

st.markdown("<br>", unsafe_allow_html=True)

# ── Filter tabs ───────────────────────────────────────────────────────────────
tab_all, tab_owe, tab_receive, tab_history = st.tabs(
    ["All", "💸 I Owe", "💰 I Receive", "📜 History"]
)

def settle_handler(payment_id):
    settle_payment(payment_id)
    st.success("Payment settled!")
    st.rerun()

def report_handler(payment_id):
    report_payment(payment_id)
    st.warning("Payment reported.")
    st.rerun()

with tab_all:
    render_payment_table(payments, user_id, on_settle=settle_handler, on_report=report_handler, key_prefix="all")

with tab_owe:
    owe_list = [p for p in payments if p["payerUserId"] == user_id and p["paymentStatus"] == "pending"]
    render_payment_table(owe_list, user_id, on_settle=settle_handler, on_report=report_handler, key_prefix="owe")

with tab_receive:
    receive_list = [p for p in payments if p["payeeUserId"] == user_id and p["paymentStatus"] == "pending"]
    render_payment_table(receive_list, user_id, key_prefix="recv")

with tab_history:
    history = [p for p in payments if p["paymentStatus"] in ("settled", "reported")]
    render_payment_table(history, user_id, key_prefix="hist")
