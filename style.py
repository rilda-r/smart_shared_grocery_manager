import streamlit as st

# ==============================================================================
# GrocEase "Fresh Market" (teal & mint) Aesthetic Design Tokens
# ==============================================================================

# Sand Canvas (Main Background)
SAND = "#EEF5F3"             # Main sand canvas background
SAND_CANVAS = "#F5FAF8"      # Light canvas tint
SAND_SUBTLE = "#DCEBE7"      # Subtle warm sand tint
SAND_DARK = "#BCD6CF"

# Deep Chocolate (Text & Headings)
DEEP_CHOCOLATE = "#10272A"   # Main text & headings
CHOCOLATE = "#0E3B3A"        # Chocolate sidebar background
CHOCOLATE_HOVER = "#14504D"  # Sidebar item hover & muted labels
CHOCOLATE_CARD = "#0A2B2B"   # Deep chocolate card
CHOCOLATE_MUTED = "#4A6568"  # Muted chocolate body text

# Cream (Card & Container Background)
CREAM = "#F7FBFA"            # Card & container background
CREAM_BORDER = "#CADDD8"     # Card & input border
CREAM_LIGHT = "#FFFFFF"      # Elevated light container background

# Burgundy (Primary Action Buttons / Accents)
BURGUNDY = "#0F766E"         # Primary actions, highlights, brand accents
BURGUNDY_HOVER = "#0B5F58"   # Burgundy hover
BURGUNDY_LIGHT = "#14938A"   # Burgundy light highlight

# Sage (In the Green / Live / Success)
SAGE = "#6B8F71"             # Success, active sync, healthy budget
SAGE_LIGHT = "#EAF1EB"       # Sage light background

# Oxblood (Debts / Errors / Deletion)
OXBLOOD = "#8C1C13"          # Debts, errors, delete actions, over-budget
OXBLOOD_LIGHT = "#FCEAE8"    # Oxblood light background

# Ochre (Warnings / Pending)
OCHRE = "#E3A02E"            # Warnings, pending, caution badges
OCHRE_LIGHT = "#FBF3E3"      # Ochre light background

# Backward-compatibility token aliases
PAPER = SAND
SURFACE = CREAM
SURFACE_WARM = SAND_CANVAS
INK = DEEP_CHOCOLATE
INK_MUTED = CHOCOLATE_MUTED
PRIMARY = BURGUNDY
PRIMARY_HOVER = BURGUNDY_HOVER
SECONDARY = SAGE
ACCENT_WARM = CREAM_BORDER
LINE = CREAM_BORDER
LINE_SOLID = CREAM_BORDER
SIDEBAR_BG = CHOCOLATE

WARM_SHADOW = "0 4px 20px -2px rgba(16, 39, 42, 0.08)"
WARM_SHADOW_MD = "0 8px 30px -4px rgba(16, 39, 42, 0.12)"

BASE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700;9..144,800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    color: {DEEP_CHOCOLATE} !important;
}}

/* Warm Dotted Kitchen Counter Texture */
.stApp {{ 
    background-color: {SAND} !important;
    background-image: radial-gradient(rgba(16, 39, 42, 0.08) 1.5px, transparent 1.5px) !important;
    background-size: 24px 24px !important;
}}

/* Typography */
h1, h2, h3, h4, .stTitle, .stHeader {{
    font-family: 'Fraunces', Georgia, serif !important;
    color: {DEEP_CHOCOLATE} !important;
    font-weight: 700 !important;
    letter-spacing: -0.015em;
}}
h1 {{ font-size: 2.35rem !important; margin-bottom: 0.4rem !important; }}
h2 {{ font-size: 1.85rem !important; }}
h3 {{ font-size: 1.35rem !important; }}
h4 {{ font-size: 1.1rem !important; }}

