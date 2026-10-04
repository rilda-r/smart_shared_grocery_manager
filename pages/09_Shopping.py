"""
pages/09_Shopping.py
====================
Shopping mode — mark items as purchased or unavailable in real time.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_current_room_id, get_current_room_name
from utils.formatting import badge_html
from components.sidebar import render_sidebar
from components.cards import render_empty_state
from mock.mock_api import (
    get_grocery_items,
    start_shopping,
    update_grocery_item_status,
    finish_shopping,
)

st.set_page_config(
    page_title="Shopping — GrocEase",
    page_icon="🧺",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id   = get_current_user_id()
room_id   = get_current_room_id()
room_name = get_current_room_name()

st.markdown("# 🧺 Shopping Mode")

if not room_id:
    render_empty_state("🏠", "No room selected", "Please open a Grocery List first.")
    if st.button("Go to Rooms"):
        st.switch_page("pages/07_Rooms.py")
    st.stop()

st.markdown(f"<p style='color:#5B6459; margin-top:-0.8rem;'>Room: <strong>{room_name}</strong></p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Start shopping if not in mode ─────────────────────────────────────────────
if not st.session_state.get("shopping_mode", False):
    st.info("You are not in shopping mode.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧺 Start Shopping", type="primary"):
            start_shopping(room_id)
            st.rerun()
    with col2:
        if st.button("← Back to Grocery List"):
            st.switch_page("pages/08_Grocery_List.py")
    st.stop()

# ── Shopping mode active ──────────────────────────────────────────────────────
st.success("🛒 Shopping mode is ON — mark items as you shop!")

items = get_grocery_items(room_id)
pending_items     = [i for i in items if i["status"] == "pending"]
purchased_items   = [i for i in items if i["status"] == "purchased"]
unavailable_items = [i for i in items if i["status"] == "unavailable"]

# ── Pending items ─────────────────────────────────────────────────────────────
st.markdown(f"### 🟡 Pending ({len(pending_items)})")

if not pending_items:
    st.success("All items have been marked! Ready to finish shopping.")
else:
    for item in pending_items:
        col_name, col_qty, col_buy, col_na = st.columns([3, 1, 2, 2])
        col_name.write(f"**{item['itemName']}**")
        col_qty.write(f"×{item['quantity']}")
        with col_buy:
            if st.button("✅ Purchased", key=f"buy_{item['id']}"):
                update_grocery_item_status(item["id"], "purchased")
                st.rerun()
        with col_na:
            if st.button("❌ Unavailable", key=f"na_{item['id']}"):
                update_grocery_item_status(item["id"], "unavailable")
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ── Purchased items ───────────────────────────────────────────────────────────
if purchased_items:
    st.markdown(f"### ✅ Purchased ({len(purchased_items)})")
    for item in purchased_items:
        col_name, col_qty, col_undo = st.columns([3, 1, 2])
        col_name.write(f"~~{item['itemName']}~~")
        col_qty.write(f"×{item['quantity']}")
        with col_undo:
            if st.button("↩ Undo", key=f"undo_buy_{item['id']}"):
                update_grocery_item_status(item["id"], "pending")
                st.rerun()

# ── Unavailable items ─────────────────────────────────────────────────────────
if unavailable_items:
    st.markdown(f"### ❌ Unavailable ({len(unavailable_items)})")
    for item in unavailable_items:
        col_name, col_qty, col_undo = st.columns([3, 1, 2])
        col_name.write(item["itemName"])
        col_qty.write(f"×{item['quantity']}")
        with col_undo:
            if st.button("↩ Undo", key=f"undo_na_{item['id']}"):
                update_grocery_item_status(item["id"], "pending")
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ── Finish shopping ───────────────────────────────────────────────────────────
if st.button("🏁 Finish Shopping", type="primary"):
    summary = finish_shopping(room_id)
    st.session_state["last_shopping_summary"] = summary
    st.rerun()

if not st.session_state.get("shopping_mode", False) and "last_shopping_summary" in st.session_state:
    summary = st.session_state.pop("last_shopping_summary")
    st.balloons()
    st.markdown("## 🏁 Shopping Summary")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Items",   summary["total"])
    s2.metric("Purchased",     summary["purchased"])
    s3.metric("Unavailable",   summary["unavailable"])
    s4.metric("Still Pending", summary["pending"])
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📷 Scan Bill", type="primary"):
        st.switch_page("pages/10_Bill_Scanning.py")
    if st.button("← Back to Grocery List"):
        st.switch_page("pages/08_Grocery_List.py")
