from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash,generate_password_hash

from app.admin import admin_bp
from app.auth.decorators import (
    permission_required,
    role_required,
)
from app.extensions import db
from app.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
    abort,
)

from flask_login import (
    current_user,
    login_required,
)

ALLOWED_AVATAR_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}

def delete_old_uploaded_avatar(
    avatar_path
):
    if not avatar_path:
        return

    prefix = "uploads/avatars/"

    if not avatar_path.startswith(prefix):
        return

    relative_name = avatar_path[
        len(prefix):
    ]

    old_file = (
        Path(current_app.static_folder)
        / "uploads"
        / "avatars"
        / relative_name
    )

    try:
        if old_file.exists():
            old_file.unlink()
    except OSError:
        pass

def allowed_avatar_file(filename):
    return (
        "."
        in filename
        and filename
        .rsplit(".", 1)[1]
        .lower()
        in ALLOWED_AVATAR_EXTENSIONS
    )

MAX_AVATAR_SIZE = 5 * 1024 * 1024

ALLOWED_AVATAR_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}


def validate_avatar_image(file):
    if not file or not file.filename:
        return False, "Vui lòng chọn ảnh đại diện."

    # -----------------------------------------
    # Kiểm tra phần mở rộng
    # -----------------------------------------

    if not allowed_avatar_file(
        file.filename
    ):
        return (
            False,
            (
                "Chỉ hỗ trợ ảnh JPG, JPEG, "
                "PNG hoặc WEBP."
            ),
        )

    # -----------------------------------------
    # Kiểm tra dung lượng thật
    # -----------------------------------------

    file.stream.seek(
        0,
        2,
    )

    file_size = file.stream.tell()

    file.stream.seek(0)

    if file_size > MAX_AVATAR_SIZE:
        return (
            False,
            "Ảnh đại diện không được vượt quá 5 MB.",
        )

    if file_size == 0:
        return (
            False,
            "Tệp ảnh không hợp lệ.",
        )

    # -----------------------------------------
    # Kiểm tra nội dung thực sự là ảnh
    # -----------------------------------------

    try:
        image = Image.open(
            file.stream
        )

        image.verify()

        image_format = image.format

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        file.stream.seek(0)

        return (
            False,
            "Tệp được chọn không phải ảnh hợp lệ.",
        )

    file.stream.seek(0)

    # -----------------------------------------
    # Chỉ cho phép JPEG / PNG / WEBP
    # -----------------------------------------

    if image_format not in ALLOWED_AVATAR_FORMATS:
        return (
            False,
            (
                "Chỉ hỗ trợ ảnh JPG, JPEG, "
                "PNG hoặc WEBP."
            ),
        )

    return True, image_format

def process_avatar_image(
    source_path,
    image_format,
):
    max_size = (1024, 1024)

    with Image.open(source_path) as image:
        image.thumbnail(
            max_size,
            Image.Resampling.LANCZOS,
        )

        if image_format == "JPEG":
            if image.mode not in (
                "RGB",
                "L",
            ):
                image = image.convert("RGB")

            image.save(
                source_path,
                format="JPEG",
                quality=90,
                optimize=True,
            )

        elif image_format == "PNG":
            image.save(
                source_path,
                format="PNG",
                optimize=True,
            )

        elif image_format == "WEBP":
            image.save(
                source_path,
                format="WEBP",
                quality=90,
                method=6,
            )

def get_admin_sidebar_stats():
    return {
        "total_users": User.query.count(),
    }

def get_safe_per_page(
    default=12,
    allowed=(12, 24, 48),
):
    per_page = request.args.get(
        "per_page",
        default,
        type=int,
    )

    if per_page not in allowed:
        return default

    return per_page

