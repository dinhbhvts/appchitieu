-- ============================================================================
-- Manual DB fix for production Postgres (Render) - equivalent to
-- `alembic upgrade head` for revisions b6d4e2a9c1f7 -> c2a5f8e3b1d4 -> d7e4a1c9f6b3.
--
-- Vì sao cần chạy: code backend mới đã đọc/ghi các cột dưới đây, nhưng
-- database production hiện chưa có (chưa chạy `alembic upgrade head`), gây ra
-- đúng 2 lỗi anh đang gặp:
--   1. Màn "Tài sản" báo "Failed to fetch" - vì AssetSnapshot giờ có thêm cột
--      system_key (dùng để ghim 4 mục Tài khoản/Chứng khoán vợ/chồng), mà cột
--      này CHƯA CÓ trên DB production -> mọi truy vấn bảng asset_snapshots lỗi.
--   2. "Hồ sơ đính kèm" không tạo được folder trên Drive - vì NotebookItem giờ
--      có thêm cột profile_name + drive_folder_id, cũng CHƯA CÓ trên DB
--      production -> lưu "Tên hồ sơ" / tạo folder tương ứng không hoạt động
--      được (thậm chí có thể khiến việc lưu mục Thông tin cá nhân bị lỗi).
--
-- AN TOÀN: script này CHỈ THÊM (ADD COLUMN / CREATE INDEX), không DROP,
-- không UPDATE dữ liệu hiện có, không xóa gì cả. Mọi câu lệnh đều có
-- IF NOT EXISTS nên chạy lại nhiều lần cũng không lỗi, không hại.
--
-- CÁCH CHẠY:
--   1. Vào Render Dashboard -> database Postgres của app -> tab "Connect" ->
--      copy "PSQL Command" (hoặc "External Connection String").
--   2. Trên máy anh, mở terminal, dán lệnh psql đó để kết nối vào DB.
--   3. Chạy: \i manual_fix_2026_07_assets_drive_folder.sql
--      (hoặc copy toàn bộ nội dung file này paste thẳng vào psql)
--   4. Nên backup trước (Render có "Backups" tab) dù script chỉ thêm cột.
-- ============================================================================

BEGIN;

-- --- asset_snapshots: đánh dấu 4 mục hệ thống (Tài khoản/Chứng khoán vợ/chồng) --
ALTER TABLE asset_snapshots ADD COLUMN IF NOT EXISTS system_key VARCHAR(30);
CREATE INDEX IF NOT EXISTS ix_asset_snapshots_system_key ON asset_snapshots (system_key);

-- --- notebook_items: "Tên hồ sơ" + id thư mục Drive tương ứng ----------------
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS profile_name    VARCHAR(150);
ALTER TABLE notebook_items ADD COLUMN IF NOT EXISTS drive_folder_id VARCHAR(120);

-- --- Đánh dấu cho Alembic biết là đã áp dụng tới revision này ----------------
-- (để lần sau chạy `alembic upgrade head` bình thường không bị lỗi/lặp lại)
UPDATE alembic_version SET version_num = 'd7e4a1c9f6b3';
INSERT INTO alembic_version (version_num)
SELECT 'd7e4a1c9f6b3'
WHERE NOT EXISTS (SELECT 1 FROM alembic_version);

COMMIT;

-- Kiểm tra nhanh sau khi chạy xong:
-- SELECT version_num FROM alembic_version;              -- phải ra d7e4a1c9f6b3
-- SELECT system_key FROM asset_snapshots LIMIT 1;        -- không lỗi là OK
-- SELECT profile_name, drive_folder_id FROM notebook_items LIMIT 1;  -- không lỗi là OK
