"""
components/sidebar.py
=====================
GrocEase sidebar navigation component.

Renders the branded sidebar with:
- Logo / user greeting
- Page navigation links
- Current room indicator
- Logout button

Usage:
    from components.sidebar import render_sidebar
    render_sidebar()
"""

import streamlit as st
from utils.session import get_username, get_current_room_name


# Navigation items: (label, emoji, page_path)
NAV_ITEMS = [
    ("Dashboard",         "📊", "pages/06_Dashboard.py"),
    ("Rooms",             "🏠", "pages/07_Rooms.py"),
    ("Grocery List",      "🛒", "pages/08_Grocery_List.py"),
    ("Shopping",          "🧺", "pages/09_Shopping.py"),
    ("Bill Scanning",     "📷", "pages/10_Bill_Scanning.py"),
    ("Payments",          "💳", "pages/11_Payments.py"),
    ("Personal Expenses", "📝", "pages/12_Personal_Expenses.py"),
    ("Budget",            "🎯", "pages/13_Budget.py"),
    ("Profile",           "👤", "pages/14_Profile.py"),
]

_SIDEBAR_CSS = """
<style>
/* Hide Streamlit's auto-generated multipage nav */
[data-testid="stSidebarNav"] { display: none !important; }

/* Sidebar base */
[data-testid="stSidebar"] {
    background-color: #1F4C3D !important;
    min-width: 220px !important;
}
[data-testid="stSidebar"] * {
    color: #000000 !important;
}

/* Sidebar logo */
.sb-logo {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.55rem;
    font-weight: 700;
    color: #000000;
    letter-spacing: -0.02em;
    margin-bottom: 0.1rem;
}
.sb-tagline {
    font-size: 0.76rem;
    color: #000000;
    margin-bottom: 1.2rem;
}
.sb-divider {
    border: none;
    border-top: 1px solid rgba(0,0,0,0.15);
    margin: 0.8rem 0;
}
.sb-section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #000000;
    margin: 1rem 0 0.4rem 0;
}
.sb-user-chip {
    background: rgba(0,0,0,0.06);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.83rem;
    font-weight: 600;
    color: #000000;
    display: inline-block;
    margin-bottom: 0.6rem;
}
.sb-room-chip {
    background: rgba(169,122,31,0.25);
    border: 1px solid rgba(169,122,31,0.5);
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 0.78rem;
    color: #000000;
    display: inline-block;
    margin-top: 0.2rem;
}

/* Nav links in sidebar */
[data-testid="stSidebar"] [data-testid="stPageLink"] a,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
    color: #000000 !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    padding: 6px 0 !important;
    display: block;
    text-decoration: none !important;
    border-radius: 4px;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
    color: #000000 !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover p {
    color: #000000 !important;
    text-decoration: underline !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background-color: transparent !important;
    color: #000000 !important;
    border: 1px solid rgba(0,0,0,0.25) !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 0.8rem !important;
    width: 100%;
    text-align: left;
    margin-top: 0.3rem;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(0,0,0,0.05) !important;
}
</style>
"""


def render_sidebar():
    """
    Render the GrocEase sidebar navigation.
    Call this at the top of every protected page.
    """
    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)

    with st.sidebar:
        # ── Logo ──────────────────────────────────────
        st.markdown(
            '<div class="sb-logo">🛒 GrocEase</div>'
            '<div class="sb-tagline">Shop together. Split smarter.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── User chip ─────────────────────────────────
        username = get_username()
        st.markdown(
            f'<div class="sb-user-chip">👤 {username}</div>',
            unsafe_allow_html=True,
        )

        # ── Active room chip ──────────────────────────
        room_name = get_current_room_name()
        if room_name:
            st.markdown(
                f'<div class="sb-room-chip">🏠 {room_name}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── Navigation ────────────────────────────────
        st.markdown('<div class="sb-section-label">Navigation</div>', unsafe_allow_html=True)

        for label, emoji, path in NAV_ITEMS:
            st.page_link(path, label=f"{emoji}  {label}")

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── Logout ────────────────────────────────────
        if st.button("🚪  Logout", key="sidebar_logout_btn"):
            st.switch_page("pages/05_Logout.py")
