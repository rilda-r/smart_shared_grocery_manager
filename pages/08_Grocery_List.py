"""
pages/08_Grocery_List.py
========================
Grocery list page — view, add, edit, and delete items in the current room.
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
from components.alerts import permission_error
from components.grocery_table import render_grocery_table
from components.forms import render_add_grocery_form
from mock.mock_api import (
    get_grocery_items,
    add_grocery_item,
    update_grocery_item,
    delete_grocery_item,
)

st.set_page_config(
    page_title="Grocery List — GrocEase",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id  = get_current_user_id()
room_id  = get_current_room_id()
room_name = get_current_room_name()

st.markdown("# 🛒 Grocery List")

# ── Room guard ────────────────────────────────────────────────────────────────
if not room_id:
    render_empty_state(
        "🏠",
        "No room selected",
        "Go to Rooms and open a grocery list from there.",
    )
    if st.button("Go to Rooms", type="primary"):
        st.switch_page("pages/07_Rooms.py")
    st.stop()

st.markdown(
    f"<p style='color:#5B6459; margin-top:-0.8rem;'>Room: <strong>{room_name}</strong></p>",
    unsafe_allow_html=True,
)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Status filter ─────────────────────────────────────────────────────────────
status_filter = st.radio(
    "Filter by status",
    options=["All", "Pending", "Purchased", "Unavailable"],
    horizontal=True,
    key="grocery_status_filter",
)

# ── Add item form ─────────────────────────────────────────────────────────────
new_item = render_add_grocery_form(room_id, key_prefix="gl_")
if new_item:
    add_grocery_item(room_id, user_id, new_item["itemName"], new_item["quantity"])
    st.success(f"✅ Added **{new_item['itemName']}** ×{new_item['quantity']}")
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ── Edit state ────────────────────────────────────────────────────────────────
if "edit_item_id" not in st.session_state:
    st.session_state["edit_item_id"] = None

def handle_edit(item):
    st.session_state["edit_item_id"] = item["id"]
    st.session_state["edit_item_name_val"] = item["itemName"]
    st.session_state["edit_item_qty_val"]  = item["quantity"]
    st.rerun()

def handle_delete(item_id):
    delete_grocery_item(item_id)
    st.success("Item deleted.")
    st.rerun()

# ── Inline edit form ──────────────────────────────────────────────────────────
if st.session_state["edit_item_id"] is not None:
    edit_id = st.session_state["edit_item_id"]
    st.markdown("#### ✏️ Edit Item")
    with st.form("edit_grocery_form"):
        col_n, col_q = st.columns([3, 1])
        with col_n:
            new_name = st.text_input("Item name", value=st.session_state.get("edit_item_name_val", ""))
        with col_q:
            new_qty = st.number_input("Qty", min_value=1, max_value=999,
                                       value=st.session_state.get("edit_item_qty_val", 1), step=1)
        save_col, cancel_col = st.columns(2)
        with save_col:
            if st.form_submit_button("Save", type="primary"):
                if new_name.strip():
                    update_grocery_item(edit_id, new_name.strip(), int(new_qty))
                    st.session_state["edit_item_id"] = None
                    st.success("Item updated.")
                    st.rerun()
        with cancel_col:
            if st.form_submit_button("Cancel"):
                st.session_state["edit_item_id"] = None
                st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

# ── Items table ───────────────────────────────────────────────────────────────
items = get_grocery_items(room_id)

if status_filter != "All":
    filter_val = status_filter.lower()
    items = [i for i in items if i["status"] == filter_val]

# Summary counts
all_items = get_grocery_items(room_id)
counts = {
    "pending":     sum(1 for i in all_items if i["status"] == "pending"),
    "purchased":   sum(1 for i in all_items if i["status"] == "purchased"),
    "unavailable": sum(1 for i in all_items if i["status"] == "unavailable"),
}
sc1, sc2, sc3 = st.columns(3)
sc1.markdown(badge_html("pending") + f"&nbsp; **{counts['pending']}** pending", unsafe_allow_html=True)
sc2.markdown(badge_html("purchased") + f"&nbsp; **{counts['purchased']}** purchased", unsafe_allow_html=True)
sc3.markdown(badge_html("unavailable") + f"&nbsp; **{counts['unavailable']}** unavailable", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

render_grocery_table(items, user_id, on_edit=handle_edit, on_delete=handle_delete)

# ── Start Shopping button ─────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if counts["pending"] > 0:
    if st.button("🧺 Start Shopping", type="primary"):
        st.session_state["shopping_mode"] = True
        st.switch_page("pages/09_Shopping.py")
