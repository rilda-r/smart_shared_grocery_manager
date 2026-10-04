"""
services/ocr_service.py

OCR abstraction for bill processing. The rest of the application only calls
``process_bill`` / ``extract_text`` / ``parse_bill_items``; the concrete
engine (Tesseract or Google Vision) is selected via ``GROCEASE_OCR_PROVIDER``
and can be swapped or faked through ``register_provider``.

OCR never raises to callers: failures return a controlled error envelope
(``error_code == "ocr_failed"``, ``data.manual_entry_required == True``) so the
UI can fall back to manual entry.
"""

import io
import logging
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from config.settings import get_settings
from utils.helpers import (
    MONEY_QUANT,
    ServiceError,
    error_response,
    success_response,
)
from utils.validators import validate_bill_file

logger = logging.getLogger("grocease.ocr")

# OCR status constants (match bills.ocr_status)
OCR_PENDING = "pending"
OCR_PROCESSING = "processing"
OCR_COMPLETED = "completed"
OCR_FAILED = "failed"

MAX_PDF_PAGES = 5


class OCRError(Exception):
    """Internal OCR failure (converted to a controlled error response)."""


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
class OCRProvider:
    """Interface: turn ONE raster image (bytes) into text."""

    name = "base"

    def extract_text(self, image_bytes: bytes) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class TesseractProvider(OCRProvider):
    name = "tesseract"

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise OCRError("Tesseract OCR libraries are not installed.") from exc
        cfg = get_settings()
        if cfg.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd
        Image.MAX_IMAGE_PIXELS = 50_000_000  # decompression-bomb guard
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.load()
                return pytesseract.image_to_string(image.convert("L"), lang=cfg.ocr_language)
        except pytesseract.TesseractNotFoundError as exc:
            raise OCRError("The Tesseract engine is not available.") from exc
        except Exception as exc:  # corrupt image, engine failure, ...
            raise OCRError("The image could not be read.") from exc


class GoogleVisionProvider(OCRProvider):
    """Uses GOOGLE_APPLICATION_CREDENTIALS from the environment (never in code)."""

    name = "google_vision"

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            from google.cloud import vision
        except ImportError as exc:
            raise OCRError("Google Vision client is not installed.") from exc
        try:
            client = vision.ImageAnnotatorClient()
            response = client.text_detection(image=vision.Image(content=image_bytes))
            if response.error.message:
                raise OCRError("Google Vision could not process the image.")
            return response.full_text_annotation.text or ""
        except OCRError:
            raise
        except Exception as exc:
            raise OCRError("Google Vision request failed.") from exc


_PROVIDERS = {"tesseract": TesseractProvider, "google_vision": GoogleVisionProvider}


def register_provider(name: str, factory) -> None:
    """Register/replace a provider factory (used by tests or custom engines)."""
    _PROVIDERS[name.lower()] = factory


def get_provider(name=None) -> OCRProvider:
    key = (name or get_settings().ocr_provider).lower()
    factory = _PROVIDERS.get(key)
    if factory is None:
        raise OCRError("Unknown OCR provider.")
    return factory()


# ---------------------------------------------------------------------------
# Text extraction (images + PDFs)
# ---------------------------------------------------------------------------
def _pdf_to_text(file_bytes: bytes, provider: OCRProvider) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OCRError("PDF support is not installed.") from exc
    try:
        pdf = pdfium.PdfDocument(file_bytes)
        parts = []
        for index in range(min(len(pdf), MAX_PDF_PAGES)):
            page = pdf[index]
            embedded = (page.get_textpage().get_text_range() or "").strip()
            if len(embedded) >= 20:  # digital PDF: use the real text layer
                parts.append(embedded)
                continue
            buffer = io.BytesIO()
            page.render(scale=2.5).to_pil().save(buffer, format="PNG")
            parts.append(provider.extract_text(buffer.getvalue()))
        return "\n".join(parts)
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError("The PDF could not be processed.") from exc


def extract_text(file_bytes: bytes, file_name: str, provider=None) -> str:
    """Return raw text for an image or PDF. Raises ``OCRError`` on failure."""
    engine = provider or get_provider()
    is_pdf = str(file_name).lower().endswith(".pdf")
    text = _pdf_to_text(file_bytes, engine) if is_pdf else engine.extract_text(file_bytes)
    return text or ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
_AMOUNT_RE = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d+)[.,]\d{2}$")
_QTY_TOKEN_RE = re.compile(r"^(\d{1,2})[xX\u00d7]?$")
_QTY_PREFIX_RE = re.compile(r"^(\d{1,2})\s*[xX\u00d7@]\s+(.+)$")
_CURRENCY_PREFIX_RE = re.compile(r"^(?:rs\.?|inr)", re.IGNORECASE)
_SEPARATORS = {"x", "X", "\u00d7", "@", "*"}
_SKIP_RE = re.compile(
    r"\b(sub\s*-?\s*total|total|tax|gst|cgst|sgst|igst|vat|discount|change|cash|card|"
    r"visa|upi|round(?:ing)?\s*off|invoice|receipt|bill\s*(?:no|number)|date|time|phone|"
    r"tel|thank|balance|tender|paid|savings|items?\s*count)\b",
    re.IGNORECASE,
)
_GRAND_RE = re.compile(
    r"\b(grand\s*total|net\s*(?:amount|total|payable)|amount\s*(?:due|payable)|"
    r"total\s*(?:amount|due|payable))\b",
    re.IGNORECASE,
)
_SUBTOTAL_RE = re.compile(r"\bsub\s*-?\s*total\b", re.IGNORECASE)
_PLAIN_TOTAL_RE = re.compile(r"\btotal\b", re.IGNORECASE)