p, span, label, div {{
    color: {DEEP_CHOCOLATE};
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
[data-testid="stSidebarNav"] {{
    display: none !important;
}}

.block-container {{ 
    padding-top: 2rem; 
    padding-bottom: 3.5rem;
    max-width: 1160px; 
}}

/* Streamlit Primary & Default Buttons (BURGUNDY) */
.stButton > button,
button[kind="primary"] {{
    background-color: {BURGUNDY} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.65rem 1.4rem !important;
    font-weight: 600 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.94rem !important;
    box-shadow: 0 4px 14px rgba(15, 118, 110, 0.22) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    letter-spacing: 0.01em;
}}
.stButton > button:hover,
button[kind="primary"]:hover {{ 
    background-color: {BURGUNDY_HOVER} !important; 
    box-shadow: 0 6px 18px rgba(15, 118, 110, 0.32) !important;
    transform: translateY(-1px);
}}
.stButton > button:active,
button[kind="primary"]:active {{
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(15, 118, 110, 0.2) !important;
    background-color: #54121B !important;
}}
.stButton > button:focus,
button[kind="primary"]:focus {{ 
    background-color: {BURGUNDY} !important; 
    color: #FFFFFF !important; 
    box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.25) !important;
}}
.stButton > button * {{ color: inherit !important; }}

/* Secondary button style (CREAM & BORDER) */
.groc-secondary .stButton > button,
button[kind="secondary"] {{
    background-color: {CREAM} !important;
    color: {CHOCOLATE} !important;
    border: 1.5px solid {CREAM_BORDER} !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(16, 39, 42, 0.05) !important;
}}
.groc-secondary .stButton > button:hover,
button[kind="secondary"]:hover {{ 
    background-color: {SAND_CANVAS} !important; 
    color: {BURGUNDY} !important;
    border-color: {BURGUNDY} !important;
    transform: translateY(-1px);
}}

/* Danger button style (OXBLOOD OUTLINE / ACCENT) */
.groc-danger .stButton > button {{
    background-color: {OXBLOOD_LIGHT} !important;
    color: {OXBLOOD} !important;
    border: 1.5px solid {OXBLOOD} !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}}
.groc-danger .stButton > button:hover {{
    background-color: {OXBLOOD} !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}}

/* Form Inputs (Cream Background, Warm Border, Burgundy Focus) */
.stTextInput div div input,
.stNumberInput div div input,
.stDateInput div div input,
.stTextArea div div textarea {{
    color: {DEEP_CHOCOLATE} !important;
    background-color: {CREAM} !important;
    border: 1.5px solid {CREAM_BORDER} !important;
    border-radius: 12px !important;
    font-size: 0.98rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    padding: 0.65rem 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 4px rgba(16, 39, 42, 0.04) !important;
}}
.stTextInput div div input:focus,
.stNumberInput div div input:focus,
.stDateInput div div input:focus,
.stTextArea div div textarea:focus {{
    border-color: {BURGUNDY} !important;
    box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.16) !important;
    background-color: {CREAM_LIGHT} !important;
}}

/* Selectbox Dropdown Control & Readability Fix */
[data-baseweb="select"],
[data-baseweb="select"] > div,
[data-baseweb="select"] div[role="combobox"] {{
    background-color: #F7FBFA !important;
    border: 1.5px solid #CADDD8 !important;
    border-radius: 12px !important;
    color: #10272A !important;
    box-shadow: 0 1px 4px rgba(16, 39, 42, 0.04) !important;
}}
[data-baseweb="select"] * {{
    color: #10272A !important;
}}
[data-baseweb="select"] svg {{
    fill: #10272A !important;
}}
[data-baseweb="select"] > div:focus-within {{
    border-color: #0F766E !important;
    box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.16) !important;
}}

/* BaseWeb Dropdown Popover & Options List */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
ul[role="listbox"] {{
    background-color: #F7FBFA !important;
    border: 1.5px solid #CADDD8 !important;
    border-radius: 14px !important;
    box-shadow: 0 10px 30px -4px rgba(16, 39, 42, 0.16) !important;
    padding: 6px !important;
}}
ul[role="listbox"] li,
li[role="option"],
[data-baseweb="menu"] li {{
    background-color: transparent !important;
    color: #10272A !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.94rem !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    padding: 0.55rem 0.85rem !important;
    transition: background 0.15s ease !important;
}}
ul[role="listbox"] li:hover,
li[role="option"]:hover,
li[role="option"][aria-selected="true"],
[data-baseweb="menu"] li:hover {{
    background-color: #DCEBE7 !important;
    color: #0F766E !important;
    font-weight: 700 !important;
}}