@admin_bp.get("/")
@role_required("SYSTEM_ADMIN")
def dashboard():
    now = datetime.now(timezone.utc)

    total_users = User.query.count()

    active_users = User.query.filter_by(
        status="ACTIVE"
    ).count()

    locked_users = User.query.filter_by(
        status="LOCKED"
    ).count()

    pending_users = User.query.filter_by(
        status="PENDING_VERIFICATION"
    ).count()

    staff_role_codes = [
        "SYSTEM_ADMIN",
        "CLINIC_MANAGER",
        "VETERINARIAN",
        "RECEPTIONIST",
    ]

    staff_users = (
        User.query
        .join(
            UserRole,
            User.userID == UserRole.userID,
        )
        .join(
            Role,
            Role.roleID == UserRole.roleID,
        )
        .filter(
            Role.roleCode.in_(
                staff_role_codes
            )
        )
        .distinct()
        .count()
    )

    # =====================================================
    # USER CREATED IN LAST 7 DAYS
    # =====================================================

    seven_days_ago = (
        now - timedelta(days=7)
    )

    new_users = (
        User.query
        .filter(
            User.createdAt >= seven_days_ago
        )
        .count()
    )

    # =====================================================
    # ROLE DISTRIBUTION
    # =====================================================

    role_rows = (
        db.session.query(
            Role.roleCode,
            Role.name,
            func.count(
                UserRole.userID
            ).label("total"),
        )
        .outerjoin(
            UserRole,
            Role.roleID
            == UserRole.roleID,
        )
        .filter(
            Role.isActive.is_(True)
        )
        .group_by(
            Role.roleID,
            Role.roleCode,
            Role.name,
        )
        .order_by(
            Role.roleID
        )
        .all()
    )

    role_stats = [
        {
            "roleCode": row.roleCode,
            "name": row.name,
            "total": row.total,
        }
        for row in role_rows
    ]

    # =====================================================
    # ACCOUNT ACTIVITY CHART
    # Last 90 days so frontend can switch 7/30/90
    # =====================================================

    chart_start_date = (
        now.date()
        - timedelta(days=89)
    )

    chart_rows = (
        db.session.query(
            func.date(
                User.createdAt
            ).label("date"),
            func.count(
                User.userID
            ).label("total"),
        )
        .filter(
            User.createdAt
            >= datetime.combine(
                chart_start_date,
                datetime.min.time(),
                tzinfo=timezone.utc,
            )
        )
        .group_by(
            func.date(
                User.createdAt
            )
        )
        .order_by(
            func.date(
                User.createdAt
            )
        )
        .all()
    )

    chart_count_map = {
        row.date: row.total
        for row in chart_rows
    }

    account_chart = []

    for day_offset in range(90):
        current_date = (
            chart_start_date
            + timedelta(
                days=day_offset
            )
        )

        account_chart.append(
            {
                "date": current_date.isoformat(),
                "label": current_date.strftime(
                    "%d/%m"
                ),
                "total": chart_count_map.get(
                    current_date,
                    0,
                ),
            }
        )

    dashboard_stats = {
        "total_users": total_users,
        "active_users": active_users,
        "staff_users": staff_users,
        "locked_users": locked_users,
        "pending_users": pending_users,
        "new_users": new_users,
    }
    
    sidebar_stats = get_admin_sidebar_stats()

    return render_template(
        "admin/dashboard.html",
        dashboard_stats=dashboard_stats,
        role_stats=role_stats,
        account_chart=account_chart,
        sidebar_stats=sidebar_stats,
    )
    
@admin_bp.get("/users")
@permission_required("USER_VIEW")
def users():
    search = request.args.get(
        "q",
        "",
    ).strip()

    status = request.args.get(
        "status",
        "",
    ).strip()

    role_code = request.args.get(
        "role",
        "",
    ).strip()

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    per_page = 12


    query = User.query


    if search:
        keyword = f"%{search}%"

        query = query.filter(
            or_(
                User.fullName.ilike(keyword),
                User.email.ilike(keyword),
                User.phone.ilike(keyword),
            )
        )


    if status:
        query = query.filter(
            User.status == status
        )


    if role_code:
        query = (
            query
            .join(
                UserRole,
                User.userID
                == UserRole.userID,
            )
            .join(
                Role,
                Role.roleID
                == UserRole.roleID,
            )
            .filter(
                Role.roleCode
                == role_code
            )
            .distinct()
        )


    query = query.order_by(
        User.createdAt.desc()
    )


    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )


    users = pagination.items


    roles = (
        Role.query
        .filter_by(
            isActive=True
        )
        .order_by(
            Role.roleID
        )
        .all()
    )


    status_options = [
        "ACTIVE",
        "PENDING_VERIFICATION",
        "LOCKED",
        "INACTIVE",
    ]

    sidebar_stats = get_admin_sidebar_stats()

    return render_template(
        "admin/users/index.html",
        users=users,
        pagination=pagination,
        roles=roles,
        status_options=status_options,
        search=search,
        selected_status=status,
        selected_role=role_code,
        sidebar_stats=sidebar_stats,
    )
    
