"""
pages/13_Budget.py
==================
Budget page — set, edit, and delete monthly category budgets with
progress indicators and over-budget alerts.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from collections import defaultdict

from style import apply_base_style
from utils.session import require_auth, get_current_user_id
from utils.formatting import format_currency
from components.sidebar import render_sidebar
from components.cards import render_empty_state
from components.budget_progress import render_budget_progress
from components.forms import render_add_budget_form
from components.charts import render_budget_utilization_chart
from datetime import datetime
from database.database import (
    get_monthly_budget_history,
    save_monthly_budget_history,
    reset_active_monthly_data,
)
from services.budget_service import (
    get_budgets as svc_get_budgets,
    create_budget as svc_create_budget,
    update_budget as svc_update_budget,
    delete_budget as svc_delete_budget,
)
from services.personal_expense_service import get_personal_expenses as svc_get_personal_expenses
from components.charts import (
    render_budget_utilization_chart,
    render_monthly_history_chart,
    render_month_end_summary_chart,
)

st.set_page_config(
    page_title="Budget — GrocEase",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_base_style()
require_auth()
render_sidebar()

user_id = get_current_user_id()

st.markdown("# 🎯 Budget Manager")
st.markdown("<p style='color:#4A6568; margin-top:-0.8rem;'>Set monthly category limits, monitor active utilization, and inspect visual month-end analytics on a single screen.</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#CADDD8; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)


# ── Data Loading from Database ────────────────────────────────────────────────
def load_budgets(uid: int) -> list:
    res = svc_get_budgets(uid)
    if res and res.get("success"):
        return [
            {
                "id": b["id"],
                "userId": b.get("user_id", uid),
                "category": b["category"],
                "monthlyLimit": float(b.get("monthly_limit", 0)),
            }
            for b in res.get("data", [])
        ]
    return []


def load_expenses(uid: int) -> list:
    res = svc_get_personal_expenses(uid)
    if res and res.get("success"):
        return [
            {
                "id": e["id"],
                "amount": float(e["amount"]),
                "category": e["category"],
            }
            for e in res.get("data", [])
        ]
    return []


budgets  = load_budgets(user_id)
expenses = load_expenses(user_id)

spending_by_cat = defaultdict(float)
for e in expenses:
    spending_by_cat[e["category"]] += e["amount"]

existing_cats = [b["category"] for b in budgets]


def fetch_budget_history(uid: int) -> list:
    """Fetch history from Supabase."""
    try:
        return get_monthly_budget_history(uid) or []
    except Exception:
        return []


def do_save_archive(uid: int, month_yr: str, tot_b: float, tot_sp: float, tot_sv: float, breakdown: dict) -> bool:
    """Persist static month-end report in Supabase."""
    try:
        return save_monthly_budget_history(uid, month_yr, tot_b, tot_sp, tot_sv, breakdown)
    except Exception:
        return False


def do_reset_active(uid: int) -> bool:
    """Clear active expenses for new month in Supabase."""
    try:
        return reset_active_monthly_data(uid)
    except Exception:
        return False


# ── Month-End Calculations (Co-located on Main Dashboard) ─────────────────────
calc_budget = sum(b["monthlyLimit"] for b in budgets)
calc_spent  = sum(spending_by_cat.get(b["category"], 0.0) for b in budgets)
calc_saved  = calc_budget - calc_spent
calc_rate   = (calc_saved / calc_budget * 100) if calc_budget > 0 else 0

category_summary = {}
for b in budgets:
    c_spent = spending_by_cat.get(b["category"], 0.0)
    c_saved = b["monthlyLimit"] - c_spent
    category_summary[b["category"]] = {
        "limit": float(b["monthlyLimit"]),
        "spent": float(c_spent),
        "saved": float(c_saved),
    }

# ── Month-End Numerical Summary KPI Row ────────────────────────────────────────
st.markdown("### 📊 Month-End Numerical Summary")
ms1, ms2, ms3, ms4 = st.columns(4)
ms1.metric("Total Budget Allocated", format_currency(calc_budget))
ms2.metric("Total Amount Spent", format_currency(calc_spent))
ms3.metric(
    "Net Saved vs. Used",
    format_currency(calc_saved),
    delta=f"{calc_rate:.1f}% saved" if calc_saved >= 0 else "Over budget",
)
ms4.metric("Savings Efficiency", f"{calc_rate:.1f}%")

st.markdown("<hr style='border-color:#CADDD8; margin:1.2rem 0 1.5rem 0;'>", unsafe_allow_html=True)

# ── Main Consolidated Dashboard Grid ──────────────────────────────────────────
left_col, right_col = st.columns([1.15, 1], gap="large")

with left_col:
    st.markdown("### 🎯 Category Budgets")
    
    # Add new category budget form
    new_budget = render_add_budget_form(existing_cats, key_prefix="bg_")
    if new_budget:
        res = svc_create_budget(user_id, new_budget["category"], new_budget["monthlyLimit"])
        if res and res.get("success"):
            st.success(f"✅ Budget set for **{new_budget['category']}**: {format_currency(new_budget['monthlyLimit'])}/month")
            st.rerun()
        else:
            st.error(res.get("message") if res else "Could not set budget.")

    st.markdown("<br>", unsafe_allow_html=True)

    if not budgets:
        render_empty_state("🎯", "No budgets set yet", "Add your first budget using the form above.")
    else:
        st.markdown("#### Active Category Progress")
        for budget in budgets:
            spent = spending_by_cat.get(budget["category"], 0.0)
            render_budget_progress(budget, spent)

            edit_key   = f"edit_budget_{budget['id']}"
            delete_key = f"del_confirm_{budget['id']}"

            col_edit, col_del = st.columns(2)
            with col_edit:
                if st.button("✏️ Edit Limit", key=f"edit_btn_{budget['id']}"):
                    st.session_state[edit_key] = True

            with col_del:
                st.markdown('<div class="groc-danger">', unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_btn_{budget['id']}"):
                    st.session_state[delete_key] = True
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get(edit_key, False):
                with st.form(f"edit_budget_form_{budget['id']}"):
                    new_limit = st.number_input(
                        f"New monthly limit for {budget['category']} (₹)",
                        min_value=1.0,
                        value=float(budget["monthlyLimit"]),
                        step=100.0,
                        format="%.2f",
                    )
                    sc, cc = st.columns(2)
                    with sc:
                        if st.form_submit_button("Save", type="primary"):
                            res_up = svc_update_budget(user_id, budget["id"], monthly_limit=new_limit)
                            if res_up and res_up.get("success"):
                                st.session_state[edit_key] = False
                                st.success("Budget updated.")
                                st.rerun()
                            else:
                                st.error(res_up.get("message") if res_up else "Could not update budget.")
                    with cc:
                        if st.form_submit_button("Cancel"):
                            st.session_state[edit_key] = False
                            st.rerun()

            if st.session_state.get(delete_key, False):
                st.warning(f"Delete budget for **{budget['category']}**?")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("Yes, Delete", key=f"yes_del_{budget['id']}", type="primary"):
                        res_del = svc_delete_budget(user_id, budget["id"])
                        if res_del and res_del.get("success"):
                            st.session_state[delete_key] = False
                            st.success(f"Budget for {budget['category']} deleted.")
                            st.rerun()
                        else:
                            st.error(res_del.get("message") if res_del else "Could not delete budget.")
                with dc2:
                    if st.button("Cancel", key=f"no_del_{budget['id']}"):
                        st.session_state[delete_key] = False
                        st.rerun()

            st.markdown("<hr style='border-color:#EEE; margin:0.3rem 0 1rem 0;'>", unsafe_allow_html=True)

with right_col:
    # Co-located Visual Representation: Used vs. Saved
    st.markdown("### 📉 Visual Breakdown: Used vs. Saved")
    if category_summary:
        render_month_end_summary_chart(category_summary)
    else:
        render_empty_state("📉", "No Category Data", "Set budgets and record expenses to see Used vs. Saved visuals.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Budget Utilization per Category Chart
    st.markdown("### 📊 Budget Utilization per Category")
    if budgets:
        render_budget_utilization_chart(budgets, dict(spending_by_cat))
    else:
        render_empty_state("📊", "No Utilization Data", "Configure budget limits to view utilization bars.")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#CADDD8; margin:1.5rem 0 1.2rem 0;'>", unsafe_allow_html=True)

# ── Archiving & Month-End Actions (Preserved Calculation & State Handlers) ───────
with st.expander("🗓️ Month-End Archiving & Reset Actions", expanded=False):
    st.markdown(
        "<p style='color:#4A6568; font-size:0.9rem; margin-bottom:1rem;'>"
        "Archive this month's finalized report permanently to Supabase, "
        "and cleanly reset active personal expenses for the new calendar month."
        "</p>",
        unsafe_allow_html=True,
    )

    cur_month_str = datetime.now().strftime("%Y-%m")
    col_sel_m, _ = st.columns([1.5, 2])
    with col_sel_m:
        archive_month = st.text_input(
            "Target Calendar Month",
            value=cur_month_str,
            help="Format YYYY-MM (e.g. 2026-10)",
        )

    act_col1, act_col2 = st.columns(2)
    with act_col1:
        if st.button("💾 Save & Archive Report to Supabase", type="primary", use_container_width=True):
            if not archive_month.strip():
                st.error("Please enter a valid month (e.g. 2026-10).")
            else:
                do_save_archive(
                    user_id,
                    archive_month.strip(),
                    float(calc_budget),
                    float(calc_spent),
                    float(calc_saved),
                    category_summary,
                )
                st.success(f"✅ Month-end report for **{archive_month.strip()}** saved forever in Supabase history table!")
                st.rerun()

    with act_col2:
        if st.button("🔄 Reset Active Data for New Month", use_container_width=True):
            st.session_state["show_month_reset_modal"] = True

    # Clean Confirmation Modal
    if st.session_state.get("show_month_reset_modal", False):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background:#FFF9E6; border:2px solid #E6D080; border-radius:12px; padding:1.2rem;">
                <h4 style="margin:0 0 0.5rem 0; color:#856404;">⚠️ Confirm New Month Reset</h4>
                <p style="margin:0 0 0.8rem 0; color:#333; font-size:0.9rem;">
                    Are you sure you want to clear active expense data for <strong>{archive_month.strip()}</strong>?
                    <br><br>
                    • Permanently archives your <strong>{archive_month.strip()}</strong> summary to Supabase.<br>
                    • Active personal expenses will be cleared to start fresh for the new month.<br>
                    • Your configured budget limits remain intact.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("✅ Yes, Archive & Clear Active Data", type="primary", key="confirm_reset_btn", use_container_width=True):
                do_save_archive(
                    user_id,
                    archive_month.strip(),
                    float(calc_budget),
                    float(calc_spent),
                    float(calc_saved),
                    category_summary,
                )
                do_reset_active(user_id)
                st.session_state["show_month_reset_modal"] = False
                st.balloons()
                st.success(f"🎉 Active data cleared! {archive_month.strip()} archived. Welcome to the new month!")
                st.rerun()
        with rc2:
            if st.button("Cancel", key="cancel_reset_btn", use_container_width=True):
                st.session_state["show_month_reset_modal"] = False
                st.rerun()


