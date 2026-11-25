--đã chạy
-- Giai đoạn 1. Chạy sau 02, 03 và 07; không phụ thuộc 10–14.
-- Chỉ chuẩn bị file, không được tự coi là đã chạy. Không cấp quyền chuyên môn cho admin/lễ tân.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.roles WHERE "roleCode" = 'VETERINARIAN' AND "isActive") THEN
        RAISE EXCEPTION 'Thiếu role VETERINARIAN hoạt động. Kiểm tra seed 03 trước.';
    END IF;
END $$;
INSERT INTO auth.permissions ("permissionCode", "name", "description", "module", "isActive") VALUES
 ('VET_DASHBOARD_VIEW', 'Xem tổng quan bác sĩ', 'Thống kê lịch khám được giao cho bản thân.', 'VETERINARIAN', true),
 ('VET_SCHEDULE_VIEW_SELF', 'Xem lịch làm việc cá nhân', 'Chỉ lịch phân công của bác sĩ hiện tại.', 'VETERINARIAN', true),
 ('VET_LEAVE_VIEW_SELF', 'Xem yêu cầu nghỉ cá nhân', 'Chỉ yêu cầu nghỉ của bản thân.', 'VETERINARIAN', true),
 ('VET_LEAVE_CREATE_SELF', 'Gửi yêu cầu nghỉ cá nhân', 'Gửi yêu cầu chờ quản lý duyệt.', 'VETERINARIAN', true),
 ('VET_LEAVE_CANCEL_SELF', 'Hủy yêu cầu nghỉ cá nhân', 'Chỉ hủy yêu cầu của mình còn PENDING.', 'VETERINARIAN', true)
ON CONFLICT ("permissionCode") DO UPDATE SET
 "name" = EXCLUDED."name", "description" = EXCLUDED."description", "module" = EXCLUDED."module";
-- Không tự bật lại quyền đã bị quản trị vô hiệu hóa khi chạy lại seed.
INSERT INTO auth."rolePermissions" ("roleID", "permissionID")
SELECT r."roleID", p."permissionID" FROM auth.roles r CROSS JOIN auth.permissions p
WHERE r."roleCode" = 'VETERINARIAN' AND r."isActive" AND p."isActive"
AND p."permissionCode" IN ('VET_DASHBOARD_VIEW', 'VET_SCHEDULE_VIEW_SELF',
 'VET_LEAVE_VIEW_SELF', 'VET_LEAVE_CREATE_SELF', 'VET_LEAVE_CANCEL_SELF')
ON CONFLICT ("roleID", "permissionID") DO NOTHING;
COMMIT;
