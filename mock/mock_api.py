"""
mock/mock_api.py
================
UI-facing mock API functions for GrocEase.

These functions mimic the real backend API surface.
When real backend integration happens, swap these imports in each page
without changing the visual components.

All functions operate on in-memory copies stored in st.session_state
so changes persist for the duration of the session.
"""

import copy
import random
import string
import streamlit as st

from mock.mock_data import (
    MOCK_ROOMS,
    MOCK_ROOM_MEMBERS,
    MOCK_GROCERY_ITEMS,
    MOCK_BILLS,
    MOCK_BILL_ITEMS,
    MOCK_PAYMENTS,
    MOCK_PERSONAL_EXPENSES,
    MOCK_BUDGETS,
    MOCK_USERS,
)


# ─────────────────────────────────────────────────────────────
# SESSION STORE INITIALISER
# Called once per session to deep-copy mock data into state.
# ─────────────────────────────────────────────────────────────
def _init_store():
    if "store_rooms" not in st.session_state:
        st.session_state["store_rooms"] = copy.deepcopy(MOCK_ROOMS)
    if "store_room_members" not in st.session_state:
        st.session_state["store_room_members"] = copy.deepcopy(MOCK_ROOM_MEMBERS)
    if "store_grocery_items" not in st.session_state:
        st.session_state["store_grocery_items"] = copy.deepcopy(MOCK_GROCERY_ITEMS)
    if "store_bills" not in st.session_state:
        st.session_state["store_bills"] = copy.deepcopy(MOCK_BILLS)
    if "store_bill_items" not in st.session_state:
        st.session_state["store_bill_items"] = copy.deepcopy(MOCK_BILL_ITEMS)
    if "store_payments" not in st.session_state:
        st.session_state["store_payments"] = copy.deepcopy(MOCK_PAYMENTS)
    if "store_personal_expenses" not in st.session_state:
        st.session_state["store_personal_expenses"] = copy.deepcopy(MOCK_PERSONAL_EXPENSES)
    if "store_budgets" not in st.session_state:
        st.session_state["store_budgets"] = copy.deepcopy(MOCK_BUDGETS)
    if "store_next_id" not in st.session_state:
        st.session_state["store_next_id"] = 9000


def _next_id() -> int:
    _init_store()
    nid = st.session_state["store_next_id"]
    st.session_state["store_next_id"] += 1
    return nid


def _gen_room_code() -> str:
    prefix = "".join(random.choices(string.ascii_uppercase, k=2))
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{prefix}-{suffix}"


# ─────────────────────────────────────────────────────────────
# ROOMS
# ─────────────────────────────────────────────────────────────
def get_rooms(user_id: int) -> list:
    """Return all rooms the user is a member of."""
    _init_store()
    member_room_ids = {
        m["roomId"]
        for m in st.session_state["store_room_members"]
        if m["userId"] == user_id
    }
    return [r for r in st.session_state["store_rooms"] if r["id"] in member_room_ids]


def create_room(room_name: str, creator_user_id: int) -> dict:
    """Create a new room and return it (with generated code)."""
    _init_store()
    room = {
        "id": _next_id(),
        "name": room_name.strip(),
        "creatorId": creator_user_id,
        "createdAt": "2026-10-04T22:00:00",
        "code": _gen_room_code(),
    }
    st.session_state["store_rooms"].append(room)
    member = {
        "roomId": room["id"],
        "userId": creator_user_id,
        "role": "creator",
        "joinedAt": "2026-10-04T22:00:00",
    }
    st.session_state["store_room_members"].append(member)
    return room


def join_room(room_code: str, user_id: int) -> dict | None:
    """
    Join a room by code. Returns the room dict on success, None if code not found
    or user is already a member.
    """
    _init_store()
    room = next(
        (r for r in st.session_state["store_rooms"] if r.get("code") == room_code.strip().upper()),
        None,
    )
    if not room:
        return None
    already = any(
        m["roomId"] == room["id"] and m["userId"] == user_id
        for m in st.session_state["store_room_members"]
    )
    if already:
        return None
    st.session_state["store_room_members"].append(
        {
            "roomId": room["id"],
            "userId": user_id,
            "role": "member",
            "joinedAt": "2026-10-04T22:00:00",
        }
    )
    return room


def leave_room(room_id: int, user_id: int) -> bool:
    """Remove a user from a room. Returns True on success."""
    _init_store()
    before = len(st.session_state["store_room_members"])
    st.session_state["store_room_members"] = [
        m
        for m in st.session_state["store_room_members"]
        if not (m["roomId"] == room_id and m["userId"] == user_id)
    ]
    return len(st.session_state["store_room_members"]) < before


