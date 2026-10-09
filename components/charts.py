"""
components/charts.py
====================
Matplotlib chart components for GrocEase.

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

# Palette
OXBLOOD      = "#5C0203"  # Primary highlights & titles
CHAMPAGNE    = "#D9C4B1"  # Canvas warm base
EMERALD_SAGE = "#4D4828"  # Success & secondary accents
ESPRESSO     = "#372713"  # Text & dark elements
VINTAGE_ROSE = "#A39670"  # Subtle tags, borders
SURFACE      = "#FFFFFF"  # Crisp card background

CATEGORY_COLORS = [OXBLOOD, EMERALD_SAGE, VINTAGE_ROSE, "#853629", "#635D39", "#BD7B66", "#372713"]


def _base_fig(figsize=(6, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=ESPRESSO, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(CHAMPAGNE)
        spine.set_linewidth(1.0)
    return fig, ax


def render_category_pie_chart(expenses: list):
    """
    Pie chart of spending by category.
    expenses: list of PersonalExpense dicts
    """
    if not expenses:
        st.info("No expense data to display yet.")
        return

    totals = defaultdict(float)
    for e in expenses:
        totals[e["category"]] += e["amount"]

    labels = list(totals.keys())
    values = list(totals.values())
    colors = CATEGORY_COLORS[: len(labels)]

    fig, ax = _base_fig(figsize=(5, 5))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct="%1.0f%%",
        startangle=140,
        pctdistance=0.82,
        wedgeprops={"linewidth": 1.5, "edgecolor": SURFACE},
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_color(SURFACE)
        at.set_fontweight("bold")

    ax.legend(
        wedges,
        [f"{l}  ₹{totals[l]:,.0f}" for l in labels],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        fontsize=8,
        framealpha=0,
    )
    ax.set_title("Spending by Category", fontsize=11, color=OXBLOOD, fontweight="bold", pad=10)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_monthly_bar_chart(expenses: list):
    """
    Bar chart of monthly total spending.
    expenses: list of PersonalExpense dicts
    """
    if not expenses:
        st.info("No expense data to display yet.")
        return

    monthly = defaultdict(float)
    for e in expenses:
        month = e["expenseDate"][:7]  # "YYYY-MM"
        monthly[month] += e["amount"]

    months = sorted(monthly.keys())
    values = [monthly[m] for m in months]
    labels = [m[5:] + "/" + m[2:4] for m in months]  # "MM/YY"

    fig, ax = _base_fig(figsize=(6, 3.5))
    bars = ax.bar(labels, values, color=OXBLOOD, edgecolor=SURFACE, linewidth=0.8, width=0.55)
    ax.set_ylabel("Amount (₹)", fontsize=9, color=ESPRESSO)
    ax.set_title("Monthly Spending", fontsize=11, color=OXBLOOD, fontweight="bold")
    ax.set_ylim(0, max(values) * 1.2)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.02,
            f"₹{val:,.0f}",
            ha="center", va="bottom", fontsize=8, color=ESPRESSO,
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

    ax.barh(list(y), limits,    color=VINTAGE_ROSE, edgecolor=CHAMPAGNE, linewidth=0.8, label="Limit",   height=0.45)
    ax.barh(list(y), spendings, color=OXBLOOD,      edgecolor=SURFACE,   linewidth=0.8, label="Spent",   height=0.45)

    ax.set_yticks(list(y))
    ax.set_yticklabels(categories, fontsize=9)
    ax.set_xlabel("Amount (₹)", fontsize=9, color=ESPRESSO)
    ax.set_title("Budget Utilization", fontsize=11, color=OXBLOOD, fontweight="bold")

    legend_patches = [
        mpatches.Patch(color=VINTAGE_ROSE, label="Limit"),
        mpatches.Patch(color=OXBLOOD,      label="Spent"),
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
    ax.bar(x - width, budgets, width, label="Budget", color=VINTAGE_ROSE, edgecolor=SURFACE)
    ax.bar(x,         spents,  width, label="Spent",  color=OXBLOOD,      edgecolor=SURFACE)
    ax.bar(x + width, saveds,  width, label="Saved",  color=EMERALD_SAGE, edgecolor=SURFACE)

    ax.set_ylabel("Amount (₹)", fontsize=9, color=ESPRESSO)
    ax.set_title("Historical Budget vs. Spent vs. Saved", fontsize=11, color=OXBLOOD, fontweight="bold")
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
    ax.barh(y - height/2, spent_vals, height, label="Used (Spent)", color=OXBLOOD,      edgecolor=SURFACE)
    ax.barh(y + height/2, saved_vals, height, label="Saved",        color=EMERALD_SAGE, edgecolor=SURFACE)

    ax.set_yticks(y)
    ax.set_yticklabels(categories, fontsize=9)
    ax.set_xlabel("Amount (₹)", fontsize=9, color=ESPRESSO)
    ax.set_title("Month-End Breakdown: Used vs. Saved", fontsize=11, color=OXBLOOD, fontweight="bold")
    ax.legend(fontsize=8, framealpha=0, loc="lower right")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

