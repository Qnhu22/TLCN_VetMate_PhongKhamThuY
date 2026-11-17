import re
import uuid
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

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.auth.activation_service import (
    create_activation_link,
)

from flask_login import current_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.booking.scheduling import SERVICES_SQL, VETS_SQL, available_slots

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
from app.models import OwnerProfile, Pet, User, Role, Species, Breed, Appointment
from app.receptionist import receptionist_bp

from sqlalchemy import func, or_, text
from app.pets.validation import (
    PetValidationError,
    validate_pet_form,
)

from app.pets.image_utils import (
    PetImageError,
    save_pet_image,
    delete_pet_image,
)

from app.pets.csrf import (
    pet_csrf_token,
    validate_pet_csrf,
)


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

                raw_token, activation_link = create_activation_link(
                    user.userID
                )

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

                activation_url = url_for(
                    "auth.customer_activation",
                    token=raw_token,
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


@receptionist_bp.get("/pets")
@role_required("RECEPTIONIST")
def pets():
    """Danh sách thú cưng dành cho lễ tân."""

    if current_user.status != "ACTIVE":
        abort(403)

    keyword = request.args.get(
        "q", ""
    ).strip()[:100]

    status = request.args.get(
        "status", ""
    ).strip().upper()

    if status not in {"", "ACTIVE", "INACTIVE"}:
        status = ""

    page = request.args.get(
        "page", 1, type=int
    )

    page = max(page or 1, 1)

    query = (
        db.session.query(Pet)
        .join(
            OwnerProfile,
            Pet.ownerID == OwnerProfile.ownerID,
        )
        .join(
            User,
            OwnerProfile.userID == User.userID,
        )
        .filter(
            User.roles.any(
                Role.roleCode == "PET_OWNER"
            )
        )
    )

    if keyword:
        term = f"%{keyword}%"

        query = query.filter(
            or_(
                Pet.name.ilike(term),
                Pet.petCode.ilike(term),
                User.fullName.ilike(term),
                User.email.ilike(term),
            )
        )

    if status:
        query = query.filter(
            Pet.status == status
        )

    pagination = query.order_by(
        Pet.createdAt.desc(),
        Pet.petID.desc(),
    ).paginate(
        page=page,
        per_page=10,
        error_out=False,
    )

    return render_template(
        "receptionist/pets/index.html",
        pets=pagination.items,
        pagination=pagination,
        keyword=keyword,
        selected_status=status,
    )


@receptionist_bp.get("/pets/<int:pet_id>")
@role_required("RECEPTIONIST")
def pet_detail(pet_id):
    """Xem chi tiết thú cưng."""

    if current_user.status != "ACTIVE":
        abort(403)

    pet = db.session.get(Pet, pet_id)

    if pet is None:
        abort(404)

    if (
        pet.owner is None
        or pet.owner.user is None
        or not pet.owner.user.has_role("PET_OWNER")
    ):
        abort(404)

    return render_template(
        "receptionist/pets/detail.html",
        pet=pet,
        owner=pet.owner,
        customer=pet.owner.user,
    )


@receptionist_bp.get("/pets/create")
@role_required("RECEPTIONIST")
def pet_create_select_owner():
    """Chọn chủ nuôi trước khi tạo hồ sơ thú cưng."""

    if current_user.status != "ACTIVE":
        abort(403)

    keyword = request.args.get("q", "").strip()[:100]
    page = max(request.args.get("page", 1, type=int) or 1, 1)

    query = (
        db.session.query(OwnerProfile, User)
        .join(
            User,
            OwnerProfile.userID == User.userID,
        )
        .filter(
            User.roles.any(
                Role.roleCode == "PET_OWNER"
            )
        )
    )

    if keyword:
        term = f"%{keyword}%"

        query = query.filter(
            or_(
                User.fullName.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )

    pagination = query.order_by(
        User.fullName.asc(),
        OwnerProfile.ownerID.asc(),
    ).paginate(
        page=page,
        per_page=10,
        error_out=False,
    )

    return render_template(
        "receptionist/pets/select_owner.html",
        customers=pagination.items,
        pagination=pagination,
        keyword=keyword,
    )


@receptionist_bp.route(
    "/customers/<int:owner_id>/pets/create",
    methods=["GET", "POST"],
)
@role_required("RECEPTIONIST")
def customer_pet_create(owner_id):
    """Lễ tân thêm thú cưng cho khách hàng."""

    if current_user.status != "ACTIVE":
        abort(403)

    # Chỉ cho phép tạo thú cưng cho chủ nuôi hợp lệ.
    customer_record = (
        db.session.query(OwnerProfile, User)
        .join(User, OwnerProfile.userID == User.userID)
        .filter(
            OwnerProfile.ownerID == owner_id,
            User.roles.any(
                Role.roleCode == "PET_OWNER"
            ),
        )
        .first()
    )

    if customer_record is None:
        abort(404)

    owner, customer = customer_record

    species_list = (
        Species.query
        .filter_by(isActive=True)
        .order_by(Species.name)
        .all()
    )

    breeds = (
        Breed.query
        .filter_by(isActive=True)
        .order_by(Breed.name)
        .all()
    )

    if request.method == "POST":
        validate_pet_csrf()

        new_photo = None

        try:
            data = validate_pet_form(request.form)

            photo_file = request.files.get("photo")

            if photo_file and photo_file.filename:
                new_photo = save_pet_image(photo_file)

            pet = Pet(
                ownerID=owner.ownerID,
                **data,
                photoUrl=new_photo,
            )

            db.session.add(pet)
            db.session.commit()

        except (PetValidationError, PetImageError) as exc:
            db.session.rollback()
            flash(str(exc), "error")

        except IntegrityError:
            db.session.rollback()
            current_app.logger.exception(
                "Lỗi ràng buộc khi thêm thú cưng."
            )
            flash(
                "Dữ liệu thú cưng bị trùng hoặc không hợp lệ.",
                "error",
            )

        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Không thể thêm thú cưng cho khách hàng."
            )
            flash(
                "Không thể thêm thú cưng. Vui lòng thử lại.",
                "error",
            )

        else:
            flash(
                "Đã thêm thú cưng cho khách hàng thành công!",
                "success",
            )

            return redirect(
                url_for(
                    "receptionist.pet_detail",
                    pet_id=pet.petID,
                )
            )

        if new_photo:
            delete_pet_image(new_photo)

    return render_template(
        "receptionist/pets/create.html",
        owner=owner,
        customer=customer,
        species_list=species_list,
        breeds=breeds,
        form_data=(
            request.form
            if request.method == "POST"
            else {}
        ),
        csrf_token=pet_csrf_token(),
    )


@receptionist_bp.route(
    "/pets/<int:pet_id>/edit",
    methods=["GET", "POST"],
)
@role_required("RECEPTIONIST")
def pet_edit(pet_id):
    """Chỉnh sửa hồ sơ thú cưng dành cho lễ tân."""

    if current_user.status != "ACTIVE":
        abort(403)

    pet = db.session.get(Pet, pet_id)

    if (
        pet is None
        or pet.owner is None
        or pet.owner.user is None
        or not pet.owner.user.has_role("PET_OWNER")
    ):
        abort(404)

    species_list = (
        Species.query
        .filter_by(isActive=True)
        .order_by(Species.name)
        .all()
    )

    breeds = (
        Breed.query
        .filter_by(isActive=True)
        .order_by(Breed.name)
        .all()
    )

    if request.method == "GET":
        form_data = {
            "name": pet.name,
            "speciesID": str(pet.speciesID),
            "breedID": str(pet.breedID or ""),
            "sex": pet.sex or "UNKNOWN",
            "dateOfBirth": (
                pet.dateOfBirth.isoformat()
                if pet.dateOfBirth else ""
            ),
            "color": pet.color or "",
            "sterilized": (
                "" if pet.sterilized is None
                else "true" if pet.sterilized else "false"
            ),
            "microchipNumber": pet.microchipNumber or "",
            "allergies": pet.allergies or "",
            "chronicConditions": pet.chronicConditions or "",
            "note": pet.note or "",
        }

    else:
        validate_pet_csrf()
        form_data = request.form
        new_photo = None
        old_photo = pet.photoUrl

        try:
            data = validate_pet_form(
                request.form,
                current_pet=pet,
            )

            photo_file = request.files.get("photo")

            if photo_file and photo_file.filename:
                new_photo = save_pet_image(photo_file)

            for field, value in data.items():
                setattr(pet, field, value)

            if new_photo:
                pet.photoUrl = new_photo

            db.session.commit()

        except (PetValidationError, PetImageError) as exc:
            db.session.rollback()
            if new_photo:
                delete_pet_image(new_photo)
            flash(str(exc), "error")

        except IntegrityError:
            db.session.rollback()
            if new_photo:
                delete_pet_image(new_photo)
            current_app.logger.exception(
                "Dữ liệu thú cưng không hợp lệ."
            )
            flash(
                "Dữ liệu không hợp lệ hoặc mã microchip bị trùng.",
                "error",
            )

        except Exception:
            db.session.rollback()
            if new_photo:
                delete_pet_image(new_photo)
            current_app.logger.exception(
                "Không thể cập nhật thú cưng %s.",
                pet_id,
            )
            flash(
                "Không thể cập nhật hồ sơ. Vui lòng thử lại.",
                "error",
            )

        else:
            if new_photo and old_photo:
                delete_pet_image(old_photo)

            flash(
                "Đã cập nhật hồ sơ thú cưng thành công!",
                "success",
            )

            return redirect(
                url_for(
                    "receptionist.pet_detail",
                    pet_id=pet.petID,
                )
            )

    return render_template(
        "receptionist/pets/edit.html",
        pet=pet,
        owner=pet.owner,
        customer=pet.owner.user,
        species_list=species_list,
        breeds=breeds,
        form_data=form_data,
        csrf_token=pet_csrf_token(),
    )

@receptionist_bp.get("/appointments")
@role_required("RECEPTIONIST")
def appointments():
    """Danh sách lịch hẹn: chỉ xem, không thay đổi trạng thái."""
    if current_user.status != "ACTIVE":
        abort(403)

    keyword = request.args.get("q", "").strip()[:100]
    selected_status = request.args.get("status", "").strip().upper()
    allowed_statuses = {
        "PENDING", "CONFIRMED", "CHECKED_IN", "IN_PROGRESS",
        "COMPLETED", "CANCELLED", "NO_SHOW",
    }
    if selected_status not in allowed_statuses:
        selected_status = ""

    selected_type = request.args.get("type", "").strip().upper()
    if selected_type not in {"SCHEDULED", "WALK_IN", "EMERGENCY"}:
        selected_type = ""

    date_text = request.args.get("date", "").strip()
    from datetime import date as date_type
    try:
        selected_date = date_type.fromisoformat(date_text) if date_text else None
    except ValueError:
        selected_date = None
        date_text = ""

    page = max(request.args.get("page", 1, type=int) or 1, 1)

    query = (
        db.session.query(Appointment)
        .join(Pet, Appointment.petID == Pet.petID)
        .join(OwnerProfile, Pet.ownerID == OwnerProfile.ownerID)
        .join(User, OwnerProfile.userID == User.userID)
    )

    if keyword:
        term = f"%{keyword}%"
        query = query.filter(or_(
            Appointment.appointmentCode.ilike(term),
            Pet.name.ilike(term),
            Pet.petCode.ilike(term),
            User.fullName.ilike(term),
            User.phone.ilike(term),
        ))
    if selected_status:
        query = query.filter(Appointment.status == selected_status)
    if selected_type:
        query = query.filter(Appointment.appointmentType == selected_type)
    if selected_date:
        query = query.filter(Appointment.scheduledDate == selected_date)

    pagination = query.order_by(
        Appointment.scheduledDate.desc(),
        Appointment.startTime.desc(),
        Appointment.appointmentID.desc(),
    ).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        "receptionist/appointments/index.html",
        appointments=pagination.items,
        pagination=pagination,
        keyword=keyword,
        selected_status=selected_status,
        selected_type=selected_type,
        selected_date=date_text,
    )
    
