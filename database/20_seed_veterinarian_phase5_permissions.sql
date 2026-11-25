-- đã CHẠY: người dùng tự thực thi sau SQL 13, DDL kho và SQL 14.
-- Không tạo bảng kho, không cấp quyền cho role khác, không bật sửa/hủy đã cấp phát.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.roles WHERE "roleCode"='VETERINARIAN' AND "isActive") THEN
        RAISE EXCEPTION 'Thiếu role VETERINARIAN hoạt động.';
    END IF;
END $$;
INSERT INTO auth.permissions ("permissionCode", "name", "description", "module", "isActive") VALUES
 ('PRESCRIPTION_VIEW','Xem đơn thuốc trong phạm vi chăm sóc','Ca tham gia hoặc bệnh án lịch sử được phép.','VETERINARIAN',true),
 ('PRESCRIPTION_CREATE','Kê đơn thuốc','Bác sĩ chính của ca đang khám, thuốc có hồ sơ hợp lệ.','VETERINARIAN',true),
 ('PRESCRIPTION_UPDATE','Sửa đơn thuốc chưa cấp phát','Bác sĩ kê đơn, đang là bác sĩ chính, ca chưa chốt; kiểm tra cấp phát.','VETERINARIAN',true),
 ('PRESCRIPTION_CANCEL','Hủy đơn thuốc chưa cấp phát','Bác sĩ kê đơn, ca chưa chốt, có lý do; kiểm tra cấp phát.','VETERINARIAN',true)
ON CONFLICT ("permissionCode") DO UPDATE SET
 "name"=EXCLUDED."name", "description"=EXCLUDED."description", "module"=EXCLUDED."module";
INSERT INTO auth."rolePermissions" ("roleID","permissionID")
SELECT r."roleID",p."permissionID" FROM auth.roles r CROSS JOIN auth.permissions p
WHERE r."roleCode"='VETERINARIAN' AND r."isActive" AND p."isActive"
AND p."permissionCode" IN ('PRESCRIPTION_VIEW','PRESCRIPTION_CREATE','PRESCRIPTION_UPDATE','PRESCRIPTION_CANCEL')
ON CONFLICT ("roleID","permissionID") DO NOTHING;
COMMIT;
