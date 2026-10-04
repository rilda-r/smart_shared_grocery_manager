"""
components/grocery_table.py
===========================
Grocery list table component.
"""

import streamlit as st
from utils.formatting import badge_html
from mock.mock_data import get_username


def render_grocery_table(
    items: list,
    current_user_id: int,
    on_edit=None,
    on_delete=None,
):
    """
    Render the grocery items as an interactive table.

    Args:
        items: list of GroceryItem dicts
        current_user_id: logged-in user's id (for permission checks)
        on_edit: optional callback(item) for edit action
        on_delete: optional callback(item_id) for delete action
    """
    if not items:
        st.markdown(
            """
            <div style="text-align:center; padding:2rem; color:#5B6459;">
                <div style="font-size:2.5rem;">🛒</div>
                <div style="font-weight:600; color:#20261F; margin-top:0.5rem;">No items yet</div>
                <div style="font-size:0.88rem; margin-top:0.3rem;">Add your first grocery item above.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Header row
    cols = st.columns([3, 1, 2, 2, 1, 1])
    for col, header in zip(cols, ["Item", "Qty", "Added By", "Status", "Edit", "Delete"]):
        col.markdown(f"**{header}**")
    st.markdown("<hr style='margin:0.3rem 0 0.5rem 0; border-color:#D8D0BE;'>", unsafe_allow_html=True)

    for item in items:
        cols = st.columns([3, 1, 2, 2, 1, 1])
        cols[0].write(item["itemName"])
        cols[1].write(str(item["quantity"]))
        cols[2].write(get_username(item["userId"]))
        cols[3].markdown(badge_html(item["status"]), unsafe_allow_html=True)

        is_owner = item["userId"] == current_user_id

        with cols[4]:
            if is_owner and on_edit:
                if st.button("✏️", key=f"edit_item_{item['id']}"):
                    on_edit(item)
            elif not is_owner:
                st.markdown("—")

        with cols[5]:
            if is_owner and on_delete:
                if st.button("🗑️", key=f"del_item_{item['id']}"):
                    on_delete(item["id"])
            elif not is_owner:
                st.markdown("—")
