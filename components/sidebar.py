"""
components/sidebar.py
=====================
GrocEase sidebar navigation component.

Renders the branded sidebar with:
- Browser-style Back and Forward navigation controls
- Logo / user greeting
- Interactive joined room switcher dropdown
- Page navigation links
- Logout button

Usage:
    from components.sidebar import render_sidebar, render_room_selector
    render_sidebar()
"""

import streamlit as st
from utils.session import (
    get_username,
    get_current_user_id,
    get_current_room_id,
    get_current_room_name,
    set_current_room,
)


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

/* Sleek vertical sidebar panel */
[data-testid="stSidebar"] {
    background-color: #2B1D0F !important;
    background-image: linear-gradient(180deg, #2B1D0F 0%, #372713 100%) !important;
    border-right: 1.5px solid rgba(163, 150, 112, 0.25) !important;
    min-width: 250px !important;
    box-shadow: 4px 0 24px rgba(43, 29, 15, 0.2) !important;
}
[data-testid="stSidebar"] * {
    color: #F5ECE3 !important;
}

/* Sidebar logo */
.sb-logo {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.65rem;
    font-weight: 800;
    color: #FFFFFF !important;
    letter-spacing: -0.02em;
    margin-bottom: 0.15rem;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.sb-tagline {
    font-size: 0.78rem;
    color: #D9C4B1 !important;
    font-weight: 500;
    margin-bottom: 1.3rem;
    letter-spacing: 0.02em;
}
.sb-divider {
    border: none;
    border-top: 1px solid rgba(217, 196, 177, 0.18);
    margin: 0.9rem 0;
}
.sb-section-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #A39670 !important;
    margin: 1.1rem 0 0.45rem 0.4rem;
}
.sb-user-chip {
    background: #D9C4B1 !important;
    border-radius: 24px;
    padding: 6px 14px;
    font-size: 0.85rem;
    font-weight: 700;
    color: #372713 !important;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 0.3rem;
    box-shadow: 0 3px 8px rgba(0,0,0,0.18);
}
.sb-user-chip * {
    color: #372713 !important;
}

/* Nav links in sidebar (pill items with micro-interactions) */
[data-testid="stSidebar"] [data-testid="stPageLink"] {
    margin-bottom: 3px !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
    color: #E8DDD2 !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    padding: 8px 14px !important;
    display: flex !important;
    align-items: center !important;
    text-decoration: none !important;
    border-radius: 12px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a p,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
    color: #E8DDD2 !important;
    font-weight: 500 !important;
    margin: 0 !important;
    transition: color 0.15s ease !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
    background-color: rgba(217, 196, 177, 0.14) !important;
    transform: translateX(4px) !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p,
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover p {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}

/* Sidebar action buttons (e.g. Logout) */
[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(217, 196, 177, 0.08) !important;
    color: #E8DDD2 !important;
    border: 1.5px solid rgba(163, 150, 112, 0.35) !important;
    border-radius: 14px !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    padding: 0.55rem 1rem !important;
    width: 100%;
    text-align: center;
    margin-top: 0.5rem;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #5C0203 !important;
    border-color: #5C0203 !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 12px rgba(92, 2, 3, 0.3) !important;
    transform: translateY(-1px);
}
</style>
"""


def _get_available_rooms(user_id: int) -> list:
    """Fetch joined rooms from DB."""
    try:
        from database.database import get_user_joined_rooms
        return get_user_joined_rooms(user_id) or []
    except Exception:
        return []


def render_room_selector(key_prefix: str = "global"):
    """
    Renders an interactive, universal Room Selection dropdown anywhere on a page.
    Automatically keeps active room in sync across pages.
    """
    user_id = get_current_user_id()
    rooms = _get_available_rooms(user_id)
    if not rooms:
        st.info("🏠 You have not joined any rooms yet. Visit **Rooms** to create or join one.")
        return None

    room_map = {f"{r['name']} ({r.get('secret_code') or r.get('code', '')})": r for r in rooms}
    current_id = get_current_room_id()

    cur_idx = 0
    options = list(room_map.keys())
    for i, (label, r) in enumerate(room_map.items()):
        if r["id"] == current_id:
            cur_idx = i
            break
    else:
        # If no room was active, default to first room
        first_r = rooms[0]
        set_current_room(first_r["id"], first_r["name"])
        cur_idx = 0

    selected_label = st.selectbox(
        "🏠 Active Room",
        options=options,
        index=cur_idx,
        key=f"{key_prefix}_room_dropdown",
    )

    selected_room = room_map[selected_label]
    if selected_room["id"] != get_current_room_id():
        set_current_room(selected_room["id"], selected_room["name"])
        st.rerun()

    return selected_room


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
        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── Navigation Links ──────────────────────────
        st.markdown('<div class="sb-section-label">Navigation</div>', unsafe_allow_html=True)

        for label, emoji, path in NAV_ITEMS:
            st.page_link(path, label=f"{emoji}  {label}")

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # ── Logout ────────────────────────────────────
        if st.button("🚪  Logout", key="sidebar_logout_btn"):
            st.switch_page("pages/05_Logout.py")
