from getpass import getpass

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Role, User, UserRole


app = create_app()


with app.app_context():

    print("\n=== TẠO SYSTEM ADMIN VETMATE ===\n")

    email = input(
        "Email admin: "
    ).strip().lower()

    full_name = input(
        "Họ tên: "
    ).strip()

    password = getpass(
        "Mật khẩu: "
    )

    confirm_password = getpass(
        "Nhập lại mật khẩu: "
    )

    if not email:
        raise ValueError(
            "Email không được để trống."
        )

    if not full_name:
        raise ValueError(
            "Họ tên không được để trống."
        )

    if not password:
        raise ValueError(
            "Mật khẩu không được để trống."
        )

    if password != confirm_password:
        raise ValueError(
            "Mật khẩu xác nhận không khớp."
        )

    role = Role.query.filter_by(
        roleCode="SYSTEM_ADMIN"
    ).first()

    if role is None:
        raise RuntimeError(
            "Chưa có role SYSTEM_ADMIN. "
            "Hãy chạy 03_seed_auth.sql trước."
        )

    user = User.query.filter_by(
        email=email
    ).first()

    if user is None:

        user = User(
            email=email,
            passwordHash=generate_password_hash(
                password
            ),
            fullName=full_name,
            status="ACTIVE",
        )

        db.session.add(user)
        db.session.flush()

        print(
            "Đã tạo tài khoản admin."
        )

    else:

        print(
            "Tài khoản đã tồn tại."
        )

    existing_role = UserRole.query.filter_by(
        userID=user.userID,
        roleID=role.roleID,
    ).first()

    if existing_role is None:

        user_role = UserRole(
            userID=user.userID,
            roleID=role.roleID,
        )

        db.session.add(user_role)

        print(
            "Đã gán role SYSTEM_ADMIN."
        )

    else:

        print(
            "Tài khoản đã có role SYSTEM_ADMIN."
        )

    db.session.commit()

    print(
        "\nHoàn tất.\n"
    )