-- GrocEase Supabase PostgreSQL schema. Idempotent: safe to re-run.
-- Money is always DECIMAL(10,2) (quantity DECIMAL(10,3)); never FLOAT/DOUBLE.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    full_name VARCHAR(255) NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    otp_code VARCHAR(6) NULL,
    otp_expires_at VARCHAR(64) NULL,
    otp_last_sent_at VARCHAR(64) NULL,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until VARCHAR(64) NULL,
    nickname VARCHAR(50) NULL,
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_username UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id INT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    secret_code VARCHAR(16) NOT NULL,
    creator_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_rooms_secret_code UNIQUE (secret_code),
    CONSTRAINT fk_rooms_creator FOREIGN KEY (creator_id) REFERENCES users (id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_rooms_creator ON rooms (creator_id);

CREATE TABLE IF NOT EXISTS room_members (
    room_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (room_id, user_id),
    CONSTRAINT fk_room_members_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_room_members_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_room_members_user ON room_members (user_id);

CREATE TABLE IF NOT EXISTS grocery_items (
    id SERIAL PRIMARY KEY,
    room_id INT NOT NULL,
    user_id INT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    purchased_quantity INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_grocery_quantity CHECK (quantity > 0),
    CONSTRAINT fk_grocery_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_grocery_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_grocery_room_status ON grocery_items (room_id, status);
CREATE INDEX IF NOT EXISTS idx_grocery_user ON grocery_items (user_id);

CREATE TABLE IF NOT EXISTS bills (
    id SERIAL PRIMARY KEY,
    room_id INT NOT NULL,
    uploaded_by INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    ocr_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_bills_total CHECK (total_amount >= 0),
    CONSTRAINT fk_bills_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_bills_uploader FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_bills_room ON bills (room_id);
CREATE INDEX IF NOT EXISTS idx_bills_uploaded_by ON bills (uploaded_by);

CREATE TABLE IF NOT EXISTS bill_items (
    id SERIAL PRIMARY KEY,
    bill_id INT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    unit_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    matched_grocery_item_id INT NULL,
    assigned_user_id INT NULL,
    CONSTRAINT chk_bill_items_amounts CHECK (quantity > 0 AND unit_price >= 0 AND total_price >= 0),
    CONSTRAINT fk_bill_items_bill FOREIGN KEY (bill_id) REFERENCES bills (id) ON DELETE CASCADE,
    CONSTRAINT fk_bill_items_grocery FOREIGN KEY (matched_grocery_item_id) REFERENCES grocery_items (id) ON DELETE SET NULL,
    CONSTRAINT fk_bill_items_user FOREIGN KEY (assigned_user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_bill_items_bill ON bill_items (bill_id);
CREATE INDEX IF NOT EXISTS idx_bill_items_assigned ON bill_items (assigned_user_id);
CREATE INDEX IF NOT EXISTS idx_bill_items_matched ON bill_items (matched_grocery_item_id);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    room_id INT NOT NULL,
    bill_id INT NOT NULL,
    payer_user_id INT NOT NULL,
    payee_user_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMP NULL,
    reported_at TIMESTAMP NULL,
    CONSTRAINT uq_payments_bill_payer UNIQUE (bill_id, payer_user_id),
    CONSTRAINT chk_payments_amount CHECK (amount > 0),
    CONSTRAINT chk_payments_parties CHECK (payer_user_id <> payee_user_id),
    CONSTRAINT fk_payments_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_payments_bill FOREIGN KEY (bill_id) REFERENCES bills (id) ON DELETE CASCADE,
    CONSTRAINT fk_payments_payer FOREIGN KEY (payer_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payments_payee FOREIGN KEY (payee_user_id) REFERENCES users (id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_payments_room_status ON payments (room_id, payment_status);
CREATE INDEX IF NOT EXISTS idx_payments_payer ON payments (payer_user_id);
CREATE INDEX IF NOT EXISTS idx_payments_payee ON payments (payee_user_id);

CREATE TABLE IF NOT EXISTS personal_expenses (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    expense_date DATE NOT NULL,
    description VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_expenses_amount CHECK (amount > 0),
    CONSTRAINT fk_expenses_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON personal_expenses (user_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON personal_expenses (user_id, category);

CREATE TABLE IF NOT EXISTS budgets (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    category VARCHAR(50) NOT NULL,
    monthly_limit DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_budgets_user_category UNIQUE (user_id, category),
    CONSTRAINT chk_budgets_limit CHECK (monthly_limit > 0),
    CONSTRAINT fk_budgets_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS monthly_budget_history (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    month_year VARCHAR(7) NOT NULL,
    total_budget DECIMAL(10,2) NOT NULL,
    total_spent DECIMAL(10,2) NOT NULL,
    total_saved DECIMAL(10,2) NOT NULL,
    category_breakdown JSONB NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_month_history UNIQUE (user_id, month_year),
    CONSTRAINT fk_budget_hist_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_budget_hist_user ON monthly_budget_history (user_id);
