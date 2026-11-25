-- đã chạy
-- Giai đoạn 3: chạy sau 02/03, SQL 10 và seed 16.
-- Chỉ chuẩn bị file. Không mở quyền sửa sau hoàn tất hoặc quyền chuyên môn cho admin/lễ tân.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.roles WHERE "roleCode"='VETERINARIAN' AND "isActive") THEN
        RAISE EXCEPTION 'Thiếu role VETERINARIAN hoạt động.';
    END IF;
END $$;
INSERT INTO auth.permissions ("permissionCode", "name", "description", "module", "isActive") VALUES
 ('VISIT_UPDATE_ASSIGNED', 'Cập nhật bệnh án được giao', 'Chỉ bác sĩ PRIMARY sửa ca DRAFT đang IN_PROGRESS.', 'VETERINARIAN', true),
 ('VISIT_COMPLETE', 'Hoàn tất ca khám được giao', 'Chỉ PRIMARY chốt ca; phải có cả quyền cập nhật bệnh án.', 'VETERINARIAN', true),
 ('PET_HISTORY_VIEW_FOR_CARE', 'Xem lịch sử thú cưng để khám', 'Chỉ qua ca đang tham gia; ca cũ hoàn tất hoặc ca mình tham gia.', 'VETERINARIAN', true)
ON CONFLICT ("permissionCode") DO UPDATE SET
 "name"=EXCLUDED."name", "description"=EXCLUDED."description", "module"=EXCLUDED."module";
INSERT INTO auth."rolePermissions" ("roleID", "permissionID")
SELECT r."roleID", p."permissionID" FROM auth.roles r CROSS JOIN auth.permissions p
WHERE r."roleCode"='VETERINARIAN' AND r."isActive" AND p."isActive"
AND p."permissionCode" IN ('VISIT_UPDATE_ASSIGNED','VISIT_COMPLETE','PET_HISTORY_VIEW_FOR_CARE')
ON CONFLICT ("roleID","permissionID") DO NOTHING;
COMMIT;
