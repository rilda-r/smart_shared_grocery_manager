# DIAGNOSIS.md — Receipt Scanning (OCR) Failure Analysis

## 1. Executive Summary
The receipt scanning feature in GrocEase fails at multiple levels:
1. **Disconnected UI**: `pages/10_Bill_Scanning.py` never called any real OCR or backend service. It imported `upload_bill` from `mock/mock_api.py`, passing only `uploaded_file.name` (a string) rather than the uploaded file bytes. It returned static mock data ("Rice", "Sugar") stored purely in ephemeral `st.session_state`.
2. **Missing Dependencies & API Keys**: The required primary extractor SDK `google-genai` and fuzzy matching library `rapidfuzz` are not in `requirements.txt` and not installed. No `GEMINI_API_KEY` was configured in `.env` or Streamlit secrets (`.streamlit/secrets.toml` did not exist).
3. **Tesseract Binary & Parser Inadequacy**: While a Tesseract binary was detected on the host OS (`C:\Program Files\Tesseract-OCR\tesseract.EXE`), `GROCEASE_TESSERACT_CMD` in `.env` was blank. When tested with a real receipt image, Tesseract generated severely garbled text (missing decimal points, dropped characters, merged tokens like `"MilleiL 2x4500 9000"` and `"Total 28400"`). The existing regex parser in `services/ocr_service.py` failed to extract the total, dropped 3 of 5 items, and corrupted the names of the remaining 2.
4. **Schema & Multi-Assignee Gaps**: The existing database only contains legacy tables `bills` (single total) and `bill_items` (single `assigned_user_id`). It lacks the required `receipts` schema (with store, receipt_date, tax, discount, other_charges, image_path), `is_extra` flagging, and `receipt_item_assignments` for splitting a single item line across multiple room members.

---

## 2. Detailed Findings

### A. Library & API Configuration
| Component | Status | Finding |
|---|---|---|
| `google-genai` | ❌ Not Installed | Primary structured JSON OCR engine requested in prompt is not installed. |
| `rapidfuzz` | ❌ Not Installed | Required for item name fuzzy matching against pending grocery list. |
| `GEMINI_API_KEY` | ❌ Missing | Not found in `.env`, user environment, or `.streamlit/secrets.toml`. |
| `pytesseract` & Binary | ⚠️ Unconfigured | Binary exists at `C:\Program Files\Tesseract-OCR\tesseract.exe`, but `GROCEASE_TESSERACT_CMD` in `.env` was empty. |
| `requirements.txt` | ❌ Incomplete | Missing `google-genai`, `rapidfuzz`, `pillow`, `pypdfium2`/`pymupdf`. |

### B. File Upload & Flow Through the Pipeline
- In `pages/10_Bill_Scanning.py`:
  - `st.file_uploader` accepted JPG, PNG, and PDF files.
  - However, the uploaded file object was never read (`.getvalue()` was never called).
  - The handler invoked:
    ```python
    bill = upload_bill(room_id, user_id, uploaded_file.name)
    ```
  - This routed directly to `mock/mock_api.py`, which simulated OCR with `time.sleep(1.5)` and inserted two hardcoded mock items ("Rice", "Sugar") into `st.session_state["store_bill_items"]`.
  - The actual file bytes never reached `services/ocr_service.py` or Supabase Storage.

### C. Raw OCR Output & Parsing Quality (Tested with Real Receipt)
We executed the existing OCR pipeline (`TesseractProvider` + `parse_bill_items`) against a generated sample receipt:
```
FRESH SUPERMARKET
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
```
**Results**:
- **Raw Tesseract OCR Output**:
  - `Milk 1L` -> `MilleiL 2x4500 9000`
  - `Whole Wheat Bread` -> `Whole Wheat Bread 14000 40.00`
  - `Farm Fresh Eggs` -> `Fatm Fresh Eggs6pk 18500 6500`
  - `Total` -> `Total 28400` (lost decimal point)
- **Regex Parsing Results**:
  - `total_amount` returned `None` because the regex `_AMOUNT_RE` strictly demanded `.XX` or `,XX`.
  - Out of 5 items, only 2 were parsed. Their names absorbed numerical noise: `item_name: 'Whole Wheat Bread 14000'`.
  - Tax, discounts, and date were discarded entirely by `_SKIP_RE`.

### D. Exceptions, Database Schema & Supabase RLS
1. **Swallowed Exceptions**:
   - `services/ocr_service.py`: Wrapped in blanket `except Exception:` returning generic `_failure(...)`, hiding real failure reasons.
   - `mock/mock_api.py` and `database/database.py`: Blanket `except Exception:` blocks swallow errors and return empty lists or `False`.
2. **Database Schema Limitations**:
   - The Postgres database currently has `bills` and `bill_items`.
   - `bill_items` has only a single `assigned_user_id` column, which makes it impossible to split a single receipt line (e.g., 3 milks: 2 for Rilda, 1 for Tejashree) across multiple users.
   - Missing fields: store, receipt_date, subtotal, tax, discount, other_charges, image_path, and `is_extra` flag.
   - Missing atomic Postgres transaction / RPC to record receipt assignments, mark grocery list items as purchased, and generate payment debts in a single operation.
3. **RLS & Permissions**:
   - Connection is currently made through the Supabase connection pooler as direct Postgres superuser (`relrowsecurity = False`). However, application-level checks and proper RLS policies are needed for room privacy and uploader permissions.

---

## 3. Corrective Plan
1. **Engine Setup**:
   - Install `google-genai` and `rapidfuzz`. Update `requirements.txt`.
   - Configure `GEMINI_API_KEY` via `st.secrets` and `.env`.
   - Support PDF-to-image conversion using `pypdfium2`.
   - Implement Gemini structured JSON OCR extraction (`store`, `date`, `items`, `tax`, `discount`, `other_charges`, `total`).
   - Use Tesseract only as a fallback engine.
2. **Data Model & Migrations**:
   - Add/adapt `receipts`, `receipt_items`, and `receipt_item_assignments` tables (or extend existing `bills` schema) to support line items, extras, and multiple user assignments per line.
   - Create a Postgres atomic RPC function for single-transaction settlement (receipt + line items + assignments + payment debts + grocery item status updates).
3. **UI Flow (Streamlit `pages/10_Bill_Scanning.py`)**:
   - Connect UI directly to live database & services (retire mock API in bill scanning).
   - Require room selection upfront.
   - Upload file to Supabase Storage and run Gemini structured extraction.
   - Editable extraction table with Decimal arithmetic and math validation (sum of lines + tax + charges - discount == total).
   - Fuzzy matching with `rapidfuzz` against room pending grocery items, handling multi-user quantity splits.
   - "Your items purchased" tab for extras and unpurchased grocery list items.
   - Proportional vs. equal split for tax and charges using exact-cent largest remainder method.
   - Final confirmation with double-submission prevention and payment tab reflection.
4. **Automated & Manual Tests**:
   - Pytest tests for structured parsing, validation, fuzzy matching with multi-requester splits, proportional tax distribution, and zero-sum rounding.
   - End-to-end manual verification script.