/* Ghost Panel Removal (Loading States & Smooth Transitions) */
div[data-testid="stAppViewContainer"],
div.stApp[data-test-script-state="running"],
div.stApp[data-test-script-state="running"] div[data-testid="stAppViewContainer"],
div.stApp[data-test-script-state="running"] > div:first-child,
div[data-testid="stAppViewBlockContainer"] {{
    opacity: 1 !important;
    filter: none !important;
    transition: none !important;
}}
.stSkeleton, [data-testid="stSkeleton"] {{
    display: none !important;
}}
[data-testid="stStatusWidget"] {{
    display: none !important;
    visibility: hidden !important;
}}
.stDeployButton, [data-testid="stDeployButton"] {{
    display: none !important;
    visibility: hidden !important;
}}

/* Expanders */
div[data-testid="stExpander"] {{
    background-color: {CREAM} !important;
    border: 1px solid {CREAM_BORDER} !important;
    border-radius: 18px !important;
    box-shadow: 0 4px 20px -2px rgba(16, 39, 42, 0.08) !important;
    margin-bottom: 0.9rem !important;
    overflow: hidden !important;
}}
div[data-testid="stExpander"] summary {{
    padding: 0.85rem 1.25rem !important;
    font-weight: 600 !important;
    color: {DEEP_CHOCOLATE} !important;
}}
div[data-testid="stExpander"] summary:hover {{
    background-color: {SAND_CANVAS} !important;
    color: {BURGUNDY} !important;
}}

/* Tabs */
button[data-baseweb="tab"] {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    color: {CHOCOLATE_MUTED} !important;
    border-radius: 10px 10px 0 0 !important;
    padding: 0.65rem 1.25rem !important;
    transition: all 0.15s ease !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {BURGUNDY} !important;
    border-bottom: 2.5px solid {BURGUNDY} !important;
    background: transparent !important;
}}

/* Cards & Layout Blocks */
div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background-color: {CREAM} !important;
    border: 1px solid {CREAM_BORDER} !important;
    border-top: 4px solid {BURGUNDY} !important;
    border-radius: 18px !important;
    padding: 1.85rem !important;
    box-shadow: 0 4px 20px -2px rgba(16, 39, 42, 0.08) !important;
}}
.groc-card {{
    background-color: {CREAM};
    border: 1px solid {CREAM_BORDER};
    border-top: 4px solid {BURGUNDY};
    border-radius: 18px;
    padding: 1.85rem;
    box-shadow: 0 4px 20px -2px rgba(16, 39, 42, 0.08);
    margin-bottom: 1.2rem;
}}
.groc-panel {{
    background-color: {SAND_CANVAS};
    border: 1px solid {CREAM_BORDER};
    border-radius: 18px;
    padding: 1.5rem;
    box-shadow: 0 4px 20px -2px rgba(16, 39, 42, 0.08);
}}
.groc-hr {{
    border: none;
    border-top: 1px solid {CREAM_BORDER};
    margin: 1.6rem 0;
}}

/* Nav Banner */
.groc-nav {{
    padding: 0.6rem 0 1.2rem 0;
    border-bottom: 1px solid {CREAM_BORDER};
    margin-bottom: 1.8rem;
}}
.groc-logo {{
    font-family: 'Fraunces', serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: {BURGUNDY};
    letter-spacing: -0.02em;
}}
.groc-tagline {{
    color: {CHOCOLATE_MUTED};
    font-size: 0.88rem;
    font-weight: 500;
    margin-top: -0.1rem;
}}
.groc-muted {{ color: {CHOCOLATE_MUTED} !important; }}

/* Page Links */
[data-testid="stPageLink"] {{ 
    margin: 0 !important; 
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    vertical-align: baseline !important;
}}
[data-testid="stPageLink"] a,
[data-testid="stPageLink-NavLink"] {{
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    color: {BURGUNDY} !important;
    font-weight: 600 !important;
    font-size: 0.94rem !important;
    text-decoration: none !important;
    display: inline-flex !important;
    align-items: center !important;
    line-height: normal !important;
}}
[data-testid="stPageLink"] a p,
[data-testid="stPageLink-NavLink"] p {{
    color: {BURGUNDY} !important;
    font-weight: 600 !important;
    margin: 0 !important;
    line-height: normal !important;
}}
[data-testid="stPageLink"] a:hover p,
[data-testid="stPageLink-NavLink"]:hover p {{
    color: {BURGUNDY_HOVER} !important;
    text-decoration: underline;
}}

