"""
tests/test_receipt_scanning.py
==============================
Unit tests for:
- Receipt structured parsing and mathematical validation (Decimal arithmetic, tolerance, currency signs)
- Item normalization and fuzzy matching with multiple requesters for one item
- Proportional vs equal tax, discount, and charge distribution
- Deterministic penny rounding (sum of shares equals total exactly)
- Safe error handling without crashes
"""

from decimal import Decimal
import pytest

from services.receipt_ocr_service import (
    to_decimal,
    validate_receipt_math,
    _parse_tesseract_text,
    process_receipt_file,
)
from services.item_matching_service import (
    normalize_item_name,
    calculate_match_score,
    match_receipt_items,
)
from services.receipt_split_service import (
    split_amount_proportionally,
    split_amount_equally,
    calculate_receipt_split,
)


# ── 1. Decimal & Math Validation Tests ─────────────────────────────────────────

def test_to_decimal_handling():
    assert to_decimal("45.50") == Decimal("45.50")
    assert to_decimal("₹ 1,250.75") == Decimal("1250.75")
    assert to_decimal("$99.99") == Decimal("99.99")
    assert to_decimal("-15.00") == Decimal("-15.00")
    assert to_decimal(None) == Decimal("0.00")
    assert to_decimal("invalid") == Decimal("0.00")


def test_validate_receipt_math_exact_match():
    items = [
        {"line_total": Decimal("90.00")},
        {"line_total": Decimal("40.00")},
        {"line_total": Decimal("70.00")},
    ]
    tax = Decimal("10.00")
    discount = Decimal("5.00")
    charges = Decimal("2.00")
    # 90 + 40 + 70 + 10 + 2 - 5 = 207.00
    total = Decimal("207.00")
    
    is_valid, calc_tot, warning = validate_receipt_math(items, tax, discount, charges, total)
    assert is_valid is True
    assert calc_tot == Decimal("207.00")
    assert warning == ""


def test_validate_receipt_math_mismatch_detected():
    items = [{"line_total": Decimal("100.00")}]
    tax = Decimal("10.00")
    discount = Decimal("0.00")
    charges = Decimal("0.00")
    total = Decimal("120.00")  # Actual sum is 110.00, mismatch of 10.00
    
    is_valid, calc_tot, warning = validate_receipt_math(items, tax, discount, charges, total)
    assert is_valid is False
    assert calc_tot == Decimal("110.00")
    assert "Math mismatch" in warning


# ── 2. Item Normalization & Fuzzy Matching Tests ──────────────────────────────

def test_normalize_item_name():
    assert normalize_item_name("Amul Fresh Milk 1L") == "amul milk"
    assert normalize_item_name("Organic Farm Eggs 12 pcs") == "egg"
    assert normalize_item_name("Red Onions 1 kg") == "red onion"
    assert normalize_item_name("Whole Wheat Breads") == "whole wheat bread"


def test_match_score():
    score = calculate_match_score("Amul Taaza Toned Milk 1L", "Milk")
    assert score >= 70.0

    score_exact = calculate_match_score("Whole Wheat Bread", "whole wheat bread 400g")
    assert score_exact >= 80.0

    score_unrelated = calculate_match_score("Dishwashing Liquid", "Bananas")
    assert score_unrelated < 40.0


def test_multi_requester_proportional_split():
    """
    Scenario: Rilda wants 2 milk, Tejashree wants 1 milk.
    Receipt contains 3 milk @ ₹45.00 each = ₹135.00.
    Receipt line must be split proportionally: Rilda gets 2 (₹90), Tejashree gets 1 (₹45).
    """
    receipt_items = [
        {"name": "Fresh Milk 1L", "quantity": Decimal("3"), "unit_price": Decimal("45.00"), "line_total": Decimal("135.00")}
    ]
    pending_grocery = [
        {"id": 101, "userId": 1, "itemName": "Milk", "quantity": 2},  # Rilda
        {"id": 102, "userId": 2, "itemName": "Milk", "quantity": 1},  # Tejashree
    ]
    room_members = [
        {"user_id": 1, "display_name": "Rilda"},
        {"user_id": 2, "display_name": "Tejashree"},
    ]

    res = match_receipt_items(receipt_items, pending_grocery, room_members, shopper_user_id=1)
    matched = res["matched_items"]
    assert len(matched) == 1
    item = matched[0]
    assert item["total_requested_qty"] == Decimal("3")
    assert item["qty_difference"] == Decimal("0")

    assignments = {a["user_id"]: a for a in item["assignments"]}
    assert len(assignments) == 2
    assert assignments[1]["quantity"] == Decimal("2.000")
    assert assignments[1]["amount"] == Decimal("90.00")
    assert assignments[2]["quantity"] == Decimal("1.000")
    assert assignments[2]["amount"] == Decimal("45.00")
    assert assignments[1]["amount"] + assignments[2]["amount"] == Decimal("135.00")


