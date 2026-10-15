"""
pages/10_Bill_Scanning.py
=========================
Bill scanning & OCR page — multi-step workflow:
Step 1: Mandatory Room Selection at the top
Step 2: Conditional Receipt Upload & Scan Trigger
Step 3: Extraction & Mapping Logic:
        - Cross-reference extracted receipt items against active shopping list
        - Automatically check off matching items
        - Map extracted item names, quantities, and costs to requesting room users
        - Automatically generate responsive dynamic tabs breaking down split balance per user
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_current_room_id, get_current_room_name
from utils.formatting import format_currency, badge_html
from components.sidebar import render_sidebar, render_room_selector
from components.cards import render_empty_state
from database.database import (
    get_live_grocery_items,
    mark_grocery_item_purchased_live,
)
from mock.mock_api import (
    upload_bill,
    get_bill,
    get_bill_items,
    update_bill_items,
    assign_bill_item,
    calculate_bill_split,
    calculate_equal_split,
    get_room_members,
    get_grocery_items,
    update_grocery_item_status,
)
from mock.mock_data import MOCK_USERS, get_username, USER_BY_ID

st.set_page_config(
    page_title="Bill Scanning — GrocEase",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

# ── Step 1: Mandatory Room Selection Header ───────────────────────────────────
col_title, col_sel = st.columns([1.6, 1], gap="medium")
with col_title:
    st.markdown("# 📷 Bill Scanning")
with col_sel:
    st.write("")
    render_room_selector(key_prefix="bill_scanning_page")

user_id   = get_current_user_id()
room_id   = get_current_room_id()
room_name = get_current_room_name()

# ── Step 2: Conditional UI State Updates Only After Room Selection ─────────────
if not room_id:
    render_empty_state(
        "🏠",
        "Select a Room to Scan Receipts",
        "Please choose an active room from the dropdown above to upload receipts and orchestrate expense splits.",
    )
    st.stop()

st.markdown(
    f"""
    <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:14px; padding:0.6rem 1rem; margin-bottom:1.2rem;">
        <span style="color:#5C4A3E; font-size:0.95rem;">Active Room: <strong style="color:#2A1D16;">{room_name}</strong></span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── State keys ────────────────────────────────────────────────────────────────
if "selected_bill_id" not in st.session_state:
    st.session_state["selected_bill_id"] = None
if "ocr_results" not in st.session_state:
    st.session_state["ocr_results"] = None

