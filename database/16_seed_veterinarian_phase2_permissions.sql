-- đã chạy
-- Chuẩn bị cho giai đoạn 2, chưa tự thực thi. Cần SQL 10 trước khi dùng các trang.
-- Role toàn hệ thống chỉ cấp khả năng; backend vẫn kiểm tra bác sĩ/phạm vi/trạng thái.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.roles WHERE "roleCode" = 'VETERINARIAN' AND "isActive") THEN
        RAISE EXCEPTION 'Thiếu role VETERINARIAN hoạt động.';
    END IF;
END $$;
INSERT INTO auth.permissions ("permissionCode", "name", "description", "module", "isActive") VALUES
 ('APPOINTMENT_VIEW_ASSIGNED', 'Xem lịch khám được giao', 'Chỉ lịch được phân công hoặc ca được tham gia.', 'VETERINARIAN', true),
 ('QUEUE_VIEW_ASSIGNED', 'Xem danh sách chờ được giao', 'Chỉ lượt đã check-in trong phạm vi bác sĩ.', 'VETERINARIAN', true),
 ('VISIT_START', 'Bắt đầu ca khám được giao', 'Chỉ bác sĩ được phân công chính nhận lượt CHECKED_IN.', 'VETERINARIAN', true),
 ('VISIT_VIEW_ASSIGNED', 'Xem ca khám tham gia', 'Chỉ ca có bác sĩ trong VisitVeterinarian.', 'VETERINARIAN', true)
ON CONFLICT ("permissionCode") DO UPDATE SET
 "name"=EXCLUDED."name", "description"=EXCLUDED."description", "module"=EXCLUDED."module";
INSERT INTO auth."rolePermissions" ("roleID", "permissionID")
SELECT r."roleID", p."permissionID" FROM auth.roles r CROSS JOIN auth.permissions p
WHERE r."roleCode"='VETERINARIAN' AND r."isActive" AND p."isActive"
AND p."permissionCode" IN ('APPOINTMENT_VIEW_ASSIGNED','QUEUE_VIEW_ASSIGNED','VISIT_START','VISIT_VIEW_ASSIGNED')
ON CONFLICT ("roleID","permissionID") DO NOTHING;
COMMIT;