/* Native Metrics Styling */
[data-testid="stMetricValue"] {{
    font-family: 'Fraunces', Georgia, serif !important;
    font-variant-numeric: tabular-nums !important;
    color: {DEEP_CHOCOLATE} !important;
}}
[data-testid="stMetricLabel"] {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: {CHOCOLATE_MUTED} !important;
    font-weight: 600 !important;
}}
[data-testid="stMetricDelta"] svg {{
    fill: currentColor !important;
}}

/* Alert Boxes Styling */
div[data-testid="stAlert"] {{
    border-radius: 14px !important;
    border-width: 1px !important;
    border-style: solid !important;
    box-shadow: 0 2px 10px rgba(16, 39, 42, 0.05) !important;
}}
div[data-testid="stAlert"]:has([data-testid="stNotificationContentSuccess"]) {{
    background-color: {SAGE_LIGHT} !important;
    border-color: {SAGE} !important;
    color: #2E5135 !important;
}}
div[data-testid="stAlert"]:has([data-testid="stNotificationContentInfo"]) {{
    background-color: {OCHRE_LIGHT} !important;
    border-color: {OCHRE} !important;
    color: {DEEP_CHOCOLATE} !important;
}}
div[data-testid="stAlert"]:has([data-testid="stNotificationContentWarning"]) {{
    background-color: {OCHRE_LIGHT} !important;
    border-color: {OCHRE} !important;
    color: #7A5212 !important;
}}
div[data-testid="stAlert"]:has([data-testid="stNotificationContentError"]) {{
    background-color: {OXBLOOD_LIGHT} !important;
    border-color: {OXBLOOD} !important;
    color: {OXBLOOD} !important;
}}

/* Tabular Numerals for Monetary Consistency */
.money-tabular {{
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.01em;
}}

/* Warm Subtle Scrollbars */
::-webkit-scrollbar {{
    width: 8px;
    height: 8px;
}}
::-webkit-scrollbar-track {{
    background: rgba(234, 223, 203, 0.4);
}}
::-webkit-scrollbar-thumb {{
    background: rgba(16, 39, 42, 0.2);
    border-radius: 9999px;
}}
/* Shopping Mode Compact Action Row Alignment */
.shop-action-row {{
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    margin-top: 0.15rem !important;
    margin-bottom: 0.4rem !important;
}}
.shop-action-row div[data-testid="stHorizontalBlock"] {{
    display: flex !important;
    align-items: center !important;
    flex-direction: row !important;
    width: 100% !important;
    gap: 0.5rem !important;
}}
.shop-action-row div[data-testid="column"] {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: unset !important;
    padding: 0 !important;
}}
.shop-action-row button {{
    height: 36px !important;
    min-height: 36px !important;
    max-height: 36px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 0.65rem !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    vertical-align: middle !important;
}}
</style>
"""

HIDE_SIDEBAR_CSS = """
<style>
/* Completely hide the left navigation panel before login, on register, and on logout */
[data-testid="stSidebar"],
section[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    pointer-events: none !important;
}
header [data-testid="stSidebarCollapsedControl"],
header [data-testid="stExpandSidebarButton"] {
    display: none !important;
    visibility: hidden !important;
}
</style>
"""


def hide_sidebar():
    """Unconditionally hide sidebar on guest / auth screens."""
    st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True)


def apply_base_style():
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    is_auth = bool(st.session_state.get("logged_in") or st.session_state.get("is_authenticated"))
    if not is_auth:
        hide_sidebar()


def render_dev_mode_banner():
    """Render a clear, tiny notification banner when live emails are disabled in local dev mode."""
    from security.authentication import smtp_is_configured
    if not smtp_is_configured():
        st.markdown(
            f"""
            <div style="display:inline-flex; align-items:center; gap:6px; background:{OCHRE_LIGHT};
                        border:1px solid {OCHRE}; border-radius:12px; padding:3px 10px;
                        margin-bottom:12px; font-size:0.75rem; color:#7A5212; font-weight:600; letter-spacing:0.01em;">
                <span>🛠️</span><span>Dev Mode: Live emails are disabled</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def top_nav():
    st.markdown(
        """
        <div class="groc-nav" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div class="groc-logo">🛒 GrocEase</div>
                <div class="groc-tagline">Shop together. Split smarter.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )