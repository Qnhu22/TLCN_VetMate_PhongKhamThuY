-- đã chạy
-- Giai đoạn 4. Chạy sau SQL 11 và các seed quyền bác sĩ trước đó.
-- Chỉ chuẩn bị file, không tự thực thi. Không cấp quyền cho admin/lễ tân.
BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth.roles WHERE "roleCode"='VETERINARIAN' AND "isActive") THEN
        RAISE EXCEPTION 'Thiếu role VETERINARIAN hoạt động.';
    END IF;
END $$;
INSERT INTO auth.permissions ("permissionCode", "name", "description", "module", "isActive") VALUES
 ('DIAGNOSTIC_ORDER_VIEW','Xem chỉ định trong phạm vi chăm sóc','Tham gia ca hoặc lịch sử pet được phép.','VETERINARIAN',true),
 ('DIAGNOSTIC_ORDER_CREATE','Tạo chỉ định dịch vụ','Chỉ bác sĩ chính của ca đang khám.','VETERINARIAN',true),
 ('DIAGNOSTIC_ORDER_CANCEL','Hủy chỉ định chưa hoàn tất','Chỉ bác sĩ chính, có lý do hủy.','VETERINARIAN',true),
 ('DIAGNOSTIC_RESULT_UPDATE','Nhập kết quả được giao','Chỉ người thực hiện được phân công trên ca tham gia.','VETERINARIAN',true)
ON CONFLICT ("permissionCode") DO UPDATE SET
 "name"=EXCLUDED."name", "description"=EXCLUDED."description", "module"=EXCLUDED."module";
INSERT INTO auth."rolePermissions" ("roleID","permissionID")
SELECT r."roleID",p."permissionID" FROM auth.roles r CROSS JOIN auth.permissions p
WHERE r."roleCode"='VETERINARIAN' AND r."isActive" AND p."isActive"
AND p."permissionCode" IN ('DIAGNOSTIC_ORDER_VIEW','DIAGNOSTIC_ORDER_CREATE','DIAGNOSTIC_ORDER_CANCEL','DIAGNOSTIC_RESULT_UPDATE')
ON CONFLICT ("roleID","permissionID") DO NOTHING;
COMMIT;
