"""
mock/mock_data.py
=================
Canonical mock data for GrocEase frontend development.

FIELD NAMES: camelCase (as per contract schema).
PYTHON VARIABLES: snake_case (as required by naming convention).

Do NOT change field names — they mirror the backend contract exactly.
"""

# ──────────────────────────────────────────────
# USERS
# ──────────────────────────────────────────────
MOCK_USERS = [
    {"id": 1, "username": "teja", "email": "teja@example.com"},
    {"id": 2, "username": "arjun", "email": "arjun@example.com"},
    {"id": 3, "username": "meera", "email": "meera@example.com"},
]

# The "logged in" user for all mock sessions
MOCK_CURRENT_USER = MOCK_USERS[0]

# ──────────────────────────────────────────────
# ROOMS
# ──────────────────────────────────────────────
MOCK_ROOMS = [
    {
        "id": 101,
        "name": "Home Grocery",
        "creatorId": 1,
        "createdAt": "2026-09-01T10:00:00",
        "code": "HG-4821",
    },
    {
        "id": 102,
        "name": "Office Snacks",
        "creatorId": 2,
        "createdAt": "2026-09-05T09:00:00",
        "code": "OS-7733",
    },
]

# ──────────────────────────────────────────────
# ROOM MEMBERS
# ──────────────────────────────────────────────
MOCK_ROOM_MEMBERS = [
    {"roomId": 101, "userId": 1, "role": "creator", "joinedAt": "2026-09-01T10:00:00"},
    {"roomId": 101, "userId": 2, "role": "member",  "joinedAt": "2026-09-02T11:00:00"},
    {"roomId": 101, "userId": 3, "role": "member",  "joinedAt": "2026-09-03T09:30:00"},
    {"roomId": 102, "userId": 2, "role": "creator", "joinedAt": "2026-09-05T09:00:00"},
    {"roomId": 102, "userId": 1, "role": "member",  "joinedAt": "2026-09-06T08:00:00"},
]

# ──────────────────────────────────────────────
# GROCERY ITEMS
# ──────────────────────────────────────────────
MOCK_GROCERY_ITEMS = [
    {
        "id": 1001,
        "roomId": 101,
        "userId": 1,
        "itemName": "Milk",
        "quantity": 2,
        "status": "pending",
        "createdAt": "2026-09-01T10:30:00",
        "updatedAt": "2026-09-01T10:30:00",
    },
    {
        "id": 1002,
        "roomId": 101,
        "userId": 2,
        "itemName": "Bread",
        "quantity": 1,
        "status": "pending",
        "createdAt": "2026-09-01T11:00:00",
        "updatedAt": "2026-09-01T11:00:00",
    },
    {
        "id": 1003,
        "roomId": 101,
        "userId": 1,
        "itemName": "Eggs",
        "quantity": 12,
        "status": "purchased",
        "createdAt": "2026-09-01T11:30:00",
        "updatedAt": "2026-09-02T10:00:00",
    },
    {
        "id": 1004,
        "roomId": 101,
        "userId": 3,
        "itemName": "Butter",
        "quantity": 1,
        "status": "unavailable",
        "createdAt": "2026-09-01T12:00:00",
        "updatedAt": "2026-09-02T10:15:00",
    },
    {
        "id": 1005,
        "roomId": 101,
        "userId": 1,
        "itemName": "Orange Juice",
        "quantity": 2,
        "status": "pending",
        "createdAt": "2026-09-03T08:00:00",
        "updatedAt": "2026-09-03T08:00:00",
    },
    {
        "id": 1006,
        "roomId": 102,
        "userId": 2,
        "itemName": "Biscuits",
        "quantity": 3,
        "status": "pending",
        "createdAt": "2026-09-05T10:00:00",
        "updatedAt": "2026-09-05T10:00:00",
    },
]

