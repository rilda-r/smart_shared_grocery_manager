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
    "pending":     ("⏳", "#E3A02E", "#FBF3E3"),
    "purchased":   ("✅", "#6B8F71", "#EAF1EB"),
    "unavailable": ("❌", "#8C1C13", "#FCEAE8"),
    "settled":     ("✅", "#6B8F71", "#EAF1EB"),
    "reported":    ("⚠️", "#E3A02E", "#FBF3E3"),
    "completed":   ("✅", "#6B8F71", "#EAF1EB"),
    "failed":      ("❌", "#8C1C13", "#FCEAE8"),
    "processing":  ("⏳", "#E3A02E", "#FBF3E3"),
    "creator":     ("👑", "#0F766E", "#FCEAE8"),
    "member":      ("👤", "#0E3B3A", "#F7FBFA"),
}


def badge_html(status: str) -> str:
    """Return an HTML span badge for the given status."""
    icon, color, bg = STATUS_BADGE.get(status.lower(), ("•", "#4A6568", "#F7FBFA"))
    return (
        f'<span style="background:{bg}; color:{color}; border:1.2px solid {color}; '
        f'border-radius:20px; padding:3px 10px; font-size:0.8rem; font-weight:700; '
        f'font-family:\'Plus Jakarta Sans\',sans-serif; display:inline-flex; align-items:center; gap:4px; box-shadow:0 1px 3px rgba(16,39,42,0.04);">'
        f"{icon} {status.capitalize()}</span>"
    )


def percentage_color(pct: float) -> str:
    """Return a hex color for a budget percentage bar."""
    if pct >= 100:
        return "#8C1C13"  # OXBLOOD — over budget
    if pct >= 80:
        return "#E3A02E"  # OCHRE — warning
    return "#6B8F71"      # SAGE — healthy / in the green


def safe_error_message(exc: Exception, fallback: str = "Something went wrong. Please try again.") -> str:
    """
    Text that is safe to show in the UI. Our own validation errors (ValueError) pass through;
    anything else (database driver / network errors can contain host names) is logged and replaced.
    """
    import logging
    if isinstance(exc, ValueError):
        return str(exc)
    logging.getLogger("grocease").exception("Unhandled error shown to user as generic message: %s", type(exc).__name__)
    return fallback
