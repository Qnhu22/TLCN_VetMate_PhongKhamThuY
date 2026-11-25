--đã chạy -- Bước tích hợp, KHÔNG chạy theo số thứ tự nếu module kho chưa sẵn sàng.
-- Điều kiện: 13 và DDL kho đã được nhóm xác nhận:
-- inventory.products với productID là BIGINT PK hoặc UNIQUE.
-- Tên này theo quy ước đề xuất từ tài liệu, chưa được xác minh bằng DDL kho.
-- Nếu nhóm chọn tên khác, cập nhật file này và model tương ứng trước khi áp dụng.
-- Script dừng và rollback nếu thiếu bảng; không bỏ qua FK âm thầm.
BEGIN;
DO $$
BEGIN
    IF to_regclass('inventory.products') IS NULL THEN
        RAISE EXCEPTION 'Thiếu inventory.products. Chốt và triển khai DDL kho trước khi thêm FK đơn thuốc.';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fkPrescriptionItemsProduct'
          AND conrelid = 'medical."prescriptionItems"'::regclass
    ) THEN
        ALTER TABLE medical."prescriptionItems"
            ADD CONSTRAINT "fkPrescriptionItemsProduct"
            FOREIGN KEY ("productID") REFERENCES inventory.products("productID") ON DELETE RESTRICT;
    END IF;
END;
$$;
COMMIT;
