"""
utils/formatting.py
===================
UI formatting helpers for GrocEase.
"""


def format_currency(amount: float, symbol: str = "₹") -> str:
    """Format a float as a currency string."""
    return f"{symbol}{amount:,.2f}"


def format_date(iso_str: str) -> str:
    """Format an ISO date string to DD MMM YYYY."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d %b %Y")
    except Exception:
        return iso_str or "—"


def format_datetime(iso_str: str) -> str:
    """Format an ISO datetime string to DD MMM YYYY, HH:MM."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return iso_str or "—"


STATUS_BADGE = {
    "pending":     ("⏳", "#C8963E", "#FBF3E3"),
    "purchased":   ("✅", "#6B8F71", "#EAF1EB"),
    "unavailable": ("❌", "#8C1C13", "#FCEAE8"),
    "settled":     ("✅", "#6B8F71", "#EAF1EB"),
    "reported":    ("⚠️", "#C8963E", "#FBF3E3"),
    "completed":   ("✅", "#6B8F71", "#EAF1EB"),
    "failed":      ("❌", "#8C1C13", "#FCEAE8"),
    "processing":  ("⏳", "#C8963E", "#FBF3E3"),
    "creator":     ("👑", "#7A1F2B", "#FCEAE8"),
    "member":      ("👤", "#3B2A20", "#FBF6EC"),
}


def badge_html(status: str) -> str:
    """Return an HTML span badge for the given status."""
    icon, color, bg = STATUS_BADGE.get(status.lower(), ("•", "#5C4A3E", "#FBF6EC"))
    return (
        f'<span style="background:{bg}; color:{color}; border:1.2px solid {color}; '
        f'border-radius:20px; padding:3px 10px; font-size:0.8rem; font-weight:700; '
        f'font-family:\'Plus Jakarta Sans\',sans-serif; display:inline-flex; align-items:center; gap:4px; box-shadow:0 1px 3px rgba(59,42,32,0.04);">'
        f"{icon} {status.capitalize()}</span>"
    )


def percentage_color(pct: float) -> str:
    """Return a hex color for a budget percentage bar."""
    if pct >= 100:
        return "#8C1C13"  # OXBLOOD — over budget
    if pct >= 80:
        return "#C8963E"  # OCHRE — warning
    return "#6B8F71"      # SAGE — healthy / in the green
