"""
services/receipt_ocr_service.py
================================
Primary OCR service using Google Gemini (google-genai) structured JSON output,
with Tesseract fallback and PDF-to-image conversion.
All money fields use Decimal, never float.
"""

import io
import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List, Optional, Tuple, Dict, Any

from pydantic import BaseModel, Field

logger = logging.getLogger("grocease.ocr")

MONEY_ROUND = Decimal("0.01")
QTY_ROUND = Decimal("0.001")


def to_decimal(val, default="0.00", quant=MONEY_ROUND) -> Decimal:
    """Safely convert any numeric/string value to Decimal."""
    if val is None:
        return Decimal(default)
    try:
        clean = str(val).replace(",", "").strip()
        # Handle negative sign or currency symbols
        clean = re.sub(r"[^\d.-]", "", clean)
        if not clean or clean == "-" or clean == ".":
            return Decimal(default)
        return Decimal(clean).quantize(quant, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


# ── Pydantic Schema for Gemini Structured Output ──────────────────────────────
class ExtractedReceiptItem(BaseModel):
    name: str = Field(description="Name or description of the purchased grocery item")
    quantity: float = Field(default=1.0, description="Quantity of the item (e.g. 1, 2, 0.5)")
    unit_price: float = Field(default=0.0, description="Unit price per item in the local currency")
    line_total: float = Field(default=0.0, description="AMOUNT column for this line, before any discount")
    item_discount: float = Field(default=0.0, description="Positive discount applied to this item only (from a '-xx.xx' line under it), else 0")
    gst_rate: float = Field(default=0.0, description="GST percent for this item, e.g. 0, 5, 12, 18 (from 'GST:18%')")


class ExtractedReceipt(BaseModel):
    store: Optional[str] = Field(default=None, description="Store or supermarket name")
    date: Optional[str] = Field(default=None, description="Receipt date in YYYY-MM-DD or DD/MM/YYYY")
    items: List[ExtractedReceiptItem] = Field(default_factory=list, description="List of line items")
    tax: float = Field(default=0.0, description="Total tax = CGST + SGST (+ IGST)")
    cgst: float = Field(default=0.0, description="CGST total")
    sgst: float = Field(default=0.0, description="SGST total")
    discount: float = Field(default=0.0, description="Total discount = item discounts + coupon discounts, as a positive number")
    coupon_discount: float = Field(default=0.0, description="Coupon discount only, positive")
    other_charges: float = Field(default=0.0, description="Other charges (delivery, bag fee, service charge)")
    round_off: float = Field(default=0.0, description="Round off amount, signed (e.g. -0.21)")
    total: float = Field(default=0.0, description="NET PAYABLE / grand total actually paid. NOT total tax or taxable value")


def convert_pdf_to_images(file_bytes: bytes) -> List[bytes]:
    """Convert a PDF file to a list of PNG image bytes using pypdfium2."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(file_bytes)
        if len(pdf) == 0:
            raise ValueError("PDF document contains no pages.")
        images = []
        for i in range(min(len(pdf), 3)):  # process up to 3 pages
            page = pdf[i]
            pil_img = page.render(scale=2.0).to_pil()
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            images.append(buf.getvalue())
        return images
    except Exception as exc:
        logger.warning("PDF conversion with pypdfium2 failed: %s", exc)
        raise ValueError(f"Could not convert PDF to image: {exc}") from exc


def get_gemini_api_key() -> Optional[str]:
    """Retrieve Gemini API key from streamlit.secrets, environment, or settings."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
            if key and key.strip():
                return key.strip()
    except Exception:
        pass
    
    for env_var in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GROCEASE_GEMINI_API_KEY"]:
        val = os.environ.get(env_var)
        if val and val.strip():
            return val.strip()
    return None


SYSTEM_PROMPT = (
    "You are a receipt parser. Extract ONLY purchased line items. Ignore item IDs (ITM-xxxx), HSN codes, "
    "GST% labels, GSTIN, FSSAI, phone numbers, bill/receipt/UPI reference numbers, and times. "
    "Quantity is the integer on the line below the item name, followed by rate and amount. "
    "unit_price = RATE column, line_total = AMOUNT column (before discount). "
    "If a '-xx.xx' discount line follows an item, put it (as a positive number) in that item's item_discount. "
    "gst_rate = the 'GST:xx%' printed under the item. "
    "tax = CGST + SGST (+ IGST if present). "
    "total = the 'NET PAYABLE' / grand total actually paid, NOT total tax or taxable value. "
    "discount = item discounts + coupon discounts (positive). round_off keeps its sign. "
    "Use 0 for missing numeric fields. Return valid JSON only, no prose."
)

# gemini-2.0-flash (shut down 1 Jun 2026) and gemini-2.5-flash (16 Oct 2026) are retired.
# Override with GEMINI_MODEL in .env / secrets. If every listed model is gone, the newest available
# flash model is discovered at runtime via client.models.list().
GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.8-flash"]
_WORKING_MODEL: Optional[str] = None


def _discover_flash_models(client) -> List[str]:
    """Newest-first list of usable text 'flash' models from the live model list."""
    found = []
    for m in client.models.list():
        name = (getattr(m, "name", "") or "").replace("models/", "")
        actions = getattr(m, "supported_actions", None) or []
        if "flash" not in name or (actions and "generateContent" not in actions):
            continue
        if any(bad in name for bad in ("image", "tts", "live", "audio", "embedding", "omni", "preview", "lite", "thinking")):
            continue
        ver = tuple(int(x) for x in re.findall(r"\d+", name)[:2]) or (0,)
        found.append((ver, name))
    return [n for _, n in sorted(found, reverse=True)]


def _cfg_model() -> str:
    """Optional model override: GEMINI_MODEL in env or Streamlit secrets."""
    val = os.environ.get("GEMINI_MODEL", "").strip()
    if not val:
        try:
            import streamlit as st
            val = str(st.secrets.get("GEMINI_MODEL", "")).strip()
        except Exception:
            val = ""
    return val


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "resource_exhausted", "503", "unavailable", "timeout", "deadline"))


