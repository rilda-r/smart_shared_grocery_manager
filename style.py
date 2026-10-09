import streamlit as st

PAPER = "#D9C4B1"           # CHAMPAGNE: Warm, soft canvas background
SURFACE = "#FFFFFF"         # Crisp White containers for readability
SURFACE_WARM = "#FCFBF8"    # Soft warm ivory container
INK = "#372713"             # ESPRESSO: Rich dark text & details
INK_MUTED = "#6B5A47"       # Muted espresso
PRIMARY = "#5C0203"         # OXBLOOD: Key primary actions, highlights, headers
PRIMARY_HOVER = "#7A0A0C"   # Deeper oxblood hover
SECONDARY = "#4D4828"       # EMERALD SAGE: Success, secondary actions, indicators
ACCENT_WARM = "#A39670"     # VINTAGE ROSE: Warm secondary elements, borders, subtle tags
LINE = "rgba(163, 150, 112, 0.35)" # Soft vintage rose border
LINE_SOLID = "#A39670"
SIDEBAR_BG = "#2B1D0F"      # Sleek deep espresso for vertical sidebar

BASE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700;9..144,800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;
    color: {INK} !important;
}}
.stApp {{ 
    background-color: {PAPER} !important;
    background-image: radial-gradient(rgba(163, 150, 112, 0.12) 1px, transparent 0);
    background-size: 24px 24px;
}}

/* Typography */
h1, h2, h3, h4 {{
    font-family: 'Fraunces', Georgia, serif;
    color: {PRIMARY} !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}}
h1 {{ font-size: 2.3rem !important; margin-bottom: 0.4rem !important; }}
h2 {{ font-size: 1.8rem !important; }}
h3 {{ font-size: 1.35rem !important; }}
h4 {{ font-size: 1.1rem !important; }}

p, span, label, div {{
    color: {INK};
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
    max-width: 1140px; 
}}

/* Streamlit Primary & Default Buttons (OXBLOOD) */
.stButton > button {{
    background-color: {PRIMARY} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.65rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 0.94rem !important;
    box-shadow: 0 4px 12px rgba(92, 2, 3, 0.22) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    letter-spacing: 0.01em;
}}
.stButton > button:hover {{ 
    background-color: {PRIMARY_HOVER} !important; 
    box-shadow: 0 6px 16px rgba(92, 2, 3, 0.32) !important;
    transform: translateY(-1px);
}}
.stButton > button:active {{
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(92, 2, 3, 0.2) !important;
}}
.stButton > button:focus {{ 
    background-color: {PRIMARY} !important; 
    color: #FFFFFF !important; 
    box-shadow: 0 0 0 3px rgba(92, 2, 3, 0.25) !important;
}}
.stButton > button * {{ color: inherit !important; }}

/* Secondary button style (EMERALD SAGE / WARM OUTLINE) */
.groc-secondary .stButton > button,
button[kind="secondary"] {{
    background-color: {SURFACE_WARM} !important;
    color: {SECONDARY} !important;
    border: 1.5px solid {SECONDARY} !important;
    box-shadow: 0 2px 8px rgba(77, 72, 40, 0.08) !important;
}}
.groc-secondary .stButton > button:hover,
button[kind="secondary"]:hover {{ 
    background-color: #EAE6DC !important; 
    color: {INK} !important;
    border-color: {SECONDARY} !important;
    transform: translateY(-1px);
}}

/* Danger button style (SOFT OXBLOOD OUTLINE) */
.groc-danger .stButton > button {{
    background-color: #FFF5F5 !important;
    color: {PRIMARY} !important;
    border: 1.5px solid {PRIMARY} !important;
    box-shadow: none !important;
}}
.groc-danger .stButton > button:hover {{
    background-color: {PRIMARY} !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}}

