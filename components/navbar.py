"""
components/navbar.py
====================
Top navigation bar and visual browser-style navigation controls.
"""

import streamlit as st


def render_browser_nav_controls():
    """Renders visual, browser-style 'Back' and 'Forward' buttons."""
    st.markdown(
        """
        <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:0.75rem;">
            <button onclick="window.history.back()" title="Go Back" style="
                background: #FFFFFF;
                color: #1F4C3D;
                border: 1.5px solid #C3D6C6;
                border-radius: 50%;
                width: 34px;
                height: 34px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 18px;
                font-weight: 700;
                box-shadow: 0 2px 5px rgba(0,0,0,0.06);
                transition: all 0.15s ease;"
                onmouseover="this.style.background='#E7EFE6'; this.style.borderColor='#1F4C3D';"
                onmouseout="this.style.background='#FFFFFF'; this.style.borderColor='#C3D6C6';">
                ‹
            </button>
            <button onclick="window.history.forward()" title="Go Forward" style="
                background: #FFFFFF;
                color: #1F4C3D;
                border: 1.5px solid #C3D6C6;
                border-radius: 50%;
                width: 34px;
                height: 34px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 18px;
                font-weight: 700;
                box-shadow: 0 2px 5px rgba(0,0,0,0.06);
                transition: all 0.15s ease;"
                onmouseover="this.style.background='#E7EFE6'; this.style.borderColor='#1F4C3D';"
                onmouseout="this.style.background='#FFFFFF'; this.style.borderColor='#C3D6C6';">
                ›
            </button>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_navbar():
    st.markdown(
        """
        <div class="groc-nav" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div class="groc-logo">GrocEase</div>
                <div class="groc-tagline">Shop together. Split smarter.</div>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                <button onclick="window.history.back()" title="Back" style="background:#FFFFFF; border:1px solid #C3D6C6; border-radius:50%; width:32px; height:32px; cursor:pointer; color:#1F4C3D; font-weight:bold;">‹</button>
                <button onclick="window.history.forward()" title="Forward" style="background:#FFFFFF; border:1px solid #C3D6C6; border-radius:50%; width:32px; height:32px; cursor:pointer; color:#1F4C3D; font-weight:bold;">›</button>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
