# GrocEase — Smart Shared Grocery Tracker

A modern, full-stack shared grocery manager and household expense budgeting application built with Streamlit and powered by cloud-hosted **Supabase PostgreSQL**.

---

## 🚀 Overview of Overhaul & Key Changes

The application underwent a comprehensive 3-phase overhaul to enable cloud persistence, multi-user collaboration, and realtime synchronization:

### 1. Database Architecture & Supabase Migration
* **Migrated from local MySQL to Supabase PostgreSQL**: All queries execute parameterized SQL via `psycopg2-binary` connecting to cloud-hosted Supabase with SSL enforcement.
* **Schema Updates & Idempotent Migrations**:
  * `users`: Added columns for `full_name`, `username`, `nickname`, `is_verified`, `otp_code`, `otp_expires_at`, `failed_login_attempts`, `locked_until`.
  * `profiles`: User identity table tracking `actual_name` and dynamic display `nickname`.
  * `grocery_items`: Added `purchased_quantity INT NOT NULL DEFAULT 0` to enable linear purchase tracking.
  * `monthly_budget_history`: New history table storing static month-end snapshots (`user_id`, `month_year`, `total_budget`, `total_spent`, `total_saved`, `category_breakdown` JSONB).
  * Cascading integrity: Foreign keys enforce automatic cleanup upon account deletion.

### 2. Phase 1: Cloud Backend & Auth Shell Security
* Replaced local database layer with cloud-hosted Supabase PostgreSQL backend.
* **Auth Visibility Shell Fix**: Completely hidden navigation sidebar and collapse toggle for unauthenticated visitors.
* **Registration & Email OTP**: Registration redirects to login; email OTP verification enforces validation before login; dev mode banner renders when live SMTP is disabled.

### 3. Phase 2: Identity & Global Room Context
* **Nickname Onboarding**: First-time users are prompted with a mandatory onboarding modal to select their public nickname.
* **Profile Management**: Profile view displaying Actual Name and Nickname, interactive Password Reset, and Cascading Delete Account.
* **Universal Room Context**: Universal room switcher in the sidebar and top of grocery views; real member identity attribution query replacing placeholder strings.
* **Navigation Controls**: Browser-style circular Back (`‹`) and Forward (`›`) navigation buttons.

### 4. Phase 3: Realtime Sync, Item Protection & Budget Archiving
* **Live Room Grocery Sync**: Grocery List (`pages/08_Grocery_List.py`) and Shopping Mode (`pages/09_Shopping.py`) hooked up live to active room state with instant Supabase streaming.
* **Duplicate Item Confirmation**: Pop-up confirmation dialog ("*This item already exists. Do you want to add quantity upon it?*") that increments item quantity linearly rather than creating duplicates.
* **Purchased Item Locking**: Purchased row items in the Grocery List view have Edit (`✏️`) and Delete (`🗑️`) permanently locked (`🔒`) to safeguard purchase logs.
* **Shopping Mode Attribution & Increments**: Displays member nickname (`👤 Added by <nickname>`) alongside each item; marking as purchased increments purchase count linearly in both local state and Supabase.
* **Monthly Budget History Dashboard**: Interactive visual dashboard in `pages/13_Budget.py` tracking multi-month spending, cumulative savings KPIs, and historical charts.
* **Month-End Calculation & Supabase Archiving**: Compiles numerical summary and visual Used vs. Saved chart; archives reports permanently to Supabase `monthly_budget_history`; provides a reset modal to archive and clear active expenses for the new month.

---

## 🛠️ Tech Stack

* **Frontend**: Streamlit 1.65+ (Custom CSS design system, Matplotlib visualization)
* **Backend**: Python 3.12, Supabase PostgreSQL (`psycopg2-binary`)
* **Security & Auth**: PBKDF2/SHA-256 password hashing, strict email validator, time-limited OTP tokens
* **Testing**: Pytest

---

## ⚙️ Setup & Installation

### 1. Clone & Install Dependencies
```bash
git clone <repo-url>
cd smart-grocery-tracker
python -m venv .venv
# Activate virtual environment:
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create or verify `.env` in the root directory:
```env
# Supabase PostgreSQL Configuration
GROCEASE_DB_HOST=<your-supabase-db-host>
GROCEASE_DB_PORT=5432
GROCEASE_DB_NAME=postgres
GROCEASE_DB_USER=postgres
GROCEASE_DB_PASSWORD=<your-db-password>
GROCEASE_DB_SSLMODE=require

# SMTP Configuration (Optional - falls back to Dev Mode banner with OTP code)
GROCEASE_ENABLE_LIVE_EMAILS=false
GROCEASE_SMTP_HOST=smtp.gmail.com
GROCEASE_SMTP_PORT=587
GROCEASE_SMTP_USER=
GROCEASE_SMTP_PASSWORD=
GROCEASE_FROM_EMAIL=no-reply@grocease.app
```

### 3. Run the Application
```bash
streamlit run app.py
```

### 4. Run Tests
```bash
python -m pytest -v -k "not needs_db"
```
