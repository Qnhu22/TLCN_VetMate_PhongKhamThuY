import re
import secrets
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.auth.otp_service import (
    CUSTOMER_ACTIVATION,
    create_otp_token,
)

from app.auth.email_service import (
    send_customer_activation_otp,
)

from app.receptionist.csrf import (
    get_customer_csrf_token,
    validate_customer_csrf,
)

from app.auth.decorators import role_required
from app.extensions import db
from app.models import OwnerProfile, Pet, User, Role
from app.receptionist import receptionist_bp

from sqlalchemy import func, or_



@receptionist_bp.get("/")
@role_required("RECEPTIONIST")
def dashboard():

    if current_user.status != "ACTIVE":
        abort(403)

    total_customers = db.session.query(
        db.func.count(OwnerProfile.ownerID)
    ).scalar() or 0

    total_pets = db.session.query(
        db.func.count(Pet.petID)
    ).filter(
        Pet.status == "ACTIVE"
    ).scalar() or 0

    stats = {
        "total_customers": total_customers,
        "total_pets": total_pets,
    }

    return render_template(
        "receptionist/dashboard.html",
        stats=stats,
    )


@receptionist_bp.get("/customers")
@role_required("RECEPTIONIST")
def customers():
    if current_user.status != "ACTIVE":
        abort(403)

    keyword = request.args.get("q", "").strip()[:100]

    try:
        page = max(
            int(request.args.get("page", 1)),
            1,
        )
    except (ValueError, TypeError):
        page = 1

    # Đếm số thú cưng của từng chủ nuôi.
    pet_counts = (
        db.session.query(
            Pet.ownerID.label("owner_id"),
            func.count(Pet.petID).label("pet_count"),
        )
        .group_by(Pet.ownerID)
        .subquery()
    )

    query = (
        db.session.query(
            OwnerProfile,
            User,
            func.coalesce(
                pet_counts.c.pet_count, 0
            ).label("pet_count"),
        )
        .join(
            User,
            OwnerProfile.userID == User.userID,
        )
        .outerjoin(
            pet_counts,
            OwnerProfile.ownerID == pet_counts.c.owner_id,
        )
        .filter(
            User.roles.any(
                # Chỉ hiển thị tài khoản có vai trò PET_OWNER.
                # Điều kiện được kiểm tra theo roleCode.
                Role.roleCode == "PET_OWNER"
            )
        )
    )

    if keyword:
        search_term = f"%{keyword}%"

        query = query.filter(
            or_(
                User.fullName.ilike(search_term),
                User.email.ilike(search_term),
                User.phone.ilike(search_term),
            )
        )

    pagination = query.order_by(
        User.createdAt.desc(),
        User.userID.desc(),
    ).paginate(
        page=page,
        per_page=10,
        error_out=False,
    )

    return render_template(
        "receptionist/customers/index.html",
        customers=pagination.items,
        pagination=pagination,
        keyword=keyword,
    )


@receptionist_bp.get("/customers/<int:owner_id>")
@role_required("RECEPTIONIST")
def customer_detail(owner_id):
    if current_user.status != "ACTIVE":
        abort(403)

    customer = (
        db.session.query(OwnerProfile, User)
        .join(
            User,
            OwnerProfile.userID == User.userID,
        )
        .filter(
            OwnerProfile.ownerID == owner_id,
            User.roles.any(
                Role.roleCode == "PET_OWNER"
            ),
        )
        .first()
    )

    if customer is None:
        abort(404)

    owner, user = customer

    pets = (
        Pet.query
        .filter(Pet.ownerID == owner.ownerID)
        .order_by(Pet.createdAt.desc(), Pet.petID.desc())
        .all()
    )

    return render_template(
        "receptionist/customers/detail.html",
        owner=owner,
        customer=user,
        pets=pets,
    )


