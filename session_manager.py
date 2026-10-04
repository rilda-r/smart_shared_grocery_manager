import time
import streamlit as st

try:
    from config.settings import get_settings
    INACTIVITY_TIMEOUT_SECONDS = get_settings().session_ttl_seconds
except Exception:
    INACTIVITY_TIMEOUT_SECONDS = 28800  # 8 hours default


def check_session_timeout():
    """Handles global inactivity timeout for logged-in sessions."""
    if st.session_state.get("logged_in", False) or st.session_state.get("is_authenticated", False):
        now = time.time()
        last = st.session_state.get("last_activity", now)
        if now - last > INACTIVITY_TIMEOUT_SECONDS:
            from utils.session import logout_user
            logout_user()
            st.session_state["session_expired"] = True
            st.switch_page("pages/05_Logout.py")
        else:
            st.session_state.last_activity = now