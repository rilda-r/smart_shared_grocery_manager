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

# ── Live Sync Header Frame ───────────────────────────────────────────────────
st.markdown(
    """
    <div style="background:#F7FBFA; border:1px solid #CADDD8; border-radius:16px; padding:0.65rem 1rem; margin-bottom:1.2rem; box-shadow:0 2px 10px rgba(16,39,42,0.04);">
    """,
    unsafe_allow_html=True,
)
col_sub, col_sync = st.columns([3, 1.2], vertical_alignment="center")
with col_sub:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <span style="color:#4A6568; font-size:1.02rem;">Shopping in: <strong style="color:#10272A;">{room_name}</strong></span>
            <span style="background:#EAF1EB; color:#2E5135; border:1px solid #6B8F71; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; display:inline-flex; align-items:center; gap:6px;">
                <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#6B8F71;"></span>
                Supabase Live Sync
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_sync:
    st.markdown('<div style="display:flex; justify-content:flex-end; padding-right:1rem;">', unsafe_allow_html=True)
    if st.button("🔄 Live Sync", key="shop_live_sync", help="Fetch live shopping state from Supabase"):
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)


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


# ── Pending items (Compact Responsive Grid) ───────────────────────────────────
st.markdown(f"### 🟡 Pending ({len(pending_items)})")

if not pending_items:
    st.success("All items have been marked! Ready to finish shopping.")
