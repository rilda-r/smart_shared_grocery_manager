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
st.markdown("<p style='color:#5B6459; margin-top:-0.8rem;'>Set monthly spending limits, inspect historical archives, and run month-end reports.</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#D8D0BE; margin:0.5rem 0 1.5rem 0;'>", unsafe_allow_html=True)


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


# ── Tabs Navigation ───────────────────────────────────────────────────────────
tab_active, tab_history, tab_archive = st.tabs([
    "📊 Active Budgets",
    "📜 Monthly History Dashboard",
    "🗓️ Month-End Calculation & Archiving",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: ACTIVE BUDGETS
# ─────────────────────────────────────────────────────────────────────────────
with tab_active:
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
        left_col, right_col = st.columns([1.2, 1], gap="large")

        with left_col:
            st.markdown("### Budget Progress")
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
            st.markdown("### Budget Utilization Chart")
            render_budget_utilization_chart(budgets, dict(spending_by_cat))

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Active Summary")
            total_limit = sum(b["monthlyLimit"] for b in budgets)
            total_spent = sum(spending_by_cat.get(b["category"], 0.0) for b in budgets)
            total_remaining = total_limit - total_spent

            sc1, sc2 = st.columns(2)
            sc1.metric("Total Budget", format_currency(total_limit))
            sc2.metric("Total Spent",  format_currency(total_spent))
            st.metric("Remaining",     format_currency(max(total_remaining, 0)))


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: MONTHLY HISTORY DASHBOARD (GOAL 5)
# ─────────────────────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📜 Monthly Budget History Dashboard")
    st.markdown("<p style='color:#5B6459; font-size:0.9rem;'>Visual tracker of archived past months, spending patterns, and cumulative savings.</p>", unsafe_allow_html=True)

    history_records = fetch_budget_history(user_id)

    if not history_records:
        render_empty_state("📜", "No Monthly History Yet", "Use the 'Month-End Calculation & Archiving' tab to archive your first month.")
    else:
        # Cumulative KPIs
        hist_total_budget = sum(r.get("totalBudget", 0) for r in history_records)
        hist_total_spent  = sum(r.get("totalSpent", 0) for r in history_records)
        hist_total_saved  = sum(r.get("totalSaved", 0) for r in history_records)
        hist_savings_rate = (hist_total_saved / hist_total_budget * 100) if hist_total_budget > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Historical Budget", format_currency(hist_total_budget))
        k2.metric("Historical Spent", format_currency(hist_total_spent))
        k3.metric("Total Saved", format_currency(hist_total_saved), delta=f"{hist_savings_rate:.1f}%")
        k4.metric("Archived Months", f"{len(history_records)} months")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📈 Historical Spending vs. Savings Trends")
        render_monthly_history_chart(history_records)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🗂️ Archived Month Records")
        for rec in history_records:
            m_yr = rec.get("monthYear", "Unknown")
            b_val = rec.get("totalBudget", 0)
            s_val = rec.get("totalSpent", 0)
            sv_val = rec.get("totalSaved", 0)
            pct_saved = (sv_val / b_val * 100) if b_val > 0 else 0
            badge_color = "#1F4C3D" if sv_val >= 0 else "#9C4B3E"
            badge_bg = "#E7EFE6" if sv_val >= 0 else "#FBEBE8"
            status_text = f"+{format_currency(sv_val)} saved ({pct_saved:.1f}%)" if sv_val >= 0 else f"-{format_currency(abs(sv_val))} over budget"

            with st.expander(f"📅 **{m_yr}** — Budget: {format_currency(b_val)} | Spent: {format_currency(s_val)} ({status_text})"):
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Budget Limit", format_currency(b_val))
                col_m2.metric("Total Spent", format_currency(s_val))
                col_m3.metric("Net Saved", format_currency(sv_val), delta=f"{pct_saved:.1f}%" if sv_val >= 0 else f"-{abs(pct_saved):.1f}%")

                cat_bd = rec.get("categoryBreakdown", {})
                if cat_bd:
                    st.markdown("**Category Breakdown:**")
                    bd_cols = st.columns(min(len(cat_bd), 4) or 1)
                    for idx, (cname, cinfo) in enumerate(cat_bd.items()):
                        with bd_cols[idx % len(bd_cols)]:
                            if isinstance(cinfo, dict):
                                st.markdown(
                                    f"<div style='background:#FDFBF7; border:1px solid #D8D0BE; border-radius:6px; padding:0.6rem; margin-bottom:0.4rem;'>"
                                    f"<strong>{cname}</strong><br>"
                                    f"<small>Spent: {format_currency(cinfo.get('spent', 0))}</small><br>"
                                    f"<small>Limit: {format_currency(cinfo.get('limit', 0))}</small><br>"
                                    f"<small style='color:{FOREST if cinfo.get('saved', 0) >= 0 else RUST}; font-weight:600;'>"
                                    f"Saved: {format_currency(cinfo.get('saved', 0))}</small>"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: MONTH-END CALCULATION & ARCHIVING (GOAL 6)
# ─────────────────────────────────────────────────────────────────────────────
with tab_archive:
    st.markdown("### 🗓️ Month-End Calculation & Archiving")
    st.markdown(
        "<p style='color:#5B6459; font-size:0.9rem;'>"
        "Compile this month's budget usage report, archive it forever to Supabase, "
        "and cleanly reset active data for the new calendar month."
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

    # 1. Compile numerical summary
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

    st.markdown("#### 📊 Month-End Numerical Summary")
    ms1, ms2, ms3, ms4 = st.columns(4)
    ms1.metric("Total Budget Allocated", format_currency(calc_budget))
    ms2.metric("Total Amount Spent", format_currency(calc_spent))
    ms3.metric(
        "Net Saved vs. Used",
        format_currency(calc_saved),
        delta=f"{calc_rate:.1f}% saved" if calc_saved >= 0 else "Over budget",
    )
    ms4.metric("Savings Efficiency", f"{calc_rate:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 📉 Visual Representation: Used vs. Saved")
    render_month_end_summary_chart(category_summary)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#D8D0BE; margin:1rem 0;'>", unsafe_allow_html=True)

    # 2. Action Buttons: Archive to Supabase & Reset Modal
    st.markdown("#### ⚡ Archiving & Month-End Actions")
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

    # 3. Clean Reset Modal
    if st.session_state.get("show_month_reset_modal", False):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background:#FFF9E6; border:2px solid #E6D080; border-radius:8px; padding:1.4rem;">
                <h4 style="margin:0 0 0.5rem 0; color:#856404;">⚠️ Confirm New Month Reset</h4>
                <p style="margin:0 0 0.8rem 0; color:#333;">
                    Are you sure you want to clear active expense data for <strong>{archive_month.strip()}</strong>?
                    <br><br>
                    • This will permanently save your <strong>{archive_month.strip()}</strong> report to Supabase history.<br>
                    • Active personal expenses will be cleared out so you start fresh for the new month.<br>
                    • Your configured budget limits will remain intact.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("✅ Yes, Archive & Clear Active Data", type="primary", key="confirm_reset_btn", use_container_width=True):
                # Save archive first
                do_save_archive(
                    user_id,
                    archive_month.strip(),
                    float(calc_budget),
                    float(calc_spent),
                    float(calc_saved),
                    category_summary,
                )
                # Clear active data
                do_reset_active(user_id)
                st.session_state["show_month_reset_modal"] = False
                st.balloons()
                st.success(f"🎉 Active data cleared! {archive_month.strip()} archived. Welcome to the new month!")
                st.rerun()
        with rc2:
            if st.button("Cancel", key="cancel_reset_btn", use_container_width=True):
                st.session_state["show_month_reset_modal"] = False
                st.rerun()

