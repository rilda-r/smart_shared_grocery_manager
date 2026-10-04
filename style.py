import streamlit as st

PAPER = "#F6F2E9"
SURFACE = "#FFFFFF"
INK = "#20261F"
INK_MUTED = "#5B6459"
FOREST = "#1F4C3D"
MOSS = "#3D7A5D"
SAGE = "#E7EFE6"
LINE = "#D8D0BE"
LINE_GREEN = "#C3D6C6"
GOLD = "#A97A1F"
RUST = "#9C4B3E"
BLACK = "#0F0F0F"
BLACK_HOVER = "#2A2A2A"

BASE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, sans-serif;
    color: {INK} !important;
}}
.stApp {{ background-color: {PAPER}; }}

h1, h2, h3, h4 {{
    font-family: 'Fraunces', Georgia, serif;
    color: {FOREST} !important;
    font-weight: 600 !important;
}}

#MainMenu, footer, .stDeployButton, [data-testid="stToolbarActions"] {{
    visibility: hidden !important;
}}
header {{
    background: transparent !important;
}}
header [data-testid="stToolbar"] {{
    visibility: visible !important;
    display: flex !important;
}}
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] {{
    visibility: visible !important;
    display: flex !important;
    z-index: 99999 !important;
}}
[data-testid="stExpandSidebarButton"] button, [data-testid="stSidebarCollapsedControl"] button {{
    color: {FOREST} !important;
    background-color: {SAGE} !important;
    border: 1px solid {LINE_GREEN} !important;
    border-radius: 6px !important;
    padding: 4px 8px !important;
}}
[data-testid="stExpandSidebarButton"] button:hover, [data-testid="stSidebarCollapsedControl"] button:hover {{
    background-color: {LINE_GREEN} !important;
}}
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg {{
    fill: {FOREST} !important;
    stroke: {FOREST} !important;
}}

.block-container {{ padding-top: 2rem; max-width: 1120px; }}

/* All Streamlit buttons = black */
.stButton > button {{
    background-color: {BLACK} !important;
    color: {PAPER} !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.6rem 1.4rem !important;
    font-weight: 600 !important;
    font-size: 0.94rem !important;
    box-shadow: none !important;
    transition: background-color 0.15s ease;
}}
.stButton > button:hover {{ background-color: {BLACK_HOVER} !important; }}
.stButton > button:focus {{ background-color: {BLACK} !important; color: {PAPER} !important; }}

/* Force button label/icon text to inherit the button's own color.
   Without this, the global `[class*="css"]` text-color rule above
   wins over the button's intended color on the inner <p>/<span>
   Streamlit wraps the label in, making labels like "Logout" render
   in near-black INK on the near-black button background. */
.stButton > button * {{ color: inherit !important; }}

/* Secondary buttons */
.groc-secondary .stButton > button {{
    background-color: transparent !important;
    color: {FOREST} !important;
    border: 1.5px solid {FOREST} !important;
}}
.groc-secondary .stButton > button:hover {{ background-color: {SAGE} !important; }}

/* Danger buttons */
.groc-danger .stButton > button {{
    background-color: transparent !important;
    color: {RUST} !important;
    border: 1.5px solid {RUST} !important;
}}
.groc-danger .stButton > button:hover {{
    background-color: {RUST} !important;
    color: {PAPER} !important;
}}

/* Inputs */
.stTextInput div div input {{
    color: {INK} !important;
    background-color: {SURFACE} !important;
    border: 1.5px solid {LINE} !important;
    border-radius: 6px !important;
    font-size: 1rem !important;
    padding: 0.6rem 0.8rem !important;
}}
.stTextInput div div input:focus {{
    border-color: {FOREST} !important;
    box-shadow: 0 0 0 1px {FOREST} !important;
}}

/* Cards */
.groc-card {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-top: 3px solid {FOREST};
    border-radius: 4px;
    padding: 1.75rem;
}}
.groc-panel {{
    background-color: {SAGE};
    border: 1px solid {LINE_GREEN};
    border-radius: 4px;
    padding: 1.5rem;
}}
.groc-hr {{
    border: none;
    border-top: 1px solid {LINE};
    margin: 2rem 0;
}}

