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
from components.sidebar import render_sidebar, render_room_selector
from components.cards import render_empty_state
from database.database import (
    get_live_grocery_items,
    mark_grocery_item_purchased_live,
    update_grocery_item_status_live,
)
from mock.mock_api import (
    get_grocery_items as mock_get_grocery_items,
    start_shopping,
    update_grocery_item_status as mock_update_grocery_item_status,
    finish_shopping,
)
from mock.mock_data import get_username as mock_get_username

st.set_page_config(
    page_title="Shopping — GrocEase",
    page_icon="🧺",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

col_title, col_sel = st.columns([1.6, 1], gap="medium")
with col_title:
    st.markdown("# 🧺 Shopping Mode")
with col_sel:
    st.write("")
    render_room_selector(key_prefix="shopping_page")

user_id   = get_current_user_id()
room_id   = get_current_room_id()
room_name = get_current_room_name()

if not room_id:
    render_empty_state("🏠", "No room selected", "Select or join a room from above to start shopping.")
    if st.button("Go to Rooms"):
        st.switch_page("pages/07_Rooms.py")
    st.stop()

col_sub, col_sync = st.columns([3, 1])
with col_sub:
    st.markdown(
        f"<p style='color:#5B6459; margin-top:-0.8rem;'>"
        f"Shopping in: <strong>{room_name}</strong> &nbsp;"
        f"<span style='background:#E7EFE6; color:#1F4C3D; padding:2px 8px; border-radius:12px; font-size:0.78rem; font-weight:600;'>"
        f"🟢 Supabase Live Sync</span></p>",
        unsafe_allow_html=True,
    )
with col_sync:
    if st.button("🔄 Live Sync", key="shop_live_sync", help="Fetch live shopping state from Supabase"):
        st.rerun()

st.markdown("<hr style='border-color:#D8D0BE; margin:0.2rem 0 1.2rem 0;'>", unsafe_allow_html=True)


# ── Helper to load live items from Supabase ───────────────────────────────────
def fetch_shopping_items(rid: int) -> list:
    try:
        return get_live_grocery_items(rid) or []
    except Exception:
        return []


# ── Start shopping if not in mode ─────────────────────────────────────────────
if not st.session_state.get("shopping_mode", False):
    st.info("You are not in shopping mode.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧺 Start Shopping", type="primary"):
            st.session_state["shopping_mode"] = True
            st.rerun()
    with col2:
        if st.button("← Back to Grocery List"):
            st.switch_page("pages/08_Grocery_List.py")
    st.stop()

# ── Shopping mode active ──────────────────────────────────────────────────────
st.success("🛒 Shopping mode is ON — click '+1 Bought' to mark items off one by one!")

items = fetch_shopping_items(room_id)
pending_items     = [i for i in items if i["status"] == "pending"]
purchased_items   = [i for i in items if i["status"] == "purchased"]
unavailable_items = [i for i in items if i["status"] == "unavailable"]


def do_mark_purchased(item_id: int, inc: int = 1):
    """Incrementally mark purchase in Supabase."""
    try:
        mark_grocery_item_purchased_live(item_id, increment=inc)
    except Exception as e:
        st.error(f"Error updating item: {e}")
    st.rerun()


def do_reset_item(item_id: int):
    """Reset item back to pending."""
    try:
        from database.database import reset_grocery_item_purchased_live
        reset_grocery_item_purchased_live(item_id)
    except Exception:
        update_grocery_item_status_live(item_id, "pending")
    st.rerun()


def do_mark_status(item_id: int, status: str):
    """Update status in Supabase."""
    try:
        update_grocery_item_status_live(item_id, status)
    except Exception as e:
        st.error(f"Error updating status: {e}")
    st.rerun()


# ── Pending items ─────────────────────────────────────────────────────────────
st.markdown(f"### 🟡 Pending ({len(pending_items)})")

if not pending_items:
    st.success("All items have been marked! Ready to finish shopping.")
else:
    for item in pending_items:
        added_by = item.get("addedByName") or item.get("added_by_name") or "Member"
        total_qty = item["quantity"]
        purchased_qty = item.get("purchasedQuantity", 0) or 0
        remaining_qty = max(0, total_qty - purchased_qty)

        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid rgba(163, 150, 112, 0.35); border-left:4px solid #5C0203;
                        border-radius:16px; padding:0.95rem 1.25rem; margin-bottom:0.6rem; box-shadow:0 4px 14px rgba(55, 39, 19, 0.03);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:1.05rem; font-weight:700; color:#372713;">🛒 {item['itemName']}</div>
                        <div style="margin-top:4px;">
                            <span style='font-size:0.78rem; color:#4D4828; background:#FAF6F0; border:1px solid #A39670; padding:2px 8px; border-radius:12px; font-weight:600;'>👤 Added by {added_by}</span>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-family:'Fraunces',Georgia,serif; font-size:1.2rem; font-weight:700; color:#5C0203;">Remaining: ×{remaining_qty}</div>
                        <div style="font-size:0.8rem; color:#4D4828; font-weight:600;">Bought: {purchased_qty} / {total_qty}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_buy, col_na, _ = st.columns([1.5, 1.5, 3])
        with col_buy:
            if st.button("🛒 +1 Bought", key=f"buy_{item['id']}", help="Mark 1 purchased (remaining decreases by 1)"):
                do_mark_purchased(item["id"], inc=1)
        with col_na:
            st.markdown('<div class="groc-secondary">', unsafe_allow_html=True)
            if st.button("❌ Unavailable", key=f"na_{item['id']}"):
                do_mark_status(item["id"], "unavailable")
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Purchased items ───────────────────────────────────────────────────────────
if purchased_items:
    st.markdown(f"### ✅ Fully Purchased ({len(purchased_items)})")
    for item in purchased_items:
        added_by = item.get("addedByName") or item.get("added_by_name") or "Member"
        total_qty = item["quantity"]
        purchased_count = item.get("purchasedQuantity", total_qty) or total_qty
        st.markdown(
            f"""
            <div style="background:#FAF6F0; border:1px solid rgba(163, 150, 112, 0.35); border-left:4px solid #4D4828;
                        border-radius:16px; padding:0.9rem 1.25rem; margin-bottom:0.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:1rem; font-weight:600; color:#6B5A47; text-decoration:line-through;">✅ {item['itemName']}</div>
                        <div style="margin-top:3px;">
                            <span style='font-size:0.76rem; color:#4D4828; background:#FFFFFF; border:1px solid #A39670; padding:2px 8px; border-radius:12px;'>👤 Added by {added_by}</span>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:700; color:#4D4828;">Total: ×{total_qty}</div>
                        <div style="font-size:0.8rem; color:#4D4828; font-weight:600;">Completed: {purchased_count}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_undo, col_reset, _ = st.columns([1.3, 1.3, 3])
        with col_undo:
            st.markdown('<div class="groc-secondary">', unsafe_allow_html=True)
            if st.button("↩ -1 Undo", key=f"undo_buy_{item['id']}", help="Decrease purchased count by 1"):
                do_mark_purchased(item["id"], inc=-1)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_reset:
            st.markdown('<div class="groc-secondary">', unsafe_allow_html=True)
            if st.button("🔄 Reset", key=f"reset_buy_{item['id']}", help="Reset to 0 bought"):
                do_reset_item(item["id"])
            st.markdown('</div>', unsafe_allow_html=True)

# ── Unavailable items ─────────────────────────────────────────────────────────
if unavailable_items:
    st.markdown(f"### ❌ Unavailable ({len(unavailable_items)})")
    for item in unavailable_items:
        added_by = item.get("addedByName") or item.get("added_by_name") or "Member"
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid rgba(163, 150, 112, 0.35); border-left:4px solid #5C0203;
                        border-radius:16px; padding:0.9rem 1.25rem; margin-bottom:0.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:1rem; font-weight:600; color:#5C0203;">❌ {item['itemName']} (Unavailable)</div>
                        <div style="margin-top:3px;">
                            <span style='font-size:0.76rem; color:#6B5A47;'>👤 Added by {added_by}</span>
                        </div>
                    </div>
                    <div>
                        <span style="font-weight:700; color:#5C0203;">×{item['quantity']}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_undo, _ = st.columns([1.3, 4])
        with col_undo:
            st.markdown('<div class="groc-secondary">', unsafe_allow_html=True)
            if st.button("↩ Undo", key=f"undo_na_{item['id']}"):
                do_mark_status(item["id"], "pending")
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ── Finish shopping ───────────────────────────────────────────────────────────
if st.button("🏁 Finish Shopping", type="primary"):
    all_current = fetch_shopping_items(room_id)
    summary = {
        "total": len(all_current),
        "purchased": len([i for i in all_current if i["status"] == "purchased"]),
        "unavailable": len([i for i in all_current if i["status"] == "unavailable"]),
        "pending": len([i for i in all_current if i["status"] == "pending"]),
    }
    st.session_state["shopping_mode"] = False
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

