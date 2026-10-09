"""
pages/14_Profile.py
====================
User profile page — identity details (Actual Name & dynamic Nickname stored in Supabase profiles),
Password Reset, and cascading Delete Account with confirmation dialog.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from style import apply_base_style
from utils.session import require_auth, get_current_user_id, get_username, logout_user
from components.sidebar import render_sidebar
from components.cards import render_metric_card
from database.database import (
    get_profile,
    update_nickname,
    update_password,
    delete_user_account,
    get_user_by_id,
    get_user_joined_rooms,
)
from security.password_hash import verify_password, hash_password, password_strength

st.set_page_config(
    page_title="Profile — GrocEase",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id = get_current_user_id()
profile = get_profile(user_id) or {}
user_db = get_user_by_id(user_id) or {}

actual_name = profile.get("actual_name") or user_db.get("full_name") or "User"
nickname = profile.get("nickname") or user_db.get("nickname") or get_username()
email = user_db.get("email") or st.session_state.get("user_email", "")

st.markdown("# 👤 My Profile")
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Profile layout ────────────────────────────────────────────────────────────
left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    # Avatar badge
    initial = (nickname[0] if nickname else actual_name[0]).upper()
    st.markdown(
        f"""
        <div style="background:#5C0203; color:#FFFFFF; border-radius:50%;
                    width:92px; height:92px; display:flex; align-items:center;
                    justify-content:center; font-family:'Fraunces',Georgia,serif;
                    font-size:2.6rem; font-weight:700; margin-bottom:1rem; box-shadow:0 6px 18px rgba(92,2,3,0.25);">
            {initial}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="margin-bottom:0.8rem;">
            <div style="font-family:'Fraunces',Georgia,serif; font-size:1.55rem; font-weight:700;
                        color:#5C0203;">{nickname}</div>
            <div style="font-size:0.92rem; color:#372713; font-weight:600;">Legal Name: {actual_name}</div>
            <div style="font-size:0.85rem; color:#6B5A47;">{email}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Activity Stats
    db_rooms = get_user_joined_rooms(user_id) or []
    rooms_count = len(db_rooms)
    from services.personal_expense_service import get_personal_expenses as svc_get_personal_expenses
    from services.budget_service import get_budgets as svc_get_budgets
    exp_res = svc_get_personal_expenses(user_id)
    expenses_count = len(exp_res.get("data", [])) if exp_res and exp_res.get("success") else 0
    bg_res = svc_get_budgets(user_id)
    budgets_count = len(bg_res.get("data", [])) if bg_res and bg_res.get("success") else 0

    st.markdown("<br>", unsafe_allow_html=True)
    render_metric_card("Rooms Joined", str(rooms_count))
    render_metric_card("Total Expenses", str(expenses_count))
    render_metric_card("Budgets Set", str(budgets_count))

