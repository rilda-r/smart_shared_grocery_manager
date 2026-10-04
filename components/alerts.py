"""
components/alerts.py
====================
Alert and confirmation dialog helpers.
"""

import streamlit as st


def success_alert(msg: str):
    st.success(msg)


def error_alert(msg: str):
    st.error(msg)


def warning_alert(msg: str):
    st.warning(msg)


def info_alert(msg: str):
    st.info(msg)


def confirmation_dialog(key: str, prompt: str, confirm_label: str = "Confirm", cancel_label: str = "Cancel") -> bool | None:
    """
    Render an inline confirmation dialog.

    Returns:
        True  — user clicked confirm
        False — user clicked cancel
        None  — neither clicked yet
    """
    confirm_key = f"{key}_confirm"
    cancel_key  = f"{key}_cancel"

    st.warning(prompt)
    col_confirm, col_cancel = st.columns([1, 1])
    with col_confirm:
        if st.button(confirm_label, key=confirm_key, type="primary"):
            return True
    with col_cancel:
        if st.button(cancel_label, key=cancel_key):
            return False
    return None


def permission_error(action: str = "modify this item"):
    """Display a standard permission-denied message."""
    st.markdown(
        f"""
        <div style="background:#FDE8E4; border:1px solid #9C4B3E; border-radius:6px;
                    padding:0.8rem 1.2rem; color:#9C4B3E; font-size:0.9rem;">
            🔒 You don't have permission to {action}.
        </div>
        """,
        unsafe_allow_html=True,
    )