def _is_model_missing(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "404" in msg or "not_found" in msg or "not found" in msg


def extract_with_gemini(
    file_bytes: bytes,
    mime_type: str = "image/png",
    api_key: Optional[str] = None,
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Primary extractor. Sends the ORIGINAL file (PDF bytes or image) straight to Gemini
    with a strict JSON schema, temperature 0. Raises ValueError with the real reason on failure.
    """
    import time

    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError("Gemini API key not found. Add GEMINI_API_KEY to .streamlit/secrets.toml or .env.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ValueError(f"google-genai is not installed (pip install google-genai): {exc}") from exc

    client = genai.Client(api_key=key)
    user_prompt = "Parse this grocery receipt."
    if feedback:
        user_prompt += f" Your previous attempt failed this check: {feedback} Re-read the receipt carefully and correct it."

    global _WORKING_MODEL
    errors: List[str] = []
    candidates = [m for m in [_WORKING_MODEL, _cfg_model()] + GEMINI_MODELS if m]
    candidates = list(dict.fromkeys(candidates))
    tried_discovery = False
    last_err: Optional[Exception] = None
    idx = 0
    while idx < len(candidates):
        model_name = candidates[idx]
        idx += 1
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[types.Part.from_bytes(data=file_bytes, mime_type=mime_type), user_prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=ExtractedReceipt,
                        temperature=0,
                    ),
                )
                raw_text = (response.text or "").strip()
                if not raw_text:
                    raise ValueError("Gemini returned an empty response.")
                parsed = ExtractedReceipt.model_validate_json(raw_text)
                data = _standardize_extraction(parsed)
                data["model"] = model_name
                _WORKING_MODEL = model_name
                return data
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                logger.warning("Gemini %s attempt %d failed: %s: %s", model_name, attempt + 1, type(exc).__name__, exc)
                if _is_model_missing(exc):
                    if model_name == _WORKING_MODEL:
                        _WORKING_MODEL = None
                    errors.append(f"{model_name}: model not available")
                    break  # try next model
                if _is_retryable(exc) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                errors.append(f"{model_name}: {type(exc).__name__}: {str(exc)[:200]}")
                break
        # every known model is gone -> ask the API which flash models exist right now (once)
        if idx >= len(candidates) and not tried_discovery:
            tried_discovery = True
            try:
                for name in _discover_flash_models(client):
                    if name not in candidates:
                        candidates.append(name)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"model discovery failed: {type(exc).__name__}: {str(exc)[:150]}")
    raise ValueError("; ".join(errors) or f"{type(last_err).__name__}: {last_err}")


# ── Text-based fallback (PDF text layer / Tesseract) ──────────────────────────
_SKIP_RE = re.compile(
    r"(ID:|HSN|GSTIN|FSSAI|\bPh\b|Ph:|Cust\.?\s*Ph|Bill\s*No|Receipt\s*ID|RCPT-|UPI|Counter|Cashier|Customer|"
    r"^Date|^Time|Payment\s*mode|Amount\s*paid|^Change|Thank|Goods\s*once|Visit|www\.|@|TAX\s*INVOICE|"
    r"^ITEM\s+QTY|Total\s*Items|Total\s*Qty|You\s*saved|^GST%|Taxable\s*value|Perishables|with this receipt|\bSupermarket\b.*\bChennai\b)",
    re.I,
)
_DEC = r"-?\d[\d,]*\.\d{2}"
_DEC_RE = re.compile(_DEC)
_QRA_RE = re.compile(rf"^\s*(\d+(?:\.\d+)?)\s+({_DEC})\s+({_DEC})\s*$")
_GST_RE = re.compile(r"GST\s*:\s*(\d+(?:\.\d+)?)\s*%", re.I)
_DATE_RE = re.compile(r"(\d{1,2})[-/ ]([A-Za-z]{3}|\d{1,2})[-/ ](\d{4})")


def _last_dec(line: str) -> Optional[Decimal]:
    nums = _DEC_RE.findall(line)
    return to_decimal(nums[-1]) if nums else None


def _guess_date(text: str) -> Optional[str]:
    from datetime import datetime
    m = re.search(r"Date\s*:?\s*([0-9A-Za-z/\- ]{8,12})", text)
    cand = m.group(1).strip() if m else None
    if cand:
        for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(cand, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def parse_receipt_text(text: str) -> Dict[str, Any]:
    """Guarded, label-driven parser. Prices must have 2 decimals; IDs/HSN/phones are skipped."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    items: List[Dict[str, Any]] = []
    pending_name: Optional[str] = None
    pending_gst = Decimal("0")
    z = Decimal("0.00")
    total = subtotal = cgst = sgst = igst = tax_line = total_tax = coupon = generic_disc = round_off = z

    for line in lines:
        low = line.lower()
        gm = _GST_RE.search(line)
        if gm:
            pending_gst = Decimal(gm.group(1))
        # item-level discount line, e.g. "Item discount (10%) -48.00"
        if re.match(r"item\s+discount\s*\(", low):
            v = _last_dec(line)
            if v is not None and items:
                items[-1]["item_discount"] = abs(v)
            continue
        # labelled totals (before the skip filter: "Total tax" etc.)
        if "net payable" in low or "grand total" in low or "amount payable" in low:
            v = _last_dec(line); total = v if v is not None else total; continue
        if re.match(r"sub\s*-?\s*total", low):
            v = _last_dec(line); subtotal = v if v is not None else subtotal; continue
        if re.match(r"item\s+discounts", low):
            continue
        if "coupon" in low:
            v = _last_dec(line); coupon = abs(v) if v is not None else coupon; continue
        if low.startswith("cgst"):
            v = _last_dec(line); cgst = v if v is not None else cgst; continue
        if low.startswith("sgst"):
            v = _last_dec(line); sgst = v if v is not None else sgst; continue
        if low.startswith("igst"):
            v = _last_dec(line); igst = v if v is not None else igst; continue
        if "total tax" in low:
            v = _last_dec(line); total_tax = v if v is not None else total_tax; continue
        if "round" in low and "off" in low:
            v = _last_dec(line); round_off = v if v is not None else round_off; continue
        if re.match(r"(tax|gst)\b", low) and "gst:" not in low:
            v = _last_dec(line); tax_line = v if v is not None else tax_line; continue
        if "discount" in low:
            v = _last_dec(line); generic_disc = abs(v) if v is not None else generic_disc; continue
        if re.match(r"total\b", low) and "items" not in low and "qty" not in low:
            v = _last_dec(line); total = v if v is not None and total == z else total; continue

        # multi-line item: "qty rate amount"
        qm = _QRA_RE.match(line)
        if qm and pending_name:
            qty, rate, amt = to_decimal(qm.group(1), default="1.000", quant=QTY_ROUND), to_decimal(qm.group(2)), to_decimal(qm.group(3))
            if 0 < qty < 1000 and 0 < rate < 100000:
                items.append({"name": pending_name, "quantity": qty, "unit_price": rate, "line_total": amt,
                              "item_discount": z, "gst_rate": pending_gst})
            pending_name, pending_gst = None, Decimal("0")
            continue

        if _SKIP_RE.search(line):
            continue

        # single-line item: "Name  2 x 45.00  90.00" / "Name 90.00"
        nums = _DEC_RE.findall(line)
        if nums:
            amt = to_decimal(nums[-1])
            name = line[: line.rfind(nums[-1])].strip(" -:*.#₹$")
            xm = re.search(rf"(\d+(?:\.\d+)?)\s*[xX*@]\s*({_DEC})", name + " " + nums[-1])
            qty, unit = Decimal("1.000"), amt
            if xm:
                qty = to_decimal(xm.group(1), default="1.000", quant=QTY_ROUND)
                unit = to_decimal(xm.group(2))
                name = re.sub(rf"\s*\d+(?:\.\d+)?\s*[xX*@]\s*{_DEC}.*$", "", name).strip(" -:*.#₹$")
            if len(name) >= 2 and any(c.isalpha() for c in name) and 0 < qty < 1000 and 0 < unit < 100000:
                items.append({"name": name, "quantity": qty, "unit_price": unit, "line_total": amt,
                              "item_discount": z, "gst_rate": Decimal("0")})
            continue

        # plain text line: candidate item name for the next "qty rate amount" line
        if any(c.isalpha() for c in line) and len(line) < 60:
            pending_name = line

    item_disc_sum = sum((i["item_discount"] for i in items), z)
    sub = sum((i["line_total"] for i in items), z)
    tax = total_tax or (cgst + sgst + igst) or tax_line
    discount = (item_disc_sum + coupon) if (item_disc_sum or coupon) else generic_disc
    if total == z:
        total = (sub - discount + tax + round_off).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)

    store = lines[0] if lines and not _SKIP_RE.search(lines[0]) and any(c.isalpha() for c in lines[0]) else None
    return {
        "store": store.title() if store else None,
        "date": _guess_date(text),
        "items": items,
        "subtotal": sub,
        "tax": tax,
        "cgst": cgst,
        "sgst": sgst,
        "discount": discount,
        "coupon_discount": coupon,
        "other_charges": z,
        "round_off": round_off,
        "total": total,
    }


def _parse_tesseract_text(text: str) -> Dict[str, Any]:
    """Backward-compatible alias."""
    return parse_receipt_text(text)


def extract_pdf_text(file_bytes: bytes) -> str:
    """Read the embedded text layer of a PDF (exact digits, no OCR errors)."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(file_bytes)
    parts = []
    for i in range(min(len(pdf), 3)):
        parts.append(pdf[i].get_textpage().get_text_range())
    return "\n".join(parts).replace("\r", "\n")


def extract_with_tesseract(image_bytes: bytes) -> Dict[str, Any]:
    """Last-resort OCR extractor using Tesseract."""
    import pytesseract
    from PIL import Image

    tess_cmd = os.environ.get("GROCEASE_TESSERACT_CMD")
    if tess_cmd and os.path.exists(tess_cmd):
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

    img = Image.open(io.BytesIO(image_bytes))
    raw_text = pytesseract.image_to_string(img)
    if not raw_text.strip():
        raise ValueError("Tesseract could not find any text on the image.")
    return parse_receipt_text(raw_text)


def _standardize_extraction(extracted: ExtractedReceipt) -> Dict[str, Any]:
    """Convert ExtractedReceipt to a Decimal dict. Recomputes only line totals; never 'fixes' totals."""
    items = []
    for it in extracted.items:
        qty = to_decimal(it.quantity, default="1.000", quant=QTY_ROUND)
        if qty <= 0:
            qty = Decimal("1.000")
        line_tot = to_decimal(it.line_total)
        unit_p = to_decimal(it.unit_price)
        if unit_p <= 0 and line_tot > 0:
            unit_p = (line_tot / qty).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)
        elif unit_p > 0 and abs(line_tot - unit_p * qty) > Decimal("0.01"):
            line_tot = (unit_p * qty).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)
        items.append({
            "name": it.name.strip(),
            "quantity": qty,
            "unit_price": unit_p,
            "line_total": line_tot,
            "item_discount": abs(to_decimal(it.item_discount)),
            "gst_rate": to_decimal(it.gst_rate),
        })

    cgst, sgst = to_decimal(extracted.cgst), to_decimal(extracted.sgst)
    tax = to_decimal(extracted.tax)
    if cgst + sgst > tax:
        tax = cgst + sgst
    disc = abs(to_decimal(extracted.discount))
    items_disc = sum((i["item_discount"] for i in items), Decimal("0.00"))
    coupon = abs(to_decimal(extracted.coupon_discount))
    if disc < items_disc + coupon:
        disc = items_disc + coupon
    charges = to_decimal(extracted.other_charges)
    round_off = to_decimal(extracted.round_off)
    tot = to_decimal(extracted.total)
    subtotal = sum((i["line_total"] for i in items), Decimal("0.00"))
    if tot <= 0:
        tot = (subtotal - disc + tax + charges + round_off).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)

    return {
        "store": extracted.store or None,
        "date": extracted.date or None,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "cgst": cgst,
        "sgst": sgst,
        "discount": disc,
        "coupon_discount": coupon,
        "other_charges": charges,
        "round_off": round_off,
        "total": tot,
    }


def validate_receipt_math(
    items: List[Dict[str, Any]],
    tax: Decimal,
    discount: Decimal,
    other_charges: Decimal,
    total: Decimal,
    tolerance: Decimal = Decimal("0.05"),
    round_off: Decimal = Decimal("0.00"),
) -> Tuple[bool, Decimal, str]:
    """Check: sum(line_totals) - discount + tax + other_charges + round_off == total."""
    subtotal = sum((to_decimal(i.get("line_total", 0)) for i in items), Decimal("0.00"))
    calc_total = (subtotal - discount + tax + other_charges + round_off).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)
    diff = abs(calc_total - total)
    if diff <= tolerance:
        return True, calc_total, ""
    warning = (
        f"⚠️ Math mismatch: {subtotal} (items) - {discount} (discount) + {tax} (tax) + {round_off} (round-off) "
        f"+ {other_charges} (other) = {calc_total}, but Printed Total = {total} (diff {diff:.2f}). "
        f"Adjust the numbers below."
    )
    return False, calc_total, warning


def _finish(data: Dict[str, Any], engine: str) -> Dict[str, Any]:
    z = Decimal("0.00")
    is_valid, calc_tot, warn = validate_receipt_math(
        data["items"], data["tax"], data["discount"], data.get("other_charges", z),
        data["total"], round_off=data.get("round_off", z),
    )
    data.update(success=bool(data["items"]), is_valid_math=is_valid, math_warning=warn,
                calculated_total=calc_tot, engine=engine)
    if not data["items"]:
        data["error"] = "No items could be extracted. Please add them manually below."
    return data


def process_receipt_file(file_bytes: bytes, file_name: str) -> Dict[str, Any]:
    """
    Pipeline: Gemini (original PDF/image, JSON schema) -> retry once on math failure ->
    PDF text layer -> Tesseract -> manual entry. Records why Gemini failed in 'gemini_error'.
    """
    fname = file_name.lower()
    is_pdf = fname.endswith(".pdf")
    mime = "application/pdf" if is_pdf else ("image/png" if fname.endswith(".png") else "image/jpeg")
    gemini_error: Optional[str] = None

    # 1. Gemini on the original file
    key = get_gemini_api_key()
    if not key:
        gemini_error = "Gemini API key not found (GEMINI_API_KEY in st.secrets / env)."
    else:
        try:
            data = extract_with_gemini(file_bytes, mime_type=mime, api_key=key)
            res = _finish(data, "gemini")
            if not res["is_valid_math"]:
                try:  # one retry with the failed check in the prompt
                    retry = _finish(extract_with_gemini(file_bytes, mime_type=mime, api_key=key,
                                                        feedback=res["math_warning"]), "gemini")
                    if retry["is_valid_math"] or len(retry["items"]) >= len(res["items"]):
                        res = retry
                except Exception as exc:  # keep first result
                    logger.warning("Gemini retry failed: %s", exc)
            if res["items"]:
                return res
            gemini_error = "Gemini returned no items."
        except Exception as exc:  # noqa: BLE001
            gemini_error = str(exc)
            logger.warning("Gemini OCR failed: %s", exc)

    # 2. PDF text layer (exact digits)
    if is_pdf:
        try:
            parsed = parse_receipt_text(extract_pdf_text(file_bytes))
            if parsed["items"]:
                res = _finish(parsed, "pdf_text")
                res["gemini_error"] = gemini_error
                return res
        except Exception as exc:
            logger.warning("PDF text extraction failed: %s", exc)

    # 3. Tesseract on an image (rasterise PDF first)
    try:
        img_bytes = convert_pdf_to_images(file_bytes)[0] if is_pdf else file_bytes
        res = _finish(extract_with_tesseract(img_bytes), "tesseract_fallback")
        res["gemini_error"] = gemini_error
        if res["items"]:
            return res
    except Exception as exc:
        logger.warning("Tesseract OCR fallback failed: %s", exc)

    z = Decimal("0.00")
    return {
        "success": False,
        "error": "Automatic extraction could not read this receipt. You can still add your items manually below.",
        "gemini_error": gemini_error,
        "engine": "none",
        "store": "", "date": None, "items": [],
        "subtotal": z, "tax": z, "cgst": z, "sgst": z, "discount": z, "coupon_discount": z,
        "other_charges": z, "round_off": z, "total": z,
        "is_valid_math": True, "math_warning": "",
    }