@admin_bp.get("/roles")
@permission_required("ROLE_VIEW")
def roles():
    search = request.args.get(
        "q",
        "",
    ).strip()

    status = request.args.get(
        "status",
        "",
    ).strip().upper()

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    per_page = get_safe_per_page()

    # =====================================================
    # BASE QUERY
    # =====================================================

    query = (
        db.session.query(
            Role,
            func.count(
                func.distinct(
                    UserRole.userID
                )
            ).label("user_count"),
            func.count(
                func.distinct(
                    RolePermission.permissionID
                )
            ).label("permission_count"),
        )
        .outerjoin(
            UserRole,
            Role.roleID
            == UserRole.roleID,
        )
        .outerjoin(
            RolePermission,
            Role.roleID
            == RolePermission.roleID,
        )
    )

    # =====================================================
    # SEARCH
    # =====================================================

    if search:
        keyword = f"%{search}%"

        query = query.filter(
            or_(
                Role.name.ilike(keyword),
                Role.roleCode.ilike(keyword),
                Role.description.ilike(keyword),
            )
        )

    # =====================================================
    # STATUS
    # =====================================================

    if status == "ACTIVE":
        query = query.filter(
            Role.isActive.is_(True)
        )

    elif status == "INACTIVE":
        query = query.filter(
            Role.isActive.is_(False)
        )

    # =====================================================
    # GROUP / SORT
    # =====================================================

    query = (
        query
        .group_by(
            Role.roleID,
        )
        .order_by(
            Role.isActive.desc(),
            Role.name.asc(),
        )
    )

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    role_rows = [
        {
            "role": row[0],
            "user_count": row[1],
            "permission_count": row[2],
        }
        for row in pagination.items
    ]

    # =====================================================
    # SUMMARY
    # =====================================================

    total_roles = Role.query.count()

    active_roles = (
        Role.query
        .filter(
            Role.isActive.is_(True)
        )
        .count()
    )

    inactive_roles = (
        Role.query
        .filter(
            Role.isActive.is_(False)
        )
        .count()
    )

    total_assignments = (
        db.session.query(
            UserRole
        )
        .count()
    )

    role_summary = {
        "total": total_roles,
        "active": active_roles,
        "inactive": inactive_roles,
        "assignments": total_assignments,
    }

    sidebar_stats = (
        get_admin_sidebar_stats()
    )

    return render_template(
        "admin/access/roles.html",
        role_rows=role_rows,
        pagination=pagination,
        role_summary=role_summary,
        search=search,
        selected_status=status,
        per_page=per_page,
        sidebar_stats=sidebar_stats,
    )
    
@admin_bp.get("/roles/<int:role_id>")
@permission_required("ROLE_VIEW")
def role_detail(role_id):
    role = Role.query.get_or_404(
        role_id
    )

    # =====================================================
    # PERMISSIONS OF THIS ROLE
    # =====================================================

    permissions = (
        Permission.query
        .join(
            RolePermission,
            Permission.permissionID
            == RolePermission.permissionID,
        )
        .filter(
            RolePermission.roleID
            == role.roleID
        )
        .order_by(
            Permission.module.asc(),
            Permission.permissionCode.asc(),
        )
        .all()
    )

    permission_groups = {}

    for permission in permissions:
        module_name = (
            permission.module
            or "OTHER"
        )

        permission_groups.setdefault(
            module_name,
            [],
        ).append(permission)

    # =====================================================
    # USER COUNT
    # =====================================================

    user_count = (
        db.session.query(
            func.count(
                func.distinct(
                    UserRole.userID
                )
            )
        )
        .filter(
            UserRole.roleID
            == role.roleID
        )
        .scalar()
        or 0
    )

    # =====================================================
    # ACTIVE USER COUNT
    # =====================================================

    active_user_count = (
        db.session.query(
            func.count(
                func.distinct(
                    User.userID
                )
            )
        )
        .join(
            UserRole,
            User.userID
            == UserRole.userID,
        )
        .filter(
            UserRole.roleID
            == role.roleID,
            User.status == "ACTIVE",
        )
        .scalar()
        or 0
    )

    # =====================================================
    # RECENT USERS
    # =====================================================

    recent_users = (
        User.query
        .join(
            UserRole,
            User.userID
            == UserRole.userID,
        )
        .filter(
            UserRole.roleID
            == role.roleID
        )
        .order_by(
            UserRole.assignedAt.desc()
        )
        .limit(6)
        .all()
    )

    role_summary = {
        "user_count": user_count,
        "active_user_count": (
            active_user_count
        ),
        "permission_count": len(
            permissions
        ),
        "module_count": len(
            permission_groups
        ),
    }

    sidebar_stats = (
        get_admin_sidebar_stats()
    )

    return render_template(
        "admin/access/role-detail.html",
        role=role,
        permission_groups=permission_groups,
        recent_users=recent_users,
        role_summary=role_summary,
        sidebar_stats=sidebar_stats,
    )

