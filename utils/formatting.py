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
    "pending":     ("⏳", "#A39670", "#FAF6F0"),
    "purchased":   ("✅", "#4D4828", "#ECEAE0"),
    "unavailable": ("❌", "#5C0203", "#FCEEEF"),
    "settled":     ("✅", "#4D4828", "#ECEAE0"),
    "reported":    ("⚠️", "#5C0203", "#FCEEEF"),
    "completed":   ("✅", "#4D4828", "#ECEAE0"),
    "failed":      ("❌", "#5C0203", "#FCEEEF"),
    "processing":  ("⏳", "#6B5A47", "#F5ECE3"),
    "creator":     ("👑", "#5C0203", "#FCEEEF"),
    "member":      ("👤", "#4D4828", "#ECEAE0"),
}


def badge_html(status: str) -> str:
    """Return an HTML span badge for the given status."""
    icon, color, bg = STATUS_BADGE.get(status.lower(), ("•", "#6B5A47", "#F5ECE3"))
    return (
        f'<span style="background:{bg}; color:{color}; border:1.2px solid {color}; '
        f'border-radius:20px; padding:3px 10px; font-size:0.8rem; font-weight:700; '
        f'display:inline-flex; align-items:center; gap:4px; box-shadow:0 1px 3px rgba(55,39,19,0.03);">'
        f"{icon} {status.capitalize()}</span>"
    )


def percentage_color(pct: float) -> str:
    """Return a hex color for a budget percentage bar."""
    if pct >= 100:
        return "#5C0203"  # OXBLOOD — over budget
    if pct >= 80:
        return "#A39670"  # VINTAGE ROSE — warning
    return "#4D4828"      # EMERALD SAGE — healthy