else:
    COLS_PER_ROW = 2
    for row_idx in range(0, len(pending_items), COLS_PER_ROW):
        chunk = pending_items[row_idx:row_idx + COLS_PER_ROW]
        grid_cols = st.columns(COLS_PER_ROW, gap="medium")
        for col_idx, item in enumerate(chunk):
            with grid_cols[col_idx]:
                added_by = item.get("addedByName") or item.get("added_by_name") or "Member"
                total_qty = item["quantity"]
                purchased_qty = item.get("purchasedQuantity", 0) or 0
                remaining_qty = max(0, total_qty - purchased_qty)

                # Compact Item Card
                st.markdown(
                    f"""
                    <div style="background:#F7FBFA; border:1px solid #CADDD8; border-left:3.5px solid #0F766E;
                                border-radius:12px; padding:0.5rem 0.8rem; margin-bottom:0.25rem;
                                box-shadow:0 2px 8px -2px rgba(16, 39, 42, 0.05);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:0.4rem; overflow:hidden;">
                                <span style="font-size:0.95rem; font-weight:700; color:#10272A; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">🛒 {item['itemName']}</span>
                                <span style='font-size:0.7rem; color:#4A6568; background:#F5FAF8; border:1px solid #CADDD8; padding:1px 6px; border-radius:10px; font-weight:600; white-space:nowrap;'>👤 {added_by}</span>
                            </div>
                            <div style="display:flex; align-items:center; gap:0.45rem; flex-shrink:0;">
                                <span style="font-size:0.72rem; color:#6B8F71; font-weight:600;">{purchased_qty}/{total_qty}</span>
                                <span style="font-family:'Fraunces',Georgia,serif; font-size:1.15rem; font-weight:800; color:#0F766E;">×{remaining_qty}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Flex Row Container with Centered Cross-Axis Alignment for Action Buttons
                st.markdown('<div class="shop-action-row">', unsafe_allow_html=True)
                btn_c1, btn_c2 = st.columns([1, 1], gap="small")
                with btn_c1:
                    if st.button("❌ Unavailable", key=f"na_{item['id']}", use_container_width=True, help="Mark item unavailable"):
                        do_mark_status(item["id"], "unavailable")
                with btn_c2:
                    if st.button("🛒 +1 Bought", key=f"buy_{item['id']}", type="primary", use_container_width=True, help="Mark 1 purchased (remaining decreases by 1)"):
                        do_mark_purchased(item["id"], inc=1)
                st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Fully Purchased items (Compact Responsive Grid) ───────────────────────────
if purchased_items:
    st.markdown(f"### ✅ Fully Purchased ({len(purchased_items)})")
    COLS_PER_ROW = 2
    for row_idx in range(0, len(purchased_items), COLS_PER_ROW):
        chunk = purchased_items[row_idx:row_idx + COLS_PER_ROW]
        grid_cols = st.columns(COLS_PER_ROW, gap="medium")
        for col_idx, item in enumerate(chunk):
            with grid_cols[col_idx]:
                added_by = item.get("addedByName") or item.get("added_by_name") or "Member"
                total_qty = item["quantity"]
                purchased_count = item.get("purchasedQuantity", total_qty) or total_qty

                # Compact Purchased Card
                st.markdown(
                    f"""
                    <div style="background:#F4F9F8; border:1px solid rgba(163, 150, 112, 0.35); border-left:3.5px solid #6B8F71;
                                border-radius:12px; padding:0.5rem 0.8rem; margin-bottom:0.25rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:0.4rem; overflow:hidden;">
                                <span style="font-size:0.95rem; font-weight:600; color:#5A7679; text-decoration:line-through; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">✅ {item['itemName']}</span>
                                <span style='font-size:0.7rem; color:#4D4828; background:#FFFFFF; border:1px solid #A39670; padding:1px 6px; border-radius:10px; white-space:nowrap;'>👤 {added_by}</span>
                            </div>
                            <div style="display:flex; align-items:center; gap:0.45rem; flex-shrink:0;">
                                <span style="font-size:0.75rem; color:#4D4828; font-weight:600;">{purchased_count}/{total_qty}</span>
                                <span style="font-family:'Fraunces',Georgia,serif; font-size:1.1rem; font-weight:700; color:#6B8F71;">Done</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown('<div class="shop-action-row">', unsafe_allow_html=True)
                p_c1, p_c2 = st.columns([1, 1], gap="small")
                with p_c1:
                    if st.button("↩ -1 Undo", key=f"undo_buy_{item['id']}", use_container_width=True, help="Decrease purchased count by 1"):
                        do_mark_purchased(item["id"], inc=-1)
                with p_c2:
                    if st.button("🔄 Reset", key=f"reset_buy_{item['id']}", use_container_width=True, help="Reset to 0 bought"):
                        do_reset_item(item["id"])
                st.markdown('</div>', unsafe_allow_html=True)

# ── Unavailable items (Compact Responsive Grid) ───────────────────────────────
if unavailable_items:
    st.markdown(f"### ❌ Unavailable ({len(unavailable_items)})")
    COLS_PER_ROW = 2
    for row_idx in range(0, len(unavailable_items), COLS_PER_ROW):
        chunk = unavailable_items[row_idx:row_idx + COLS_PER_ROW]
        grid_cols = st.columns(COLS_PER_ROW, gap="medium")
        for col_idx, item in enumerate(chunk):
            with grid_cols[col_idx]:
                added_by = item.get("addedByName") or item.get("added_by_name") or "Member"
                st.markdown(
                    f"""
                    <div style="background:#F7FBFA; border:1px solid #CADDD8; border-left:3.5px solid #8C1C13;
                                border-radius:12px; padding:0.5rem 0.8rem; margin-bottom:0.25rem; box-shadow:0 2px 8px -2px rgba(16, 39, 42, 0.05);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="display:flex; align-items:center; gap:0.4rem; overflow:hidden;">
                                <span style="font-size:0.95rem; font-weight:600; color:#8C1C13; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">❌ {item['itemName']}</span>
                                <span style='font-size:0.7rem; color:#4A6568; background:#F5FAF8; border:1px solid #CADDD8; padding:1px 6px; border-radius:10px; white-space:nowrap;'>👤 {added_by}</span>
                            </div>
                            <span style="font-family:'Fraunces',Georgia,serif; font-size:1.15rem; font-weight:700; color:#8C1C13;">×{item['quantity']}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="shop-action-row">', unsafe_allow_html=True)
                if st.button("↩ Restore to Pending", key=f"undo_na_{item['id']}", use_container_width=True):
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