@receptionist_bp.route(
    "/customers/create",
    methods=["GET", "POST"],
)
@role_required("RECEPTIONIST")
def customer_create():
    if current_user.status != "ACTIVE":
        abort(403)

    errors = {}

    form_data = {
        "fullName": "",
        "email": "",
        "phone": "",
        "address": "",
        "emergencyPhone": "",
        "note": "",
    }

    if request.method == "POST":
        validate_customer_csrf()

        for field in form_data:
            form_data[field] = (
                request.form.get(field, "").strip()
            )

        full_name = form_data["fullName"]
        email = form_data["email"].lower()
        phone = form_data["phone"]
        address = form_data["address"]
        emergency_phone = form_data["emergencyPhone"]
        note = form_data["note"]

        form_data["email"] = email

        if not 2 <= len(full_name) <= 150:
            errors["fullName"] = (
                "Họ tên phải từ 2 đến 150 ký tự."
            )

        if (
            len(email) > 255
            or not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                email,
            )
        ):
            errors["email"] = (
                "Vui lòng nhập email hợp lệ."
            )

        if phone and not re.fullmatch(
            r"0\d{9}", phone
        ):
            errors["phone"] = (
                "Số điện thoại phải gồm 10 chữ số "
                "và bắt đầu bằng 0."
            )

        if emergency_phone and not re.fullmatch(
            r"0\d{9}", emergency_phone
        ):
            errors["emergencyPhone"] = (
                "Số điện thoại khẩn cấp không hợp lệ."
            )

        if len(address) > 500:
            errors["address"] = (
                "Địa chỉ không được vượt quá 500 ký tự."
            )

        if len(note) > 2000:
            errors["note"] = (
                "Ghi chú không được vượt quá 2000 ký tự."
            )

        if "email" not in errors:
            existing_user = User.query.filter(
                db.func.lower(User.email) == email
            ).first()

            if existing_user:
                errors["email"] = (
                    "Email này đã được sử dụng."
                )

        if not errors:
            try:
                pet_owner_role = Role.query.filter_by(
                    roleCode="PET_OWNER",
                    isActive=True,
                ).first()

                if pet_owner_role is None:
                    raise RuntimeError(
                        "Không tìm thấy vai trò PET_OWNER."
                    )

                # Hash của mật khẩu ngẫu nhiên,
                # không chia sẻ với khách hàng.
                random_password = secrets.token_urlsafe(48)

                user = User(
                    fullName=full_name,
                    email=email,
                    phone=phone or None,
                    passwordHash=generate_password_hash(
                        random_password
                    ),
                    status="PENDING_VERIFICATION",
                )

                db.session.add(user)
                db.session.flush()

                user.roles.append(pet_owner_role)

                owner = OwnerProfile(
                    userID=user.userID,
                    address=address or None,
                    emergencyPhone=emergency_phone or None,
                    note=note or None,
                )

                db.session.add(owner)

                otp, _ = create_otp_token(
                    user.userID,
                    CUSTOMER_ACTIVATION,
                )

                # Lưu dữ liệu và OTP.
                db.session.commit()

            except IntegrityError:
                db.session.rollback()
                errors["email"] = (
                    "Email này đã được sử dụng "
                    "hoặc dữ liệu không hợp lệ."
                )

            except Exception:
                db.session.rollback()
                current_app.logger.exception(
                    "Không thể tạo khách hàng."
                )
                errors["general"] = (
                    "Không thể tạo khách hàng lúc này."
                )

            else:
                # URL tạm thời; route kích hoạt
                # sẽ được bổ sung ở bước tiếp theo.
                activation_url = url_for(
                    "auth.customer_activation",
                    email=user.email,
                    _external=True,
                )

                try:
                    send_customer_activation_otp(
                        recipient_email=user.email,
                        full_name=user.fullName,
                        otp=otp,
                        activation_url=activation_url,
                    )

                except Exception:
                    current_app.logger.exception(
                        "Không thể gửi OTP kích hoạt."
                    )

                    flash(
                        "Đã tạo hồ sơ khách hàng nhưng "
                        "chưa gửi được email kích hoạt.",
                        "warning",
                    )

                else:
                    flash(
                        "Đã tạo khách hàng và gửi email "
                        "hướng dẫn kích hoạt.",
                        "success",
                    )

                return redirect(
                    url_for(
                        "receptionist.customer_detail",
                        owner_id=owner.ownerID,
                    )
                )

    return render_template(
        "receptionist/customers/create.html",
        errors=errors,
        form_data=form_data,
        csrf_token=get_customer_csrf_token(),
    )
