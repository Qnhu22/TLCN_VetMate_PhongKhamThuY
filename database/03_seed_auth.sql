/* =========================================================
   VETMATE - AUTH SEED DATA
   File: database/03_seed_auth.sql

   Yêu cầu:
   - 01_create_schemas.sql đã chạy
   - 02_auth.sql đã chạy
   ========================================================= */


/* =========================================================
   1. ROLES
   ========================================================= */

INSERT INTO auth.roles (
    "roleCode",
    "name",
    "description",
    "isActive"
)
VALUES
(
    'PET_OWNER',
    'Chủ nuôi',
    'Người dùng quản lý thú cưng và sử dụng các dịch vụ của phòng khám.',
    TRUE
),
(
    'VETERINARIAN',
    'Bác sĩ thú y',
    'Bác sĩ thực hiện khám, điều trị và quản lý hồ sơ y tế thú cưng.',
    TRUE
),
(
    'RECEPTIONIST',
    'Lễ tân',
    'Nhân viên tiếp nhận, quản lý lịch hẹn và hỗ trợ khách hàng tại phòng khám.',
    TRUE
),
(
    'CLINIC_MANAGER',
    'Quản lý phòng khám',
    'Quản lý hoạt động nghiệp vụ và vận hành của phòng khám.',
    TRUE
),
(
    'SYSTEM_ADMIN',
    'Quản trị hệ thống',
    'Quản lý tài khoản, vai trò, quyền và cấu hình hệ thống.',
    TRUE
)
ON CONFLICT ("roleCode")
DO UPDATE SET
    "name" = EXCLUDED."name",
    "description" = EXCLUDED."description",
    "isActive" = EXCLUDED."isActive";


/* =========================================================
   2. AUTH PERMISSIONS
   Đây mới là bộ quyền nền ban đầu.
   Các module PET, BOOKING, MEDICAL... sẽ seed sau.
   ========================================================= */

INSERT INTO auth.permissions (
    "permissionCode",
    "name",
    "description",
    "module",
    "isActive"
)
VALUES
(
    'USER_VIEW',
    'Xem tài khoản',
    'Cho phép xem danh sách và thông tin tài khoản người dùng.',
    'AUTH',
    TRUE
),
(
    'USER_CREATE',
    'Tạo tài khoản',
    'Cho phép tạo tài khoản cho nhân viên.',
    'AUTH',
    TRUE
),
(
    'USER_UPDATE',
    'Cập nhật tài khoản',
    'Cho phép cập nhật thông tin tài khoản.',
    'AUTH',
    TRUE
),
(
    'USER_STATUS_UPDATE',
    'Cập nhật trạng thái tài khoản',
    'Cho phép khóa, mở khóa hoặc thay đổi trạng thái tài khoản.',
    'AUTH',
    TRUE
),
(
    'USER_ROLE_ASSIGN',
    'Gán vai trò cho tài khoản',
    'Cho phép gán hoặc thay đổi vai trò của người dùng.',
    'AUTH',
    TRUE
),
(
    'ROLE_VIEW',
    'Xem vai trò',
    'Cho phép xem danh sách vai trò trong hệ thống.',
    'AUTH',
    TRUE
),
(
    'PERMISSION_VIEW',
    'Xem quyền',
    'Cho phép xem danh sách quyền trong hệ thống.',
    'AUTH',
    TRUE
)
ON CONFLICT ("permissionCode")
DO UPDATE SET
    "name" = EXCLUDED."name",
    "description" = EXCLUDED."description",
    "module" = EXCLUDED."module",
    "isActive" = EXCLUDED."isActive";


/* =========================================================
   3. SYSTEM_ADMIN
   Admin nhận toàn bộ permission AUTH hiện tại.
   ========================================================= */

INSERT INTO auth."rolePermissions" (
    "roleID",
    "permissionID"
)
SELECT
    r."roleID",
    p."permissionID"
FROM auth.roles r
CROSS JOIN auth.permissions p
WHERE
    r."roleCode" = 'SYSTEM_ADMIN'
    AND p."module" = 'AUTH'
    AND p."isActive" = TRUE
ON CONFLICT (
    "roleID",
    "permissionID"
)
DO NOTHING;




/* =========================================================
   3. SYSTEM_ADMIN PERMISSIONS
   Chỉ cấp các quyền AUTH đã được xác định rõ.
   Permission mới sẽ được bổ sung khi chức năng tương ứng
   được triển khai.
   ========================================================= */

INSERT INTO auth."rolePermissions" (
    "roleID",
    "permissionID"
)
SELECT
    r."roleID",
    p."permissionID"
FROM auth.roles r
CROSS JOIN auth.permissions p
WHERE
    r."roleCode" = 'SYSTEM_ADMIN'
    AND p."permissionCode" IN (
        'USER_VIEW',
        'USER_CREATE',
        'USER_UPDATE',
        'USER_STATUS_UPDATE',
        'USER_ROLE_ASSIGN',
        'ROLE_VIEW',
        'PERMISSION_VIEW'
    )
    AND p."isActive" = TRUE
ON CONFLICT (
    "roleID",
    "permissionID"
)
DO NOTHING;