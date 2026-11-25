"""Vaccination and follow-up transactions. No booking, inventory or mail writes."""
import hashlib
import json
from datetime import date, datetime, timezone

from flask import abort, current_app
from itsdangerous import BadSignature, URLSafeSerializer

from app.extensions import db
from app.models import (Appointment, ClinicStaff, FollowUp, MedicalVisit, User,
                        VaccinationRecord, Vaccine, Veterinarian, VisitVeterinarian)
from app.veterinarian.medical_records import lock_record, validate_revision
from app.veterinarian.validation import today

FOLLOW_UP_STATUSES = {"UPCOMING": "Chờ tái khám", "OVERDUE": "Quá hạn",
                      "COMPLETED": "Đã tái khám", "CANCELLED": "Đã hủy"}
FOLLOW_FIELDS = ("visitID", "petID", "veterinarianID", "scheduledDate", "reason", "note", "status", "appointmentID")


def form_day(raw, label, errors, key, required=True):
    if not raw and not required:
        return None
    try:
        value = date.fromisoformat(raw)
        if not 1900 <= value.year <= 9998:
            raise ValueError
        return value
    except (ValueError, TypeError):
        errors[key] = f"{label} không hợp lệ."
        return None


def form_id(raw, label, errors, key, optional=False):
    if not raw and optional:
        return None
    try:
        if len(raw) > 19:
            raise ValueError
        value = int(raw)
        if not 0 < value <= 9223372036854775807:
            raise ValueError
        return value
    except (ValueError, TypeError):
        errors[key] = f"{label} không hợp lệ."
        return None


def active_doctors_query():
    return db.select(Veterinarian, User.fullName).join(ClinicStaff,
        ClinicStaff.staffID == Veterinarian.staffID).join(User, User.userID == ClinicStaff.userID).where(
        Veterinarian.status == "ACTIVE", ClinicStaff.status == "ACTIVE",
        ClinicStaff.staffType == "VETERINARIAN", User.status == "ACTIVE")


def procedure_allowed(visit_id, vet_id):
    role = db.session.scalar(db.select(VisitVeterinarian.participationRole).where(
        VisitVeterinarian.visitID == visit_id, VisitVeterinarian.veterinarianID == vet_id))
    # PROCEDURE is the explicit procedure assignment already present in SQL 10.
    # ASSISTING / CONSULTING alone is not an assignment to perform vaccination.
    if role not in ("PRIMARY", "PROCEDURE"):
        abort(403, description="Chỉ bác sĩ chính hoặc bác sĩ được phân công PROCEDURE được ghi tiêm.")


def save_vaccination(visit_id, vet_id, form):
    visit, _, _ = lock_record(visit_id, vet_id, require_primary=False)
    procedure_allowed(visit_id, vet_id)
    validate_revision(visit, form.get("revision", ""))
    errors = {}
    vaccine_id = form_id(form.get("vaccineID", ""), "Vaccine", errors, "vaccineID")
    day = form_day(form.get("vaccinationDate", ""), "Ngày tiêm", errors, "vaccinationDate")
    next_day = form_day(form.get("nextDueDate", ""), "Ngày nhắc", errors, "nextDueDate", False)
    data = {key: form.get(key, "").strip() or None for key in ("dose", "lotNumber", "reaction", "note")}
    for key, maximum in (("dose", 150), ("lotNumber", 100), ("reaction", 2000), ("note", 2000)):
        if (key == "dose" and not data[key]) or len(data[key] or "") > maximum:
            errors[key] = "Liều bắt buộc; liều/lô/phản ứng/ghi chú cần đúng giới hạn độ dài."
    if day and (day != visit.visitDate or day > today()):
        errors["vaccinationDate"] = "Ngày tiêm phải là ngày của ca khám và không ở tương lai."
    if day and next_day and next_day <= day:
        errors["nextDueDate"] = "Ngày nhắc phải sau ngày tiêm."
    if not errors:
        vaccine = db.session.scalar(db.select(Vaccine).where(Vaccine.vaccineID == vaccine_id)
            .with_for_update().execution_options(populate_existing=True))
        if vaccine is None or not vaccine.isActive:
            errors["vaccineID"] = "Vaccine không tồn tại hoặc đã ngừng hoạt động."
    if errors:
        db.session.rollback()
        return None, errors
    row = VaccinationRecord(petID=visit.petID, visitID=visit_id, veterinarianID=vet_id,
        vaccineID=vaccine_id, vaccinationDate=day, nextDueDate=next_day, **data)
    db.session.add(row)
    visit.updatedAt = datetime.now(timezone.utc)
    db.session.flush()
    saved = row.vaccinationID
    db.session.commit()
    return saved, {}


