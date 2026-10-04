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
FOREST  = "#1F4C3D"
MOSS    = "#3D7A5D"
SAGE    = "#E7EFE6"
GOLD    = "#A97A1F"
RUST    = "#9C4B3E"
INK_MUT = "#5B6459"
LINE    = "#D8D0BE"
PAPER   = "#F6F2E9"

CATEGORY_COLORS = [FOREST, MOSS, GOLD, RUST, "#4A90D9", "#7B5EA7", "#D4845A"]


def _base_fig(figsize=(6, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.tick_params(colors=INK_MUT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(LINE)
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
        wedgeprops={"linewidth": 1.5, "edgecolor": PAPER},
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_color(PAPER)
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
    ax.set_title("Spending by Category", fontsize=11, color=FOREST, fontweight="bold", pad=10)
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
    bars = ax.bar(labels, values, color=FOREST, edgecolor=PAPER, linewidth=0.8, width=0.55)
    ax.set_ylabel("Amount (₹)", fontsize=9, color=INK_MUT)
    ax.set_title("Monthly Spending", fontsize=11, color=FOREST, fontweight="bold")
    ax.set_ylim(0, max(values) * 1.2)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.02,
            f"₹{val:,.0f}",
            ha="center", va="bottom", fontsize=8, color=INK_MUT,
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

    ax.barh(list(y), limits,    color=SAGE,   edgecolor=LINE,   linewidth=0.8, label="Limit",   height=0.45)
    ax.barh(list(y), spendings, color=FOREST,  edgecolor=PAPER, linewidth=0.8, label="Spent",   height=0.45)

    ax.set_yticks(list(y))
    ax.set_yticklabels(categories, fontsize=9)
    ax.set_xlabel("Amount (₹)", fontsize=9, color=INK_MUT)
    ax.set_title("Budget Utilization", fontsize=11, color=FOREST, fontweight="bold")

    legend_patches = [
        mpatches.Patch(color=SAGE,   label="Limit"),
        mpatches.Patch(color=FOREST, label="Spent"),
    ]
    ax.legend(handles=legend_patches, fontsize=8, framealpha=0, loc="lower right")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
