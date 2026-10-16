"""
pages/10_Bill_Scanning.py
=========================
End-to-end receipt scanning and expense attribution powered by Google Gemini (google-genai)
and Supabase PostgreSQL. Supports PDF & image receipts, fuzzy grocery list matching,
multi-requester splits, extra items management, and atomic database settlement.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hashlib
from decimal import Decimal
import streamlit as st

from style import apply_base_style
from utils.session import (
    require_auth,
    get_current_user_id,
    get_current_room_id,
    get_current_room_name,
)
from utils.formatting import format_currency, badge_html
from components.sidebar import render_sidebar, render_room_selector
from components.cards import render_empty_state
from database.database import (
    get_room_members_with_identities,
    get_live_grocery_items,
)
from services.receipt_ocr_service import (
    process_receipt_file,
    validate_receipt_math,
    to_decimal,
)
from services.item_matching_service import match_receipt_items
from services.receipt_split_service import calculate_receipt_split
from services.receipt_storage_service import store_receipt_file
from services.receipt_service import confirm_receipt_transaction

st.set_page_config(
    page_title="Receipt Scanning — GrocEase",
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
    st.markdown("# 📷 Receipt Scanning & Split")
with col_sel:
    st.write("")
    render_room_selector(key_prefix="bill_scanning_page")

user_id = get_current_user_id()
room_id = get_current_room_id()
room_name = get_current_room_name()

if not room_id:
    render_empty_state(
        "🏠",
        "Select a Room to Scan Receipts",
        "Please choose an active room from the dropdown above to upload receipts and orchestrate expense splits.",
    )
    st.stop()

st.markdown(
    "<p style='color:#5C4A3E; margin-top:-0.8rem; font-size:0.95rem;'>"
    "Scan grocery bills, auto-attribute requested items to room members, and split expenses effortlessly."
    "</p>",
    unsafe_allow_html=True,
)

# Reset any in-progress scan when the active room changes
if st.session_state.get("scan_room_id") != room_id:
    st.session_state["scan_room_id"] = room_id
    st.session_state["scan_data"] = None
    st.session_state["scan_step"] = 1
    st.session_state["rematch_needed"] = True
    st.session_state["confirmed_receipt_id"] = None
    st.session_state["is_submitting"] = False

# Load room members and pending grocery list
raw_members = get_room_members_with_identities(room_id)
member_name_map = {m["user_id"]: m["display_name"] for m in raw_members}
room_member_ids = list(member_name_map.keys())

all_grocery_items = get_live_grocery_items(room_id)
pending_grocery_items = [g for g in all_grocery_items if g.get("status") == "pending"]

st.markdown(
    f"""
    <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:14px; padding:0.6rem 1rem; margin-bottom:1.2rem;">
        <span style="color:#5C4A3E; font-size:0.95rem;">
            Active Room: <strong style="color:#2A1D16;">{room_name}</strong> &nbsp;|&nbsp;
            Members: <strong style="color:#2A1D16;">{len(raw_members)}</strong> &nbsp;|&nbsp;
            Pending Items: <strong style="color:#2A1D16;">{len(pending_grocery_items)}</strong>
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# ── Session State Initialization ─────────────────────────────────────────────
if "scan_step" not in st.session_state:
    st.session_state["scan_step"] = 1
if "scan_data" not in st.session_state:
    st.session_state["scan_data"] = None
if "confirmed_receipt_id" not in st.session_state:
    st.session_state["confirmed_receipt_id"] = None
if "is_submitting" not in st.session_state:
    st.session_state["is_submitting"] = False


