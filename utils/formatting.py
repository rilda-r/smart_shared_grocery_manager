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
    "pending":     ("🟡", "#A97A1F", "#FFF8E1"),
    "purchased":   ("✅", "#1F4C3D", "#E7EFE6"),
    "unavailable": ("❌", "#9C4B3E", "#FDE8E4"),
    "settled":     ("✅", "#1F4C3D", "#E7EFE6"),
    "reported":    ("⚠️", "#9C4B3E", "#FDE8E4"),
    "completed":   ("✅", "#1F4C3D", "#E7EFE6"),
    "failed":      ("❌", "#9C4B3E", "#FDE8E4"),
    "processing":  ("⏳", "#5B6459", "#F0F0F0"),
    "creator":     ("👑", "#A97A1F", "#FFF8E1"),
    "member":      ("👤", "#1F4C3D", "#E7EFE6"),
}


def badge_html(status: str) -> str:
    """Return an HTML span badge for the given status."""
    icon, color, bg = STATUS_BADGE.get(status.lower(), ("•", "#5B6459", "#F0F0F0"))
    return (
        f'<span style="background:{bg}; color:{color}; border:1px solid {color}; '
        f'border-radius:4px; padding:2px 8px; font-size:0.82rem; font-weight:600;">'
        f"{icon} {status.capitalize()}</span>"
    )


def percentage_color(pct: float) -> str:
    """Return a hex color for a budget percentage bar."""
    if pct >= 100:
        return "#9C4B3E"  # RUST — over budget
    if pct >= 80:
        return "#A97A1F"  # GOLD — warning
    return "#1F4C3D"      # FOREST — healthy