# ── Dynamic Receipt Upload Block & Scan Trigger ───────────────────────────────
if st.session_state["selected_bill_id"] is None:
    st.markdown("### 📤 Step 2 — Upload & Scan Receipt")
    uploaded_file = st.file_uploader(
        "Upload receipt (JPEG, PNG, or PDF)",
        type=["jpg", "jpeg", "png", "pdf"],
        key="bill_receipt_uploader",
    )

    if uploaded_file:
        st.info(f"📎 **{uploaded_file.name}** — ready to scan")
        if st.button("🔍 Scan Receipt", type="primary", use_container_width=True):
            with st.spinner("🤖 Extracting line items via OCR..."):
                time.sleep(1.2)
            bill = upload_bill(room_id, user_id, uploaded_file.name)
            st.session_state["selected_bill_id"] = bill["id"]
            st.session_state["ocr_results"] = "completed"
            st.session_state.pop(f"auto_matched_{bill['id']}", None)
            st.success("✅ OCR completed! Line items extracted.")
            st.rerun()
    else:
        st.markdown(
            """
            <div style="border:2px dashed #E3D6BE; border-radius:18px; padding:2.5rem;
                        text-align:center; color:#5C4A3E; margin-top:0.8rem; background:#FFFDF9; box-shadow:0 2px 8px rgba(59,42,32,0.03);">
                <div style="font-size:2.8rem; margin-bottom:0.4rem;">🧾</div>
                <div style="font-family:'Fraunces',Georgia,serif; font-size:1.15rem; font-weight:700; color:#2A1D16; margin-top:0.5rem;">
                    Drag & drop your grocery receipt here
                </div>
                <div style="font-size:0.85rem; margin-top:0.3rem; color:#5C4A3E;">Supports JPG, PNG, PDF</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()
else:
    # ── Step 3: Extraction & Mapping Logic ────────────────────────────────────
    bill_id = st.session_state["selected_bill_id"]
    bill = get_bill(bill_id)

    if not bill:
        st.error("Bill not found. Please upload again.")
        st.session_state["selected_bill_id"] = None
        if st.button("Upload Again", key="reupload_missing_bill"):
            st.rerun()
        st.stop()

    ocr_status = bill.get("ocrStatus", "completed")

    bill_items = get_bill_items(bill_id) or []
    room_members = get_room_members(room_id) or []
    member_ids = [m["userId"] for m in room_members]
    member_names = {uid: get_username(uid) for uid in member_ids}

    # Fetch active shopping list items for this room (Supabase live or mock fallback)
    active_groceries = get_live_grocery_items(room_id) or []
    if not active_groceries:
        active_groceries = get_grocery_items(room_id) or []

    # Cross-referencing and automatic check-off orchestration
    matched_flag_key = f"auto_matched_{bill_id}"
    if not st.session_state.get(matched_flag_key, False):
        matched_count = 0
        for b_item in bill_items:
            b_name = b_item.get("itemName", "").strip().lower()
            if not b_name:
                continue

            # Cross-reference with active shopping list
            for g_item in active_groceries:
                g_name = (g_item.get("itemName") or g_item.get("item_name") or "").strip().lower()
                if b_name in g_name or g_name in b_name:
                    # Find requester userId
                    req_uid = g_item.get("addedBy") or g_item.get("added_by") or g_item.get("userId")
                    if not req_uid:
                        g_added_by_name = g_item.get("addedByName") or g_item.get("added_by_name")
                        if g_added_by_name:
                            for uid, uname in member_names.items():
                                if uname.lower() == g_added_by_name.lower():
                                    req_uid = uid
                                    break

                    if req_uid and req_uid in member_ids:
                        b_item["assignedUserId"] = req_uid
                    elif not b_item.get("assignedUserId") and member_ids:
                        b_item["assignedUserId"] = member_ids[0]

                    b_item["matchedGroceryItemId"] = g_item.get("id")

                    # Automatically check off matching item in room shopping list
                    if g_item.get("status") != "purchased":
                        try:
                            mark_grocery_item_purchased_live(g_item["id"], increment=g_item.get("quantity", 1))
                        except Exception:
                            try:
                                update_grocery_item_status(g_item["id"], "purchased")
                            except Exception:
                                pass
                    matched_count += 1
                    break

        update_bill_items(bill_id, bill_items)
        st.session_state[matched_flag_key] = True
        if matched_count > 0:
            st.toast(f"🎯 Automatically cross-referenced {matched_count} item(s) to roommate requests & checked them off the shopping list!", icon="✅")

    # ── Receipt header ────────────────────────────────────────────────────────
    st.markdown("### Step 3 — Extracted Items & Split Balances")
    st.markdown(
        f"""
        <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:18px;
                    padding:1rem 1.4rem; margin-bottom:1.2rem; display:flex;
                    justify-content:space-between; align-items:center; box-shadow:0 4px 20px -2px rgba(59,42,32,0.08);">
            <div>
                <span style="font-weight:700; color:#2A1D16; font-size:1.05rem;">{bill.get('fileName', 'Receipt')}</span>
                &nbsp; {badge_html(ocr_status)}
            </div>
            <div style="font-family:'Fraunces',serif; font-size:1.4rem; font-weight:700; color:#7A1F2B;">
                Total: {format_currency(bill.get('totalAmount', 0.0))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Editable Item Table ───────────────────────────────────────────────────
    with st.expander("📝 View / Edit Extracted Items & Roommate Assignments", expanded=True):
        header_cols = st.columns([3, 1, 2, 2, 2, 1])
        for col, h in zip(header_cols, ["Item", "Qty", "Unit Price", "Total", "Assign To", "Delete"]):
            col.markdown(f"**{h}**")
        st.markdown("<hr style='margin:0.3rem 0 0.5rem 0; border-color:#E3D6BE;'>", unsafe_allow_html=True)

        updated_items = list(bill_items)
        for idx, item in enumerate(updated_items):
            row = st.columns([3, 1, 2, 2, 2, 1])
            row[0].write(item.get("itemName", "Item"))
            row[1].write(str(item.get("quantity", 1)))
            row[2].write(format_currency(item.get("unitPrice", 0.0)))
            row[3].write(format_currency(item.get("totalPrice", 0.0)))

            with row[4]:
                assign_options = ["— Unassigned —"] + [member_names.get(uid, "Member") for uid in member_ids]
                current_idx = 0
                if item.get("assignedUserId") in member_ids:
                    current_idx = member_ids.index(item["assignedUserId"]) + 1
                selected = st.selectbox(
                    "Assign",
                    options=assign_options,
                    index=current_idx,
                    key=f"assign_{item.get('id', idx)}",
                    label_visibility="collapsed",
                )
                if selected != "— Unassigned —":
                    uid = member_ids[assign_options.index(selected) - 1]
                    item["assignedUserId"] = uid
                else:
                    item["assignedUserId"] = None

            with row[5]:
                if st.button("🗑️", key=f"del_bill_item_{item.get('id', idx)}"):
                    updated_items = [i for i in updated_items if i.get("id") != item.get("id")]
                    update_bill_items(bill_id, updated_items)
                    st.rerun()

        # Add missing item block
        with st.form("add_bill_item_form", clear_on_submit=True):
            st.markdown("<p style='font-weight:600; font-size:0.9rem; color:#2A1D16; margin-bottom:4px;'>➕ Add Missing Item</p>", unsafe_allow_html=True)
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                new_item_name = st.text_input("Item name")
            with ac2:
                new_qty = st.number_input("Qty", min_value=1, value=1, step=1)
            with ac3:
                new_price = st.number_input("Unit Price (₹)", min_value=0.01, value=10.0, step=1.0, format="%.2f")
            if st.form_submit_button("Add Item"):
                if new_item_name.strip():
                    from mock.mock_api import _next_id
                    new_bill_item = {
                        "id": _next_id(),
                        "billId": bill_id,
                        "itemName": new_item_name.strip(),
                        "quantity": int(new_qty),
                        "unitPrice": float(new_price),
                        "totalPrice": round(float(new_price) * int(new_qty), 2),
                        "matchedGroceryItemId": None,
                        "assignedUserId": member_ids[0] if member_ids else None,
                    }
                    updated_items.append(new_bill_item)
                    update_bill_items(bill_id, updated_items)
                    st.success(f"Added **{new_item_name}**.")
                    st.rerun()

    # ── Step 3: Responsive Tabs Generation Breaking Down Split Balance per User ───
    st.markdown("### 💳 Split Balance Breakdown")

    # Group mapped items per member
    user_items = {uid: [] for uid in member_ids}
    user_totals = {uid: 0.0 for uid in member_ids}
    unassigned_items = []

    for item in updated_items:
        assigned_uid = item.get("assignedUserId")
        if assigned_uid in user_items:
            user_items[assigned_uid].append(item)
            user_totals[assigned_uid] += float(item.get("totalPrice", 0.0))
        else:
            unassigned_items.append(item)

    # Dynamic Tabs: Per Member + Overview Breakdown + Equal Split
    tab_labels = [f"👤 {member_names.get(uid, 'User')}" for uid in member_ids]
    tab_labels.append("📊 Overview Split")
    tab_labels.append("⚖️ Equal Split")

    rendered_tabs = st.tabs(tab_labels)

    # Individual Member Tabs
    for idx, uid in enumerate(member_ids):
        with rendered_tabs[idx]:
            u_name = member_names.get(uid, "User")
            u_list = user_items[uid]
            u_total = user_totals[uid]
            st.markdown(
                f"""
                <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-left:4px solid #7A1F2B;
                            border-radius:14px; padding:0.9rem 1.2rem; margin-bottom:1rem; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; color:#2A1D16; font-size:1.05rem;">{u_name}'s Balance Owed</div>
                        <div style="font-size:0.82rem; color:#5C4A3E;">{len(u_list)} mapped line-item(s)</div>
                    </div>
                    <div style="font-family:'Fraunces',serif; font-size:1.45rem; font-weight:700; color:#7A1F2B;">
                        {format_currency(u_total)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if u_list:
                for it in u_list:
                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0.8rem; border-bottom:1px solid #E3D6BE;">
                            <div>
                                <strong style="color:#2A1D16;">{it.get('itemName')}</strong>
                                <span style="color:#5C4A3E; font-size:0.85rem; margin-left:8px;">×{it.get('quantity', 1)} @ {format_currency(it.get('unitPrice', 0.0))}</span>
                            </div>
                            <div style="font-weight:700; color:#7A1F2B; font-variant-numeric:tabular-nums;">{format_currency(it.get('totalPrice', 0.0))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info(f"No items from this receipt are mapped to {u_name}.")

    # Overview Split Tab
    with rendered_tabs[len(member_ids)]:
        st.markdown("#### 📊 Roommate Split Balances")
        for uid in member_ids:
            u_name = member_names.get(uid, "User")
            u_total = user_totals[uid]
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; padding:0.65rem 0.8rem; border-bottom:1px solid #E3D6BE;">
                    <div style="font-weight:600; color:#2A1D16;">👤 {u_name}</div>
                    <div style="font-family:'Fraunces',serif; font-weight:700; color:#7A1F2B; font-variant-numeric:tabular-nums;">{format_currency(u_total)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if unassigned_items:
            unassigned_sum = sum(i.get("totalPrice", 0.0) for i in unassigned_items)
            st.warning(f"⚠️ {len(unassigned_items)} unassigned item(s) totaling {format_currency(unassigned_sum)}.")

    # Equal Split Tab
    with rendered_tabs[len(member_ids) + 1]:
        st.markdown("#### ⚖️ Equal Split Comparison")
        equal_split = calculate_equal_split(bill_id, member_ids)
        for uid, amt in equal_split.items():
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; padding:0.65rem 0.8rem; border-bottom:1px solid #E3D6BE;">
                    <div style="font-weight:600; color:#2A1D16;">👤 {member_names.get(uid, 'User')}</div>
                    <div style="font-weight:700; color:#7A1F2B; font-variant-numeric:tabular-nums;">{format_currency(amt)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Action Buttons ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_save, col_split = st.columns(2)

    with col_save:
        if st.button("💾 Save Assignments"):
            update_bill_items(bill_id, updated_items)
            st.success("Assignments saved successfully!")

    with col_split:
        if st.button("➡️ Continue to Expense Split", type="primary"):
            update_bill_items(bill_id, updated_items)
            st.session_state["split_bill_id"] = bill_id
            st.switch_page("pages/11_Payments.py")

    if st.button("← Upload Another Bill"):
        st.session_state["selected_bill_id"] = None
        st.rerun()
