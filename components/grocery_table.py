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
            <div style="background:#FFFFFF; border:1.5px dashed rgba(163, 150, 112, 0.45); border-radius:18px;
                        text-align:center; padding:2.5rem 1rem; color:#6B5A47; box-shadow:0 2px 8px rgba(55,39,19,0.02);">
                <div style="font-size:2.8rem; margin-bottom:0.4rem;">🛒</div>
                <div style="font-family:'Fraunces',Georgia,serif; font-size:1.1rem; font-weight:700; color:#372713;">No items yet</div>
                <div style="font-size:0.88rem; color:#6B5A47; margin-top:0.3rem;">Add your first grocery item using the form above.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Header row
    cols = st.columns([3, 1, 2, 2, 1, 1])
    for col, header in zip(cols, ["Item", "Qty", "Added By", "Status", "Edit", "Delete"]):
        col.markdown(f"<span style='font-size:0.82rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#A39670;'>{header}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:0.4rem 0 0.8rem 0; border:none; border-top:1.5px solid rgba(163, 150, 112, 0.35);'>", unsafe_allow_html=True)

    for item in items:
        cols = st.columns([3, 1, 2, 2, 1, 1])
        cols[0].write(item["itemName"])
        cols[1].write(str(item["quantity"]))
        
        # Display nickname / username attribution
        added_by_display = item.get("addedByName") or item.get("added_by_name") or get_username(item["userId"])
        cols[2].write(added_by_display)
        cols[3].markdown(badge_html(item["status"]), unsafe_allow_html=True)

        is_owner = item["userId"] == current_user_id
        is_purchased = item.get("status") == "purchased"

        with cols[4]:
            if is_purchased:
                st.markdown("<span title='Purchased items cannot be edited' style='color:#8C9588; font-size:0.95rem; cursor:not-allowed;'>🔒</span>", unsafe_allow_html=True)
            elif is_owner and on_edit:
                if st.button("✏️", key=f"edit_item_{item['id']}"):
                    on_edit(item)
            else:
                st.markdown("—")

        with cols[5]:
            if is_purchased:
                st.markdown("<span title='Purchased items cannot be deleted to protect purchase logs' style='color:#8C9588; font-size:0.95rem; cursor:not-allowed;'>🔒</span>", unsafe_allow_html=True)
            elif is_owner and on_delete:
                if st.button("🗑️", key=f"del_item_{item['id']}"):
                    on_delete(item["id"])
            else:
                st.markdown("—")
