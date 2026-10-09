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
            <div style="background:#FFFFFF; border:1.5px dashed rgba(163, 150, 112, 0.45); border-radius:18px;
                        text-align:center; padding:2.5rem 1rem; color:#6B5A47; box-shadow:0 2px 8px rgba(55,39,19,0.02);">
                <div style="font-size:2.8rem; margin-bottom:0.4rem;">💳</div>
                <div style="font-family:'Fraunces',Georgia,serif; font-size:1.1rem; font-weight:700; color:#372713;">No payments yet</div>
                <div style="font-size:0.88rem; color:#6B5A47; margin-top:0.3rem;">Payments appear after a bill is split in your rooms.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    headers = ["Payer", "Payee", "Amount", "Status", "Date", "Actions"]
    header_cols = st.columns([2, 2, 2, 2, 3, 2])
    for col, h in zip(header_cols, headers):
        col.markdown(f"<span style='font-size:0.82rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#A39670;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:0.4rem 0 0.8rem 0; border:none; border-top:1.5px solid rgba(163, 150, 112, 0.35);'>", unsafe_allow_html=True)

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