# ──────────────────────────────────────────────
# BILLS
# ──────────────────────────────────────────────
MOCK_BILLS = [
    {
        "id": 501,
        "roomId": 101,
        "uploadedBy": 1,
        "fileName": "grocery_bill_sep1.jpg",
        "ocrStatus": "completed",
        "totalAmount": 850.00,
        "createdAt": "2026-09-01T18:00:00",
    },
    {
        "id": 502,
        "roomId": 101,
        "uploadedBy": 2,
        "fileName": "supermart_sep5.png",
        "ocrStatus": "completed",
        "totalAmount": 1240.00,
        "createdAt": "2026-09-05T19:00:00",
    },
]

# ──────────────────────────────────────────────
# BILL ITEMS
# ──────────────────────────────────────────────
MOCK_BILL_ITEMS = [
    {
        "id": 701,
        "billId": 501,
        "itemName": "Milk",
        "quantity": 2,
        "unitPrice": 40.00,
        "totalPrice": 80.00,
        "matchedGroceryItemId": 1001,
        "assignedUserId": 1,
    },
    {
        "id": 702,
        "billId": 501,
        "itemName": "Bread",
        "quantity": 1,
        "unitPrice": 35.00,
        "totalPrice": 35.00,
        "matchedGroceryItemId": 1002,
        "assignedUserId": 2,
    },
    {
        "id": 703,
        "billId": 501,
        "itemName": "Eggs",
        "quantity": 12,
        "unitPrice": 8.00,
        "totalPrice": 96.00,
        "matchedGroceryItemId": 1003,
        "assignedUserId": 1,
    },
    {
        "id": 704,
        "billId": 501,
        "itemName": "Cooking Oil",
        "quantity": 1,
        "unitPrice": 200.00,
        "totalPrice": 200.00,
        "matchedGroceryItemId": None,
        "assignedUserId": None,
    },
    {
        "id": 705,
        "billId": 502,
        "itemName": "Orange Juice",
        "quantity": 2,
        "unitPrice": 120.00,
        "totalPrice": 240.00,
        "matchedGroceryItemId": 1005,
        "assignedUserId": 1,
    },
    {
        "id": 706,
        "billId": 502,
        "itemName": "Biscuits",
        "quantity": 3,
        "unitPrice": 30.00,
        "totalPrice": 90.00,
        "matchedGroceryItemId": 1006,
        "assignedUserId": 2,
    },
]

# ──────────────────────────────────────────────
# PAYMENTS
# ──────────────────────────────────────────────
MOCK_PAYMENTS = [
    {
        "id": 801,
        "roomId": 101,
        "billId": 501,
        "payerUserId": 2,
        "payeeUserId": 1,
        "amount": 35.00,
        "paymentStatus": "pending",
        "createdAt": "2026-09-01T18:10:00",
        "settledAt": None,
        "reportedAt": None,
    },
    {
        "id": 802,
        "roomId": 101,
        "billId": 501,
        "payerUserId": 3,
        "payeeUserId": 1,
        "amount": 50.00,
        "paymentStatus": "settled",
        "createdAt": "2026-09-01T18:15:00",
        "settledAt": "2026-09-02T10:00:00",
        "reportedAt": None,
    },
    {
        "id": 803,
        "roomId": 101,
        "billId": 502,
        "payerUserId": 1,
        "payeeUserId": 2,
        "amount": 240.00,
        "paymentStatus": "pending",
        "createdAt": "2026-09-05T19:30:00",
        "settledAt": None,
        "reportedAt": None,
    },
    {
        "id": 804,
        "roomId": 101,
        "billId": 502,
        "payerUserId": 1,
        "payeeUserId": 2,
        "amount": 120.00,
        "paymentStatus": "reported",
        "createdAt": "2026-09-05T19:35:00",
        "settledAt": None,
        "reportedAt": "2026-09-06T08:00:00",
    },
]