@admin_bp.get("/permissions")
@permission_required("PERMISSION_VIEW")
def permissions():
    search = request.args.get(
        "q",
        "",
    ).strip()

    module = request.args.get(
        "module",
        "",
    ).strip().upper()

    status = request.args.get(
        "status",
        "",
    ).strip().upper()

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    per_page = get_safe_per_page()

    # =====================================================
    # BASE QUERY
    # =====================================================

    query = (
        db.session.query(
            Permission,
            func.count(
                func.distinct(
                    RolePermission.roleID
                )
            ).label("role_count"),
        )
        .outerjoin(
            RolePermission,
            Permission.permissionID
            == RolePermission.permissionID,
        )
    )

    # =====================================================
    # SEARCH
    # =====================================================

    if search:
        keyword = f"%{search}%"

        query = query.filter(
            or_(
                Permission.permissionCode.ilike(
                    keyword
                ),
                Permission.name.ilike(
                    keyword
                ),
                Permission.description.ilike(
                    keyword
                ),
                Permission.module.ilike(
                    keyword
                ),
            )
        )

    # =====================================================
    # MODULE FILTER
    # =====================================================

    if module:
        query = query.filter(
            Permission.module == module
        )

    # =====================================================
    # STATUS FILTER
    # =====================================================

    if status == "ACTIVE":
        query = query.filter(
            Permission.isActive.is_(True)
        )

    elif status == "INACTIVE":
        query = query.filter(
            Permission.isActive.is_(False)
        )

    # =====================================================
    # GROUP / SORT
    # =====================================================

    query = (
        query
        .group_by(
            Permission.permissionID,
        )
        .order_by(
            Permission.module.asc(),
            Permission.permissionCode.asc(),
        )
    )

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    permission_rows = [
        {
            "permission": row[0],
            "role_count": row[1],
        }
        for row in pagination.items
    ]

    # =====================================================
    # MODULE OPTIONS
    # =====================================================

    module_rows = (
        db.session.query(
            Permission.module
        )
        .filter(
            Permission.module.isnot(None),
            Permission.module != "",
        )
        .distinct()
        .order_by(
            Permission.module.asc()
        )
        .all()
    )

    modules = [
        row[0]
        for row in module_rows
    ]

    # =====================================================
    # SUMMARY
    # =====================================================

    total_permissions = (
        Permission.query.count()
    )

    active_permissions = (
        Permission.query
        .filter(
            Permission.isActive.is_(True)
        )
        .count()
    )

    inactive_permissions = (
        Permission.query
        .filter(
            Permission.isActive.is_(False)
        )
        .count()
    )

    total_modules = len(modules)

    permission_summary = {
        "total": total_permissions,
        "active": active_permissions,
        "inactive": inactive_permissions,
        "modules": total_modules,
    }

    sidebar_stats = (
        get_admin_sidebar_stats()
    )

    return render_template(
        "admin/access/permissions.html",
        permission_rows=permission_rows,
        pagination=pagination,
        permission_summary=permission_summary,
        modules=modules,
        search=search,
        selected_module=module,
        selected_status=status,
        per_page=per_page,
        sidebar_stats=sidebar_stats,
    )
    
@admin_bp.get(
    "/permissions/<int:permission_id>"
)
@permission_required("PERMISSION_VIEW")
def permission_detail(permission_id):
    permission = (
        Permission.query.get_or_404(
            permission_id
        )
    )

    # =====================================================
    # ROLES USING THIS PERMISSION
    # =====================================================

    assigned_roles = (
        Role.query
        .join(
            RolePermission,
            Role.roleID
            == RolePermission.roleID,
        )
        .filter(
            RolePermission.permissionID
            == permission.permissionID
        )
        .order_by(
            Role.isActive.desc(),
            Role.name.asc(),
        )
        .all()
    )

    # =====================================================
    # USER IMPACT
    # Distinct users who inherit this permission
    # through at least one assigned role.
    # =====================================================

    affected_user_count = (
        db.session.query(
            func.count(
                func.distinct(
                    UserRole.userID
                )
            )
        )
        .join(
            RolePermission,
            UserRole.roleID
            == RolePermission.roleID,
        )
        .filter(
            RolePermission.permissionID
            == permission.permissionID
        )
        .scalar()
        or 0
    )

    # =====================================================
    # ACTIVE ROLE COUNT
    # =====================================================

    active_role_count = sum(
        1
        for role in assigned_roles
        if role.isActive
    )

    permission_summary = {
        "role_count": len(
            assigned_roles
        ),
        "active_role_count": (
            active_role_count
        ),
        "affected_user_count": (
            affected_user_count
        ),
    }

    sidebar_stats = (
        get_admin_sidebar_stats()
    )

    return render_template(
        "admin/access/permission-detail.html",
        permission=permission,
        assigned_roles=assigned_roles,
        permission_summary=permission_summary,
        sidebar_stats=sidebar_stats,
    )

