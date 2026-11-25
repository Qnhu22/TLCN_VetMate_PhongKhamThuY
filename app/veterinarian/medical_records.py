"""Validation, revision checks and transactional medical-record changes."""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import abort, current_app
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy import inspect

from app.extensions import db
from app.models import Appointment, MedicalVisit, PetWeightHistory, QueueEntry, VisitVeterinarian
from app.veterinarian.visits import visit_scope

TEXT_FIELDS = {
    "chiefComplaint": "Lý do khám", "symptoms": "Triệu chứng",
    "clinicalExamination": "Khám lâm sàng", "preliminaryDiagnosis": "Chẩn đoán ban đầu",
    "finalDiagnosis": "Chẩn đoán cuối cùng", "treatmentPlan": "Hướng điều trị",
    "careInstructions": "Dặn dò chăm sóc",
}
NUMBER_FIELDS = {"weightKg": (Decimal("99999.999"), 3),
                 "temperatureC": (Decimal("999.99"), 2),
                 "heartRate": (Decimal("2147483647"), 0),
                 "respiratoryRate": (Decimal("2147483647"), 0)}
NUMBER_LABELS = {"weightKg": "Cân nặng", "temperatureC": "Nhiệt độ",
                 "heartRate": "Nhịp tim", "respiratoryRate": "Nhịp thở"}


def validate_record(form, complete=False):
    data, errors = {}, {}
    for field, label in TEXT_FIELDS.items():
        value = form.get(field, "").strip()
        if len(value) > 10000:
            errors[field] = f"{label} không được quá 10.000 ký tự."
        data[field] = value or None
    required = ("chiefComplaint", "clinicalExamination", "finalDiagnosis") if complete else ("chiefComplaint",)
    for field in required:
        if not data[field]:
            errors[field] = f"Vui lòng nhập {TEXT_FIELDS[field]}."
    for field, (maximum, places) in NUMBER_FIELDS.items():
        raw = form.get(field, "").strip()
        data[field] = None
        if not raw:
            continue
        try:
            if len(raw) > 40:
                raise ValueError
            value = Decimal(raw)
            if not value.is_finite() or value <= 0 or value > maximum:
                raise ValueError
            # Reject precision that PostgreSQL would silently round.
            if value != value.quantize(Decimal(1).scaleb(-places)):
                raise ValueError
            data[field] = int(value) if places == 0 else value
        except (InvalidOperation, ValueError, OverflowError):
            errors[field] = f"{NUMBER_LABELS[field]} phải là số dương hợp lệ, tối đa {places} chữ số thập phân."
    record_weight = form.get("recordWeight") == "1"
    if record_weight and data["weightKg"] is None:
        errors["weightKg"] = "Nhập cân nặng để ghi nhận một lần đo."
    return data, record_weight, errors


def form_values(visit):
    return {field: "" if getattr(visit, field) is None else str(getattr(visit, field))
            for field in (*TEXT_FIELDS, *NUMBER_FIELDS)}


def revision_digest(visit):
    values = form_values(visit)
    for field in NUMBER_FIELDS:
        if values[field]:
            values[field] = str(Decimal(values[field]).normalize())
    stamp = visit.updatedAt
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    values.update(visitID=visit.visitID, petID=visit.petID, appointmentID=visit.appointmentID,
                  status=visit.status, updatedAt=stamp.astimezone(timezone.utc).isoformat())
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def revision_token(visit):
    return URLSafeSerializer(current_app.secret_key, salt="vet-medical-revision").dumps(
        {"visitID": visit.visitID, "digest": revision_digest(visit)})


def validate_revision(visit, token):
    try:
        if not token or len(token) > 1000:
            raise BadSignature("Missing revision")
        payload = URLSafeSerializer(current_app.secret_key, salt="vet-medical-revision").loads(token)
        if not isinstance(payload, dict) or payload.get("visitID") != visit.visitID:
            raise BadSignature("Wrong visit")
    except BadSignature:
        abort(400, description="Phiên bản bệnh án không hợp lệ. Vui lòng mở lại bệnh án.")
    if payload.get("digest") != revision_digest(visit):
        abort(409, description="Bệnh án đã thay đổi ở một cửa sổ khác. Mở lại để kiểm tra trước khi lưu.")