/* Nav */
.groc-nav {{
    padding: 0.4rem 0 1.3rem 0;
    border-bottom: 1px solid {LINE};
    margin-bottom: 2rem;
}}
.groc-logo {{
    font-family: 'Fraunces', serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: {FOREST};
}}
.groc-tagline {{
    color: {INK_MUTED};
    font-size: 0.86rem;
    font-weight: 500;
    margin-top: -0.1rem;
}}

.groc-muted {{ color: {INK_MUTED} !important; }}

.groc-feature-icon {{
    font-size: 1.6rem;
    background-color: {SAGE};
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    margin-bottom: 0.7rem;
}}

/* ============ st.page_link — THE WORKING LINK ============ */
[data-testid="stPageLink"] {{ margin: 0 !important; }}

[data-testid="stPageLink"] a,
[data-testid="stPageLink-NavLink"] {{
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: {FOREST} !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    text-decoration: none !important;
}}
[data-testid="stPageLink"] a p,
[data-testid="stPageLink-NavLink"] p {{
    color: {FOREST} !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
}}
[data-testid="stPageLink"] a:hover p,
[data-testid="stPageLink-NavLink"]:hover p {{
    color: {MOSS} !important;
    text-decoration: underline;
}}

/* Black link wrapper */
.black-link [data-testid="stPageLink"] a p,
.black-link [data-testid="stPageLink-NavLink"] p {{
    color: {BLACK} !important;
    font-weight: 700 !important;
}}
.black-link [data-testid="stPageLink"] a:hover p,
.black-link [data-testid="stPageLink-NavLink"]:hover p {{
    color: {BLACK_HOVER} !important;
    text-decoration: underline;
}}

/* Forgot password wrapper */
.forgot-link [data-testid="stPageLink"] {{
    display: flex;
    justify-content: flex-end;
}}
.forgot-link [data-testid="stPageLink"] a p,
.forgot-link [data-testid="stPageLink-NavLink"] p {{
    color: {FOREST} !important;
    font-weight: 600 !important;
}}
.forgot-link [data-testid="stPageLink"] a:hover p,
.forgot-link [data-testid="stPageLink-NavLink"]:hover p {{
    color: {MOSS} !important;
    text-decoration: underline;
}}

/* Receipt card */
.groc-receipt {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 4px;
    padding: 1.6rem;
    box-shadow: 6px 6px 0 {SAGE};
}}
.groc-receipt-title {{
    font-family: 'Fraunces', serif;
    font-weight: 600;
    color: {FOREST};
    font-size: 1.1rem;
    border-bottom: 1px dashed {LINE};
    padding-bottom: 0.6rem;
    margin-bottom: 0.8rem;
}}
.groc-receipt-item {{
    display: flex;
    justify-content: space-between;
    padding: 0.3rem 0;
    font-size: 0.92rem;
}}
.groc-receipt-item .status-done {{ color: {MOSS}; font-weight: 500; }}
.groc-receipt-item .status-pending {{ color: {GOLD}; font-weight: 500; }}
.groc-receipt-total {{
    margin-top: 0.9rem;
    padding-top: 0.7rem;
    border-top: 1px dashed {LINE};
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.groc-receipt-total .amount {{
    font-family: 'Fraunces', serif;
    font-weight: 600;
    color: {GOLD};
    font-size: 1.2rem;
}}

/* Feature card */
.feature-card {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 4px;
    padding: 1.6rem 1.2rem 1.4rem;
}}
.feature-card h4 {{
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: {INK};
    margin-bottom: 0.25rem;
}}
.feature-card p {{
    font-size: 0.88rem;
    color: {INK_MUTED};
    line-height: 1.5;
}}
</style>
"""

def apply_base_style():
    st.markdown(BASE_CSS, unsafe_allow_html=True)

def top_nav():
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