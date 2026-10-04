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
from components.sidebar import render_sidebar
from components.cards import render_metric_card, render_empty_state
from components.payment_table import render_payment_table
from mock.mock_api import (
    get_payments,
    settle_payment,
    report_payment,
    get_bill,
    get_bill_items,
    calculate_bill_split,
    calculate_equal_split,
    get_room_members,
)
from mock.mock_data import get_username

st.set_page_config(
    page_title="Payments — GrocEase",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id   = get_current_user_id()
room_id   = get_current_room_id()
room_name = get_current_room_name()

st.markdown("# 💳 Payments")

if not room_id:
    render_empty_state("🏠", "No room selected", "Please select a room first.")
    if st.button("Go to Rooms"):
        st.switch_page("pages/07_Rooms.py")
    st.stop()

st.markdown(f"<p style='color:#5B6459; margin-top:-0.8rem;'>Room: <strong>{room_name}</strong></p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Expense split preview (from bill scanning flow) ───────────────────────────
split_bill_id = st.session_state.pop("split_bill_id", None)
if split_bill_id:
    bill = get_bill(split_bill_id)
    if bill:
        st.markdown("### 🧾 Expense Split Preview")
        st.markdown(
            f"""
            <div style="background:#E7EFE6; border:1px solid #C3D6C6; border-radius:6px;
                        padding:0.8rem 1.2rem; margin-bottom:1rem;">
                <strong>{bill['fileName']}</strong> — Total:
                <span style="font-family:'Fraunces',serif; font-weight:700; color:#A97A1F;">
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
                                    padding:0.5rem 0.8rem; border-bottom:1px solid #F0F0F0;">
                            <div>👤 {get_username(uid)}</div>
                            <div style="font-weight:600; color:#1F4C3D;">{format_currency(amt)}</div>
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
                                padding:0.5rem 0.8rem; border-bottom:1px solid #F0F0F0;">
                        <div>👤 {get_username(uid)}</div>
                        <div style="font-weight:600; color:#1F4C3D;">{format_currency(amt)}</div>
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
    render_payment_table(payments, user_id, on_settle=settle_handler, on_report=report_handler, key_prefix="all_")

with tab_owe:
    owe_list = [p for p in payments if p["payerUserId"] == user_id and p["paymentStatus"] == "pending"]
    render_payment_table(owe_list, user_id, on_settle=settle_handler, on_report=report_handler, key_prefix="owe_")

with tab_receive:
    receive_list = [p for p in payments if p["payeeUserId"] == user_id and p["paymentStatus"] == "pending"]
    render_payment_table(receive_list, user_id, key_prefix="rec_")

with tab_history:
    history = [p for p in payments if p["paymentStatus"] in ("settled", "reported")]
    render_payment_table(history, user_id, key_prefix="hist_")
