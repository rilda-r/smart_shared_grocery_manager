import time
import streamlit as st

INACTIVITY_TIMEOUT_SECONDS = 180

def check_session_timeout():
    """Handles global inactivity timeout for logged-in sessions."""
    if st.session_state.get("logged_in", False):
        now = time.time()
        last = st.session_state.get("last_activity", now)
        if now - last > INACTIVITY_TIMEOUT_SECONDS:
            st.session_state.logged_in = False
            st.session_state.pop("user_email", None)
            st.session_state.pop("user_name", None)
            st.session_state.pop("last_activity", None)
            st.session_state["session_expired"] = True
            st.switch_page("pages/05_Logout.py")
        else:
            st.session_state.last_activity = now