def test_multi_requester_with_receipt_qty_difference():
    """
    Scenario: Requesters ask for total 3 milk, but receipt has 2 milk.
    """
    receipt_items = [
        {"name": "Milk 1L", "quantity": Decimal("2"), "unit_price": Decimal("50.00"), "line_total": Decimal("100.00")}
    ]
    pending_grocery = [
        {"id": 101, "userId": 1, "itemName": "Milk", "quantity": 2},
        {"id": 102, "userId": 2, "itemName": "Milk", "quantity": 1},
    ]
    room_members = [
        {"user_id": 1, "display_name": "Rilda"},
        {"user_id": 2, "display_name": "Tejashree"},
    ]

    res = match_receipt_items(receipt_items, pending_grocery, room_members, shopper_user_id=1)
    matched = res["matched_items"]
    assert matched[0]["qty_difference"] == Decimal("-1")  # 2 - 3 = -1 short
    # Total assigned money still equals 100.00 exactly
    total_assigned_amt = sum(a["amount"] for a in matched[0]["assignments"])
    assert total_assigned_amt == Decimal("100.00")


# ── 3. Proportional Tax & Deterministic Rounding Tests ─────────────────────────

def test_split_amount_proportionally_penny_exact():
    """
    ₹100 split among 3 members with equal weights (1:1:1).
    100 / 3 = 33.3333... cents.
    The largest-remainder method must allocate 33.34, 33.33, 33.33, summing to 100.00 EXACTLY.
    """
    weights = {1: Decimal("10.00"), 2: Decimal("10.00"), 3: Decimal("10.00")}
    split = split_amount_proportionally(Decimal("100.00"), weights)
    
    assert sum(split.values()) == Decimal("100.00")
    assert split[1] == Decimal("33.34")
    assert split[2] == Decimal("33.33")
    assert split[3] == Decimal("33.33")


def test_receipt_full_split_reconciliation():
    """
    Full split: Items cost + Tax - Discount.
    Verify sum(member shares) == receipt total.
    Verify shopper does not owe money to themselves.
    """
    matched_items = [
        {
            "name": "Milk",
            "receipt_quantity": Decimal("2"),
            "unit_price": Decimal("50.00"),
            "line_total": Decimal("100.00"),
            "assignments": [
                {"user_id": 1, "quantity": Decimal("1"), "amount": Decimal("50.00")},  # Shopper
                {"user_id": 2, "quantity": Decimal("1"), "amount": Decimal("50.00")},  # Member B
            ]
        }
    ]
    extra_items = [
        {
            "name": "Chocolate",
            "quantity": Decimal("1"),
            "unit_price": Decimal("60.00"),
            "line_total": Decimal("60.00"),
            "assignments": [
                {"user_id": 3, "quantity": Decimal("1"), "amount": Decimal("60.00")},  # Member C
            ]
        }
    ]
    # Subtotal = 50 (user 1) + 50 (user 2) + 60 (user 3) = 160.00
    tax = Decimal("16.00")
    discount = Decimal("6.00")
    charges = Decimal("0.00")
    total = Decimal("170.00")
    
    result = calculate_receipt_split(
        matched_items=matched_items,
        extra_items=extra_items,
        tax=tax,
        discount=discount,
        other_charges=charges,
        total=total,
        shopper_user_id=1,
        all_room_member_ids=[1, 2, 3],
        member_name_map={1: "Alice (Shopper)", 2: "Bob", 3: "Charlie"},
        tax_split_mode="proportional",
    )

    # Reconciled sum must equal receipt total
    assert result["reconciled_sum"] == Decimal("170.00")
    
    summaries = {m["user_id"]: m for m in result["member_summaries"]}
    # Shopper's debt to self is 0
    assert summaries[1]["owed_to_shopper"] == Decimal("0.00")
    # Other members owe their share
    assert summaries[2]["owed_to_shopper"] > Decimal("0.00")
    assert summaries[3]["owed_to_shopper"] > Decimal("0.00")

    # Debts list only contains members 2 and 3
    debts = {d["payer_user_id"]: d["amount"] for d in result["debts"]}
    assert 1 not in debts
    assert debts[2] == summaries[2]["owed_to_shopper"]
    assert debts[3] == summaries[3]["owed_to_shopper"]


# ── 4. Edge Cases & Robustness Tests ──────────────────────────────────────────

def test_empty_or_corrupt_receipt_no_crash():
    # Empty byte payload
    res = process_receipt_file(b"", "empty.png")
    assert res["success"] is False
    assert "error" in res
    assert res["total"] == Decimal("0.00")


def test_tesseract_raw_parser_edge_cases():
    raw_text = """
    SUPERMARKET
    Milk 2 x 45.00 90.00
    TAX 5.00
    DISCOUNT 10.00
    TOTAL 85.00
    """
    res = _parse_tesseract_text(raw_text)
    assert len(res["items"]) >= 1
    assert res["tax"] == Decimal("5.00")
    assert res["discount"] == Decimal("10.00")
    assert res["total"] == Decimal("85.00")
