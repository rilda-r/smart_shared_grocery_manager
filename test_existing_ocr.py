import sys
import io
from PIL import Image, ImageDraw, ImageFont
from decimal import Decimal

# 1. Create a synthetic receipt image
img = Image.new("RGB", (600, 800), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

receipt_text = """FRESH SUPERMARKET
Date: 15/10/2026

Milk 1L              2 x 45.00    90.00
Whole Wheat Bread    1 x 40.00    40.00
Farm Fresh Eggs 6pk  1 x 65.00    65.00
Red Onion 1kg        1 x 35.00    35.00
Organic Sugar 1kg    1 x 50.00    50.00

Subtotal                         280.00
Tax / GST 5%                      14.00
Discount                         -10.00
Total                            284.00
"""

y = 40
for line in receipt_text.splitlines():
    draw.text((40, y), line, fill=(0, 0, 0))
    y += 28

buf = io.BytesIO()
img.save(buf, format="PNG")
image_bytes = buf.getvalue()

# Save sample receipt image
with open("sample_receipt.png", "wb") as f:
    f.write(image_bytes)

print("Generated sample_receipt.png, size:", len(image_bytes))

# 2. Test Tesseract directly
try:
    import pytesseract
    raw_ocr = pytesseract.image_to_string(img)
    print("--- RAW OCR OUTPUT FROM TESSERACT ---")
    print(raw_ocr)
    print("-------------------------------------")
except Exception as e:
    print("Tesseract raw OCR failed:", e)
    raw_ocr = ""

# 3. Test services.ocr_service
try:
    from services.ocr_service import process_bill, parse_bill_items
    parsed = parse_bill_items(raw_ocr)
    print("--- PARSED BILL ITEMS ---")
    print(parsed)
    print("-------------------------")
    
    proc_result = process_bill(image_bytes, "sample_receipt.png")
    print("--- PROCESS_BILL RESULT ---")
    print(proc_result)
    print("---------------------------")
except Exception as e:
    print("ocr_service test failed:", e)