def follow_values(row):
    return {key: "" if getattr(row, key) is None else str(getattr(row, key)) for key in FOLLOW_FIELDS}


def follow_token(row):
    digest = hashlib.sha256(json.dumps(follow_values(row), sort_keys=True).encode()).hexdigest()
    return URLSafeSerializer(current_app.secret_key, salt="follow-up-revision").dumps(
        {"id": row.followUpID, "digest": digest})


def validate_follow_token(row, token):
    try:
        if not token or len(token) > 1000:
            raise BadSignature("Missing revision")
        data = URLSafeSerializer(current_app.secret_key, salt="follow-up-revision").loads(token)
        expected = URLSafeSerializer(current_app.secret_key, salt="follow-up-revision").loads(follow_token(row))
        if not isinstance(data, dict) or data.get("id") != row.followUpID:
            raise BadSignature("Wrong follow-up")
    except BadSignature:
        abort(400, description="Phiên bản yêu cầu tái khám không hợp lệ.")
    if data != expected:
        abort(409, description="Yêu cầu đã thay đổi. Vui lòng mở lại trước khi lưu.")


def validate_follow_form(form, visit, existing=None):
    errors = {}
    day = form_day(form.get("scheduledDate", ""), "Ngày tái khám", errors, "scheduledDate")
    vet_id = form_id(form.get("veterinarianID", ""), "Bác sĩ dự kiến", errors, "veterinarianID", True)
    reason, note = form.get("reason", "").strip(), form.get("note", "").strip() or None
    status = form.get("status", "UPCOMING") if existing else "UPCOMING"
    if not reason or len(reason) > 2000:
        errors["reason"] = "Lý do tái khám bắt buộc, tối đa 2.000 ký tự."
    if len(note or "") > 2000:
        errors["note"] = "Ghi chú tối đa 2.000 ký tự."
    if day and (day <= visit.visitDate or (existing is None and day < today())):
        errors["scheduledDate"] = "Ngày tái khám phải sau ngày ca nguồn, không tạo yêu cầu mới trong quá khứ."
    if status not in FOLLOW_UP_STATUSES:
        errors["status"] = "Trạng thái không hợp lệ."
    if day and status == "UPCOMING" and day < today():
        errors["status"] = "Ngày hẹn đã qua; chọn Quá hạn hoặc cập nhật ngày dự kiến."
    if day and status == "OVERDUE" and day >= today():
        errors["status"] = "Chỉ ghi Quá hạn khi ngày dự kiến đã qua."
    if visit.status == "COMPLETED" and existing is not None:
        frozen = (day, vet_id, reason, note)
        if frozen != (existing.scheduledDate, existing.veterinarianID, existing.reason, existing.note):
            errors["locked"] = "Ca nguồn đã chốt: chỉ liên kết lịch và cập nhật trạng thái, không sửa nội dung đề nghị."
    if errors:
        return {}, errors
    if vet_id is not None and (existing is None or vet_id != existing.veterinarianID):
        # Keep the active identity stable until the clinical transaction commits.
        active = db.session.execute(active_doctors_query().where(Veterinarian.veterinarianID == vet_id)
            .with_for_update(of=(Veterinarian, ClinicStaff, User))).first()
        if active is None:
            errors["veterinarianID"] = "Bác sĩ dự kiến không hoạt động hoặc không có hồ sơ hợp lệ."
    return dict(scheduledDate=day, veterinarianID=vet_id, reason=reason, note=note, status=status), errors


