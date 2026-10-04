import os

os.environ.setdefault("GROCEASE_BCRYPT_ROUNDS", "4")

from decimal import Decimal

import pytest

from database.seed import (
    database_available_for_tests,
    make_test_room,
    make_test_user,
    prepare_test_database,
)
from services import ocr_service
from services.bill_service import create_bill, get_bill, update_bill_items
from services.ocr_service import OCRError, OCRProvider, parse_bill_items, process_bill

DB = database_available_for_tests()
needs_db = pytest.mark.skipif(not DB, reason="MySQL test database unavailable")

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
RECEIPT = """FRESH MART
Date: 04/10/2026
2 x Amul Milk 1L        90.00
Bread                   40.00
Eggs 12 pcs   1   65.00   65.00
Tomato  3  20.00  60.00
Rice 5kg  Rs.1,250.50
SUBTOTAL               1505.50
GST 5%                   75.28
TOTAL                  1580.78
Thank you!
"""


class FakeProvider(OCRProvider):
    name = "fake"

    def __init__(self, text=None, error=None):
        self.text, self.error = text, error

    def extract_text(self, image_bytes):
        if self.error:
            raise OCRError(self.error)
        return self.text


@pytest.fixture(autouse=True)
def fresh_db():
    if DB:
        prepare_test_database()


# ------------------------------------------------------------- parsing (pure)
def test_parse_bill_items_quantities_prices_and_total():
    parsed = parse_bill_items(RECEIPT)
    by_name = {i["item_name"]: i for i in parsed["items"]}
    assert parsed["total_amount"] == Decimal("1580.78")
    assert set(by_name) == {"Amul Milk 1L", "Bread", "Eggs 12 pcs", "Tomato", "Rice 5kg"}
    milk = by_name["Amul Milk 1L"]
    assert (milk["quantity"], milk["unit_price"], milk["total_price"]) == (
        Decimal("2.000"), Decimal("45.00"), Decimal("90.00"))
    tomato = by_name["Tomato"]
    assert (tomato["quantity"], tomato["unit_price"], tomato["total_price"]) == (
        Decimal("3.000"), Decimal("20.00"), Decimal("60.00"))
    assert by_name["Bread"]["quantity"] == Decimal("1.000")
    assert by_name["Rice 5kg"]["total_price"] == Decimal("1250.50")


def test_parse_garbage_yields_nothing():
    assert parse_bill_items("###\n\nlorem ipsum\n12345")["items"] == []


# ------------------------------------------------------ process_bill (no DB)
def test_ocr_failure_is_controlled_not_a_crash():
    r = process_bill(PNG, "bill.png", FakeProvider(error="engine exploded"))
    assert not r["success"] and r["error_code"] == "ocr_failed"
    assert r["data"]["manual_entry_required"] and r["data"]["ocr_status"] == "failed"
    assert "exploded" not in r["message"]  # internals not leaked


def test_unexpected_provider_exception_is_contained():
    class Boom(OCRProvider):
        def extract_text(self, image_bytes):
            raise RuntimeError("secret internal detail")

    r = process_bill(PNG, "bill.png", Boom())
    assert r["error_code"] == "ocr_failed" and "secret" not in r["message"]


def test_no_items_recognised_is_controlled_failure():
    r = process_bill(PNG, "bill.png", FakeProvider(text="nothing useful here"))
    assert r["error_code"] == "ocr_failed"


def test_successful_processing():
    r = process_bill(PNG, "bill.png", FakeProvider(text=RECEIPT))
    assert r["success"] and r["data"]["ocr_status"] == "completed" and len(r["data"]["items"]) == 5


def test_missing_engine_reports_failure(monkeypatch):
    class Missing(OCRProvider):
        def extract_text(self, image_bytes):
            raise OCRError("Tesseract OCR libraries are not installed.")

    ocr_service.register_provider("missing", Missing)
    monkeypatch.setenv("GROCEASE_OCR_PROVIDER", "missing")
    assert process_bill(PNG, "bill.png")["error_code"] == "ocr_failed"


@pytest.mark.parametrize(
    "name,content",
    [
        ("bill.exe", PNG),
        ("bill.png", b"not really a png"),
        ("bill.pdf", PNG),
        ("bill.png", b""),
        ("../../etc/passwd", PNG),
    ],
)
def test_invalid_files_rejected_before_ocr(name, content):
    r = process_bill(content, name, FakeProvider(text=RECEIPT))
    assert not r["success"] and r["error_code"] == "invalid_input"


# ------------------------------------------------------------- bills with DB
@needs_db
def test_create_bill_from_ocr_persists_status_and_items():
    a = make_test_user("alice")
    room = make_test_room(a)["id"]
    r = create_bill(a, room, "bill.png", PNG, ocr_provider=FakeProvider(text=RECEIPT))
    assert r["success"] and r["data"]["ocr_status"] == "completed"
    assert r["data"]["total_amount"] == Decimal("1580.78") and len(r["data"]["items"]) == 5
    assert set(r["data"]["items"][0]) == {"id", "bill_id", "item_name", "quantity", "unit_price",
                                          "total_price", "matched_grocery_item_id", "assigned_user_id"}
    assert get_bill(a, r["data"]["id"])["data"]["file_name"] == "bill.png"


@needs_db
def test_ocr_failure_creates_bill_marked_failed_and_allows_manual_entry():
    a = make_test_user("alice")
    room = make_test_room(a)["id"]
    r = create_bill(a, room, "bill.png", PNG, ocr_provider=FakeProvider(error="boom"))
    assert r["success"] and r["data"]["ocr_status"] == "failed" and r["data"]["manual_entry_required"]
    assert r["data"]["items"] == []
    manual = update_bill_items(a, r["data"]["id"], [
        {"item_name": "Milk", "quantity": 2, "unit_price": "45.00"},
        {"item_name": "Bread", "total_price": "40.00"},
    ])
    assert manual["success"] and manual["data"]["total_amount"] == Decimal("130.00")


@needs_db
def test_invalid_bill_items_rejected_and_missing_bill_reported():
    a, b = make_test_user("alice"), make_test_user("bob")
    room = make_test_room(a)["id"]
    bill = create_bill(a, room, items=[{"item_name": "Milk", "unit_price": 10}])["data"]["id"]
    for bad in ([], [{"item_name": "", "unit_price": 1}], [{"item_name": "X", "unit_price": -1}],
                [{"item_name": "X"}], [{"item_name": "X", "quantity": 0, "unit_price": 1}],
                [{"item_name": "X", "unit_price": 1, "assigned_user_id": b}], "nope"):
        assert update_bill_items(a, bill, bad)["error_code"] == "invalid_bill_item"
    assert get_bill(a, 99999)["error_code"] == "bill_not_found"
    assert get_bill(b, bill)["error_code"] == "bill_not_found"  # non-member cannot see it
    assert create_bill(a, room)["error_code"] == "invalid_input"
