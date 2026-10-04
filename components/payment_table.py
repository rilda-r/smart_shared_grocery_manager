"""
components/payment_table.py
===========================
Payment records table component.
"""

import streamlit as st
from utils.formatting import format_currency, format_datetime, badge_html
from mock.mock_data import get_username


def render_payment_table(payments: list, current_user_id: int, on_settle=None, on_report=None):
    """
    Render payment records.

    Args:
        payments: list of Payment dicts
        current_user_id: logged-in user id
        on_settle: callback(payment_id)
        on_report: callback(payment_id)
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

    for p in payments:
        row = st.columns([2, 2, 2, 2, 3, 2])
        row[0].write(get_username(p["payerUserId"]))
        row[1].write(get_username(p["payeeUserId"]))
        row[2].write(format_currency(p["amount"]))
        row[3].markdown(badge_html(p["paymentStatus"]), unsafe_allow_html=True)
        row[4].write(format_datetime(p["createdAt"]))

        with row[5]:
            status = p["paymentStatus"]
            if status == "pending":
                # Payer can settle; either party can report
                if p["payerUserId"] == current_user_id and on_settle:
                    if st.button("✅ Settle", key=f"settle_{p['id']}"):
                        on_settle(p["id"])
                if on_report:
                    if st.button("⚠️ Report", key=f"report_{p['id']}"):
                        on_report(p["id"])
            else:
                st.write("—")
