"""
services/receipt_split_service.py
=================================
Exact penny/cent math for distributing items, taxes, discounts, and charges.
Guarantees that sum of member shares equals the receipt total EXACTLY.
Allocates remainders deterministically using the largest-remainder method.
"""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Tuple

MONEY_ROUND = Decimal("0.01")


def to_cents(val: Decimal) -> int:
    return int((Decimal(str(val)) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal(100)).quantize(MONEY_ROUND)


def split_amount_proportionally(total_amount: Decimal, weights: Dict[int, Decimal]) -> Dict[int, Decimal]:
    """
    Split `total_amount` across keys in proportion to `weights` using the largest-remainder method.
    Guarantees sum(result.values()) == total_amount exactly.
    Handles negative amounts (like discounts) as well.
    """
    total_cents = to_cents(total_amount)
    if total_cents == 0 or not weights:
        return {k: Decimal("0.00") for k in weights}

    # If all weights are zero or equal, split equally
    positive_weights = {k: max(0, to_cents(w)) for k, w in weights.items()}
    sum_weights = sum(positive_weights.values())

    is_negative = total_cents < 0
    abs_cents = abs(total_cents)

    if sum_weights <= 0:
        # Fallback to equal count split
        count = len(weights)
        base_cent = abs_cents // count
        rem = abs_cents % count
        res = {}
        for idx, k in enumerate(sorted(weights.keys())):
            c = base_cent + (1 if idx < rem else 0)
            res[k] = from_cents(-c if is_negative else c)
        return res

    base = {}
    remainders = {}
    for k, w_cents in positive_weights.items():
        quota = (abs_cents * w_cents) // sum_weights
        rem = (abs_cents * w_cents) % sum_weights
        base[k] = quota
        remainders[k] = rem

    allocated_sum = sum(base.values())
    leftover = abs_cents - allocated_sum

    # Distribute leftover cents to keys with largest remainder; tie-breaker: lower key ID
    sorted_keys = sorted(positive_weights.keys(), key=lambda k: (-remainders[k], k))
    for k in sorted_keys[:leftover]:
        base[k] += 1

    return {k: from_cents(-base[k] if is_negative else base[k]) for k in weights}


def split_amount_equally(total_amount: Decimal, user_ids: List[int]) -> Dict[int, Decimal]:
    """Split `total_amount` equally across user_ids using largest-remainder method."""
    weights = {uid: Decimal(1) for uid in user_ids}
    return split_amount_proportionally(total_amount, weights)


def calculate_receipt_split(
    matched_items: List[Dict[str, Any]],
    extra_items: List[Dict[str, Any]],
    tax: Decimal,
    discount: Decimal,
    other_charges: Decimal,
    total: Decimal,
    shopper_user_id: int,
    all_room_member_ids: List[int],
    member_name_map: Dict[int, str],
    tax_split_mode: str = "proportional",  # "proportional" or "equal"
) -> Dict[str, Any]:
    """
    Compile member subtotals, distribute taxes/discounts/charges,
    and calculate debts owed to the shopper.
    
    The sum of all member shares MUST equal the receipt total EXACTLY.
    The shopper's own share is not a debt to themselves.
    """
    # 1. Calculate item subtotal per member
    member_item_subtotals = defaultdict(lambda: Decimal("0.00"))
    member_items_detail = defaultdict(list)

    # From matched items
    for m_item in matched_items:
        for assign in m_item.get("assignments", []):
            uid = assign["user_id"]
            amt = Decimal(str(assign["amount"]))
            qty = Decimal(str(assign["quantity"]))
            member_item_subtotals[uid] += amt
            member_items_detail[uid].append({
                "name": m_item["name"],
                "quantity": qty,
                "amount": amt,
                "is_extra": False,
            })

    # From extra items
    for e_item in extra_items:
        for assign in e_item.get("assignments", []):
            uid = assign["user_id"]
            amt = Decimal(str(assign["amount"]))
            qty = Decimal(str(assign["quantity"]))
            member_item_subtotals[uid] += amt
            member_items_detail[uid].append({
                "name": e_item["name"],
                "quantity": qty,
                "amount": amt,
                "is_extra": True,
            })

    # Ensure all active members in room have an entry if needed
    participating_members = set(member_item_subtotals.keys())
    if not participating_members:
        participating_members = {shopper_user_id}

    weights = {uid: member_item_subtotals[uid] for uid in participating_members}

    # 2. Distribute Tax
    if tax_split_mode == "equal":
        tax_shares = split_amount_equally(tax, list(participating_members))
    else:
        tax_shares = split_amount_proportionally(tax, weights)

    # 3. Distribute Discount (subtracted)
    if tax_split_mode == "equal":
        discount_shares = split_amount_equally(discount, list(participating_members))
    else:
        discount_shares = split_amount_proportionally(discount, weights)

    # 4. Distribute Other Charges
    if tax_split_mode == "equal":
        charges_shares = split_amount_equally(other_charges, list(participating_members))
    else:
        charges_shares = split_amount_proportionally(other_charges, weights)

    # 5. Compute net total share per member
    member_summaries = []
    total_reconciled = Decimal("0.00")

    for uid in sorted(participating_members):
        sub = member_item_subtotals[uid]
        t_share = tax_shares.get(uid, Decimal("0.00"))
        d_share = discount_shares.get(uid, Decimal("0.00"))
        c_share = charges_shares.get(uid, Decimal("0.00"))
        
        net_share = (sub + t_share + c_share - d_share).quantize(MONEY_ROUND)
        total_reconciled += net_share

        # Debt owed to shopper: if shopper, debt is 0. If other member, they owe net_share.
        is_shopper = (uid == shopper_user_id)
        owed_to_shopper = Decimal("0.00") if is_shopper else net_share

        member_summaries.append({
            "user_id": uid,
            "display_name": member_name_map.get(uid, f"User {uid}"),
            "is_shopper": is_shopper,
            "items_count": len(member_items_detail[uid]),
            "items": member_items_detail[uid],
            "subtotal": sub,
            "tax_share": t_share,
            "discount_share": d_share,
            "charges_share": c_share,
            "net_total_share": net_share,
            "owed_to_shopper": owed_to_shopper,
        })

    # Exact reconciliation against printed receipt total
    remainder_diff = total - total_reconciled
    if remainder_diff != Decimal("0.00") and member_summaries:
        # Allocate any 1-cent discrepancy to the member with the largest subtotal
        sorted_by_sub = sorted(member_summaries, key=lambda m: (-m["subtotal"], m["user_id"]))
        sorted_by_sub[0]["net_total_share"] += remainder_diff
        if not sorted_by_sub[0]["is_shopper"]:
            sorted_by_sub[0]["owed_to_shopper"] += remainder_diff

    # Payments list to insert into database
    debts = []
    for m in member_summaries:
        if not m["is_shopper"] and m["owed_to_shopper"] > Decimal("0.00"):
            debts.append({
                "payer_user_id": m["user_id"],
                "payee_user_id": shopper_user_id,
                "amount": m["owed_to_shopper"],
            })

    return {
        "member_summaries": member_summaries,
        "debts": debts,
        "tax_split_mode": tax_split_mode,
        "receipt_total": total,
        "reconciled_sum": sum(m["net_total_share"] for m in member_summaries),
    }
