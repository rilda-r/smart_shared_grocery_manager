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
import uuid
import re

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


def sanitize_ocr_item(item: dict, default_bill_id: int) -> dict:
    """
    Sanitizes OCR extracted items:
    - Strips whitespace & cleans text
    - Enforces safe numerical types (float, int)
    - Generates guaranteed unique randomized fallback ID string if missing or invalid
    - Enforces camelCase contract: id, billId, itemName, quantity, unitPrice, totalPrice, matchedGroceryItemId, assignedUserId
    """
    raw_id = item.get("id")
    if raw_id is None or str(raw_id).strip() == "" or raw_id == 0:
        safe_id = f"item_{uuid.uuid4().hex[:8]}"
    else:
        safe_id = raw_id

    # Item name sanitization
    raw_name = str(item.get("itemName", item.get("name", "Item"))).strip()
    raw_name = re.sub(r"\s+", " ", raw_name)
    if not raw_name:
        raw_name = f"Item-{uuid.uuid4().hex[:4]}"

    # Quantity sanitization
    try:
        raw_qty = float(item.get("quantity", item.get("qty", 1)))
        quantity = max(1, int(round(raw_qty)))
    except (ValueError, TypeError):
        quantity = 1

    # Unit price & total price sanitization
    try:
        unit_price = max(0.0, float(item.get("unitPrice", item.get("price", 0.0))))
    except (ValueError, TypeError):
        unit_price = 0.0

    try:
        total_price = max(0.0, float(item.get("totalPrice", item.get("total", unit_price * quantity))))
    except (ValueError, TypeError):
        total_price = round(unit_price * quantity, 2)

    if total_price == 0.0 and unit_price > 0.0:
        total_price = round(unit_price * quantity, 2)
    elif unit_price == 0.0 and total_price > 0.0 and quantity > 0:
        unit_price = round(total_price / quantity, 2)

    return {
        "id": safe_id,
        "billId": item.get("billId", default_bill_id),
        "itemName": raw_name,
        "quantity": quantity,
        "unitPrice": round(unit_price, 2),
        "totalPrice": round(total_price, 2),
        "matchedGroceryItemId": item.get("matchedGroceryItemId"),
        "assignedUserId": item.get("assignedUserId"),
    }


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
            with st.spinner("🤖 Analyzing bill layout and extracting items... please wait"):
                file_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                extracted_items = []
                total_amount = 0.0

                # 1. Attempt OCR processing pipeline
                try:
                    from services.ocr_service import process_bill
                    result = process_bill(file_bytes, file_name)
                    if result.get("success") and result.get("data", {}).get("items"):
                        data = result["data"]
                        for raw_item in data["items"]:
                            qty = int(round(float(raw_item.get("quantity", 1))))
                            unit_p = float(raw_item.get("unit_price", 0.0))
                            tot_p = round(float(raw_item.get("total_price", unit_p * qty)), 2)
                            extracted_items.append(
                                sanitize_ocr_item(
                                    {
                                        "id": f"item_{uuid.uuid4().hex[:8]}",
                                        "itemName": raw_item.get("item_name", "Item"),
                                        "quantity": max(1, qty),
                                        "unitPrice": unit_p,
                                        "totalPrice": tot_p,
                                        "matchedGroceryItemId": None,
                                        "assignedUserId": None,
                                    },
                                    default_bill_id=0,
                                )
                            )
                        if data.get("total_amount") is not None:
                            total_amount = float(data["total_amount"])
                except Exception:
                    pass

                # 2. PDF text stream fallback
                if not extracted_items and file_name.lower().endswith(".pdf"):
                    try:
                        import pypdfium2 as pdfium
                        pdf = pdfium.PdfDocument(file_bytes)
                        full_text = "\n".join(
                            (page.get_textpage().get_text_range() or "").strip()
                            for page in pdf
                        )
                        if full_text.strip():
                            from services.ocr_service import parse_bill_items
                            parsed = parse_bill_items(full_text)
                            for raw_item in parsed.get("items", []):
                                qty = int(round(float(raw_item.get("quantity", 1))))
                                unit_p = float(raw_item.get("unit_price", 0.0))
                                tot_p = round(float(raw_item.get("total_price", unit_p * qty)), 2)
                                extracted_items.append(
                                    sanitize_ocr_item(
                                        {
                                            "id": f"item_{uuid.uuid4().hex[:8]}",
                                            "itemName": raw_item.get("item_name", "Item"),
                                            "quantity": max(1, qty),
                                            "unitPrice": unit_p,
                                            "totalPrice": tot_p,
                                            "matchedGroceryItemId": None,
                                            "assignedUserId": None,
                                        },
                                        default_bill_id=0,
                                    )
                                )
                            if parsed.get("total_amount") is not None:
                                total_amount = float(parsed["total_amount"])
                    except Exception:
                        pass

                # 3. Dynamic Cost + 5% GST computation (2.5% CGST + 2.5% SGST)
                subtotal = sum(i["totalPrice"] for i in extracted_items)
                if total_amount <= 0 and subtotal > 0:
                    gst = round(subtotal * 0.05, 2)
                    total_amount = round(subtotal + gst, 2)

                bill = upload_bill(
                    room_id=room_id,
                    user_id=user_id,
                    file_name=file_name,
                    extracted_items=extracted_items,
                    total_amount=total_amount,
                )
                st.session_state["selected_bill_id"] = bill["id"]
                st.session_state["ocr_results"] = "completed"
                if extracted_items:
                    st.success(f"✅ OCR completed! Extracted {len(extracted_items)} items.")
                else:
                    st.info("ℹ️ Bill uploaded. No automated items found; you can add items manually below.")
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