@receptionist_bp.get('/appointments/create')
@role_required('RECEPTIONIST')
def appointment_create_select_owner():
    if current_user.status != 'ACTIVE':
        abort(403)

    keyword = request.args.get('q', '').strip()[:100]
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    query = (
        db.session.query(OwnerProfile, User)
        .join(User, OwnerProfile.userID == User.userID)
        .filter(User.roles.any(Role.roleCode == 'PET_OWNER'))
    )
    if keyword:
        term = f'%{keyword}%'
        query = query.filter(or_(
            User.fullName.ilike(term),
            User.email.ilike(term),
            User.phone.ilike(term),
        ))
    pagination = query.order_by(User.fullName.asc(), OwnerProfile.ownerID.asc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template(
        'receptionist/appointments/select_owner.html',
        customers=pagination.items, pagination=pagination, keyword=keyword,
    )


@receptionist_bp.get('/appointments/create/owners/<int:owner_id>/pets')
@role_required('RECEPTIONIST')
def appointment_create_select_pet(owner_id):
    if current_user.status != 'ACTIVE':
        abort(403)

    owner = (
        OwnerProfile.query.join(User, OwnerProfile.userID == User.userID)
        .filter(OwnerProfile.ownerID == owner_id)
        .filter(User.roles.any(Role.roleCode == 'PET_OWNER'))
        .first()
    )
    if owner is None:
        abort(404)

    pets = (
        Pet.query.filter_by(ownerID=owner.ownerID, status='ACTIVE')
        .order_by(Pet.name.asc(), Pet.petID.asc()).all()
    )
    return render_template(
        'receptionist/appointments/select_pet.html', owner=owner,
        customer=owner.user, pets=pets,
    )
    
@receptionist_bp.route('/appointments/create/pets/<int:pet_id>', methods=['GET', 'POST'])
@role_required('RECEPTIONIST')

def appointment_create_form(pet_id):
    if current_user.status != "ACTIVE":
        abort(403)

    pet = Pet.query.filter_by(
        petID=pet_id,
        status="ACTIVE"
    ).first_or_404()

    services = db.session.execute(
        SERVICES_SQL
    ).mappings().all()

    data = request.form if request.method == "POST" else request.args

    service_id = data.get("serviceID", type=int)
    vet_id = data.get("veterinarianID", type=int)
    day_str = data.get("scheduledDate", "").strip()

    try:
        day = date.fromisoformat(day_str) if day_str else None
    except ValueError:
        day = None

    vets = (
        db.session.execute(
            VETS_SQL,
            {"day": day, "service_id": service_id}
        ).mappings().all()
        if day and service_id
        else []
    )

    slots = (
        available_slots(service_id, day, pet_id, vet_id)
        if day and service_id and vet_id
        else []
    )

    error = None

    if request.method == "POST":
        validate_customer_csrf()

        start = request.form.get("startTime", "")
        reason = request.form.get("reason", "").strip()
        source = request.form.get("bookingSource", "")

        selected = next(
            (
                s for s in services
                if s["serviceID"] == service_id
            ),
            None,
        )

        if source not in ("RECEPTION", "PHONE"):
            error = "Nguồn đặt lịch không hợp lệ."

        elif selected is None:
            error = (
                "Dịch vụ không tồn tại hoặc "
                "không còn cho phép đặt lịch."
            )

        elif (
            not day
            or day < datetime.now(
                ZoneInfo("Asia/Ho_Chi_Minh")
            ).date()
            or not vet_id
            or not reason
            or len(reason) > 2000
        ):
            error = "Vui lòng nhập đầy đủ thông tin lịch khám hợp lệ."

        elif start not in slots:
            error = "Khung giờ không còn trống. Vui lòng chọn lại."

        else:
            try:
                # Khóa giao dịch theo ngày để tránh đặt trùng.
                db.session.execute(
                    text(
                        "SELECT pg_advisory_xact_lock(:key)"
                    ),
                    {
                        "key": int(day.strftime("%Y%m%d"))
                    }
                )

                # Kiểm tra lại giờ trống sau khi lấy khóa.
                slots = available_slots(
                    service_id, day, pet_id, vet_id
                )

                if start not in slots:
                    error = (
                        "Khung giờ vừa được đặt. "
                        "Vui lòng chọn giờ khác."
                    )

                else:
                    start_time = datetime.strptime(
                        start, "%H:%M"
                    )

                    end_time = start_time + timedelta(
                        minutes=selected["defaultDurationMinutes"]
                    )

                    staff_id = db.session.execute(
                        text("""
                            SELECT "staffID"
                            FROM clinic."clinicStaff"
                            WHERE "userID" = :uid
                              AND "status" = 'ACTIVE'
                              AND "staffType" = 'RECEPTIONIST'
                        """),
                        {"uid": current_user.userID}
                    ).scalar()

                    if not staff_id:
                        abort(403)

                    code = (
                        "VM"
                        + uuid.uuid4().hex[:16].upper()
                    )

                    appointment = Appointment(
                        appointmentCode=code,
                        petID=pet.petID,
                        serviceID=service_id,
                        veterinarianID=vet_id,
                        appointmentType="SCHEDULED",
                        bookingSource=source,
                        priority="NORMAL",
                        scheduledDate=day,
                        startTime=start_time.time(),
                        endTime=end_time.time(),
                        reason=reason,
                        status="CONFIRMED",
                        confirmedByStaffID=staff_id,
                        confirmedAt=datetime.now(timezone.utc),
                        createdByUserID=current_user.userID,
                    )

                    db.session.add(appointment)
                    db.session.commit()

                    flash(
                        "Đã tạo và xác nhận lịch hẹn thành công.",
                        "success"
                    )

                    return redirect(
                        url_for("receptionist.appointments")
                    )

                # Không lưu lịch: kết thúc transaction,
                # giải phóng advisory lock.
                db.session.rollback()

            except SQLAlchemyError:
                db.session.rollback()

                current_app.logger.exception(
                    "Failed to create appointment"
                )

                error = (
                    "Không thể lưu lịch hẹn. "
                    "Vui lòng thử lại."
                )

    return render_template(
        "receptionist/appointments/create.html",
        pet=pet,
        services=services,
        vets=vets,
        slots=slots,
        selected_service=service_id,
        selected_vet=vet_id,
        selected_date=day_str,
        selected_time=data.get("startTime", ""),
        selected_source=data.get(
            "bookingSource", "RECEPTION"
        ),
        reason=data.get("reason", ""),
        error=error,
        csrf_token=get_customer_csrf_token(),
    )


@receptionist_bp.get("/appointments/<int:appointment_id>")
@role_required("RECEPTIONIST")
def appointment_detail(appointment_id):
    if current_user.status != "ACTIVE":
        abort(403)

    appointment = db.session.get(
        Appointment, appointment_id
    )

    if appointment is None:
        abort(404)

    service = db.session.execute(
        text("""
            SELECT "name", "price", "defaultDurationMinutes"
            FROM clinic."services"
            WHERE "serviceID" = :service_id
        """),
        {"service_id": appointment.serviceID}
    ).mappings().first()

    veterinarian = db.session.execute(
        text("""
            SELECT u."fullName"
            FROM clinic."veterinarians" v
            JOIN clinic."clinicStaff" st
              ON st."staffID" = v."staffID"
            JOIN auth."users" u
              ON u."userID" = st."userID"
            WHERE v."veterinarianID" = :vet_id
        """),
        {"vet_id": appointment.veterinarianID}
    ).mappings().first() if appointment.veterinarianID else None

    return render_template(
        "receptionist/appointments/detail.html",
        appointment=appointment,
        service=service,
        veterinarian=veterinarian,
        queue_entry=appointment.queueEntry,
    )
