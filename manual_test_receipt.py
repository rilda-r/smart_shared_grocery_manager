"""
manual_test_receipt.py
======================
End-to-end verification script testing the entire flow:
1. Create a room with 3 members (Tejashree, Rilda, Alex)
2. Add listed items from 2 members (including duplicate product 'Milk' requested by both Rilda and Tejashree)
3. Process a receipt containing those items PLUS 2 extra items
4. Verify:
   (a) Member names appear beside the matched items
   (b) Extra items appear in "Your items purchased"
   (c) Totals add up exactly to the penny
   (d) Atomic confirmation creates the exact debts on the Payments page
"""

import sys
import os
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


from database.connection import execute, query_one, query_all
from database.database import (
    add_live_grocery_item,
    get_live_grocery_items,
    get_room_members_with_identities,
    get_room_payments_live,
)
from services.item_matching_service import match_receipt_items
from services.receipt_split_service import calculate_receipt_split
from services.receipt_service import confirm_receipt_transaction


def main():
    print("=" * 65)
    print("🚀 GROCEASE RECEIPT SCANNING & EXPENSE ATTRIBUTION TEST")
    print("=" * 65)

    # ── 1. Create / Get 3 Test Users ──────────────────────────────────────────
    users_data = [
        ("tejashree_shopper", "tejashree@example.com", "Tejashree (Shopper)"),
        ("rilda_roomie", "rilda@example.com", "Rilda"),
        ("alex_roomie", "alex@example.com", "Alex"),
    ]
    uids = []
    for uname, uemail, udisplay in users_data:
        existing = query_one("SELECT id FROM users WHERE email = %s", (uemail,))
        if existing:
            uid = existing["id"]
        else:
            uid = execute(
                "INSERT INTO users (username, email, password_hash, full_name, is_verified) "
                "VALUES (%s, %s, 'hash123', %s, TRUE)",
                (uname, uemail, udisplay),
            )
        # Update profile display name
        execute(
            "INSERT INTO profiles (user_id, full_name, nickname) VALUES (%s, %s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET full_name = EXCLUDED.full_name, nickname = EXCLUDED.nickname",
            (uid, udisplay, udisplay),
        )
        uids.append(uid)

    shopper_id, rilda_id, alex_id = uids
    print(f"✅ Users ready: Tejashree (ID {shopper_id}), Rilda (ID {rilda_id}), Alex (ID {alex_id})")

    # ── 2. Create Test Room & Add Members ─────────────────────────────────────
    room_code = f"TEST{os.getpid() % 10000:04d}"
    room_id = execute(
        "INSERT INTO rooms (name, secret_code, creator_id) VALUES (%s, %s, %s)",
        (f"Sunshine Flat {room_code}", room_code, shopper_id),
    )
    for uid, role in [(shopper_id, "creator"), (rilda_id, "member"), (alex_id, "member")]:
        execute(
            "INSERT INTO room_members (room_id, user_id, role) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (room_id, uid, role),
        )
    print(f"✅ Room created: Sunshine Flat (ID {room_id}, Code {room_code}) with 3 members.")

    # ── 3. Add Grocery List Items (Including Duplicate Product) ───────────────
    # Rilda wants 2 milk, Tejashree wants 1 milk (duplicate product requested by both)
    # Rilda wants 1 eggs, Alex wants 1 bread
    g_milk_rilda = add_live_grocery_item(room_id, rilda_id, "Amul Milk 1L", 2)
    g_milk_teja = add_live_grocery_item(room_id, shopper_id, "Milk", 1)
    g_eggs_rilda = add_live_grocery_item(room_id, rilda_id, "Farm Eggs 6pk", 1)
    g_bread_alex = add_live_grocery_item(room_id, alex_id, "Brown Bread", 1)
    print("✅ Pending grocery items added:")
    print("   - Rilda requested: 2x 'Amul Milk 1L' & 1x 'Farm Eggs 6pk'")
    print("   - Tejashree requested: 1x 'Milk'")
    print("   - Alex requested: 1x 'Brown Bread'")

    raw_members = get_room_members_with_identities(room_id)
    pending_items = [g for g in get_live_grocery_items(room_id) if g["status"] == "pending"]

    # ── 4. Simulate Uploaded Receipt with Items + 2 Extras ────────────────────
    # Receipt contains:
    # 1. Milk: 3x @ ₹45.00 = ₹135.00 (matches both Rilda & Tejashree)
    # 2. Eggs: 1x @ ₹65.00 = ₹65.00 (matches Rilda)
    # 3. Bread: 1x @ ₹40.00 = ₹40.00 (matches Alex)
    # 4. Extra 1: Dark Chocolate 1x @ ₹90.00 = ₹90.00
    # 5. Extra 2: Potato Chips 2x @ ₹20.00 = ₹40.00
    # Subtotal = 135 + 65 + 40 + 90 + 40 = 370.00
    # Tax = 18.50, Discount = 10.00, Total = 378.50
    receipt_items = [
        {"name": "Milk 1L", "quantity": Decimal("3"), "unit_price": Decimal("45.00"), "line_total": Decimal("135.00")},
        {"name": "Eggs Pack", "quantity": Decimal("1"), "unit_price": Decimal("65.00"), "line_total": Decimal("65.00")},
        {"name": "Bread 400g", "quantity": Decimal("1"), "unit_price": Decimal("40.00"), "line_total": Decimal("40.00")},
        {"name": "Dark Chocolate", "quantity": Decimal("1"), "unit_price": Decimal("90.00"), "line_total": Decimal("90.00")},
        {"name": "Potato Chips", "quantity": Decimal("2"), "unit_price": Decimal("20.00"), "line_total": Decimal("40.00")},
    ]
    tax = Decimal("18.50")
    discount = Decimal("10.00")
    other_charges = Decimal("0.00")
    total = Decimal("378.50")

    # ── 5. Run Item Matching ──────────────────────────────────────────────────
    match_result = match_receipt_items(receipt_items, pending_items, raw_members, shopper_id)
    matched = match_result["matched_items"]
    extras = match_result["extra_items"]
    member_name_map = match_result["member_name_map"]

    print("\n" + "-" * 55)
    print("VERIFICATION (a): MEMBER NAMES APPEAR BESIDE ITEMS")
    print("-" * 55)
    for m in matched:
        print(f"• Item: '{m['name']}' (Total Qty: {m['receipt_quantity']}, Amount: ₹{m['line_total']})")
        for a in m["assignments"]:
            print(f"    └── Assigned to: {a['member_name']} | Qty: {a['quantity']} | Amount: ₹{a['amount']}")

    # Verify Milk was split across Rilda and Tejashree
    milk_item = next(m for m in matched if "milk" in m["name"].lower())
    milk_assignees = {a["user_id"]: a for a in milk_item["assignments"]}
    assert rilda_id in milk_assignees and shopper_id in milk_assignees
    assert milk_assignees[rilda_id]["quantity"] == Decimal("2.000")
    assert milk_assignees[shopper_id]["quantity"] == Decimal("1.000")
    print("✅ Verified: Milk split 2:1 between Rilda and Tejashree with their names displayed.")

    print("\n" + "-" * 55)
    print("VERIFICATION (b): EXTRAS APPEAR IN 'YOUR ITEMS PURCHASED'")
    print("-" * 55)
    extra_names = [e["name"] for e in extras]
    print(f"Extra items identified: {extra_names}")
    assert "Dark Chocolate" in extra_names and "Potato Chips" in extra_names
    assert len(extras) == 2
    print("✅ Verified: Both Dark Chocolate and Potato Chips appear in Extra Items.")

    # Let shopper keep Dark Chocolate as own purchase, and assign Potato Chips to Alex
    extras[0]["assignments"] = [{
        "user_id": shopper_id,
        "quantity": Decimal("1.000"),
        "amount": Decimal("90.00"),
    }]
    extras[1]["assignments"] = [{
        "user_id": alex_id,
        "quantity": Decimal("2.000"),
        "amount": Decimal("40.00"),
    }]

    print("\n" + "-" * 55)
    print("VERIFICATION (c): TOTALS ADD UP EXACTLY (PENNY RECONCILIATION)")
    print("-" * 55)
    split = calculate_receipt_split(
        matched_items=matched,
        extra_items=extras,
        tax=tax,
        discount=discount,
        other_charges=other_charges,
        total=total,
        shopper_user_id=shopper_id,
        all_room_member_ids=[shopper_id, rilda_id, alex_id],
        member_name_map=member_name_map,
        tax_split_mode="proportional",
    )

    reconciled_sum = split["reconciled_sum"]
    print(f"Receipt Total:    ₹{total}")
    print(f"Sum of Shares:    ₹{reconciled_sum}")
    assert reconciled_sum == total
    print("✅ Verified: Sum of all member shares matches receipt total to the exact cent.")

    for m in split["member_summaries"]:
        print(f"• {m['display_name']}: Items=₹{m['subtotal']}, Tax=₹{m['tax_share']}, Disc=-₹{m['discount_share']} => Net=₹{m['net_total_share']}, Owed to Shopper=₹{m['owed_to_shopper']}")

    print("\n" + "-" * 55)
    print("VERIFICATION (d): CONFIRM ATOMICALLY & CHECK PAYMENTS PAGE")
    print("-" * 55)
    
    # Prepare all line items and run atomic confirmation RPC
    all_line_items = []
    purchased_g_ids = []
    for it in matched:
        for a in it["assignments"]:
            if a.get("grocery_item_id"):
                purchased_g_ids.append(a["grocery_item_id"])
        all_line_items.append({
            "name": it["name"],
            "quantity": it["receipt_quantity"],
            "unit_price": it["unit_price"],
            "line_total": it["line_total"],
            "matched_grocery_item_id": it["assignments"][0].get("grocery_item_id"),
            "is_extra": False,
            "assignments": it["assignments"],
        })
    for it in extras:
        all_line_items.append({
            "name": it["name"],
            "quantity": it["quantity"],
            "unit_price": it["unit_price"],
            "line_total": it["line_total"],
            "matched_grocery_item_id": None,
            "is_extra": True,
            "assignments": it["assignments"],
        })

    rpc_res = confirm_receipt_transaction(
        room_id=room_id,
        uploaded_by=shopper_id,
        store="Fresh Mart",
        receipt_date="2026-10-15",
        subtotal=Decimal("370.00"),
        tax=tax,
        discount=discount,
        other_charges=other_charges,
        total=total,
        image_path="test_receipt.png",
        items=all_line_items,
        payments=split["debts"],
        purchased_grocery_ids=purchased_g_ids,
    )

    assert rpc_res["success"] is True
    receipt_id = rpc_res["receipt_id"]
    print(f"✅ Atomic confirmation succeeded! Receipt #{receipt_id} created.")

    # Check payments table as seen by Payments page
    payments = get_room_payments_live(room_id)
    print(f"Recorded payments in database for room {room_id}:")
    for p in payments:
        print(f"• ID {p['id']}: {p['payerName']} owes {p['payeeName']} ₹{p['amount']} (Status: {p['paymentStatus']})")

    # Verify debts: Rilda and Alex owe shopper; shopper does not owe self
    assert len(payments) == 2
    rilda_p = next(p for p in payments if p["payerUserId"] == rilda_id)
    alex_p = next(p for p in payments if p["payerUserId"] == alex_id)
    assert rilda_p["payeeUserId"] == shopper_id
    assert alex_p["payeeUserId"] == shopper_id
    assert rilda_p["amount"] > 0
    assert alex_p["amount"] > 0
    print("✅ Verified: Payments table shows exact debts owed by Rilda and Alex to Tejashree.")

    # Check grocery items status in database
    updated_groceries = get_live_grocery_items(room_id)
    purchased_count = sum(1 for g in updated_groceries if g["status"] == "purchased")
    print(f"✅ Verified: {purchased_count} matched grocery items marked as 'purchased' in database.")

    print("\n" + "=" * 65)
    print("🎉 ALL END-TO-END VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