# ── OCR Results ───────────────────────────────────────────────────────────────
bill_id = st.session_state["selected_bill_id"]
bill    = get_bill(bill_id)

if not bill:
    st.error("Bill not found. Please upload again.")
    st.session_state["selected_bill_id"] = None
    st.rerun()

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

# ── Bill details ──────────────────────────────────────────────────────────────
st.markdown(f"### Step 2 — Review Extracted Items")
st.markdown(
    f"""
    <div style="background:#E7EFE6; border:1px solid #C3D6C6; border-radius:6px;
                padding:0.8rem 1.2rem; margin-bottom:1rem; display:flex;
                justify-content:space-between; align-items:center;">
        <div>
            <span style="font-weight:600;">{bill['fileName']}</span>
            &nbsp; {badge_html(ocr_status)}
        </div>
        <div style="font-family:'Fraunces',serif; font-size:1.4rem; font-weight:700; color:#A97A1F;">
            Total: {format_currency(bill['totalAmount'])}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

raw_bill_items = get_bill_items(bill_id)
bill_items = [sanitize_ocr_item(item, bill_id) for item in raw_bill_items]
room_members = get_room_members(room_id)
member_ids   = [m["userId"] for m in room_members]
member_names = {uid: get_username(uid) for uid in member_ids}

# ── Item table (editable) ─────────────────────────────────────────────────────
header_cols = st.columns([3, 1, 2, 2, 2, 1])
for col, h in zip(header_cols, ["Item", "Qty", "Unit Price", "Total", "Assign To", "Delete"]):
    col.markdown(f"**{h}**")
st.markdown("<hr style='margin:0.3rem 0 0.5rem 0; border-color:#D8D0BE;'>", unsafe_allow_html=True)

updated_items = list(bill_items)

for idx, item in enumerate(updated_items):
    row = st.columns([3, 1, 2, 2, 2, 1])
    row[0].write(item["itemName"])
    row[1].write(str(item["quantity"]))
    row[2].write(format_currency(item["unitPrice"]))
    row[3].write(format_currency(item["totalPrice"]))

    item_key_id = item.get("id", idx)

    with row[4]:
        assign_options = ["— Unassigned —"] + [member_names[uid] for uid in member_ids]
        current_idx = 0
        if item.get("assignedUserId") in member_ids:
            current_idx = member_ids.index(item["assignedUserId"]) + 1
        selected = st.selectbox(
            "Assign",
            options=assign_options,
            index=current_idx,
            key=f"assign_{item_key_id}_{idx}",
            label_visibility="collapsed",
        )
        if selected != "— Unassigned —":
            uid = member_ids[assign_options.index(selected) - 1]
            item["assignedUserId"] = uid
        else:
            item["assignedUserId"] = None

    with row[5]:
        if st.button("🗑️", key=f"del_bill_item_{item_key_id}_{idx}"):
            updated_items = [i for i in updated_items if i["id"] != item["id"]]
            update_bill_items(bill_id, updated_items)
            st.rerun()

# ── Add missing item ──────────────────────────────────────────────────────────
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
                new_bill_item = sanitize_ocr_item(
                    {
                        "id": f"item_{uuid.uuid4().hex[:8]}",
                        "billId": bill_id,
                        "itemName": new_item_name,
                        "quantity": int(new_qty),
                        "unitPrice": float(new_price),
                        "totalPrice": round(float(new_price) * int(new_qty), 2),
                        "matchedGroceryItemId": None,
                        "assignedUserId": None,
                    },
                    bill_id,
                )
                updated_items.append(new_bill_item)
                update_bill_items(bill_id, updated_items)
                st.success(f"Added **{new_bill_item['itemName']}**.")
                st.rerun()

# ── Save assignments & proceed ────────────────────────────────────────────────
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
