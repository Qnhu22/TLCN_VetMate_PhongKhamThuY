
import secrets
from flask import abort, render_template, request, flash, redirect, session, url_for
from flask_login import current_user, login_required
from zoneinfo import ZoneInfo

from app.booking import booking_bp
from app.extensions import db
from app.models import Appointment, OwnerProfile, Pet, Service
from datetime import date, timedelta, datetime
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from app.models import Service


@booking_bp.get('/appointments')
@login_required
def my_appointments():
    if current_user.status != 'ACTIVE' or not any(r.roleCode == 'PET_OWNER' for r in current_user.roles):
        abort(403)

    owner = OwnerProfile.query.filter_by(userID=current_user.userID).first()
    keyword = request.args.get('q', '').strip()[:100]
    status = request.args.get('status', '').strip().upper()
    source = request.args.get('source', '').strip().upper()
    date_text = request.args.get('date', '').strip()
    sort = request.args.get('sort', 'upcoming').strip()
    group = request.args.get('group', 'all').strip()

    statuses = {'PENDING', 'CONFIRMED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'}
    sources = {'ONLINE', 'PHONE', 'RECEPTION'}
    if status not in statuses: status = ''
    if source not in sources: source = ''
    if sort not in {'upcoming', 'newest', 'oldest', 'created'}: sort = 'upcoming'
    if group not in {'all', 'upcoming', 'history'}: group = 'all'
    try:
        selected_day = date.fromisoformat(date_text) if date_text else None
    except ValueError:
        selected_day, date_text = None, ''

    today = date.today()  # Nếu server chạy khác múi giờ VN, thay bằng datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
    stats = {s: 0 for s in statuses}
    total = 0
    items = []
    service_names = {}
    if owner:
        base = (db.session.query(Appointment)
                .join(Pet, Appointment.petID == Pet.petID)
                .filter(Pet.ownerID == owner.ownerID))
        for appointment_status, count in (base.with_entities(Appointment.status, db.func.count(Appointment.appointmentID))
                                           .group_by(Appointment.status).all()):
            stats[appointment_status] = count
            total += count

        query = base
        if keyword:
            term = '%' + keyword.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
            query = query.filter(or_(Appointment.appointmentCode.ilike(term, escape='\\'),
                                     Pet.name.ilike(term, escape='\\'),
                                     Pet.petCode.ilike(term, escape='\\')))
        if status: query = query.filter(Appointment.status == status)
        if source: query = query.filter(Appointment.bookingSource == source)
        if selected_day: query = query.filter(Appointment.scheduledDate == selected_day)
        if group == 'upcoming':
            query = query.filter(Appointment.scheduledDate >= today,
                                 Appointment.status.in_(['PENDING', 'CONFIRMED', 'CHECKED_IN', 'IN_PROGRESS']))
        elif group == 'history':
            query = query.filter(or_(Appointment.scheduledDate < today,
                                     Appointment.status.in_(['COMPLETED', 'CANCELLED', 'NO_SHOW'])))

        if sort == 'oldest':
            query = query.order_by(Appointment.scheduledDate.asc(), Appointment.startTime.asc(), Appointment.appointmentID.asc())
        elif sort == 'created':
            query = query.order_by(Appointment.createdAt.desc(), Appointment.appointmentID.desc())
        elif sort == 'newest':
            query = query.order_by(Appointment.scheduledDate.desc(), Appointment.startTime.desc(), Appointment.appointmentID.desc())
        else:
            query = query.order_by(Appointment.scheduledDate.asc(), Appointment.startTime.asc(), Appointment.appointmentID.asc())

        items = query.all()
        ids = list({a.serviceID for a in items})
        if ids:
            # serviceID luôn lấy từ lịch của chính chủ nuôi, không phải dữ liệu nhập từ URL.
            rows = db.session.execute(text('SELECT "serviceID", "name" FROM clinic."services" WHERE "serviceID" = ANY(:ids)'), {'ids': ids}).all()
            service_names = dict(rows)

    return render_template('booking/index.html', appointments=items,
                           service_names=service_names, total=total, stats=stats,
                           keyword=keyword, selected_status=status, selected_source=source,
                           selected_date=date_text, selected_sort=sort, selected_group=group,
                           today=today)



# ==========================================================
# PET OWNER - ONLINE APPOINTMENT BOOKING
# ==========================================================

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

BOOKING_SLOTS = [
    f"{hour:02d}:{minute:02d}"
    for hour in range(8, 17)
    for minute in (0, 30)
]

ACTIVE_BOOKING_STATUSES = (
    "PENDING",
    "CONFIRMED",
    "CHECKED_IN",
    "IN_PROGRESS",
)


def _require_pet_owner():
    if (
        current_user.status != "ACTIVE"
        or not any(
            role.roleCode == "PET_OWNER"
            for role in current_user.roles
        )
    ):
        abort(403)

    return OwnerProfile.query.filter_by(
        userID=current_user.userID
    ).first()