def lock_record(visit_id, vet_id, require_primary=True, allow_completed=False):
    # allow_completed is reserved for follow-up administration. Clinical writers
    # retain the default: a completed medical record is never editable.
    appointment_id = db.session.scalar(db.select(MedicalVisit.appointmentID).where(
        MedicalVisit.visitID == visit_id, visit_scope(vet_id)))
    if appointment_id is None:
        visible = db.session.scalar(db.select(MedicalVisit.visitID).where(
            MedicalVisit.visitID == visit_id, visit_scope(vet_id)))
        if visible is None:
            abort(404)
        abort(409, description="Ca chưa liên kết lượt tiếp nhận; cần kiểm tra dữ liệu trước khi cập nhật.")
    appointment = db.session.scalar(db.select(Appointment).where(Appointment.appointmentID == appointment_id)
        .with_for_update(of=Appointment).execution_options(populate_existing=True))
    queue = db.session.scalar(db.select(QueueEntry).where(QueueEntry.appointmentID == appointment_id)
        .with_for_update(of=QueueEntry).execution_options(populate_existing=True))
    visit = db.session.scalar(db.select(MedicalVisit).where(MedicalVisit.visitID == visit_id)
        .with_for_update(of=MedicalVisit).execution_options(populate_existing=True))
    own = db.session.scalar(db.select(VisitVeterinarian).where(
        VisitVeterinarian.visitID == visit_id, VisitVeterinarian.veterinarianID == vet_id)
        .with_for_update().execution_options(populate_existing=True))
    if visit is None or own is None:
        abort(404)
    if require_primary and own.participationRole != "PRIMARY":
        abort(403, description="Chỉ bác sĩ chính được cập nhật và hoàn tất bệnh án.")
    if not require_primary and appointment is not None:
        primary = db.session.scalar(db.select(VisitVeterinarian.veterinarianID).where(
            VisitVeterinarian.visitID == visit_id, VisitVeterinarian.participationRole == "PRIMARY"))
        if primary != appointment.veterinarianID:
            abort(409, description="Phân công bác sĩ chính không đồng bộ; cần kiểm tra trước khi thực hiện.")
    open_state = (appointment is not None and appointment.status == "IN_PROGRESS"
        and visit.status == "DRAFT" and queue is not None and queue.status == "IN_SERVICE"
        and queue.startedAt is not None and queue.completedAt is None)
    completed_state = (allow_completed and appointment is not None and appointment.status == "COMPLETED"
        and visit.status == "COMPLETED" and visit.completedAt is not None
        and queue is not None and queue.status == "DONE" and queue.startedAt is not None
        and queue.completedAt is not None)
    if (appointment is None or (require_primary and appointment.veterinarianID != vet_id)
            or appointment.petID != visit.petID or visit.appointmentID != appointment_id
            or not (open_state or completed_state)):
        abort(409, description="Ca khám đã khóa hoặc trạng thái lượt/hàng đợi không phù hợp.")
    return visit, appointment, queue


def ensure_diagnostics_resolved(visit_id):
    # Phase 4 is optional at present. Do not require SQL 11 just to finish a basic visit.
    if not inspect(db.session.connection()).has_table("diagnosticOrders", schema="medical"):
        return
    orders = db.table("diagnosticOrders", db.column("visitID"), db.column("status"), schema="medical")
    rows = db.session.scalars(db.select(orders.c.status).where(orders.c.visitID == visit_id).with_for_update()).all()
    if any(status not in ("COMPLETED", "CANCELLED") for status in rows):
        abort(409, description="Còn chỉ định chưa có kết quả hoặc chưa hủy. Vui lòng xử lý trước khi hoàn tất.")


def save_record(visit_id, vet_id, staff_id, form, complete=False):
    visit, appointment, queue = lock_record(visit_id, vet_id)
    validate_revision(visit, form.get("revision", ""))
    data, record_weight, errors = validate_record(form, complete)
    if errors:
        db.session.rollback()
        return None, errors
    if complete:
        ensure_diagnostics_resolved(visit_id)
    now = datetime.now(timezone.utc)
    for field, value in data.items():
        setattr(visit, field, value)  # Explicit allowlist only, never arbitrary request keys.
    visit.updatedAt = now
    if record_weight:
        db.session.add(PetWeightHistory(petID=visit.petID, weightKg=data["weightKg"],
            measuredAt=now, recordedByStaffID=staff_id))
    if complete:
        visit.status = "COMPLETED"
        visit.completedAt = now
        appointment.status = "COMPLETED"
        queue.status = "DONE"
        queue.completedAt = now
    saved_id = visit.visitID
    db.session.commit()
    return saved_id, {}