@admin_bp.route(
    "/users/create",
    methods=["GET", "POST"],
)
@permission_required("USER_CREATE")
def create_user():
    allowed_role_codes = [
        "VETERINARIAN",
        "RECEPTIONIST",
        "CLINIC_MANAGER",
    ]

    roles = (
        Role.query
        .filter(
            Role.roleCode.in_(
                allowed_role_codes
            ),
            Role.isActive.is_(True),
        )
        .order_by(
            Role.roleID
        )
        .all()
    )

    form_data = {
        "fullName": "",
        "email": "",
        "phone": "",
        "roleCode": "",
        "status": "ACTIVE",
    }

    errors = {}

    if request.method == "POST":
        full_name = request.form.get(
            "fullName",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip().lower()

        phone = request.form.get(
            "phone",
            "",
        ).strip()

        role_code = request.form.get(
            "roleCode",
            "",
        ).strip().upper()

        password = request.form.get(
            "password",
            "",
        )

        confirm_password = request.form.get(
            "confirmPassword",
            "",
        )

        status = request.form.get(
            "status",
            "ACTIVE",
        ).strip().upper()

        form_data = {
            "fullName": full_name,
            "email": email,
            "phone": phone,
            "roleCode": role_code,
            "status": status,
        }

        # =================================================
        # VALIDATION
        # =================================================

        if not full_name:
            errors["fullName"] = (
                "Vui lòng nhập họ tên nhân viên."
            )
        elif len(full_name) > 150:
            errors["fullName"] = (
                "Họ tên không được vượt quá 150 ký tự."
            )

        if not email:
            errors["email"] = (
                "Vui lòng nhập email."
            )
        elif "@" not in email or "." not in email:
            errors["email"] = (
                "Email không đúng định dạng."
            )
        elif len(email) > 255:
            errors["email"] = (
                "Email không được vượt quá 255 ký tự."
            )
        elif User.query.filter_by(
            email=email
        ).first():
            errors["email"] = (
                "Email này đã được sử dụng."
            )

        if phone:
            if (
                not phone.isdigit()
                or len(phone) != 10
            ):
                errors["phone"] = (
                    "Số điện thoại phải gồm đúng 10 chữ số."
                )

        if role_code not in allowed_role_codes:
            errors["roleCode"] = (
                "Vui lòng chọn vai trò nhân viên hợp lệ."
            )

        if not password:
            errors["password"] = (
                "Vui lòng nhập mật khẩu tạm thời."
            )
        elif len(password) < 8:
            errors["password"] = (
                "Mật khẩu phải có ít nhất 8 ký tự."
            )

        if not confirm_password:
            errors["confirmPassword"] = (
                "Vui lòng nhập lại mật khẩu."
            )
        elif password != confirm_password:
            errors["confirmPassword"] = (
                "Mật khẩu xác nhận không khớp."
            )

        allowed_statuses = [
            "ACTIVE",
            "INACTIVE",
        ]

        if status not in allowed_statuses:
            errors["status"] = (
                "Trạng thái tài khoản không hợp lệ."
            )

        role = (
            Role.query
            .filter_by(
                roleCode=role_code,
                isActive=True,
            )
            .first()
        )

        if (
            role_code in allowed_role_codes
            and role is None
        ):
            errors["roleCode"] = (
                "Vai trò đã chọn hiện không khả dụng."
            )

        # =================================================
        # CREATE USER
        # =================================================

        if not errors:
            try:
                user = User(
                    email=email,
                    passwordHash=generate_password_hash(
                        password
                    ),
                    fullName=full_name,
                    phone=phone or None,
                    status=status,
                )

                db.session.add(user)
                db.session.flush()

                user_role = UserRole(
                    userID=user.userID,
                    roleID=role.roleID,
                )

                db.session.add(
                    user_role
                )

                db.session.commit()

                flash(
                    (
                        f"Đã tạo tài khoản "
                        f"{full_name} thành công."
                    ),
                    "success",
                )

                return redirect(
                    url_for(
                        "admin.users"
                    )
                )

            except IntegrityError:
                db.session.rollback()

                errors["email"] = (
                    "Email này đã tồn tại trong hệ thống."
                )

            except Exception:
                db.session.rollback()

                flash(
                    (
                        "Không thể tạo tài khoản lúc này. "
                        "Vui lòng thử lại."
                    ),
                    "error",
                )

    sidebar_stats = (
        get_admin_sidebar_stats()
    )

    return render_template(
        "admin/users/create.html",
        roles=roles,
        form_data=form_data,
        errors=errors,
        sidebar_stats=sidebar_stats,
    )
    
@admin_bp.route(
    "/users/<int:user_id>",
    methods=["GET", "POST"],
)
@login_required
def user_detail(user_id):
    if request.method == "GET":
        if not current_user.has_permission(
            "USER_VIEW"
        ):
            abort(403)

    elif request.method == "POST":
        if not current_user.has_permission(
            "USER_UPDATE"
        ):
            abort(403)

    user = User.query.get_or_404(user_id)

    sidebar_stats = get_admin_sidebar_stats()
    
    available_roles = (
            Role.query
            .filter_by(isActive=True)
            .order_by(Role.name.asc())
            .all()
        )

    if request.method == "POST":
        full_name = request.form.get(
            "fullName",
            "",
        ).strip()

        phone = request.form.get(
            "phone",
            "",
        ).strip()

        errors = {}

        # =========================
        # Full name validation
        # =========================

        if not full_name:
            errors["fullName"] = (
                "Họ và tên không được để trống."
            )

        elif len(full_name) < 2:
            errors["fullName"] = (
                "Họ và tên phải có ít nhất 2 ký tự."
            )

        elif len(full_name) > 150:
            errors["fullName"] = (
                "Họ và tên không được vượt quá 150 ký tự."
            )

        # =========================
        # Phone validation
        # =========================

        if phone:
            if (
                not phone.isdigit()
                or len(phone) != 10
            ):
                errors["phone"] = (
                    "Số điện thoại phải gồm đúng 10 chữ số."
                )

        if errors:
            return render_template(
                "admin/users/detail.html",
                user=user,
                sidebar_stats=sidebar_stats,
                available_roles=available_roles,
                errors=errors,
                form_data={
                    "fullName": full_name,
                    "phone": phone,
                },
                edit_mode=True,
                password_modal_open=False,
                password_errors={},
            )

        try:
            user.fullName = full_name
            user.phone = phone or None

            db.session.commit()

            flash(
                "Đã cập nhật thông tin tài khoản.",
                "success",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        except Exception:
            db.session.rollback()

            flash(
                (
                    "Không thể cập nhật tài khoản lúc này. "
                    "Vui lòng thử lại."
                ),
                "error",
            )

    return render_template(
        "admin/users/detail.html",
        user=user,
        sidebar_stats=sidebar_stats,
        errors={},
        form_data={
            "fullName": user.fullName,
            "phone": user.phone or "",
        },
        edit_mode=False,
        available_roles=available_roles,
        password_modal_open=False,
        password_errors={},
    )
    
@admin_bp.post(
    "/users/<int:user_id>/roles"
)

@permission_required("USER_ROLE_ASSIGN")
def update_user_roles(user_id):
    user = User.query.get_or_404(user_id)

    action = request.form.get(
        "action",
        "",
    ).strip()

    role_code = request.form.get(
        "roleCode",
        "",
    ).strip()

    role = Role.query.filter_by(
        roleCode=role_code,
        isActive=True,
    ).first()

    if not role:
        flash(
            "Vai trò không hợp lệ hoặc không còn hoạt động.",
            "error",
        )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    current_role_codes = {
        item.roleCode
        for item in user.roles
    }

    staff_role_codes = {
        "RECEPTIONIST",
        "CLINIC_MANAGER",
        "VETERINARIAN",
    }

    # =========================================
    # ADD ROLE
    # =========================================

    if action == "add":

        if role_code in current_role_codes:
            flash(
                "Tài khoản đã có vai trò này.",
                "warning",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        # PET_OWNER không chuyển thẳng sang staff
        if (
            "PET_OWNER"
            in current_role_codes
            and role_code in staff_role_codes
        ):
            flash(
                (
                    "Tài khoản chủ nuôi không thể "
                    "chuyển trực tiếp thành tài khoản nhân viên."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        # Không cấp SYSTEM_ADMIN qua flow thường
        if role_code == "SYSTEM_ADMIN":
            flash(
                (
                    "Vai trò Quản trị hệ thống "
                    "không thể cấp từ thao tác này."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        # Bác sĩ cần hồ sơ Veterinarian
        if role_code == "VETERINARIAN":
            flash(
                (
                    "Vai trò Bác sĩ thú y yêu cầu "
                    "hồ sơ bác sĩ tương ứng. "
                    "Chức năng này sẽ được xử lý "
                    "trong luồng quản lý nhân viên."
                ),
                "warning",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        try:
            user.roles.append(role)

            db.session.commit()

            flash(
                f"Đã thêm vai trò {role.name}.",
                "success",
            )

        except Exception:
            db.session.rollback()

            flash(
                "Không thể thêm vai trò lúc này.",
                "error",
            )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    # =========================================
    # REMOVE ROLE
    # =========================================

    if action == "remove":

        if role_code not in current_role_codes:
            flash(
                "Tài khoản không có vai trò này.",
                "warning",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        # Không cho mất role cuối
        if len(user.roles) <= 1:
            flash(
                "Tài khoản phải có ít nhất một vai trò.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        # Admin không tự gỡ SYSTEM_ADMIN
        if (
            user.userID
            == current_user.userID
            and role_code == "SYSTEM_ADMIN"
        ):
            flash(
                (
                    "Bạn không thể tự gỡ vai trò "
                    "Quản trị hệ thống khỏi tài khoản đang đăng nhập."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        try:
            user.roles.remove(role)

            db.session.commit()

            flash(
                f"Đã gỡ vai trò {role.name}.",
                "success",
            )

        except Exception:
            db.session.rollback()

            flash(
                "Không thể gỡ vai trò lúc này.",
                "error",
            )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    flash(
        "Thao tác vai trò không hợp lệ.",
        "error",
    )

    return redirect(
        url_for(
            "admin.user_detail",
            user_id=user.userID,
        )
    )
    
@admin_bp.post(
    "/users/<int:user_id>/status"
)

@permission_required("USER_STATUS_UPDATE")
def update_user_status(user_id):
    user = User.query.get_or_404(user_id)

    new_status = request.form.get(
        "status",
        "",
    ).strip()

    allowed_statuses = {
        "ACTIVE",
        "LOCKED",
        "INACTIVE",
    }

    # =========================================
    # STATUS VALIDATION
    # =========================================

    if new_status not in allowed_statuses:
        flash(
            "Trạng thái tài khoản không hợp lệ.",
            "error",
        )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    # =========================================
    # SAME STATUS
    # =========================================

    if new_status == user.status:
        flash(
            "Tài khoản đã ở trạng thái này.",
            "warning",
        )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    # =========================================
    # SELF PROTECTION
    # =========================================

    if (
        user.userID == current_user.userID
        and new_status in {
            "LOCKED",
            "INACTIVE",
        }
    ):
        flash(
            (
                "Bạn không thể tự khóa hoặc "
                "ngừng hoạt động tài khoản đang đăng nhập."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    old_status = user.status

    try:
        user.status = new_status

        db.session.commit()

        status_labels = {
            "ACTIVE": "Đang hoạt động",
            "LOCKED": "Đã khóa",
            "INACTIVE": "Ngừng hoạt động",
        }

        flash(
            (
                "Đã chuyển trạng thái tài khoản "
                f"từ {status_labels.get(old_status, old_status)} "
                f"sang {status_labels.get(new_status, new_status)}."
            ),
            "success",
        )

    except Exception:
        db.session.rollback()

        flash(
            (
                "Không thể thay đổi trạng thái "
                "tài khoản lúc này."
            ),
            "error",
        )

    return redirect(
        url_for(
            "admin.user_detail",
            user_id=user.userID,
        )
    )
    
@admin_bp.post(
    "/users/<int:user_id>/password"
)
@login_required
@role_required("SYSTEM_ADMIN")
def update_user_password(user_id):
    user = User.query.get_or_404(user_id)

    sidebar_stats = get_admin_sidebar_stats()

    available_roles = (
        Role.query
        .filter_by(isActive=True)
        .order_by(Role.name.asc())
        .all()
    )

    is_self = (
        user.userID
        == current_user.userID
    )

    current_password = request.form.get(
        "currentPassword",
        "",
    )

    new_password = request.form.get(
        "newPassword",
        "",
    )

    confirm_password = request.form.get(
        "confirmPassword",
        "",
    )

    password_errors = {}

    # =========================================
    # CURRENT PASSWORD
    # =========================================

    if is_self:
        if not current_password:
            password_errors["currentPassword"] = (
                "Vui lòng nhập mật khẩu hiện tại."
            )

        elif not check_password_hash(
            user.passwordHash,
            current_password,
        ):
            password_errors["currentPassword"] = (
                "Mật khẩu hiện tại không chính xác."
            )

    # =========================================
    # NEW PASSWORD
    # =========================================

    if not new_password:
        password_errors["newPassword"] = (
            "Vui lòng nhập mật khẩu mới."
        )

    elif len(new_password) < 8:
        password_errors["newPassword"] = (
            "Mật khẩu phải có ít nhất 8 ký tự."
        )

    elif (
        is_self
        and check_password_hash(
            user.passwordHash,
            new_password,
        )
    ):
        password_errors["newPassword"] = (
            "Mật khẩu mới phải khác mật khẩu hiện tại."
        )

    # =========================================
    # CONFIRM PASSWORD
    # =========================================

    if not confirm_password:
        password_errors["confirmPassword"] = (
            "Vui lòng xác nhận mật khẩu mới."
        )

    elif new_password != confirm_password:
        password_errors["confirmPassword"] = (
            "Mật khẩu xác nhận không khớp."
        )

    # =========================================
    # VALIDATION FAILED
    # =========================================

    if password_errors:
        return render_template(
            "admin/users/detail.html",
            user=user,
            sidebar_stats=sidebar_stats,
            available_roles=available_roles,
            errors={},
            form_data={
                "fullName": user.fullName,
                "phone": user.phone or "",
            },
            edit_mode=False,
            password_modal_open=True,
            password_errors=password_errors,
        )

    # =========================================
    # SAVE
    # =========================================

    try:
        user.passwordHash = (
            generate_password_hash(
                new_password
            )
        )

        db.session.commit()

        if is_self:
            flash(
                "Đã đổi mật khẩu thành công.",
                "success",
            )
        else:
            flash(
                (
                    "Đã đặt mật khẩu tạm thời "
                    f"cho {user.fullName}."
                ),
                "success",
            )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    except Exception:
        db.session.rollback()

        flash(
            (
                "Không thể cập nhật mật khẩu lúc này. "
                "Vui lòng thử lại."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )
    
@admin_bp.post(
    "/users/<int:user_id>/avatar"
)

@permission_required("USER_UPDATE")
def update_user_avatar(user_id):
    user = User.query.get_or_404(user_id)
    old_avatar_path = user.avatarUrl

    avatar_source = request.form.get(
        "avatarSource",
        "",
    ).strip()

    preset_avatar = request.form.get(
        "presetAvatar",
        "",
    ).strip()

    avatar_file = request.files.get(
        "avatarFile"
    )

    new_avatar_path = None
    uploaded_file_path = None

    # =========================================
    # PRESET AVATAR
    # =========================================

    if avatar_source == "preset":
        default_avatar = (
            "images/avatars/"
            "avatar-default.webp"
        )

        allowed_presets = {
            default_avatar,
            "images/avatars/avatar-cat.webp",
            "images/avatars/avatar-dog.webp",
            "images/avatars/avatar-paw.webp",
        }

        if preset_avatar not in allowed_presets:
            flash(
                (
                    "Ảnh đại diện được chọn "
                    "không hợp lệ."
                ),
                "error",
            )
            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        if preset_avatar == default_avatar:
            new_avatar_path = None
        else:
            new_avatar_path = preset_avatar

    # =========================================
    # UPLOAD AVATAR
    # =========================================

    elif avatar_source == "upload":

        is_valid, image_format = (
            validate_avatar_image(
                avatar_file
            )
        )

        if not is_valid:
            flash(
                image_format,
                "error",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        extension_map = {
            "JPEG": "jpg",
            "PNG": "png",
            "WEBP": "webp",
        }

        extension = extension_map[
            image_format
        ]

        filename = (
            f"user-{user.userID}-"
            f"{uuid4().hex[:10]}."
            f"{extension}"
        )

        upload_dir = (
            Path(current_app.static_folder)
            / "uploads"
            / "avatars"
        )

        upload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        save_path = (
            upload_dir
            / filename
        )

        avatar_file.save(save_path)
        uploaded_file_path = save_path
        
        try:
            process_avatar_image(
                save_path,
                image_format,
            )
        except (
            OSError,
            ValueError,
        ):
            try:
                save_path.unlink()
            except OSError:
                pass

            flash(
                "Không thể xử lý ảnh đại diện.",
                "error",
            )

            return redirect(
                url_for(
                    "admin.user_detail",
                    user_id=user.userID,
                )
            )

        new_avatar_path = (
            f"uploads/avatars/{filename}"
        )

    else:

        flash(
            "Vui lòng chọn ảnh đại diện.",
            "error",
        )

        return redirect(
            url_for(
                "admin.user_detail",
                user_id=user.userID,
            )
        )

    # =========================================
    # SAVE DATABASE
    # =========================================

    try:
        user.avatarUrl = new_avatar_path

        db.session.commit()

        if (
            old_avatar_path
            != new_avatar_path
        ):
            delete_old_uploaded_avatar(
                old_avatar_path
            )

        flash(
            "Đã cập nhật ảnh đại diện.",
            "success",
        )

    except Exception:
        db.session.rollback()

        if (
            uploaded_file_path
            and uploaded_file_path.exists()
        ):
            try:
                uploaded_file_path.unlink()
            except OSError:
                pass

        flash(
            (
                "Không thể cập nhật ảnh đại diện "
                "lúc này."
            ),
            "error",
        )

    return redirect(
        url_for(
            "admin.user_detail",
            user_id=user.userID,
        )
    )

@admin_bp.get("/users/<int:user_id>/activity")

@permission_required("USER_VIEW")
def user_activity(user_id):
    user = User.query.get_or_404(user_id)

    sidebar_stats = get_admin_sidebar_stats()

    return render_template(
        "admin/users/activity.html",
        user=user,
        sidebar_stats=sidebar_stats,
    )