# ──────────────────────────────────────────────
# PERSONAL EXPENSES
# ──────────────────────────────────────────────
MOCK_PERSONAL_EXPENSES = [
    {
        "id": 901,
        "userId": 1,
        "amount": 250.00,
        "category": "Food",
        "expenseDate": "2026-09-01",
        "description": "Lunch",
        "createdAt": "2026-09-01T19:00:00",
    },
    {
        "id": 902,
        "userId": 1,
        "amount": 1500.00,
        "category": "Transport",
        "expenseDate": "2026-09-03",
        "description": "Monthly bus pass",
        "createdAt": "2026-09-03T08:30:00",
    },
    {
        "id": 903,
        "userId": 1,
        "amount": 800.00,
        "category": "Food",
        "expenseDate": "2026-09-07",
        "description": "Weekend groceries",
        "createdAt": "2026-09-07T20:00:00",
    },
    {
        "id": 904,
        "userId": 1,
        "amount": 300.00,
        "category": "Entertainment",
        "expenseDate": "2026-09-10",
        "description": "Movie tickets",
        "createdAt": "2026-09-10T21:00:00",
    },
    {
        "id": 905,
        "userId": 1,
        "amount": 450.00,
        "category": "Utilities",
        "expenseDate": "2026-09-12",
        "description": "Electricity bill",
        "createdAt": "2026-09-12T10:00:00",
    },
    {
        "id": 906,
        "userId": 1,
        "amount": 600.00,
        "category": "Food",
        "expenseDate": "2026-09-15",
        "description": "Dinner out",
        "createdAt": "2026-09-15T22:00:00",
    },
    {
        "id": 907,
        "userId": 1,
        "amount": 200.00,
        "category": "Healthcare",
        "expenseDate": "2026-09-18",
        "description": "Pharmacy",
        "createdAt": "2026-09-18T11:30:00",
    },
]

# ──────────────────────────────────────────────
# BUDGETS
# ──────────────────────────────────────────────
MOCK_BUDGETS = [
    {
        "id": 1001,
        "userId": 1,
        "category": "Food",
        "monthlyLimit": 5000.00,
        "createdAt": "2026-09-01T19:00:00",
        "updatedAt": "2026-09-01T19:00:00",
    },
    {
        "id": 1002,
        "userId": 1,
        "category": "Transport",
        "monthlyLimit": 2000.00,
        "createdAt": "2026-09-01T19:05:00",
        "updatedAt": "2026-09-01T19:05:00",
    },
    {
        "id": 1003,
        "userId": 1,
        "category": "Entertainment",
        "monthlyLimit": 1000.00,
        "createdAt": "2026-09-01T19:10:00",
        "updatedAt": "2026-09-01T19:10:00",
    },
    {
        "id": 1004,
        "userId": 1,
        "category": "Utilities",
        "monthlyLimit": 400.00,
        "createdAt": "2026-09-01T19:15:00",
        "updatedAt": "2026-09-01T19:15:00",
    },
    {
        "id": 1005,
        "userId": 1,
        "category": "Healthcare",
        "monthlyLimit": 500.00,
        "createdAt": "2026-09-01T19:20:00",
        "updatedAt": "2026-09-01T19:20:00",
    },
]

# ──────────────────────────────────────────────
# EXPENSE CATEGORIES (canonical list)
# ──────────────────────────────────────────────
EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Other",
]

# ──────────────────────────────────────────────
# ITEM STATUSES
# ──────────────────────────────────────────────
ITEM_STATUSES = ["pending", "purchased", "unavailable"]

# ──────────────────────────────────────────────
# PAYMENT STATUSES
# ──────────────────────────────────────────────
PAYMENT_STATUSES = ["pending", "settled", "reported"]

# ──────────────────────────────────────────────
# USERNAME LOOKUP HELPER
# ──────────────────────────────────────────────
USER_BY_ID = {u["id"]: u for u in MOCK_USERS}


def get_username(user_id: int) -> str:
    """Return username string for a given user_id."""
    user = USER_BY_ID.get(user_id)
    return user["username"] if user else f"User {user_id}"
