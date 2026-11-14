from app import create_app
from app.extensions import db
from app.models import Role, User, UserRole


app = create_app()


with app.app_context():

    print("\n=== GÁN ROLE CHO TÀI KHOẢN ===\n")

    email = input(
        "Email tài khoản: "
    ).strip().lower()

    role_code = input(
        "Role code: "
    ).strip().upper()

    user = User.query.filter_by(
        email=email
    ).first()

    if user is None:
        raise RuntimeError(
            f"Không tìm thấy tài khoản: {email}"
        )

    role = Role.query.filter_by(
        roleCode=role_code,
        isActive=True,
    ).first()

    if role is None:
        raise RuntimeError(
            f"Không tìm thấy role: {role_code}"
        )

    existing = UserRole.query.filter_by(
        userID=user.userID,
        roleID=role.roleID,
    ).first()

    if existing is not None:
        print(
            f"\n{email} đã có role {role_code}."
        )

    else:
        user_role = UserRole(
            userID=user.userID,
            roleID=role.roleID,
        )

        db.session.add(user_role)
        db.session.commit()

        print(
            f"\nĐã gán {role_code} cho {email}."
        )