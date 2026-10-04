"""
components/payment_table.py
===========================
Payment records table component.
"""

import streamlit as st
from utils.formatting import format_currency, format_datetime, badge_html
from mock.mock_data import get_username


def render_payment_table(
    payments: list,
    current_user_id: int,
    on_settle=None,
    on_report=None,
    key_prefix: str = "",
):
    """
    Render payment records.

    Args:
        payments: list of Payment dicts
        current_user_id: logged-in user id
        on_settle: callback(payment_id)
        on_report: callback(payment_id)
        key_prefix: optional string prefix to guarantee element key uniqueness across tabs/sections
    """
    if not payments:
        st.markdown(
            """
            <div style="text-align:center; padding:2rem; color:#5B6459;">
                <div style="font-size:2.5rem;">💳</div>
                <div style="font-weight:600; color:#20261F; margin-top:0.5rem;">No payments yet</div>
                <div style="font-size:0.88rem; margin-top:0.3rem;">Payments appear after a bill is split.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    headers = ["Payer", "Payee", "Amount", "Status", "Date", "Actions"]
    header_cols = st.columns([2, 2, 2, 2, 3, 2])
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")
    st.markdown("<hr style='margin:0.3rem 0 0.5rem 0; border-color:#D8D0BE;'>", unsafe_allow_html=True)

    for idx, p in enumerate(payments):
        row = st.columns([2, 2, 2, 2, 3, 2])
        row[0].write(get_username(p.get("payerUserId")))
        row[1].write(get_username(p.get("payeeUserId")))
        row[2].write(format_currency(float(p.get("amount", 0.0))))
        row[3].markdown(badge_html(p.get("paymentStatus", "pending")), unsafe_allow_html=True)
        row[4].write(format_datetime(p.get("createdAt", "")))

        with row[5]:
            status = p.get("paymentStatus")
            pid = p.get("id", idx)
            if status == "pending":
                # Payer can settle; either party can report
                if p.get("payerUserId") == current_user_id and on_settle:
                    if st.button("✅ Settle", key=f"{key_prefix}settle_{pid}_{idx}"):
                        on_settle(pid)
                if on_report:
                    if st.button("⚠️ Report", key=f"{key_prefix}report_{pid}_{idx}"):
                        on_report(pid)
            else:
                st.write("—")
