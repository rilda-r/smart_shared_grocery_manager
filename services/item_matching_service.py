"""
services/item_matching_service.py
=================================
Exact & fuzzy matching of receipt items against room pending grocery items.
Supports multiple requesters for a single product (e.g. Rilda wants 2 milk, Tejashree wants 1 milk),
proportional quantity/cost splitting, extra items identification, and unmatched grocery list items.
"""

import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz

AUTO_MATCH_THRESHOLD = 80.0
CANDIDATE_THRESHOLD = 60.0

MONEY_ROUND = Decimal("0.01")
QTY_ROUND = Decimal("0.001")

_UNITS_RE = re.compile(
    r"\b(?:\d+(?:\.\d+)?\s*(?:kg|kgs|g|gm|gms|l|ltr|ltrs|liter|liters|litre|litres|ml|pk|pack|packs|pcs|pc|piece|pieces|pkt|packet|packets|btl|bottle|bottles|can|cans|box|boxes|dz|dozen))\b",
    re.IGNORECASE,
)
_MULTIPLIER_RE = re.compile(r"\b\d+\s*[xX*@]\s*\d+\b")
_NOISE_WORDS = re.compile(r"\b(?:organic|fresh|farm|premium|pure|natural|local|brand|classic|select)\b", re.IGNORECASE)


RECENT_PURCHASE_DAYS = 3


def select_matchable_grocery_items(
    all_items: List[Dict[str, Any]],
    billed_item_ids: Optional[set] = None,
    now: Optional[Any] = None,
    recent_days: int = RECENT_PURCHASE_DAYS,
) -> List[Dict[str, Any]]:
    """
    Grocery items a receipt can be matched against:
      1. every 'pending' item, and
      2. items already marked 'purchased' (e.g. bought 1/1 on the Shopping page) that were purchased
         recently and have NOT already been attributed to an earlier receipt.
    Without (2) a fully purchased item drops out of matching and lands in "Extras", owned by the shopper,
    so the person who actually asked for it has to be re-assigned by hand.
    Pending items come first so they win ties.
    """
    from datetime import datetime, timedelta

    billed = {int(x) for x in (billed_item_ids or set()) if x is not None}
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=recent_days)

    pending, recent_purchased = [], []
    for g in all_items:
        status = g.get("status")
        if status == "pending":
            pending.append(g)
        elif status == "purchased" and g.get("id") not in billed:
            try:
                updated = datetime.fromisoformat(str(g.get("updatedAt") or "").replace("Z", "")[:26])
            except ValueError:
                continue
            if updated >= cutoff:
                recent_purchased.append(g)
    return pending + recent_purchased


def normalize_item_name(name: str) -> str:
    """
    Normalize product names: lowercase, strip punctuation, measurement units,
    brand/marketing noise, and simple plurals.
    """
    if not name:
        return ""
    text = name.lower().strip()
    # Remove multipliers like '2 x 45'
    text = _MULTIPLIER_RE.sub(" ", text)
    # Remove units like '1kg', '500g', '1L', '12 pcs'
    text = _UNITS_RE.sub(" ", text)
    # Remove marketing noise words
    text = _NOISE_WORDS.sub(" ", text)
    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    # Remove standalone numbers
    text = re.sub(r"\b\d+\b", " ", text)
    
    tokens = text.split()
    cleaned_tokens = []
    for tok in tokens:
        # Simple plural stemming
        if len(tok) > 3 and tok.endswith("ies"):
            tok = tok[:-3] + "y"
        elif len(tok) > 4 and tok.endswith("es") and not tok.endswith("ses"):
            tok = tok[:-2]
        elif len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        cleaned_tokens.append(tok)
        
    return " ".join(cleaned_tokens).strip()


def calculate_match_score(receipt_name: str, grocery_name: str) -> float:
    """Calculate similarity score between receipt item name and grocery item name."""
    norm_rec = normalize_item_name(receipt_name)
    norm_groc = normalize_item_name(grocery_name)
    
    if not norm_rec or not norm_groc:
        return 0.0
    if norm_rec == norm_groc:
        return 100.0
    
    # rapidfuzz token_set_ratio handles extra words/tokens robustly
    set_score = fuzz.token_set_ratio(norm_rec, norm_groc)
    sort_score = fuzz.token_sort_ratio(norm_rec, norm_groc)
    partial_score = fuzz.partial_ratio(norm_rec, norm_groc)
    
    return float(max(set_score, sort_score, partial_score))


