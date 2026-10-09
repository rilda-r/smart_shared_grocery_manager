"""
pages/10_Bill_Scanning.py
=========================
Bill scanning & OCR page — upload a bill image, review mock-extracted items,
edit/delete/add items, assign them to members, then split the expense.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_current_room_id, get_current_room_name
from utils.formatting import format_currency, badge_html
from components.sidebar import render_sidebar
from components.cards import render_empty_state
from mock.mock_api import (
    upload_bill,
    get_bill,
    get_bill_items,
    update_bill_items,
    assign_bill_item,
    calculate_bill_split,
    calculate_equal_split,
    get_room_members,
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

user_id   = get_current_user_id()
room_id   = get_current_room_id()
room_name = get_current_room_name()

st.markdown("# 📷 Bill Scanning")

if not room_id:
    render_empty_state("🏠", "No room selected", "Please select a room first.")
    if st.button("Go to Rooms"):
        st.switch_page("pages/07_Rooms.py")
    st.stop()

st.markdown(f"<p style='color:#5B6459; margin-top:-0.8rem;'>Room: <strong>{room_name}</strong></p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── State keys ────────────────────────────────────────────────────────────────
if "selected_bill_id" not in st.session_state:
    st.session_state["selected_bill_id"] = None
if "ocr_results" not in st.session_state:
    st.session_state["ocr_results"] = None

# ── Upload section ────────────────────────────────────────────────────────────
if st.session_state["selected_bill_id"] is None:
    st.markdown("### Step 1 — Upload Bill")
    uploaded_file = st.file_uploader(
        "Upload your bill (JPEG, PNG, or PDF)",
        type=["jpg", "jpeg", "png", "pdf"],
    )

    if uploaded_file:
        st.info(f"📎 **{uploaded_file.name}** — ready to scan")
        if st.button("🔍 Scan Bill", type="primary"):
            with st.spinner("🤖 Running OCR... please wait"):
                time.sleep(1.5)  # Simulated processing delay
            bill = upload_bill(room_id, user_id, uploaded_file.name)
            st.session_state["selected_bill_id"] = bill["id"]
            st.session_state["ocr_results"] = "completed"
            st.success("✅ OCR completed! Review the extracted items below.")
            st.rerun()
    else:
        st.markdown(
            """
            <div style="border:2px dashed #D8D0BE; border-radius:8px; padding:2.5rem;
                        text-align:center; color:#5B6459; margin-top:1rem;">
                <div style="font-size:2.5rem;">📄</div>
                <div style="font-weight:600; color:#20261F; margin-top:0.5rem;">
                    Drag & drop your grocery bill here
                </div>
                <div style="font-size:0.85rem; margin-top:0.3rem;">Supports JPG, PNG, PDF</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()
else:
    # ── OCR Results ───────────────────────────────────────────────────────────
    bill_id = st.session_state["selected_bill_id"]
    bill    = get_bill(bill_id)

    if not bill:
        st.error("Bill not found. Please upload again.")
        st.session_state["selected_bill_id"] = None
        if st.button("Upload Again", key="reupload_missing_bill"):
            st.rerun()
        st.stop()

    ocr_status = bill.get("ocrStatus", "processing")

    if ocr_status == "processing":
        st.warning("⏳ OCR is still processing… check back in a moment.")
        if st.button("Refresh"):
            st.rerun()
        st.stop()

    if ocr_status == "failed":
        st.error("❌ OCR failed. Please try uploading again.")
        if st.button("Upload Again"):
            st.session_state["selected_bill_id"] = None
            st.rerun()
        st.stop()

    # ── Bill details ──────────────────────────────────────────────────────────
    st.markdown(f"### Step 2 — Review Extracted Items")
    st.markdown(
        f"""
        <div style="background:#E7EFE6; border:1px solid #C3D6C6; border-radius:6px;
                    padding:0.8rem 1.2rem; margin-bottom:1rem; display:flex;
                    justify-content:space-between; align-items:center;">
            <div>
                <span style="font-weight:600;">{bill.get('fileName', 'Bill')}</span>
                &nbsp; {badge_html(ocr_status)}
            </div>
            <div style="font-family:'Fraunces',serif; font-size:1.4rem; font-weight:700; color:#A97A1F;">
                Total: {format_currency(bill.get('totalAmount', 0.0))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bill_items = get_bill_items(bill_id) or []
    room_members = get_room_members(room_id) or []
    member_ids   = [m["userId"] for m in room_members]
    member_names = {uid: get_username(uid) for uid in member_ids}

    # ── Item table (editable) ─────────────────────────────────────────────────
    header_cols = st.columns([3, 1, 2, 2, 2, 1])
    for col, h in zip(header_cols, ["Item", "Qty", "Unit Price", "Total", "Assign To", "Delete"]):
        col.markdown(f"**{h}**")
    st.markdown("<hr style='margin:0.3rem 0 0.5rem 0; border-color:#D8D0BE;'>", unsafe_allow_html=True)

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

    # ── Add missing item ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("➕ Add Missing Item"):
        with st.form("add_bill_item_form", clear_on_submit=True):
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                new_item_name = st.text_input("Item name")
            with ac2:
                new_qty = st.number_input("Qty", min_value=1, value=1, step=1)
            with ac3:
                new_price = st.number_input("Unit Price (₹)", min_value=0.01, value=10.0, step=1.0, format="%.2f")
            if st.form_submit_button("Add"):
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
                        "assignedUserId": None,
                    }
                    updated_items.append(new_bill_item)
                    update_bill_items(bill_id, updated_items)
                    st.success(f"Added **{new_item_name}**.")
                    st.rerun()

    # ── Save assignments & proceed ────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_save, col_split = st.columns(2)

    with col_save:
        if st.button("💾 Save Assignments"):
            update_bill_items(bill_id, updated_items)
            st.success("Assignments saved!")

    with col_split:
        if st.button("➡️ Continue to Expense Split", type="primary"):
            update_bill_items(bill_id, updated_items)
            st.session_state["split_bill_id"] = bill_id
            st.switch_page("pages/11_Payments.py")

    if st.button("← Upload Another Bill"):
        st.session_state["selected_bill_id"] = None
        st.rerun()
