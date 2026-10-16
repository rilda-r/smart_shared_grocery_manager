-- Migration 001: Receipt Scanning System & Atomic Confirmation RPC
-- Safe & idempotent

CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY,
    room_id INT NOT NULL REFERENCES rooms (id) ON DELETE CASCADE,
    uploaded_by INT NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    image_path VARCHAR(500) NULL,
    store VARCHAR(255) NULL,
    receipt_date DATE NULL,
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tax DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    other_charges DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_receipts_total CHECK (total >= 0)
);

CREATE INDEX IF NOT EXISTS idx_receipts_room ON receipts (room_id);
CREATE INDEX IF NOT EXISTS idx_receipts_uploaded_by ON receipts (uploaded_by);

CREATE TABLE IF NOT EXISTS receipt_items (
    id SERIAL PRIMARY KEY,
    receipt_id INT NOT NULL REFERENCES receipts (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    unit_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    line_total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    matched_grocery_item_id INT NULL REFERENCES grocery_items (id) ON DELETE SET NULL,
    is_extra BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_receipt_items_amounts CHECK (quantity > 0 AND unit_price >= 0 AND line_total >= 0)
);

CREATE INDEX IF NOT EXISTS idx_receipt_items_receipt ON receipt_items (receipt_id);
CREATE INDEX IF NOT EXISTS idx_receipt_items_matched ON receipt_items (matched_grocery_item_id);

CREATE TABLE IF NOT EXISTS receipt_item_assignments (
    id SERIAL PRIMARY KEY,
    receipt_item_id INT NOT NULL REFERENCES receipt_items (id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    quantity DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT chk_assignment_qty CHECK (quantity >= 0),
    CONSTRAINT chk_assignment_amt CHECK (amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_ria_item ON receipt_item_assignments (receipt_item_id);
CREATE INDEX IF NOT EXISTS idx_ria_user ON receipt_item_assignments (user_id);

-- Alter payments table to support receipts
DO $$
BEGIN
    -- Make bill_id nullable if not already
    BEGIN
        ALTER TABLE payments ALTER COLUMN bill_id DROP NOT NULL;
    EXCEPTION
        WHEN OTHERS THEN NULL;
    END;

    -- Add receipt_id column if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'payments' AND column_name = 'receipt_id'
    ) THEN
        ALTER TABLE payments ADD COLUMN receipt_id INT NULL REFERENCES receipts (id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_payments_receipt ON payments (receipt_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_receipt_payer 
    ON payments (receipt_id, payer_user_id) 
    WHERE receipt_id IS NOT NULL;

-- Atomic Postgres RPC Function to confirm receipt, save items, assignments, payments, and mark grocery items purchased
CREATE OR REPLACE FUNCTION confirm_receipt_atomic(payload JSONB)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_receipt_id INT;
    v_room_id INT;
    v_uploaded_by INT;
    v_store VARCHAR(255);
    v_receipt_date DATE;
    v_subtotal NUMERIC(10,2);
    v_tax NUMERIC(10,2);
    v_discount NUMERIC(10,2);
    v_other_charges NUMERIC(10,2);
    v_total NUMERIC(10,2);
    v_image_path VARCHAR(500);
    
    v_item JSONB;
    v_item_id INT;
    v_assign JSONB;
    v_payment JSONB;
    v_grocery_id INT;
BEGIN
    -- Extract receipt fields
    v_room_id := (payload->'receipt'->>'room_id')::INT;
    v_uploaded_by := (payload->'receipt'->>'uploaded_by')::INT;
    v_store := payload->'receipt'->>'store';
    v_receipt_date := (payload->'receipt'->>'receipt_date')::DATE;
    v_subtotal := COALESCE((payload->'receipt'->>'subtotal')::NUMERIC, 0.00);
    v_tax := COALESCE((payload->'receipt'->>'tax')::NUMERIC, 0.00);
    v_discount := COALESCE((payload->'receipt'->>'discount')::NUMERIC, 0.00);
    v_other_charges := COALESCE((payload->'receipt'->>'other_charges')::NUMERIC, 0.00);
    v_total := COALESCE((payload->'receipt'->>'total')::NUMERIC, 0.00);
    v_image_path := payload->'receipt'->>'image_path';

    -- 1. Insert Receipt
    INSERT INTO receipts (
        room_id, uploaded_by, image_path, store, receipt_date,
        subtotal, tax, discount, other_charges, total, created_at
    ) VALUES (
        v_room_id, v_uploaded_by, v_image_path, v_store, v_receipt_date,
        v_subtotal, v_tax, v_discount, v_other_charges, v_total, NOW()
    ) RETURNING id INTO v_receipt_id;

    -- 2. Insert Items & Assignments
    IF payload ? 'items' AND jsonb_typeof(payload->'items') = 'array' THEN
        FOR v_item IN SELECT * FROM jsonb_array_elements(payload->'items')
        LOOP
            INSERT INTO receipt_items (
                receipt_id, name, quantity, unit_price, line_total,
                matched_grocery_item_id, is_extra
            ) VALUES (
                v_receipt_id,
                v_item->>'name',
                COALESCE((v_item->>'quantity')::NUMERIC, 1.000),
                COALESCE((v_item->>'unit_price')::NUMERIC, 0.00),
                COALESCE((v_item->>'line_total')::NUMERIC, 0.00),
                (v_item->>'matched_grocery_item_id')::INT,
                COALESCE((v_item->>'is_extra')::BOOLEAN, FALSE)
            ) RETURNING id INTO v_item_id;

            -- Insert assignments for this item
            IF v_item ? 'assignments' AND jsonb_typeof(v_item->'assignments') = 'array' THEN
                FOR v_assign IN SELECT * FROM jsonb_array_elements(v_item->'assignments')
                LOOP
                    INSERT INTO receipt_item_assignments (
                        receipt_item_id, user_id, quantity, amount
                    ) VALUES (
                        v_item_id,
                        (v_assign->>'user_id')::INT,
                        COALESCE((v_assign->>'quantity')::NUMERIC, 1.000),
                        COALESCE((v_assign->>'amount')::NUMERIC, 0.00)
                    );
                END LOOP;
            END IF;
        END LOOP;
    END IF;

    -- 3. Insert Payments
    IF payload ? 'payments' AND jsonb_typeof(payload->'payments') = 'array' THEN
        FOR v_payment IN SELECT * FROM jsonb_array_elements(payload->'payments')
        LOOP
            IF (v_payment->>'payer_user_id')::INT <> (v_payment->>'payee_user_id')::INT 
               AND (v_payment->>'amount')::NUMERIC > 0 THEN
                INSERT INTO payments (
                    room_id, receipt_id, payer_user_id, payee_user_id,
                    amount, payment_status, created_at
                ) VALUES (
                    v_room_id,
                    v_receipt_id,
                    (v_payment->>'payer_user_id')::INT,
                    (v_payment->>'payee_user_id')::INT,
                    (v_payment->>'amount')::NUMERIC,
                    'pending',
                    NOW()
                );
            END IF;
        END LOOP;
    END IF;

    -- 4. Mark matched grocery items as purchased
    IF payload ? 'purchased_grocery_ids' AND jsonb_typeof(payload->'purchased_grocery_ids') = 'array' THEN
        FOR v_grocery_id IN SELECT (jsonb_array_elements_text(payload->'purchased_grocery_ids'))::INT
        LOOP
            UPDATE grocery_items
            SET status = 'purchased',
                purchased_quantity = quantity,
                updated_at = NOW()
            WHERE id = v_grocery_id;
        END LOOP;
    END IF;

    RETURN jsonb_build_object(
        'success', TRUE,
        'receipt_id', v_receipt_id,
        'message', 'Receipt and expense split confirmed atomically.'
    );
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Atomic confirmation failed: %', SQLERRM;
END;
$$;