# ── STEP 1: UPLOAD & PREVIEW ─────────────────────────────────────────────────
if st.session_state["scan_data"] is None:
    st.markdown("### Step 1 — Upload Receipt")
    
    col_u1, col_u2 = st.columns([2, 1])
    with col_u1:
        uploaded_file = st.file_uploader(
            "Upload receipt (JPEG, PNG, or PDF)",
            type=["jpg", "jpeg", "png", "pdf"],
            key="receipt_file_uploader",
        )

    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        file_hash = hashlib.md5(file_bytes).hexdigest()
        
        # Check duplicate scan in this session
        if st.session_state.get("last_uploaded_hash") == file_hash:
            st.warning("⚠️ Notice: You uploaded this exact receipt file previously.")
        
        with col_u2:
            st.markdown("**Preview:**")
            if uploaded_file.name.lower().endswith(".pdf"):
                st.info(f"📄 PDF Document: **{uploaded_file.name}** ({len(file_bytes) / 1024:.1f} KB)")
            else:
                st.image(file_bytes, caption=uploaded_file.name, use_container_width=True)

        if st.button("🔍 Scan & Extract Receipt", type="primary"):
            st.session_state["last_uploaded_hash"] = file_hash
            with st.spinner("🤖 Processing receipt with Gemini Structured OCR..."):
                # 1. Save to Supabase Storage or local fallback
                image_path, stype = store_receipt_file(file_bytes, uploaded_file.name, room_id, user_id)
                
                # 2. Extract structured data
                extraction = process_receipt_file(file_bytes, uploaded_file.name)
                
                # 3. Save to state
                st.session_state["scan_data"] = {
                    "file_name": uploaded_file.name,
                    "image_path": image_path,
                    "store": extraction.get("store") or "Store",
                    "date": extraction.get("date"),
                    "items": extraction.get("items", []),
                    "subtotal": extraction.get("subtotal", Decimal("0.00")),
                    "tax": extraction.get("tax", Decimal("0.00")),
                    "discount": extraction.get("discount", Decimal("0.00")),
                    "other_charges": extraction.get("other_charges", Decimal("0.00")),
                    "round_off": extraction.get("round_off", Decimal("0.00")),
                    "total": extraction.get("total", Decimal("0.00")),
                    "engine": extraction.get("engine"),
                    "gemini_error": extraction.get("gemini_error"),
                    "ocr_success": extraction.get("success", False),
                    "ocr_error": extraction.get("error"),
                    "tax_split_mode": "proportional",
                }
                st.session_state["scan_step"] = 2
                st.rerun()

    else:
        st.markdown(
            """
            <div style="border:2px dashed #E3D6BE; border-radius:18px; padding:3rem;
                        text-align:center; color:#5C4A3E; background:#FFFDF9; margin-top:0.5rem;">
                <div style="font-size:3rem;">🧾</div>
                <div style="font-weight:700; font-size:1.1rem; color:#2A1D16; margin-top:0.5rem;">
                    Drag & Drop your receipt here
                </div>
                <div style="font-size:0.85rem; margin-top:0.3rem;">Supports JPG, PNG, and multi-page PDF</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()


# ── SCAN DATA RETRIEVAL ──────────────────────────────────────────────────────
scan = st.session_state["scan_data"]
step = st.session_state.get("scan_step", 2)

# Navigation breadcrumb
st.markdown(
    f"""
    <div style="display:flex; gap:1rem; align-items:center; margin-bottom:1.2rem; font-size:0.9rem;">
        <span style="font-weight:{'700; color:#7A1F2B' if step==2 else '400; color:#A39670'};">1. Review & Edit Items</span> &nbsp;→&nbsp;
        <span style="font-weight:{'700; color:#7A1F2B' if step==3 else '400; color:#A39670'};">2. Item Attribution & Extras</span> &nbsp;→&nbsp;
        <span style="font-weight:{'700; color:#7A1F2B' if step==4 else '400; color:#A39670'};">3. Summary & Confirm</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── STEP 2: REVIEW & EDIT EXTRACTED ITEMS ────────────────────────────────────
if step == 2:
    st.markdown("### Step 2 — Review & Edit Extracted Items")
    
    if not scan.get("ocr_success"):
        st.error(f"⚠️ {scan.get('ocr_error') or 'Text extraction failed. Please enter the items manually below.'}")
    else:
        engine = scan.get("engine")
        engine_label = {
            "gemini": "Gemini Structured Vision",
            "pdf_text": "PDF Text Layer (Gemini unavailable)",
            "tesseract_fallback": "Tesseract Fallback (Gemini unavailable)",
        }.get(engine, "Fallback Engine")
        if engine == "gemini":
            st.success(f"✅ Extracted with **{engine_label}**! Please verify quantities and prices.")
        else:
            st.warning(f"⚠️ Extracted with **{engine_label}**. Please review carefully.")
    if scan.get("gemini_error"):
        with st.expander("Gemini error details"):
            st.code(str(scan["gemini_error"]))

    # Receipt Metadata Header
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        scan["store"] = st.text_input("Store Name", value=scan.get("store") or "Store")
    with m_col2:
        scan["date"] = st.text_input("Receipt Date", value=scan.get("date") or "")
    with m_col3:
        st.markdown(f"<div style='margin-top:1.8rem;'>File: <code>{scan.get('file_name')}</code></div>", unsafe_allow_html=True)

    st.markdown("#### Item List")

    # Editable Item Table
    items = scan.get("items", [])
    updated_items = []
    
    h1, h2, h3, h4, h5 = st.columns([4, 1.5, 2, 2, 1])
    h1.markdown("**Item Name**")
    h2.markdown("**Quantity**")
    h3.markdown("**Unit Price (₹)**")
    h4.markdown("**Line Total (₹)**")
    h5.markdown("**Action**")

    del_idx = None
    for idx, it in enumerate(items):
        r1, r2, r3, r4, r5 = st.columns([4, 1.5, 2, 2, 1])
        with r1:
            name_val = st.text_input("Name", value=it["name"], key=f"name_{idx}", label_visibility="collapsed")
        with r2:
            qty_val = st.number_input("Qty", value=float(it["quantity"]), min_value=0.01, step=1.0, format="%.2f", key=f"qty_{idx}", label_visibility="collapsed")
        with r3:
            unit_val = st.number_input("Unit", value=float(it["unit_price"]), min_value=0.0, step=1.0, format="%.2f", key=f"unit_{idx}", label_visibility="collapsed")
        with r4:
            # Recalculate line total automatically if unit price or qty changed
            calc_line = to_decimal(Decimal(str(qty_val)) * Decimal(str(unit_val)))
            tot_val = st.number_input("Total", value=float(calc_line), min_value=0.0, step=1.0, format="%.2f", key=f"tot_{idx}", label_visibility="collapsed")
        with r5:
            if st.button("🗑️", key=f"del_{idx}"):
                del_idx = idx

        updated_items.append({
            "name": name_val.strip(),
            "quantity": to_decimal(qty_val, quant=Decimal("0.001")),
            "unit_price": to_decimal(unit_val),
            "line_total": to_decimal(tot_val),
            "item_discount": it.get("item_discount", Decimal("0.00")),
            "gst_rate": it.get("gst_rate", Decimal("0.00")),
        })

    if del_idx is not None:
        updated_items.pop(del_idx)
        scan["items"] = updated_items
        st.rerun()

    scan["items"] = updated_items

    # Add missing item form
    with st.expander("➕ Add Missing Item"):
        with st.form("add_item_form", clear_on_submit=True):
            a1, a2, a3 = st.columns([3, 1, 2])
            with a1:
                new_name = st.text_input("Item Name")
            with a2:
                new_qty = st.number_input("Qty", min_value=0.1, value=1.0, step=1.0)
            with a3:
                new_price = st.number_input("Unit Price (₹)", min_value=0.0, value=10.0, step=1.0, format="%.2f")
            if st.form_submit_button("Add Item"):
                if new_name.strip():
                    new_tot = to_decimal(Decimal(str(new_qty)) * Decimal(str(new_price)))
                    scan["items"].append({
                        "name": new_name.strip(),
                        "quantity": to_decimal(new_qty, quant=Decimal("0.001")),
                        "unit_price": to_decimal(new_price),
                        "line_total": new_tot,
                    })
                    st.success(f"Added '{new_name.strip()}'")
                    st.rerun()

    # Taxes, Charges, Discounts, and Total
    st.markdown("<hr style='margin:1.5rem 0 1rem 0; border-color:#E3D6BE;'>", unsafe_allow_html=True)
    st.markdown("#### Totals & Adjustments")
    
    c_sub = sum(i["line_total"] for i in scan["items"])
    scan["subtotal"] = c_sub

    tc1, tc2, tc3, tc4, tc5, tc6 = st.columns(6)
    with tc1:
        st.markdown(f"**Items Subtotal**<br><span style='font-size:1.2rem; font-weight:700;'>{format_currency(c_sub)}</span>", unsafe_allow_html=True)
    with tc2:
        tax_in = st.number_input("Tax / GST (₹)", value=float(scan["tax"]), min_value=0.0, step=1.0, format="%.2f")
        scan["tax"] = to_decimal(tax_in)
    with tc3:
        disc_in = st.number_input("Discount (₹)", value=float(scan["discount"]), min_value=0.0, step=1.0, format="%.2f")
        scan["discount"] = to_decimal(disc_in)
    with tc4:
        chg_in = st.number_input("Other Charges (₹)", value=float(scan["other_charges"]), min_value=0.0, step=1.0, format="%.2f")
        scan["other_charges"] = to_decimal(chg_in)
    with tc5:
        ro_in = st.number_input("Round-off (₹)", value=float(scan.get("round_off", 0) or 0), step=0.01, format="%.2f")
        scan["round_off"] = to_decimal(ro_in)
    with tc6:
        printed_tot_in = st.number_input("Printed Total (₹)", value=float(scan["total"]), min_value=0.0, step=1.0, format="%.2f")
        scan["total"] = to_decimal(printed_tot_in)

    # Validate math
    is_valid, calc_tot, math_warn = validate_receipt_math(
        scan["items"], scan["tax"], scan["discount"], scan["other_charges"], scan["total"],
        round_off=scan.get("round_off", Decimal("0.00")),
    )
    if not is_valid:
        st.warning(math_warn)
        if st.button("Fix Total to Match Math (₹" + str(calc_tot) + ")"):
            scan["total"] = calc_tot
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    nb1, nb2 = st.columns([1, 4])
    with nb1:
        if st.button("← Upload Another"):
            st.session_state["scan_data"] = None
            st.session_state["scan_step"] = 1
            st.rerun()
    with nb2:
        if st.button("➡️ Continue to Member Attribution", type="primary"):
            if not scan["items"]:
                st.error("Please add at least one item before continuing.")
            else:
                st.session_state["scan_step"] = 3
                st.rerun()


# ── STEP 3: MAPPING TO WHO ASKED FOR EACH ITEM & EXTRAS ──────────────────────
elif step == 3:
    st.markdown("### Step 3 — Item Attribution & Extras")
    
    # Run matching service if not yet computed or items modified
    if "matched_state" not in st.session_state or st.session_state.get("rematch_needed", True):
        matched_dict = match_receipt_items(
            scan["items"], pending_grocery_items, raw_members, user_id
        )
        st.session_state["matched_state"] = matched_dict
        st.session_state["rematch_needed"] = False

    mstate = st.session_state["matched_state"]
    matched_items = mstate["matched_items"]
    extra_items = mstate["extra_items"]
    unmatched_grocery = mstate["unmatched_grocery_items"]

    tab_matched, tab_extras, tab_unpurchased = st.tabs([
        f"🎯 Matched Grocery Items ({len(matched_items)})",
        f"🛍️ Your Items Purchased / Extras ({len(extra_items)})",
        f"📋 Not on Receipt ({len(unmatched_grocery)})",
    ])

    # ── TAB 1: Matched Items with Multi-Requester Splits ──────────────────────
    with tab_matched:
        if not matched_items:
            st.info("No items on this receipt automatically matched the room's pending grocery list.")
        else:
            st.markdown(
                "<p style='color:#5C4A3E; font-size:0.9rem;'>"
                "Items requested by room members. If multiple members asked for the same product, "
                "the receipt quantity is split proportionally. You can adjust member quantities or reassign."
                "</p>",
                unsafe_allow_html=True,
            )

            for m_idx, item in enumerate(matched_items):
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:14px; padding:0.8rem 1.2rem; margin-bottom:0.8rem;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <span style="font-weight:700; font-size:1.1rem; color:#2A1D16;">{item['name']}</span>
                                    &nbsp; <span style="color:#5C4A3E; font-size:0.85rem;">(Receipt Qty: {item['receipt_quantity']} @ {format_currency(item['unit_price'])} = <strong>{format_currency(item['line_total'])}</strong>)</span>
                                </div>
                                <div>
                                    <span style="background:#F6ECD8; color:#7A1F2B; padding:0.2rem 0.6rem; border-radius:12px; font-size:0.8rem; font-weight:600;">
                                        Match: {item['matched_grocery_name']} ({int(item['match_score'])}%)
                                    </span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Quantity discrepancy indicator
                    if item.get("qty_difference") and item["qty_difference"] != Decimal("0.000"):
                        diff = item["qty_difference"]
                        if diff > 0:
                            st.warning(f"ℹ️ Receipt has **+{diff} more** than total requested ({item['total_requested_qty']}). Extra allocated proportionally.")
                        else:
                            st.warning(f"⚠️ Receipt has **{abs(diff)} less** than total requested ({item['total_requested_qty']}).")

                    # Assignments table per item
                    for a_idx, assign in enumerate(item["assignments"]):
                        c_a1, c_a2, c_a3, c_a4 = st.columns([2.5, 1.5, 1.5, 2])
                        with c_a1:
                            member_opts = list(member_name_map.keys())
                            curr_member_idx = member_opts.index(assign["user_id"]) if assign["user_id"] in member_opts else 0
                            new_uid = st.selectbox(
                                "Assigned Member",
                                options=member_opts,
                                format_func=lambda uid: f"👤 {member_name_map[uid]}",
                                index=curr_member_idx,
                                key=f"mat_uid_{m_idx}_{a_idx}",
                            )
                            assign["user_id"] = new_uid
                            assign["member_name"] = member_name_map[new_uid]

                        with c_a2:
                            new_qty = st.number_input(
                                "Qty allocated",
                                value=float(assign["quantity"]),
                                min_value=0.0,
                                step=1.0,
                                key=f"mat_qty_{m_idx}_{a_idx}",
                            )
                            assign["quantity"] = to_decimal(new_qty, quant=Decimal("0.001"))

                        with c_a3:
                            # Auto-calculate amount from unit price
                            calc_amt = to_decimal(assign["quantity"] * item["unit_price"])
                            new_amt = st.number_input(
                                "Amount (₹)",
                                value=float(calc_amt),
                                min_value=0.0,
                                step=1.0,
                                key=f"mat_amt_{m_idx}_{a_idx}",
                            )
                            assign["amount"] = to_decimal(new_amt)

                        with c_a4:
                            st.markdown(
                                f"<div style='margin-top:1.8rem; font-size:0.85rem; color:#5C4A3E;'>"
                                f"Requested: {assign.get('requested_quantity', '—')}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                    st.markdown("<hr style='border-color:#E3D6BE; margin:0.5rem 0 1rem 0;'>", unsafe_allow_html=True)

    # ── TAB 2: Extra Items (Your items purchased) ────────────────────────────
    with tab_extras:
        st.markdown(
            "<p style='color:#5C4A3E; font-size:0.9rem;'>"
            "Items from the receipt that were not on the grocery list. You can keep them as your own purchase, "
            "assign them to a specific roommate, or share them equally among all members."
            "</p>",
            unsafe_allow_html=True,
        )

        if not extra_items:
            st.success("🎉 All items on the receipt matched items requested on the shopping list!")
        else:
            for e_idx, e_item in enumerate(extra_items):
                with st.container():
                    ec1, ec2, ec3 = st.columns([3, 2, 2])
                    with ec1:
                        st.markdown(f"**{e_item['name']}**")
                        st.caption(f"Qty: {e_item['quantity']} × {format_currency(e_item['unit_price'])} = {format_currency(e_item['line_total'])}")
                    
                    with ec2:
                        split_mode = st.radio(
                            "Who pays?",
                            options=["Only Me (Shopper)", "Specific Member", "Shared by All"],
                            index=0 if e_item.get("split_mode") == "own" else (1 if e_item.get("split_mode") == "specific" else 2),
                            key=f"extra_mode_{e_idx}",
                        )

                    with ec3:
                        if split_mode == "Only Me (Shopper)":
                            e_item["split_mode"] = "own"
                            e_item["assignments"] = [{
                                "user_id": user_id,
                                "member_name": member_name_map.get(user_id, "You"),
                                "quantity": e_item["quantity"],
                                "amount": e_item["line_total"],
                            }]
                            st.markdown("<div style='margin-top:1.5rem; color:#7A1F2B; font-weight:600;'>Only you pay (₹" + str(e_item["line_total"]) + ")</div>", unsafe_allow_html=True)
                        
                        elif split_mode == "Specific Member":
                            e_item["split_mode"] = "specific"
                            target_uid = st.selectbox(
                                "Assign to",
                                options=room_member_ids,
                                format_func=lambda uid: member_name_map[uid],
                                key=f"extra_target_{e_idx}",
                            )
                            e_item["assignments"] = [{
                                "user_id": target_uid,
                                "member_name": member_name_map[target_uid],
                                "quantity": e_item["quantity"],
                                "amount": e_item["line_total"],
                            }]
                        
                        else:  # Shared by All
                            e_item["split_mode"] = "shared_all"
                            n_members = len(room_member_ids)
                            per_person_amt = (e_item["line_total"] / Decimal(n_members)).quantize(Decimal("0.01"))
                            per_person_qty = (e_item["quantity"] / Decimal(n_members)).quantize(Decimal("0.001"))
                            e_item["assignments"] = [
                                {
                                    "user_id": mid,
                                    "member_name": member_name_map[mid],
                                    "quantity": per_person_qty,
                                    "amount": per_person_amt,
                                }
                                for mid in room_member_ids
                            ]
                            st.markdown(f"<div style='margin-top:1.5rem; color:#C8963E; font-weight:600;'>Shared equally ({format_currency(per_person_amt)} / member)</div>", unsafe_allow_html=True)

                    st.markdown("<hr style='border-color:#E3D6BE; margin:0.3rem 0 0.8rem 0;'>", unsafe_allow_html=True)

    # ── TAB 3: Unpurchased Grocery List Items ─────────────────────────────────
    with tab_unpurchased:
        st.markdown(
            "<p style='color:#5C4A3E; font-size:0.9rem;'>"
            "Grocery list items that were NOT found on this receipt. These will remain pending in the grocery list."
            "</p>",
            unsafe_allow_html=True,
        )
        if not unmatched_grocery:
            st.success("All pending grocery items were found on the receipt!")
        else:
            for ug in unmatched_grocery:
                st.markdown(
                    f"""
                    <div style="background:#FBF6EC; border-left:4px solid #C8963E; border-radius:4px; padding:0.5rem 1rem; margin-bottom:0.5rem; display:flex; justify-content:space-between;">
                        <div>
                            <strong>{ug['itemName']}</strong> (Qty: {ug['quantity']}) — Requested by <em>{ug['memberName']}</em>
                        </div>
                        <div>
                            <span style="color:#C8963E; font-weight:600; font-size:0.85rem;">⏳ Not Purchased (stays pending)</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<br>", unsafe_allow_html=True)
    b_col1, b_col2 = st.columns([1, 4])
    with b_col1:
        if st.button("← Back to Review"):
            st.session_state["scan_step"] = 2
            st.rerun()
    with b_col2:
        if st.button("➡️ Continue to Final Summary & Split", type="primary"):
            st.session_state["scan_step"] = 4
            st.rerun()


# ── STEP 4: SUMMARY & CONFIRM ────────────────────────────────────────────────
elif step == 4:
    st.markdown("### Step 4 — Final Expense Split & Confirmation")
    
    mstate = st.session_state["matched_state"]
    matched_items = mstate["matched_items"]
    extra_items = mstate["extra_items"]

    # Tax & Charge Distribution Toggle
    tax_toggle_col1, tax_toggle_col2 = st.columns([2, 3])
    with tax_toggle_col1:
        split_toggle = st.radio(
            "Tax & Discounts Distribution:",
            options=["Proportional to Member Items Subtotal", "Equal Split Among Members"],
            index=0 if scan.get("tax_split_mode") == "proportional" else 1,
            horizontal=True,
        )
        scan["tax_split_mode"] = "proportional" if "Proportional" in split_toggle else "equal"

    # Compute final split
    split_result = calculate_receipt_split(
        matched_items=matched_items,
        extra_items=extra_items,
        tax=scan["tax"],
        discount=scan["discount"],
        other_charges=scan["other_charges"],
        total=scan["total"],
        shopper_user_id=user_id,
        all_room_member_ids=room_member_ids,
        member_name_map=member_name_map,
        tax_split_mode=scan["tax_split_mode"],
        coupon_discount=max(
            Decimal("0.00"),
            scan["discount"] - sum((to_decimal(i.get("item_discount", 0)) for i in scan["items"]), Decimal("0.00")),
        ),
        round_off=scan.get("round_off", Decimal("0.00")),
    )

    summaries = split_result["member_summaries"]
    debts = split_result["debts"]

    # Receipt Overview Card
    st.markdown(
        f"""
        <div style="background:#FBF6EC; border:1px solid #E3D6BE; border-radius:18px; padding:1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-size:1.2rem; font-weight:700;">{scan.get('store', 'Store')}</span> &nbsp;|&nbsp; 
                <span style="color:#5C4A3E;">Date: {scan.get('date') or 'Today'}</span> &nbsp;|&nbsp;
                <span style="color:#5C4A3E;">Subtotal: {format_currency(scan['subtotal'])} | Tax: {format_currency(scan['tax'])} | Discount: -{format_currency(scan['discount'])}</span>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.85rem; color:#5C4A3E; text-transform:uppercase; letter-spacing:0.05em;">Receipt Grand Total</div>
                <div style="font-size:1.8rem; font-weight:800; color:#7A1F2B; font-family:'Fraunces',serif;">{format_currency(scan['total'])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Member Expense Breakdown")
    
    # Table header
    th1, th2, th3, th4, th5, th6 = st.columns([2.5, 1.5, 1.5, 1.5, 2, 2.5])
    th1.markdown("**Member**")
    th2.markdown("**Items Cost**")
    th3.markdown("**Tax Share**")
    th4.markdown("**Discount**")
    th5.markdown("**Total Share**")
    th6.markdown("**Owed to Shopper**")
    st.markdown("<hr style='margin:0.2rem 0 0.6rem 0; border-color:#E3D6BE;'>", unsafe_allow_html=True)

    for m in summaries:
        r1, r2, r3, r4, r5, r6 = st.columns([2.5, 1.5, 1.5, 1.5, 2, 2.5])
        with r1:
            name_label = f"👤 {m['display_name']}" + (" *(Shopper)*" if m['is_shopper'] else "")
            st.markdown(f"**{name_label}**<br><span style='font-size:0.8rem; color:#5C4A3E;'>{m['items_count']} items</span>", unsafe_allow_html=True)
        with r2:
            st.write(format_currency(m["subtotal"]))
        with r3:
            st.write(format_currency(m["tax_share"]))
        with r4:
            st.write(f"-{format_currency(m['discount_share'])}")
        with r5:
            st.markdown(f"<span style='font-weight:700;'>{format_currency(m['net_total_share'])}</span>", unsafe_allow_html=True)
        with r6:
            if m["is_shopper"]:
                st.markdown("<span style='color:#5C4A3E; font-style:italic;'>Own purchase (paid)</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='font-weight:700; color:#C8963E; font-size:1.1rem;'>Owes {format_currency(m['owed_to_shopper'])}</span>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:1rem 0; border-color:#E3D6BE;'>", unsafe_allow_html=True)

    # Reconciliation Check
    reconciled_sum = split_result["reconciled_sum"]
    if reconciled_sum == scan["total"]:
        st.success(f"⚖️ Perfect Balance: Sum of all member shares ({format_currency(reconciled_sum)}) equals receipt total ({format_currency(scan['total'])}).")
    else:
        st.warning(f"Reconciliation difference: {format_currency(reconciled_sum)} vs {format_currency(scan['total'])}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Confirm & Save Atomic Execution
    cb1, cb2 = st.columns([1, 3])
    with cb1:
        if st.button("← Back to Attribution"):
            st.session_state["scan_step"] = 3
            st.rerun()

    with cb2:
        # Prevent double submission
        is_already_confirmed = st.session_state.get("confirmed_receipt_id") is not None
        button_disabled = st.session_state["is_submitting"] or is_already_confirmed

        if st.button("✅ Confirm & Split Expense", type="primary", disabled=button_disabled):
            st.session_state["is_submitting"] = True
            
            # Collect matched grocery items to mark purchased
            purchased_g_ids = []
            all_line_items = []

            for m_item in matched_items:
                for a in m_item.get("assignments", []):
                    if a.get("grocery_item_id"):
                        purchased_g_ids.append(a["grocery_item_id"])

                all_line_items.append({
                    "name": m_item["name"],
                    "quantity": m_item["receipt_quantity"],
                    "unit_price": m_item["unit_price"],
                    "line_total": m_item["line_total"],
                    "matched_grocery_item_id": m_item["assignments"][0].get("grocery_item_id") if m_item["assignments"] else None,
                    "is_extra": False,
                    "assignments": m_item["assignments"],
                })

            for e_item in extra_items:
                all_line_items.append({
                    "name": e_item["name"],
                    "quantity": e_item["quantity"],
                    "unit_price": e_item["unit_price"],
                    "line_total": e_item["line_total"],
                    "matched_grocery_item_id": None,
                    "is_extra": True,
                    "assignments": e_item["assignments"],
                })

            try:
                with st.spinner("💾 Committing receipt, grocery status, and debts atomically..."):
                    result = confirm_receipt_transaction(
                        room_id=room_id,
                        uploaded_by=user_id,
                        store=scan["store"],
                        receipt_date=scan["date"],
                        subtotal=scan["subtotal"],
                        tax=scan["tax"],
                        discount=scan["discount"],
                        other_charges=scan["other_charges"],
                        total=scan["total"],
                        image_path=scan["image_path"],
                        items=all_line_items,
                        payments=debts,
                        purchased_grocery_ids=purchased_g_ids,
                    )

                st.session_state["confirmed_receipt_id"] = result.get("receipt_id")
                st.session_state["is_submitting"] = False
                st.success(f"🎉 Receipt #{result.get('receipt_id')} saved and expenses recorded successfully!")
                
                # Navigate to Payments page
                st.balloons()
                if st.button("💳 View Updated Debts on Payments Page", type="primary"):
                    st.session_state["scan_data"] = None
                    st.session_state["scan_step"] = 1
                    st.switch_page("pages/11_Payments.py")
            except Exception as exc:
                st.session_state["is_submitting"] = False
                st.error(f"❌ Failed to confirm receipt: {exc}")