def match_receipt_items(
    receipt_items: List[Dict[str, Any]],
    pending_grocery_items: List[Dict[str, Any]],
    room_members: List[Dict[str, Any]],
    shopper_user_id: int,
) -> Dict[str, Any]:
    """
    Match receipt items against pending grocery items.
    
    Returns a dict with:
    - 'matched_items': List of matched items with assignments per member
    - 'extra_items': List of items not found on grocery list
    - 'unmatched_grocery_items': Pending items on grocery list not on receipt
    - 'member_subtotals': Dict of user_id -> subtotal
    """
    member_name_map = {}
    for m in room_members:
        uid = m.get("user_id") or m.get("userId")
        name = m.get("display_name") or m.get("actual_name") or m.get("username") or m.get("name") or f"User {uid}"
        member_name_map[uid] = name

    # Group pending grocery items by normalized name to handle multiple requesters
    grocery_item_pool = list(pending_grocery_items)
    used_grocery_item_ids = set()
    
    matched_results = []
    extra_results = []

    for r_idx, r_item in enumerate(receipt_items):
        r_name = r_item.get("name", "")
        r_qty = Decimal(str(r_item.get("quantity", 1)))
        r_unit_price = Decimal(str(r_item.get("unit_price", 0)))
        r_line_total = Decimal(str(r_item.get("line_total", 0)))
        
        # Find best matching grocery item(s) from pool
        scored_candidates = []
        for g_item in grocery_item_pool:
            g_name = g_item.get("itemName") or g_item.get("item_name", "")
            score = calculate_match_score(r_name, g_name)
            if score >= CANDIDATE_THRESHOLD:
                scored_candidates.append({
                    "grocery_item": g_item,
                    "score": score,
                })
        
        scored_candidates.sort(key=lambda x: -x["score"])
        
        if scored_candidates and scored_candidates[0]["score"] >= AUTO_MATCH_THRESHOLD:
            top_score = scored_candidates[0]["score"]
            best_match = scored_candidates[0]["grocery_item"]
            
            # Find all pending requests matching this product (multi-requester)
            # Include candidates scoring high or close to top score
            matching_requests = [
                c["grocery_item"] for c in scored_candidates
                if c["score"] >= AUTO_MATCH_THRESHOLD or (top_score - c["score"] <= 20 and c["score"] >= CANDIDATE_THRESHOLD)
            ]
            
            total_requested_qty = sum(
                Decimal(str(g.get("quantity", 1))) for g in matching_requests
            )
            
            # Create assignments split across requesters proportionally
            assignments = []
            qty_allocated_so_far = Decimal("0.000")
            amt_allocated_so_far = Decimal("0.00")
            
            for idx, g in enumerate(matching_requests):
                g_id = g.get("id")
                g_uid = g.get("userId") or g.get("user_id")
                g_req_qty = Decimal(str(g.get("quantity", 1)))
                
                used_grocery_item_ids.add(g_id)
                if g in grocery_item_pool:
                    grocery_item_pool.remove(g)

                
                if total_requested_qty > 0:
                    share_ratio = g_req_qty / total_requested_qty
                else:
                    share_ratio = Decimal(1) / Decimal(len(matching_requests))
                
                if idx == len(matching_requests) - 1:
                    # Last person gets remainder to guarantee exact sum
                    assigned_qty = (r_qty - qty_allocated_so_far).quantize(QTY_ROUND)
                    assigned_amt = (r_line_total - amt_allocated_so_far).quantize(MONEY_ROUND)
                else:
                    assigned_qty = (r_qty * share_ratio).quantize(QTY_ROUND, rounding=ROUND_HALF_UP)
                    assigned_amt = (r_line_total * share_ratio).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)
                    qty_allocated_so_far += assigned_qty
                    amt_allocated_so_far += assigned_amt
                
                assignments.append({
                    "user_id": g_uid,
                    "member_name": member_name_map.get(g_uid, f"User {g_uid}"),
                    "requested_quantity": g_req_qty,
                    "quantity": assigned_qty,
                    "amount": assigned_amt,
                    "grocery_item_id": g_id,
                })
                
            qty_difference = r_qty - total_requested_qty
            
            matched_results.append({
                "item_index": r_idx,
                "name": r_name,
                "receipt_quantity": r_qty,
                "unit_price": r_unit_price,
                "line_total": r_line_total,
                "item_discount": r_item.get("item_discount", Decimal("0.00")),
                "gst_rate": r_item.get("gst_rate", Decimal("0.00")),
                "hsn": r_item.get("hsn"),
                "matched_grocery_name": best_match.get("itemName") or best_match.get("item_name"),
                "total_requested_qty": total_requested_qty,
                "qty_difference": qty_difference,
                "match_score": scored_candidates[0]["score"],
                "is_confident": True,
                "is_extra": False,
                "assignments": assignments,
            })
        elif scored_candidates and scored_candidates[0]["score"] >= CANDIDATE_THRESHOLD:
            # Low confidence match — show candidate suggestion for confirmation
            best_match = scored_candidates[0]["grocery_item"]
            g_uid = best_match.get("userId") or best_match.get("user_id")
            
            matched_results.append({
                "item_index": r_idx,
                "name": r_name,
                "receipt_quantity": r_qty,
                "unit_price": r_unit_price,
                "line_total": r_line_total,
                "item_discount": r_item.get("item_discount", Decimal("0.00")),
                "gst_rate": r_item.get("gst_rate", Decimal("0.00")),
                "hsn": r_item.get("hsn"),
                "matched_grocery_name": best_match.get("itemName") or best_match.get("item_name"),
                "total_requested_qty": Decimal(str(best_match.get("quantity", 1))),
                "qty_difference": r_qty - Decimal(str(best_match.get("quantity", 1))),
                "match_score": scored_candidates[0]["score"],
                "is_confident": False,
                "is_extra": False,
                "assignments": [
                    {
                        "user_id": g_uid,
                        "member_name": member_name_map.get(g_uid, f"User {g_uid}"),
                        "requested_quantity": Decimal(str(best_match.get("quantity", 1))),
                        "quantity": r_qty,
                        "amount": r_line_total,
                        "grocery_item_id": best_match.get("id"),
                    }
                ],
            })
        else:
            # Extra item (not on grocery list)
            extra_results.append({
                "item_index": r_idx,
                "name": r_name,
                "quantity": r_qty,
                "unit_price": r_unit_price,
                "line_total": r_line_total,
                "item_discount": r_item.get("item_discount", Decimal("0.00")),
                "gst_rate": r_item.get("gst_rate", Decimal("0.00")),
                "hsn": r_item.get("hsn"),
                "is_extra": True,
                # Default extra assignment: shopper pays for own purchase
                "split_mode": "own",  # "own", "specific", "shared_all"
                "assigned_user_id": shopper_user_id,
                "assigned_user_ids": [shopper_user_id],
                "assignments": [
                    {
                        "user_id": shopper_user_id,
                        "member_name": member_name_map.get(shopper_user_id, f"User {shopper_user_id}"),
                        "quantity": r_qty,
                        "amount": r_line_total,
                    }
                ],
            })

    # Find grocery items that were NOT purchased on the receipt
    unmatched_grocery_items = []
    for g in grocery_item_pool:
        if g.get("id") not in used_grocery_item_ids:
            uid = g.get("userId") or g.get("user_id")
            unmatched_grocery_items.append({
                "id": g.get("id"),
                "itemName": g.get("itemName") or g.get("item_name"),
                "quantity": g.get("quantity", 1),
                "userId": uid,
                "memberName": member_name_map.get(uid, f"User {uid}"),
                "status": "not purchased",
            })

    return {
        "matched_items": matched_results,
        "extra_items": extra_results,
        "unmatched_grocery_items": unmatched_grocery_items,
        "member_name_map": member_name_map,
    }