with right_col:
    # ── Section 1: User Identity (Actual Name + Dynamic Nickname) ─────────────
    st.markdown("### 🪪 Identity & Public Profile")
    st.markdown(
        "<p class='groc-muted' style='font-size:0.88rem; margin-top:-0.5rem;'>"
        "Your dynamic Nickname is displayed publicly across rooms, lists, and activity."
        "</p>",
        unsafe_allow_html=True,
    )

    with st.form("edit_identity_form"):
        st.text_input("Actual Name (from registration)", value=actual_name, disabled=True)
        st.text_input("Registered Email", value=email, disabled=True)
        st.caption("Email address cannot be changed after account creation.")

        new_nick_input = st.text_input(
            "Public Nickname",
            value=nickname,
            placeholder="Choose your public nickname",
            help="This is the name visible to other roommates.",
        )

        submit_nick = st.form_submit_button("Update Nickname", type="primary")

        if submit_nick:
            cleaned_nick = new_nick_input.strip()
            if len(cleaned_nick) < 2 or len(cleaned_nick) > 30:
                st.error("Nickname must be between 2 and 30 characters.")
            else:
                update_nickname(user_id, cleaned_nick)
                st.session_state["nickname"] = cleaned_nick
                st.session_state["username"] = cleaned_nick
                st.session_state["user_name"] = cleaned_nick
                st.success(f"✅ Nickname updated to **{cleaned_nick}**!")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 2: Password Reset ─────────────────────────────────────────────
    st.markdown("### 🔑 Password Reset")
    st.markdown(
        "<p class='groc-muted' style='font-size:0.88rem; margin-top:-0.5rem;'>"
        "Securely change your account password."
        "</p>",
        unsafe_allow_html=True,
    )

    if "pw_reset_success_msg" in st.session_state:
        st.success(st.session_state.pop("pw_reset_success_msg"))

    pw_form_ver = st.session_state.get("pw_form_ver", 0)
    with st.form(f"password_reset_form_{pw_form_ver}"):
        curr_pw = st.text_input("Current Password", type="password", placeholder="Enter current password")
        new_pw = st.text_input("New Password", type="password", placeholder="Create new strong password")
        conf_pw = st.text_input("Confirm New Password", type="password", placeholder="Re-enter new password")

        pw_submitted = st.form_submit_button("Update Password", type="primary")

        if pw_submitted:
            errs = []
            if not curr_pw or not new_pw or not conf_pw:
                errs.append("All password fields are required.")
            elif not verify_password(curr_pw, user_db.get("password_hash", "")):
                errs.append("Current password is incorrect.")
            elif not password_strength(new_pw)["valid"]:
                errs.append("New password must be at least 8 characters and include uppercase, lowercase, number, and special character.")
            elif new_pw != conf_pw:
                errs.append("New passwords do not match.")

            if errs:
                for e in errs:
                    st.error(e)
            else:
                hashed = hash_password(new_pw)
                update_password(email, hashed)
                # Increment key so inputs clear completely on successful update
                st.session_state["pw_form_ver"] = pw_form_ver + 1
                st.session_state["pw_reset_success_msg"] = "✅ Password successfully updated!"
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 3: Danger Zone & Cascading Account Deletion ───────────────────
    st.markdown("### ⚠️ Danger Zone")
    st.markdown(
        """
        <div style="background:#FFF6F6; border:1.5px solid rgba(92,2,3,0.3); border-radius:18px; padding:1.3rem; margin-bottom:1rem; box-shadow:0 4px 14px rgba(92,2,3,0.04);">
            <div style="font-weight:700; color:#5C0203; margin-bottom:0.3rem;">Permanent Account Deletion</div>
            <div style="font-size:0.88rem; color:#6B5A47;">
                Deleting your account will permanently remove your profile, created rooms, room memberships,
                payments, personal expenses, and budgets with cascading deletion.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "confirm_delete_account_active" not in st.session_state:
        st.session_state["confirm_delete_account_active"] = False

    if not st.session_state["confirm_delete_account_active"]:
        col_del, col_out = st.columns([1.2, 1])
        with col_del:
            st.markdown('<div class="groc-danger">', unsafe_allow_html=True)
            if st.button("🗑️ Delete Account", key="btn_trigger_delete_account"):
                st.session_state["confirm_delete_account_active"] = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_out:
            st.markdown('<div class="groc-secondary">', unsafe_allow_html=True)
            if st.button("🚪 Logout", key="profile_logout_btn"):
                st.switch_page("pages/05_Logout.py")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Confirmation Dialog Box
        st.markdown(
            """
            <div style="background:#FFF0EE; border:2px solid #9C4B3E; border-radius:8px; padding:1.2rem; margin-bottom:1rem;">
                <h4 style="color:#9C4B3E; margin:0 0 0.5rem 0;">⚠️ Are you absolutely sure?</h4>
                <p style="color:#20261F; font-size:0.92rem; margin-bottom:0.5rem;">
                    This action CANNOT be undone. All your data in Supabase will be permanently deleted with cascading effect.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c_yes, c_no = st.columns(2)
        with c_yes:
            st.markdown('<div class="groc-danger">', unsafe_allow_html=True)
            if st.button("🔥 Yes, Delete My Account", key="btn_confirm_delete_yes", type="primary"):
                delete_user_account(user_id)
                logout_user()
                st.session_state["registration_success_message"] = "Your account and all associated records have been permanently deleted."
                st.switch_page("pages/01_Login.py")
            st.markdown("</div>", unsafe_allow_html=True)
        with c_no:
            if st.button("Cancel", key="btn_confirm_delete_no"):
                st.session_state["confirm_delete_account_active"] = False
                st.rerun()
