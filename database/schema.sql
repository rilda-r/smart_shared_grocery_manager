-- GrocEase MySQL schema (MySQL 8+). Idempotent: safe to re-run.
-- Money is always DECIMAL(10,2) (quantity DECIMAL(10,3)); never FLOAT/DOUBLE.
-- The `users` table is a superset of the contract User model: the extra
-- columns (full_name, is_verified, otp_*, failed_login_attempts, locked_until)
-- exist for login lockout and for the pre-existing account/OTP pages.

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    full_name VARCHAR(255) NULL,
    is_verified TINYINT(1) NOT NULL DEFAULT 0,
    otp_code VARCHAR(6) NULL,
    otp_expires_at VARCHAR(64) NULL,
    otp_last_sent_at VARCHAR(64) NULL,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until VARCHAR(64) NULL,
    UNIQUE KEY uq_users_email (email),
    UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    secret_code VARCHAR(16) NOT NULL,
    creator_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_rooms_secret_code (secret_code),
    KEY idx_rooms_creator (creator_id),
    CONSTRAINT fk_rooms_creator FOREIGN KEY (creator_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS room_members (
    room_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('creator', 'member') NOT NULL DEFAULT 'member',
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (room_id, user_id),
    KEY idx_room_members_user (user_id),
    CONSTRAINT fk_room_members_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_room_members_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS grocery_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    user_id INT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    status ENUM('pending', 'purchased', 'unavailable') NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_grocery_room_status (room_id, status),
    KEY idx_grocery_user (user_id),
    CONSTRAINT chk_grocery_quantity CHECK (quantity > 0),
    CONSTRAINT fk_grocery_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_grocery_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    uploaded_by INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    ocr_status ENUM('pending', 'processing', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_bills_room (room_id),
    KEY idx_bills_uploaded_by (uploaded_by),
    CONSTRAINT chk_bills_total CHECK (total_amount >= 0),
    CONSTRAINT fk_bills_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_bills_uploader FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bill_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    unit_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    matched_grocery_item_id INT NULL,
    assigned_user_id INT NULL,
    KEY idx_bill_items_bill (bill_id),
    KEY idx_bill_items_assigned (assigned_user_id),
    KEY idx_bill_items_matched (matched_grocery_item_id),
    CONSTRAINT chk_bill_items_amounts CHECK (quantity > 0 AND unit_price >= 0 AND total_price >= 0),
    CONSTRAINT fk_bill_items_bill FOREIGN KEY (bill_id) REFERENCES bills (id) ON DELETE CASCADE,
    CONSTRAINT fk_bill_items_grocery FOREIGN KEY (matched_grocery_item_id) REFERENCES grocery_items (id) ON DELETE SET NULL,
    CONSTRAINT fk_bill_items_user FOREIGN KEY (assigned_user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    bill_id INT NOT NULL,
    payer_user_id INT NOT NULL,
    payee_user_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_status ENUM('pending', 'settled', 'reported') NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    settled_at DATETIME NULL,
    reported_at DATETIME NULL,
    UNIQUE KEY uq_payments_bill_payer (bill_id, payer_user_id),
    KEY idx_payments_room_status (room_id, payment_status),
    KEY idx_payments_payer (payer_user_id),
    KEY idx_payments_payee (payee_user_id),
    CONSTRAINT chk_payments_amount CHECK (amount > 0),
    CONSTRAINT chk_payments_parties CHECK (payer_user_id <> payee_user_id),
    CONSTRAINT fk_payments_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
    CONSTRAINT fk_payments_bill FOREIGN KEY (bill_id) REFERENCES bills (id) ON DELETE CASCADE,
    CONSTRAINT fk_payments_payer FOREIGN KEY (payer_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payments_payee FOREIGN KEY (payee_user_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS personal_expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    expense_date DATE NOT NULL,
    description VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_expenses_user_date (user_id, expense_date),
    KEY idx_expenses_user_category (user_id, category),
    CONSTRAINT chk_expenses_amount CHECK (amount > 0),
    CONSTRAINT fk_expenses_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS budgets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category VARCHAR(50) NOT NULL,
    monthly_limit DECIMAL(10,2) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_budgets_user_category (user_id, category),
    CONSTRAINT chk_budgets_limit CHECK (monthly_limit > 0),
    CONSTRAINT fk_budgets_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