def get_room_members(room_id: int) -> list:
    """Return all member records for a room."""
    _init_store()
    return [m for m in st.session_state["store_room_members"] if m["roomId"] == room_id]


# ─────────────────────────────────────────────────────────────
# GROCERY ITEMS
# ─────────────────────────────────────────────────────────────
def get_grocery_items(room_id: int) -> list:
    _init_store()
    return [i for i in st.session_state["store_grocery_items"] if i["roomId"] == room_id]


def add_grocery_item(room_id: int, user_id: int, item_name: str, quantity: int) -> dict:
    _init_store()
    item = {
        "id": _next_id(),
        "roomId": room_id,
        "userId": user_id,
        "itemName": item_name.strip(),
        "quantity": quantity,
        "status": "pending",
        "createdAt": "2026-10-04T22:00:00",
        "updatedAt": "2026-10-04T22:00:00",
    }
    st.session_state["store_grocery_items"].append(item)
    return item


def update_grocery_item(item_id: int, item_name: str, quantity: int) -> bool:
    _init_store()
    for item in st.session_state["store_grocery_items"]:
        if item["id"] == item_id:
            item["itemName"] = item_name.strip()
            item["quantity"] = quantity
            item["updatedAt"] = "2026-10-04T22:00:00"
            return True
    return False


def delete_grocery_item(item_id: int) -> bool:
    _init_store()
    before = len(st.session_state["store_grocery_items"])
    st.session_state["store_grocery_items"] = [
        i for i in st.session_state["store_grocery_items"] if i["id"] != item_id
    ]
    return len(st.session_state["store_grocery_items"]) < before


# ─────────────────────────────────────────────────────────────
# SHOPPING MODE
# ─────────────────────────────────────────────────────────────
def start_shopping(room_id: int) -> bool:
    """Mark shopping session as started (sets session state flag)."""
    st.session_state["shopping_mode"] = True
    return True


def update_grocery_item_status(item_id: int, status: str) -> bool:
    """Update the status of a grocery item (pending/purchased/unavailable)."""
    _init_store()
    for item in st.session_state["store_grocery_items"]:
        if item["id"] == item_id:
            item["status"] = status
            item["updatedAt"] = "2026-10-04T22:00:00"
            return True
    return False


def finish_shopping(room_id: int) -> dict:
    """End shopping session. Returns a summary dict."""
    st.session_state["shopping_mode"] = False
    items = get_grocery_items(room_id)
    summary = {
        "total": len(items),
        "purchased": sum(1 for i in items if i["status"] == "purchased"),
        "unavailable": sum(1 for i in items if i["status"] == "unavailable"),
        "pending": sum(1 for i in items if i["status"] == "pending"),
    }
    return summary


# ─────────────────────────────────────────────────────────────
# BILLS
# ─────────────────────────────────────────────────────────────
def upload_bill(room_id: int, user_id: int, file_name: str) -> dict:
    """Mock bill upload — returns a bill record with simulated OCR."""
    _init_store()
    bill = {
        "id": _next_id(),
        "roomId": room_id,
        "uploadedBy": user_id,
        "fileName": file_name,
        "ocrStatus": "completed",
        "totalAmount": round(random.uniform(300, 2000), 2),
        "createdAt": "2026-10-04T22:00:00",
    }
    st.session_state["store_bills"].append(bill)
    # Seed mock extracted items
    mock_extracted = [
        {"id": _next_id(), "billId": bill["id"], "itemName": "Rice",
         "quantity": 1, "unitPrice": 120.00, "totalPrice": 120.00,
         "matchedGroceryItemId": None, "assignedUserId": None},
        {"id": _next_id(), "billId": bill["id"], "itemName": "Sugar",
         "quantity": 2, "unitPrice": 45.00, "totalPrice": 90.00,
         "matchedGroceryItemId": None, "assignedUserId": None},
    ]
    st.session_state["store_bill_items"].extend(mock_extracted)
    return bill


def get_bill(bill_id: int) -> dict | None:
    _init_store()
    return next((b for b in st.session_state["store_bills"] if b["id"] == bill_id), None)


def get_bill_items(bill_id: int) -> list:
    _init_store()
    return [i for i in st.session_state["store_bill_items"] if i["billId"] == bill_id]


def update_bill_items(bill_id: int, items: list) -> bool:
    """Replace all bill items for a bill with the given list."""
    _init_store()
    st.session_state["store_bill_items"] = [
        i for i in st.session_state["store_bill_items"] if i["billId"] != bill_id
    ]
    st.session_state["store_bill_items"].extend(items)
    return True


