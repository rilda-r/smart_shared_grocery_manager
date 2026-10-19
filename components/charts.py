"""
components/charts.py
====================
Matplotlib chart components for GrocEase.
Shared Kitchen Counter aesthetic design.

All charts handle empty data gracefully.
Uses the GrocEase colour palette.
Do NOT use Plotly.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st
from collections import defaultdict

# GrocEase "Shared Kitchen Counter" Palette
BURGUNDY       = "#0F766E"  # Primary highlights, spendings & titles
SAGE           = "#6B8F71"  # Success, saved amounts, healthy states
OCHRE          = "#E3A02E"  # Warnings, limits, pending states
OXBLOOD        = "#8C1C13"  # Over budget, debts, errors
DEEP_CHOCOLATE = "#10272A"  # Text & labels
CHOCOLATE      = "#0E3B3A"  # Dark accent
CREAM          = "#F7FBFA"  # Chart background
CREAM_BORDER   = "#CADDD8"  # Chart border & spines
SAND           = "#EEF5F3"  # Canvas background

# Canonical category color tokens for GrocEase
CATEGORY_COLOR_MAP = {
    "Food": "#0F766E",          # Signature Burgundy
    "Transport": "#6B8F71",     # Sage Green
    "Entertainment": "#E3A02E", # Warm Amber / Ochre
    "Utilities": "#3A6073",     # Deep Slate Blue
    "Healthcare": "#8C1C13",    # Crimson Oxblood
    "Shopping": "#A36B4F",      # Warm Terracotta
    "Other": "#4A6568",         # Deep Earth Chocolate
}

FALLBACK_PALETTE = [
    "#0F766E", "#6B8F71", "#E3A02E", "#3A6073", "#8C1C13",
    "#A36B4F", "#4A6568", "#6F7A3A", "#14938A", "#4A5859",
]


def get_category_color(category: str) -> str:
    """Return a strictly deterministic color token for any given expense category."""
    if not category:
        return "#4A6568"
    clean_cat = category.strip()
    if clean_cat in CATEGORY_COLOR_MAP:
        return CATEGORY_COLOR_MAP[clean_cat]
    idx = abs(hash(clean_cat)) % len(FALLBACK_PALETTE)
    return FALLBACK_PALETTE[idx]


def _base_fig(figsize=(6, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(CREAM)
    ax.set_facecolor(CREAM)
    ax.tick_params(colors=DEEP_CHOCOLATE, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(CREAM_BORDER)
        spine.set_linewidth(1.0)
    return fig, ax


def render_category_pie_chart(expenses: list):
    """
    Pie chart of spending by category with strict synchronized color tokens.
    expenses: list of PersonalExpense dicts
    """
    if not expenses:
        st.info("No expense data to display yet.")
        return

    totals = defaultdict(float)
    for e in expenses:
        totals[e["category"]] += e["amount"]

    # Sort categories descending by amount for clean hierarchy
    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    labels = [k for k, _ in sorted_items]
    values = [v for _, v in sorted_items]
    colors = [get_category_color(cat) for cat in labels]

    fig, ax = _base_fig(figsize=(5, 5))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct="%1.0f%%",
        startangle=140,
        pctdistance=0.80,
        wedgeprops={"linewidth": 1.5, "edgecolor": CREAM},
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_color("#FFFFFF")
        at.set_fontweight("bold")

    ax.legend(
        wedges,
        [f"{l}  ₹{totals[l]:,.0f}" for l in labels],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=2,
        fontsize=8,
        framealpha=0,
    )
    ax.set_title("Spending by Category", fontsize=11, color=BURGUNDY, fontweight="bold", pad=10)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_monthly_bar_chart(expenses: list):
    """
    Stacked bar chart of monthly spending broken down by category,
    enforcing strict color mapping consistency matching the category pie chart.
    expenses: list of PersonalExpense dicts
    """
    if not expenses:
        st.info("No expense data to display yet.")
        return

    # Aggregate monthly spending broken down by category
    # monthly_cat_spending[month][category] = amount
    monthly_cat = defaultdict(lambda: defaultdict(float))
    all_categories = set()
    for e in expenses:
        m = e["expenseDate"][:7]  # "YYYY-MM"
        cat = e["category"]
        monthly_cat[m][cat] += e["amount"]
        all_categories.add(cat)

    months = sorted(monthly_cat.keys())
    labels = [m[5:] + "/" + m[2:4] for m in months]  # "MM/YY"
    cat_list = sorted(list(all_categories))

    fig, ax = _base_fig(figsize=(6, 3.8))
    width = 0.52

    # Bottom accumulator for stacking
    bottoms = [0.0] * len(months)
    used_categories = []

    for cat in cat_list:
        cat_values = [monthly_cat[m].get(cat, 0.0) for m in months]
        # Only plot category if it has non-zero values
        if any(v > 0 for v in cat_values):
            color = get_category_color(cat)
            ax.bar(
                labels,
                cat_values,
                width,
                bottom=bottoms,
                label=cat,
                color=color,
                edgecolor=CREAM,
                linewidth=0.8,
            )
            used_categories.append(cat)
            for i in range(len(months)):
                bottoms[i] += cat_values[i]

    # Display total amount text above each month's stacked bar
    max_total = max(bottoms) if bottoms else 1.0
    ax.set_ylim(0, max_total * 1.25)
    for idx, (lbl, tot) in enumerate(zip(labels, bottoms)):
        if tot > 0:
            ax.text(
                idx,
                tot + (max_total * 0.025),
                f"₹{tot:,.0f}",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                color=DEEP_CHOCOLATE,
            )

    ax.set_ylabel("Amount (₹)", fontsize=9, color=DEEP_CHOCOLATE)
    ax.set_title("Monthly Spending by Category", fontsize=11, color=BURGUNDY, fontweight="bold")

    if used_categories:
        ax.legend(
            loc="upper right",
            fontsize=8,
            ncol=min(len(used_categories), 3),
            framealpha=0,
        )

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_budget_utilization_chart(budgets: list, spending_by_category: dict):
    """
    Horizontal bar chart showing budget utilization per category.

    Args:
        budgets: list of Budget dicts
        spending_by_category: {category: amount_spent}
    """
    if not budgets:
        st.info("No budget data to display yet.")
        return

    categories = [b["category"] for b in budgets]
    limits      = [b["monthlyLimit"] for b in budgets]
    spendings   = [spending_by_category.get(b["category"], 0.0) for b in budgets]

    y = range(len(categories))
    fig, ax = _base_fig(figsize=(6, max(2.5, len(categories) * 0.8)))

    ax.barh(list(y), limits,    color=OCHRE,    edgecolor=CREAM_BORDER, linewidth=0.8, label="Limit",   height=0.45)
    ax.barh(list(y), spendings, color=BURGUNDY, edgecolor=CREAM,        linewidth=0.8, label="Spent",   height=0.45)

    ax.set_yticks(list(y))
    ax.set_yticklabels(categories, fontsize=9)
    ax.set_xlabel("Amount (₹)", fontsize=9, color=DEEP_CHOCOLATE)
    ax.set_title("Budget Utilization", fontsize=11, color=BURGUNDY, fontweight="bold")

    legend_patches = [
        mpatches.Patch(color=OCHRE,    label="Limit"),
        mpatches.Patch(color=BURGUNDY, label="Spent"),
    ]
    ax.legend(handles=legend_patches, fontsize=8, framealpha=0, loc="lower right")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_monthly_history_chart(history_records: list):
    """
    Grouped bar chart showing Budget vs Spent vs Saved across past months.
    """
    if not history_records:
        st.info("No historical budget archives found yet.")
        return

    import numpy as np
    records = sorted(history_records, key=lambda r: r.get("monthYear", ""))
    months = [r.get("monthYear", "") for r in records]
    budgets = [float(r.get("totalBudget", 0)) for r in records]
    spents = [float(r.get("totalSpent", 0)) for r in records]
    saveds = [float(r.get("totalSaved", 0)) for r in records]

    x = np.arange(len(months))
    width = 0.25

    fig, ax = _base_fig(figsize=(7, 3.8))
    ax.bar(x - width, budgets, width, label="Budget", color=OCHRE,    edgecolor=CREAM)
    ax.bar(x,         spents,  width, label="Spent",  color=BURGUNDY, edgecolor=CREAM)
    ax.bar(x + width, saveds,  width, label="Saved",  color=SAGE,     edgecolor=CREAM)

    ax.set_ylabel("Amount (₹)", fontsize=9, color=DEEP_CHOCOLATE)
    ax.set_title("Historical Budget vs. Spent vs. Saved", fontsize=11, color=BURGUNDY, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=9)
    ax.legend(fontsize=8, framealpha=0)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_month_end_summary_chart(category_breakdown: dict):
    """
    Horizontal grouped bar chart showing category breakdown of Used vs. Saved.
    """
    if not category_breakdown:
        return

    import numpy as np
    categories = list(category_breakdown.keys())
    spent_vals = [float(category_breakdown[c].get("spent", 0.0)) for c in categories]
    saved_vals = [float(max(category_breakdown[c].get("saved", 0.0), 0.0)) for c in categories]

    y = np.arange(len(categories))
    height = 0.35

    fig, ax = _base_fig(figsize=(6.5, max(2.8, len(categories) * 0.75)))
    ax.barh(y - height/2, spent_vals, height, label="Used (Spent)", color=BURGUNDY, edgecolor=CREAM)
    ax.barh(y + height/2, saved_vals, height, label="Saved",        color=SAGE,     edgecolor=CREAM)

    ax.set_yticks(y)
    ax.set_yticklabels(categories, fontsize=9)
    ax.set_xlabel("Amount (₹)", fontsize=9, color=DEEP_CHOCOLATE)
    ax.set_title("Month-End Breakdown: Used vs. Saved", fontsize=11, color=BURGUNDY, fontweight="bold")
    ax.legend(fontsize=8, framealpha=0, loc="lower right")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