/* Form Inputs (Outlined, Rounded, Soft Focus) */
.stTextInput div div input,
.stNumberInput div div input,
.stDateInput div div input,
.stTextArea div div textarea {{
    color: {INK} !important;
    background-color: {SURFACE} !important;
    border: 1.5px solid {ACCENT_WARM} !important;
    border-radius: 12px !important;
    font-size: 0.98rem !important;
    padding: 0.65rem 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(55, 39, 19, 0.03) !important;
}}
.stTextInput div div input:focus,
.stNumberInput div div input:focus,
.stDateInput div div input:focus,
.stTextArea div div textarea:focus {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 3px rgba(92, 2, 3, 0.18) !important;
    background-color: #FFFFFF !important;
}}

/* Selectbox Dropdown */
[data-baseweb="select"] > div {{
    background-color: {SURFACE} !important;
    border: 1.5px solid {ACCENT_WARM} !important;
    border-radius: 12px !important;
    color: {INK} !important;
    box-shadow: 0 1px 3px rgba(55, 39, 19, 0.03) !important;
}}
[data-baseweb="select"] > div:focus-within {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 3px rgba(92, 2, 3, 0.18) !important;
}}

/* Expanders */
div[data-testid="stExpander"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {LINE} !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 14px rgba(55, 39, 19, 0.04) !important;
    margin-bottom: 0.9rem !important;
    overflow: hidden !important;
}}
div[data-testid="stExpander"] summary {{
    padding: 0.85rem 1.2rem !important;
    font-weight: 600 !important;
    color: {INK} !important;
}}
div[data-testid="stExpander"] summary:hover {{
    background-color: {SURFACE_WARM} !important;
    color: {PRIMARY} !important;
}}

/* Tabs */
button[data-baseweb="tab"] {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    color: {SECONDARY} !important;
    border-radius: 10px 10px 0 0 !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.15s ease !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {PRIMARY} !important;
    border-bottom: 2.5px solid {PRIMARY} !important;
    background: transparent !important;
}}

/* Cards & Layout Blocks */
.groc-card {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-top: 4px solid {PRIMARY};
    border-radius: 20px;
    padding: 1.85rem;
    box-shadow: 0 8px 24px rgba(55, 39, 19, 0.06), 0 2px 6px rgba(55, 39, 19, 0.03);
    margin-bottom: 1.2rem;
}}
.groc-panel {{
    background-color: {SURFACE_WARM};
    border: 1px solid {ACCENT_WARM};
    border-radius: 18px;
    padding: 1.5rem;
    box-shadow: 0 4px 16px rgba(55, 39, 19, 0.04);
}}
.groc-hr {{
    border: none;
    border-top: 1px solid {LINE};
    margin: 1.6rem 0;
}}

/* Nav Banner */
.groc-nav {{
    padding: 0.6rem 0 1.2rem 0;
    border-bottom: 1px solid {LINE};
    margin-bottom: 1.8rem;
}}
.groc-logo {{
    font-family: 'Fraunces', serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: {PRIMARY};
    letter-spacing: -0.02em;
}}
.groc-tagline {{
    color: {INK_MUTED};
    font-size: 0.88rem;
    font-weight: 500;
    margin-top: -0.1rem;
}}
.groc-muted {{ color: {INK_MUTED} !important; }}

/* Page Links */
[data-testid="stPageLink"] {{ margin: 0 !important; }}
[data-testid="stPageLink"] a,
[data-testid="stPageLink-NavLink"] {{
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: {PRIMARY} !important;
    font-weight: 600 !important;
    font-size: 0.93rem !important;
    text-decoration: none !important;
}}
[data-testid="stPageLink"] a p,
[data-testid="stPageLink-NavLink"] p {{
    color: {PRIMARY} !important;
    font-weight: 600 !important;
}}
[data-testid="stPageLink"] a:hover p,
[data-testid="stPageLink-NavLink"]:hover p {{
    color: {PRIMARY_HOVER} !important;
    text-decoration: underline;
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
            """
            <div style="display:inline-flex; align-items:center; gap:6px; background:rgba(169,122,31,0.12);
                        border:1px solid rgba(169,122,31,0.3); border-radius:12px; padding:3px 10px;
                        margin-bottom:12px; font-size:0.75rem; color:#6B4E10; font-weight:600; letter-spacing:0.01em;">
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