def _booking_csrf_token():
    token = session.get("booking_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["booking_csrf_token"] = token

    return token


def _valid_booking_csrf():
    expected = session.get("booking_csrf_token", "")
    submitted = request.form.get("csrf_token", "")

    return bool(
        expected
        and submitted
        and secrets.compare_digest(expected, submitted)
    )


@booking_bp.route(
    "/appointments/create",
    methods=["GET", "POST"]
)
@login_required
def create_appointment():

    owner = _require_pet_owner()

    if not owner:
        flash(
            "Không tìm thấy hồ sơ chủ nuôi.",
            "danger"
        )
        return redirect(
            url_for("booking.my_appointments")
        )

    pets = (
        Pet.query
        .filter_by(ownerID=owner.ownerID)
        .order_by(Pet.name.asc())
        .all()
    )

    services = (
        Service.query
        .filter(
            Service.isBookable.is_(True),
            Service.isEmergency.is_(False),
            Service.status == "ACTIVE"
        )
        .order_by(Service.name.asc())
        .all()
    )

    now = datetime.now(VN_TZ)
    today = now.date()

    form_data = {
        "petID": "",
        "serviceID": "",
        "scheduledDate": "",
        "startTime": "",
        "reason": "",
        "ownerNote": "",
    }

    if request.method == "POST":

        if not _valid_booking_csrf():
            abort(400, description="CSRF token không hợp lệ.")

        form_data = {
            key: request.form.get(key, "").strip()
            for key in form_data
        }

        error = None

        try:
            pet_id = int(form_data["petID"])
            service_id = int(form_data["serviceID"])

            scheduled_date = datetime.strptime(
                form_data["scheduledDate"],
                "%Y-%m-%d"
            ).date()

            start_time = datetime.strptime(
                form_data["startTime"],
                "%H:%M"
            ).time()

        except (ValueError, TypeError):
            error = "Thông tin ngày, giờ hoặc lựa chọn không hợp lệ."

        if not error:

            pet = next(
                (p for p in pets if p.petID == pet_id),
                None
            )

            service = next(
                (s for s in services if s.serviceID == service_id),
                None
            )

            if not pet:
                error = "Thú cưng không hợp lệ."

            elif not service:
                error = "Dịch vụ không khả dụng."

            elif scheduled_date < today:
                error = "Không thể đặt lịch trong quá khứ."

            elif scheduled_date > today + timedelta(days=90):
                error = "Chỉ được đặt lịch trong vòng 90 ngày."

            elif form_data["startTime"] not in BOOKING_SLOTS:
                error = "Khung giờ khám không hợp lệ."

            elif not form_data["reason"]:
                error = "Vui lòng nhập lý do khám."

            elif len(form_data["reason"]) > 1000:
                error = "Lý do khám tối đa 1000 ký tự."

            elif len(form_data["ownerNote"]) > 2000:
                error = "Ghi chú tối đa 2000 ký tự."

            elif service.defaultDurationMinutes <= 0:
                error = "Thời lượng dịch vụ không hợp lệ."

        if not error:

            start_dt = datetime.combine(
                scheduled_date,
                start_time,
                tzinfo=VN_TZ
            )

            end_dt = start_dt + timedelta(
                minutes=service.defaultDurationMinutes
            )

            
            minimum_booking_time = now + timedelta(minutes=30)

            if start_dt < minimum_booking_time:
                error = (
                    "Vui lòng đặt lịch trước giờ khám "
                    "ít nhất 30 phút."
                )


            elif start_dt.hour < 8:
                error = "Giờ khám phải từ 08:00."

            elif (
                end_dt.date() != scheduled_date
                or end_dt.time() > datetime.strptime(
                    "17:00", "%H:%M"
                ).time()
            ):
                error = "Dịch vụ phải kết thúc trước 17:00."

        if not error:

            # Kiểm tra lịch đang hoạt động của chính thú cưng.
            # Lịch chưa có endTime được xem là chiếm
            # ít nhất 30 phút để tránh bỏ sót trùng lịch.

            existing = (
                Appointment.query
                .filter(
                    Appointment.petID == pet_id,
                    Appointment.scheduledDate == scheduled_date,
                    Appointment.status.in_(
                        ACTIVE_BOOKING_STATUSES
                    )
                )
                .all()
            )

            for appointment in existing:

                existing_start = datetime.combine(
                    scheduled_date,
                    appointment.startTime
                )

                existing_end = datetime.combine(
                    scheduled_date,
                    appointment.endTime
                ) if appointment.endTime else (
                    existing_start + timedelta(minutes=30)
                )

                new_start = start_dt.replace(tzinfo=None)
                new_end = end_dt.replace(tzinfo=None)

                if (
                    new_start < existing_end
                    and new_end > existing_start
                ):
                    error = (
                        "Thú cưng đã có lịch hẹn trùng "
                        "với khoảng thời gian này."
                    )
                    break

        if not error:

            appointment = Appointment(
                appointmentCode=(
                    "OL" + secrets.token_hex(10).upper()
                ),
                petID=pet_id,
                serviceID=service_id,
                veterinarianID=None,
                appointmentType="SCHEDULED",
                bookingSource="ONLINE",
                priority="NORMAL",
                scheduledDate=scheduled_date,
                startTime=start_time,
                endTime=end_dt.time(),
                reason=form_data["reason"],
                ownerNote=form_data["ownerNote"] or None,
                status="PENDING",
                createdByUserID=current_user.userID
            )

            try:
                db.session.add(appointment)
                db.session.commit()

            except IntegrityError:
                db.session.rollback()
                error = (
                    "Không thể tạo lịch hẹn do dữ liệu "
                    "bị trùng hoặc không hợp lệ."
                )

            except Exception:
                db.session.rollback()
                raise

            if not error:
                flash(
                    "Đã gửi yêu cầu đặt lịch thành công! "
                    "Vui lòng chờ Lễ tân xác nhận.",
                    "success"
                )

                return redirect(
                    url_for("booking.my_appointments")
                )

        flash(error, "danger")

    return render_template(
        "booking/create.html",
        pets=pets,
        services=services,
        booking_slots=BOOKING_SLOTS,
        today=today,
        max_date=today + timedelta(days=90),
        csrf_token=_booking_csrf_token(),
        form_data=form_data
    )
