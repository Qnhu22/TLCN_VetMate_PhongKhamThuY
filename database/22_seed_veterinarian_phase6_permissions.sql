-- đã CHẠY: người dùng tự thực thi sau SQL 12 và các quyền giai đoạn trước.
-- Không seed vaccine, không tạo lịch hẹn, không gửi thông báo hoặc ghi kho.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.roles WHERE "roleCode"='VETERINARIAN' AND "isActive") THEN
        RAISE EXCEPTION 'Thiếu role VETERINARIAN hoạt động.';
    END IF;
END $$;
INSERT INTO auth.permissions ("permissionCode", "name", "description", "module", "isActive") VALUES
 ('VACCINATION_RECORD_VIEW','Xem tiêm phòng trong phạm vi chăm sóc','Ca tham gia; lịch sử cần thêm quyền lịch sử chăm sóc.','VETERINARIAN',true),
 ('VACCINATION_RECORD_CREATE','Ghi nhận tiêm phòng','Bác sĩ PRIMARY hoặc được phân công PROCEDURE trong ca đang khám.','VETERINARIAN',true),
 ('FOLLOW_UP_VIEW','Xem đề nghị tái khám','Ca tham gia hoặc lịch sử được phép.','VETERINARIAN',true),
 ('FOLLOW_UP_CREATE','Tạo đề nghị tái khám','Bác sĩ chính, ca chưa chốt; không tự đặt lịch.','VETERINARIAN',true),
 ('FOLLOW_UP_UPDATE','Cập nhật đề nghị tái khám','Bác sĩ chính; ca đã chốt chỉ cập nhật liên kết/trạng thái, không sửa nội dung chuyên môn.','VETERINARIAN',true)
ON CONFLICT ("permissionCode") DO UPDATE SET
 "name"=EXCLUDED."name", "description"=EXCLUDED."description", "module"=EXCLUDED."module";
INSERT INTO auth."rolePermissions" ("roleID","permissionID")
SELECT r."roleID",p."permissionID" FROM auth.roles r CROSS JOIN auth.permissions p
WHERE r."roleCode"='VETERINARIAN' AND r."isActive" AND p."isActive"
AND p."permissionCode" IN ('VACCINATION_RECORD_VIEW','VACCINATION_RECORD_CREATE','FOLLOW_UP_VIEW','FOLLOW_UP_CREATE','FOLLOW_UP_UPDATE')
ON CONFLICT ("roleID","permissionID") DO NOTHING;
COMMIT;
