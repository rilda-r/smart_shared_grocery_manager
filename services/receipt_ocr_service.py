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
    line_total: float = Field(default=0.0, description="Total price for this line item")


class ExtractedReceipt(BaseModel):
    store: Optional[str] = Field(default=None, description="Store or supermarket name")
    date: Optional[str] = Field(default=None, description="Receipt date in YYYY-MM-DD or DD/MM/YYYY")
    items: List[ExtractedReceiptItem] = Field(default_factory=list, description="List of line items")
    tax: float = Field(default=0.0, description="Tax or GST/VAT total")
    discount: float = Field(default=0.0, description="Total discount applied (positive or negative number)")
    other_charges: float = Field(default=0.0, description="Other charges (delivery, bag fee, service charge)")
    total: float = Field(default=0.0, description="Final grand total printed on the receipt")


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


def extract_with_gemini(image_bytes: bytes, mime_type: str = "image/png", api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Primary OCR Extractor using the Google GenAI SDK (google-genai)
    with strict JSON structured output.
    """
    key = api_key or get_gemini_api_key()
    if not key:
        raise ValueError("Gemini API key is not configured. Please add GEMINI_API_KEY to st.secrets or .env.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)

    prompt = (
        "Extract all items, quantities, unit prices, line totals, tax, discounts, other charges, "
        "and grand total from this grocery receipt accurately. "
        "Remove currency symbols (like ₹, $, Rs) from numbers. "
        "Ensure discounts are recorded as positive values in the discount field. "
        "Normalize item names by removing extraneous printer codes, but keep the item description clear."
    )

    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash"]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedReceipt,
                    temperature=0.1,
                ),
            )
            raw_text = response.text
            if not raw_text:
                continue

            parsed = ExtractedReceipt.model_validate_json(raw_text)
            return _standardize_extraction(parsed)
        except Exception as exc:
            logger.warning("Gemini extraction with %s failed: %s", model_name, exc)
            last_err = exc

    raise ValueError(f"Gemini API extraction failed: {last_err}")


def extract_with_tesseract(image_bytes: bytes) -> Dict[str, Any]:
    """Fallback OCR extractor using Tesseract."""
    import pytesseract
    from PIL import Image

    tess_cmd = os.environ.get("GROCEASE_TESSERACT_CMD")
    if tess_cmd and os.path.exists(tess_cmd):
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

    img = Image.open(io.BytesIO(image_bytes))
    raw_text = pytesseract.image_to_string(img)
    if not raw_text.strip():
        raise ValueError("Tesseract could not find any text on the image.")

    return _parse_tesseract_text(raw_text)


def _parse_tesseract_text(text: str) -> Dict[str, Any]:
    """Simple parser for Tesseract raw text with Decimal support."""
    items = []
    total = Decimal("0.00")
    tax = Decimal("0.00")
    discount = Decimal("0.00")

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    amount_re = re.compile(r"(\d+(?:\.\d{2})?)")

    for line in lines:
        lower = line.lower()
        if "total" in lower and not "subtotal" in lower:
            nums = amount_re.findall(line)
            if nums:
                total = to_decimal(nums[-1])
            continue
        if "tax" in lower or "gst" in lower:
            nums = amount_re.findall(line)
            if nums:
                tax = to_decimal(nums[-1])
            continue
        if "discount" in lower:
            nums = amount_re.findall(line)
            if nums:
                discount = to_decimal(nums[-1])
            continue

        # Look for item lines with price at the end
        nums = amount_re.findall(line)
        if nums and len(nums) >= 1:
            line_tot = to_decimal(nums[-1])
            name_part = line[:line.rfind(nums[-1])].strip(" -:*.#₹$")
            if len(name_part) >= 2 and any(c.isalpha() for c in name_part):
                qty = Decimal("1.000")
                unit_price = line_tot
                # Check for "2 x 45.00"
                qty_match = re.search(r"(\d+(?:\.\d+)?)\s*[xX*@]\s*(\d+(?:\.\d+)?)", line)
                if qty_match:
                    qty = to_decimal(qty_match.group(1), default="1.000", quant=QTY_ROUND)
                    unit_price = to_decimal(qty_match.group(2))
                items.append({
                    "name": name_part,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_tot,
                })

    subtotal = sum(i["line_total"] for i in items)
    if total == Decimal("0.00"):
        total = subtotal + tax - discount

    return {
        "store": "Store",
        "date": None,
        "items": items,
        "tax": tax,
        "discount": discount,
        "other_charges": Decimal("0.00"),
        "total": total,
    }


def _standardize_extraction(extracted: ExtractedReceipt) -> Dict[str, Any]:
    """Convert ExtractedReceipt Pydantic model to standardized Decimal dictionary."""
    items = []
    for it in extracted.items:
        qty = to_decimal(it.quantity, default="1.000", quant=QTY_ROUND)
        if qty <= 0:
            qty = Decimal("1.000")
        line_tot = to_decimal(it.line_total)
        unit_p = to_decimal(it.unit_price)
        if unit_p <= 0 and qty > 0 and line_tot > 0:
            unit_p = (line_tot / qty).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)
        elif line_tot <= 0 and unit_p > 0:
            line_tot = (unit_p * qty).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)

        items.append({
            "name": it.name.strip(),
            "quantity": qty,
            "unit_price": unit_p,
            "line_total": line_tot,
        })

    tax = to_decimal(extracted.tax)
    disc = to_decimal(extracted.discount)
    # Discounts are typically subtractions, so keep positive
    if disc < 0:
        disc = abs(disc)
    charges = to_decimal(extracted.other_charges)
    tot = to_decimal(extracted.total)

    subtotal = sum(i["line_total"] for i in items)
    if tot <= 0:
        tot = (subtotal + tax + charges - disc).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)

    return {
        "store": extracted.store or None,
        "date": extracted.date or None,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "discount": disc,
        "other_charges": charges,
        "total": tot,
    }


def validate_receipt_math(
    items: List[Dict[str, Any]],
    tax: Decimal,
    discount: Decimal,
    other_charges: Decimal,
    total: Decimal,
    tolerance: Decimal = Decimal("0.05")
) -> Tuple[bool, Decimal, str]:
    """
    Validate: sum(line_totals) + tax + other_charges - discount == total (within tolerance).
    Returns (is_valid, calculated_total, warning_message).
    """
    subtotal = sum((to_decimal(i.get("line_total", 0))) for i in items)
    calc_total = (subtotal + tax + other_charges - discount).quantize(MONEY_ROUND, rounding=ROUND_HALF_UP)
    diff = abs(calc_total - total)

    if diff <= tolerance:
        return True, calc_total, ""
    
    warning = (
        f"⚠️ Math mismatch: The items sum ({subtotal}) + tax ({tax}) + charges ({other_charges}) "
        f"- discount ({discount}) equals ₹{calc_total}, which differs from the printed total ₹{total} "
        f"by ₹{diff:.2f}. You can adjust the numbers below."
    )
    return False, calc_total, warning


def process_receipt_file(file_bytes: bytes, file_name: str) -> Dict[str, Any]:
    """
    Full pipeline to process an uploaded receipt (JPEG, PNG, or PDF).
    Returns standardized extraction dict with Decimal numbers.
    Never crashes on bad output.
    """
    fname = file_name.lower()
    img_bytes = file_bytes
    mime_type = "image/png" if fname.endswith(".png") else "image/jpeg"

    if fname.endswith(".pdf"):
        try:
            pages = convert_pdf_to_images(file_bytes)
            if not pages:
                return {
                    "success": False,
                    "error": "The PDF file has no readable pages.",
                    "items": [],
                    "total": Decimal("0.00"),
                }
            img_bytes = pages[0]
            mime_type = "image/png"
        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to read PDF: {exc}",
                "items": [],
                "total": Decimal("0.00"),
            }

    # 1. Attempt Gemini structured extraction
    gemini_key = get_gemini_api_key()
    if gemini_key:
        try:
            data = extract_with_gemini(img_bytes, mime_type=mime_type, api_key=gemini_key)
            is_valid, calc_tot, warn = validate_receipt_math(
                data["items"], data["tax"], data["discount"], data["other_charges"], data["total"]
            )
            data["success"] = True
            data["is_valid_math"] = is_valid
            data["math_warning"] = warn
            data["calculated_total"] = calc_tot
            data["engine"] = "gemini"
            return data
        except Exception as exc:
            logger.warning("Gemini OCR failed, trying fallback: %s", exc)

    # 2. Fallback to Tesseract
    try:
        data = extract_with_tesseract(img_bytes)
        is_valid, calc_tot, warn = validate_receipt_math(
            data["items"], data["tax"], data["discount"], data["other_charges"], data["total"]
        )
        data["success"] = True
        data["is_valid_math"] = is_valid
        data["math_warning"] = warn
        data["calculated_total"] = calc_tot
        data["engine"] = "tesseract_fallback"
        return data
    except Exception as exc:
        logger.warning("Tesseract OCR fallback also failed: %s", exc)

    # 3. Controlled failure allowing manual entry
    return {
        "success": False,
        "error": "Automatic text extraction could not read this receipt clearly. You can still add your items manually below.",
        "engine": "none",
        "store": "",
        "date": None,
        "items": [],
        "subtotal": Decimal("0.00"),
        "tax": Decimal("0.00"),
        "discount": Decimal("0.00"),
        "other_charges": Decimal("0.00"),
        "total": Decimal("0.00"),
        "is_valid_math": True,
        "math_warning": "",
    }
