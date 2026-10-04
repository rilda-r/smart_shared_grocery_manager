"""
components/navbar.py
====================
Top navigation bar (used on login/public pages only).
For authenticated pages, use sidebar.py instead.
"""

import streamlit as st


def render_navbar():
    st.markdown(
        """
        <div class="groc-nav">
            <div>
                <div class="groc-logo">GrocEase</div>
                <div class="groc-tagline">Shop together. Split smarter.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