def _amount(token: str):
    token = _CURRENCY_PREFIX_RE.sub("", token.strip("\u20b9$\u20ac\u00a3*:"))
    if not _AMOUNT_RE.match(token):
        return None
    if "." in token:
        token = token.replace(",", "")
    else:  # "45,00" decimal-comma style
        token = token.replace(",", ".")
    try:
        return Decimal(token).quantize(MONEY_QUANT)
    except InvalidOperation:
        return None


def _trailing_amounts(tokens):
    """Scan from the end: up to two amounts, then an optional small int quantity."""
    amounts, i = [], len(tokens)
    while i > 0 and len(amounts) < 2:
        token = tokens[i - 1]
        if token in _SEPARATORS and amounts:
            i -= 1
            continue
        value = _amount(token)
        if value is None:
            break
        amounts.append(value)
        i -= 1
    amounts.reverse()
    qty = None
    if amounts:
        j = i
        while j > 0 and tokens[j - 1] in _SEPARATORS:
            j -= 1
        if j > 0:
            match = _QTY_TOKEN_RE.match(tokens[j - 1])
            if match and j - 1 > 0:  # keep at least one token for the name
                qty = Decimal(match.group(1))
                i = j - 1
    return amounts, qty, i


def _clean_name(tokens) -> str:
    name = " ".join(tokens).strip(" -:*.#\t")
    return re.sub(r"\s{2,}", " ", name)


def _parse_line(line: str):
    tokens = line.split()
    if len(tokens) < 2:
        return None
    amounts, qty, name_end = _trailing_amounts(tokens)
    if not amounts:
        return None
    name = _clean_name(tokens[:name_end])
    if qty is None:
        prefix = _QTY_PREFIX_RE.match(name)
        if prefix:
            qty, name = Decimal(prefix.group(1)), prefix.group(2).strip()
    if len(name) < 2 or not any(c.isalpha() for c in name):
        return None
    if len(amounts) == 2:
        unit, total = amounts
        if qty is None:
            ratio = total / unit if unit > 0 else Decimal(0)
            rounded = ratio.to_integral_value(rounding=ROUND_HALF_UP)
            if 1 <= rounded <= 99 and abs(ratio - rounded) < Decimal("0.01"):
                qty = rounded
            else:
                qty, unit = Decimal(1), total
        elif abs(qty * unit - total) > Decimal("0.05"):
            unit = (total / qty).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    else:
        total = amounts[0]
        qty = qty or Decimal(1)
        unit = (total / qty).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return {
        "item_name": name[:255],
        "quantity": qty.quantize(Decimal("0.001")),
        "unit_price": unit,
        "total_price": total,
    }


def parse_bill_items(text: str) -> dict:
    """Parse OCR text into ``{"items": [...], "total_amount": Decimal | None}``."""
    items, total, grand_found = [], None, False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        last = _trailing_amounts(line.split())[0]
        if _SUBTOTAL_RE.search(line):
            continue
        if _GRAND_RE.search(line):
            if last:
                total, grand_found = last[-1], True
            continue
        if _PLAIN_TOTAL_RE.search(line):
            if last and not grand_found:
                total = last[-1]
            continue
        if _SKIP_RE.search(line):
            continue
        parsed = _parse_line(line)
        if parsed:
            items.append(parsed)
    return {"items": items, "total_amount": total}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _failure(message: str) -> dict:
    return error_response(
        message,
        "ocr_failed",
        {"ocr_status": OCR_FAILED, "manual_entry_required": True, "items": [], "total_amount": None},
    )


def process_bill(file_bytes, file_name, provider=None) -> dict:
    """Validate, OCR and parse an uploaded bill. Never raises.

    Invalid files return ``invalid_input``; OCR problems return ``ocr_failed``.
    """
    try:
        safe_name = validate_bill_file(file_name, file_bytes)
    except ServiceError as exc:
        return error_response(exc.message, exc.error_code)
    try:
        text = extract_text(bytes(file_bytes), safe_name, provider)
        parsed = parse_bill_items(text)
    except OCRError as exc:
        logger.warning("OCR failed: %s", exc)
        return _failure("We couldn't read this bill automatically. Please enter the items manually.")
    except Exception:  # noqa: BLE001 - OCR must never crash the app
        logger.exception("Unexpected OCR failure")
        return _failure("We couldn't read this bill automatically. Please enter the items manually.")
    if not parsed["items"]:
        return _failure("No items could be recognised on this bill. Please enter them manually.")
    return success_response(
        {
            "ocr_status": OCR_COMPLETED,
            "manual_entry_required": False,
            "file_name": safe_name,
            "items": parsed["items"],
            "total_amount": parsed["total_amount"],
        },
        "Bill processed.",
    )