def assign_bill_item(bill_item_id: int, assigned_user_id: int) -> bool:
    _init_store()
    for item in st.session_state["store_bill_items"]:
        if item["id"] == bill_item_id:
            item["assignedUserId"] = assigned_user_id
            return True
    return False


# ─────────────────────────────────────────────────────────────
# EXPENSE SPLITTING
# ─────────────────────────────────────────────────────────────
def calculate_bill_split(bill_id: int) -> dict:
    """
    Calculate per-user totals from assigned bill items.
    Returns {user_id: amount} mapping.
    """
    _init_store()
    items = get_bill_items(bill_id)
    split = {}
    for item in items:
        uid = item.get("assignedUserId")
        if uid is not None:
            split[uid] = split.get(uid, 0.0) + item["totalPrice"]
    return split


def calculate_equal_split(bill_id: int, member_user_ids: list) -> dict:
    """
    Split the bill total equally among given member user IDs.
    Returns {user_id: amount} mapping.
    """
    _init_store()
    bill = get_bill(bill_id)
    if not bill or not member_user_ids:
        return {}
    per_person = round(bill["totalAmount"] / len(member_user_ids), 2)
    return {uid: per_person for uid in member_user_ids}


# ─────────────────────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────────────────────
def get_payments(room_id: int) -> list:
    _init_store()
    return [p for p in st.session_state["store_payments"] if p["roomId"] == room_id]


def settle_payment(payment_id: int) -> bool:
    _init_store()
    for payment in st.session_state["store_payments"]:
        if payment["id"] == payment_id:
            payment["paymentStatus"] = "settled"
            payment["settledAt"] = "2026-10-04T22:00:00"
            return True
    return False


def report_payment(payment_id: int) -> bool:
    _init_store()
    for payment in st.session_state["store_payments"]:
        if payment["id"] == payment_id:
            payment["paymentStatus"] = "reported"
            payment["reportedAt"] = "2026-10-04T22:00:00"
            return True
    return False


# ─────────────────────────────────────────────────────────────
# PERSONAL EXPENSES
# ─────────────────────────────────────────────────────────────
def get_personal_expenses(user_id: int) -> list:
    _init_store()
    return [e for e in st.session_state["store_personal_expenses"] if e["userId"] == user_id]


def add_personal_expense(
    user_id: int, amount: float, category: str, expense_date: str, description: str
) -> dict:
    _init_store()
    expense = {
        "id": _next_id(),
        "userId": user_id,
        "amount": round(amount, 2),
        "category": category,
        "expenseDate": expense_date,
        "description": description,
        "createdAt": "2026-10-04T22:00:00",
    }
    st.session_state["store_personal_expenses"].append(expense)
    return expense


def update_personal_expense(
    expense_id: int, amount: float, category: str, expense_date: str, description: str
) -> bool:
    _init_store()
    for expense in st.session_state["store_personal_expenses"]:
        if expense["id"] == expense_id:
            expense["amount"] = round(amount, 2)
            expense["category"] = category
            expense["expenseDate"] = expense_date
            expense["description"] = description
            return True
    return False


def delete_personal_expense(expense_id: int) -> bool:
    _init_store()
    before = len(st.session_state["store_personal_expenses"])
    st.session_state["store_personal_expenses"] = [
        e for e in st.session_state["store_personal_expenses"] if e["id"] != expense_id
    ]
    return len(st.session_state["store_personal_expenses"]) < before


# ─────────────────────────────────────────────────────────────
# BUDGETS
# ─────────────────────────────────────────────────────────────
def get_budgets(user_id: int) -> list:
    _init_store()
    return [b for b in st.session_state["store_budgets"] if b["userId"] == user_id]


def create_budget(user_id: int, category: str, monthly_limit: float) -> dict:
    _init_store()
    budget = {
        "id": _next_id(),
        "userId": user_id,
        "category": category,
        "monthlyLimit": round(monthly_limit, 2),
        "createdAt": "2026-10-04T22:00:00",
        "updatedAt": "2026-10-04T22:00:00",
    }
    st.session_state["store_budgets"].append(budget)
    return budget


def update_budget(budget_id: int, monthly_limit: float) -> bool:
    _init_store()
    for budget in st.session_state["store_budgets"]:
        if budget["id"] == budget_id:
            budget["monthlyLimit"] = round(monthly_limit, 2)
            budget["updatedAt"] = "2026-10-04T22:00:00"
            return True
    return False


def delete_budget(budget_id: int) -> bool:
    _init_store()
    before = len(st.session_state["store_budgets"])
    st.session_state["store_budgets"] = [
        b for b in st.session_state["store_budgets"] if b["id"] != budget_id
    ]
    return len(st.session_state["store_budgets"]) < before
