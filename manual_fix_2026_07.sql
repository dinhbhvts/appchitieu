-- ============================================================================
-- Manual DB fix for production Postgres (Render) - equivalent to
-- `alembic upgrade head` for revisions f3a1c9e7d8b2 -> b6d4e2a9c1f7.
--
-- Vì sao cần chạy: code backend mới đã đọc/ghi các cột/bảng dưới đây, nhưng
-- database production hiện chưa có (chưa chạy `alembic upgrade head`), gây
-- lỗi 500 khi gọi các API liên quan (ví dụ /stocks/summary đọc bảng
-- stock_dividends chưa tồn tại).
--
-- AN TOÀN: script này CHỈ THÊM (ADD COLUMN / CREATE TABLE / CREATE INDEX),
-- không DROP, không UPDATE dữ liệu hiện có, không xóa gì cả. Mọi câu lệnh
-- đều có IF NOT EXISTS nên chạy lại nhiều lần cũng không lỗi, không hại.
--
-- CÁCH CHẠY:
--   1. Vào Render Dashboard -> database Postgres của app -> tab "Connect" ->
--      copy "PSQL Command" (hoặc "External Connection String").
--   2. Trên máy anh, mở terminal, dán lệnh psql đó để kết nối vào DB.
--   3. Chạy: \i manual_fix_2026_07.sql
--      (hoặc copy toàn bộ nội dung file này paste thẳng vào psql)
--   4. Nên backup trước (Render có "Backups" tab) dù script chỉ thêm cột.
-- ============================================================================

BEGIN;

-- --- Xóa mềm (is_deleted/deleted_at) cho các bảng liên quan ----------------
ALTER TABLE transactions      ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE transactions      ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE asset_snapshots   ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE asset_snapshots   ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE notebook_items    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE notebook_items    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE stock_cashflows   ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE stock_cashflows   ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE stock_trades      ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE stock_trades      ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE stock_holdings    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE stock_holdings    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

-- --- notebook_items: các trường "Thông tin cá nhân" ------------------------
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS full_name           VARCHAR(150);
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS id_number           VARCHAR(50);
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS id_issued_date      DATE;
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS id_issued_place     VARCHAR(150);
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS birth_cert_no       VARCHAR(50);
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS health_insurance_no VARCHAR(50);
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS hometown            VARCHAR(150);

-- --- notebook_items: nhắc sinh nhật (b6d4e2a9c1f7) --------------------------
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS remind_birthday BOOLEAN NOT NULL DEFAULT TRUE;

-- --- Index bổ sung -----------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_transactions_category_id   ON transactions (category_id);
CREATE INDEX IF NOT EXISTS ix_transactions_user_date      ON transactions (user_id, date);
CREATE INDEX IF NOT EXISTS ix_asset_snapshots_year_month  ON asset_snapshots (year, month);
CREATE INDEX IF NOT EXISTS ix_stock_trades_symbol_date    ON stock_trades (symbol, date);

-- --- Bảng mới: stock_dividends (Cổ tức) -------------------------------------
CREATE TABLE IF NOT EXISTS stock_dividends (
    id           SERIAL PRIMARY KEY,
    date         DATE NOT NULL,
    symbol       VARCHAR(20) NOT NULL,
    quantity     INTEGER NULL,
    amount       NUMERIC(18, 0) NULL,
    fee          NUMERIC(18, 0) NOT NULL DEFAULT 0,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    note         VARCHAR(255) NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by   INTEGER NULL REFERENCES users(id),
    is_deleted   BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at   TIMESTAMP NULL
);
CREATE INDEX IF NOT EXISTS ix_stock_dividends_date   ON stock_dividends (date);
CREATE INDEX IF NOT EXISTS ix_stock_dividends_symbol ON stock_dividends (symbol);

-- Nếu bảng stock_dividends đã tồn tại từ trước nhưng thiếu cột quantity /
-- amount đang là NOT NULL (bản cũ hơn) thì đảm bảo đúng trạng thái mới:
ALTER TABLE stock_dividends ADD COLUMN IF NOT EXISTS quantity INTEGER NULL;
ALTER TABLE stock_dividends ALTER COLUMN amount DROP NOT NULL;

-- --- Bảng mới: notebook_attachments (Hồ sơ đính kèm) ------------------------
CREATE TABLE IF NOT EXISTS notebook_attachments (
    id               SERIAL PRIMARY KEY,
    notebook_item_id INTEGER NOT NULL REFERENCES notebook_items(id),
    file_name        VARCHAR(255) NOT NULL,
    mime_type        VARCHAR(100) NULL,
    size_bytes       INTEGER NULL,
    drive_file_id    VARCHAR(120) NOT NULL,
    drive_link       VARCHAR(500) NULL,
    uploaded_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    uploaded_by      INTEGER NULL REFERENCES users(id),
    is_deleted       BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at       TIMESTAMP NULL
);
CREATE INDEX IF NOT EXISTS ix_notebook_attachments_notebook_item_id
    ON notebook_attachments (notebook_item_id);

-- --- Seed 2 loại sổ tay mới (personal_info, task) nếu chưa có --------------
INSERT INTO notebook_types (key, name, icon, is_default, is_active)
VALUES ('personal_info', 'Thông tin cá nhân', '🪪', TRUE, TRUE)
ON CONFLICT (key) DO NOTHING;

INSERT INTO notebook_types (key, name, icon, is_default, is_active)
VALUES ('task', 'Nhắc việc', '✅', TRUE, TRUE)
ON CONFLICT (key) DO NOTHING;

-- --- Đánh dấu cho Alembic biết là đã áp dụng tới 2 revision này -------------
-- (để lần sau chạy `alembic upgrade head` bình thường không bị lỗi/lặp lại)
UPDATE alembic_version SET version_num = 'b6d4e2a9c1f7';
INSERT INTO alembic_version (version_num)
SELECT 'b6d4e2a9c1f7'
WHERE NOT EXISTS (SELECT 1 FROM alembic_version);

COMMIT;

-- Kiểm tra nhanh sau khi chạy xong:
-- SELECT version_num FROM alembic_version;                 -- phải ra b6d4e2a9c1f7
-- SELECT * FROM stock_dividends LIMIT 1;                    -- không lỗi là OK
-- SELECT remind_birthday FROM notebook_items LIMIT 1;       -- không lỗi là OK