def link_appointment(visit, row, appointment_id, values):
    if appointment_id is None:
        if values["status"] == "COMPLETED":
            abort(422, description="Hoàn tất yêu cầu cần lịch tái khám và bệnh án tái khám đã hoàn tất.")
        return
    if appointment_id == visit.appointmentID:
        abort(422, description="Không thể dùng lịch của ca nguồn làm lịch tái khám.")
    appointment = db.session.scalar(db.select(Appointment).where(Appointment.appointmentID == appointment_id,
        Appointment.petID == visit.petID)
        .with_for_update(of=Appointment).execution_options(populate_existing=True))
    if (appointment is None or appointment.petID != visit.petID
            or appointment.scheduledDate != values["scheduledDate"]
            or (values["veterinarianID"] is not None and appointment.veterinarianID != values["veterinarianID"])):
        abort(422, description="Lịch tái khám phải cùng thú cưng, ngày và bác sĩ dự kiến nếu đã chọn.")
    if appointment.status in ("CANCELLED", "NO_SHOW") and values["status"] != "CANCELLED":
        abort(409, description="Lịch đã hủy/khách không đến. Bỏ liên kết hoặc chọn lịch phù hợp.")
    if appointment.status not in ("PENDING", "CONFIRMED", "CHECKED_IN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "NO_SHOW"):
        abort(409, description="Trạng thái lịch liên kết không hợp lệ.")
    duplicate = db.session.scalar(db.select(FollowUp.followUpID).where(
        FollowUp.appointmentID == appointment_id, FollowUp.status != "CANCELLED",
        FollowUp.followUpID != row.followUpID))
    # The target appointment is already the serialization lock. Do not acquire
    # another recommendation's row lock: its owner may be waiting for this
    # appointment lock while updating/cancelling that recommendation.
    if duplicate is not None:
        abort(409, description="Lịch này đã liên kết một yêu cầu tái khám khác.")
    if values["status"] == "COMPLETED":
        target = db.session.scalar(db.select(MedicalVisit).where(MedicalVisit.appointmentID == appointment_id)
            .with_for_update(of=MedicalVisit).execution_options(populate_existing=True))
        if (appointment.status != "COMPLETED" or target is None or target.status != "COMPLETED"
                or target.petID != visit.petID or target.visitDate != values["scheduledDate"]
                or target.visitDate > today() or target.completedAt is None):
            abort(409, description="Chỉ hoàn tất khi có bệnh án tái khám đã hoàn tất thực tế.")


def save_follow_up(visit_id, vet_id, form, follow_id=None):
    visit, _, _ = lock_record(visit_id, vet_id, allow_completed=follow_id is not None)
    row = None
    if follow_id is None:
        validate_revision(visit, form.get("revision", ""))
    else:
        row = db.session.scalar(db.select(FollowUp).where(FollowUp.followUpID == follow_id,
            FollowUp.visitID == visit_id).with_for_update().execution_options(populate_existing=True))
        if row is None:
            abort(404)
        if row.petID != visit.petID:
            abort(409, description="Pet trong yêu cầu không khớp ca khám.")
        if row.status in ("COMPLETED", "CANCELLED"):
            abort(409, description="Yêu cầu đã hoàn tất/hủy, không thể sửa.")
        validate_follow_token(row, form.get("revision", ""))
    values, errors = validate_follow_form(form, visit, row)
    # Creating a recommendation never creates or attaches an appointment.
    appointment_id = None
    if row is not None:
        appointment_id = form_id(form.get("appointmentID", ""), "Lịch liên kết", errors, "appointmentID", True)
    if errors:
        db.session.rollback()
        return None, errors
    if row is None:
        row = FollowUp(visitID=visit_id, petID=visit.petID, appointmentID=None, **values)
        db.session.add(row)
    else:
        # Lock old/new target appointments in a stable order before examining
        # either, including when two recommendations try to swap bookings.
        target_ids = sorted({value for value in (row.appointmentID, appointment_id) if value is not None})
        if visit.appointmentID in target_ids:
            abort(422, description="Không thể liên kết lịch của ca nguồn.")
        if target_ids:
            db.session.scalars(db.select(Appointment).where(Appointment.appointmentID.in_(target_ids),
                Appointment.petID == visit.petID)
                .order_by(Appointment.appointmentID).with_for_update(of=Appointment)
                .execution_options(populate_existing=True)).all()
        if row.appointmentID is not None and row.appointmentID != appointment_id:
            old = db.session.scalar(db.select(Appointment).where(Appointment.appointmentID == row.appointmentID)
                .with_for_update(of=Appointment).execution_options(populate_existing=True))
            if old is not None and old.status in ("IN_PROGRESS", "COMPLETED"):
                abort(409, description="Không bỏ/đổi liên kết khi lượt tái khám đã bắt đầu hoặc hoàn tất.")
        link_appointment(visit, row, appointment_id, values)
        for key, value in values.items():
            setattr(row, key, value)
        row.appointmentID = appointment_id
    # Do not rewrite a completed medical record, even its timestamp.
    if visit.status == "DRAFT":
        visit.updatedAt = datetime.now(timezone.utc)
    db.session.flush()
    saved = row.followUpID
    db.session.commit()
    return saved, {}
