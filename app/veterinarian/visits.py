"""Phase 2 queries and transactional admission; treatment editing belongs to phase 3."""
from datetime import datetime, timezone
from uuid import uuid4

from flask import abort
from sqlalchemy import exists, or_

from app.extensions import db
from app.models import Appointment, MedicalVisit, QueueEntry, VisitVeterinarian
from app.veterinarian.validation import LOCAL_TZ
from app.veterinarian.emergency import emergency_issue, lock_start_capacity

APPOINTMENT_STATUSES = {"PENDING": "Chờ xác nhận", "CONFIRMED": "Đã xác nhận",
    "CHECKED_IN": "Đã đến phòng khám", "IN_PROGRESS": "Đang khám",
    "COMPLETED": "Hoàn tất", "CANCELLED": "Đã hủy", "NO_SHOW": "Không đến"}
APPOINTMENT_TYPES = {"SCHEDULED": "Đặt trước", "WALK_IN": "Đến trực tiếp", "EMERGENCY": "Cấp cứu"}


def appointment_scope(vet_id):
    participation = exists(db.select(1).select_from(MedicalVisit)
        .join(VisitVeterinarian, VisitVeterinarian.visitID == MedicalVisit.visitID)
        .where(MedicalVisit.appointmentID == Appointment.appointmentID,
               VisitVeterinarian.veterinarianID == vet_id))
    return or_(Appointment.veterinarianID == vet_id, participation)


def visit_scope(vet_id):
    return MedicalVisit.participants.any(VisitVeterinarian.veterinarianID == vet_id)


def appointment_query(vet_id):
    return Appointment.query.filter(appointment_scope(vet_id))


def start_visit(appointment_id, vet_id):
    """Lock in appointment → queue → visit → participants order; retry is idempotent."""
    appointment = db.session.scalar(db.select(Appointment).where(
        Appointment.appointmentID == appointment_id, Appointment.veterinarianID == vet_id
    ).with_for_update(of=Appointment).execution_options(populate_existing=True))
    if appointment is None:
        abort(404)
    if appointment.status not in ("CHECKED_IN", "IN_PROGRESS"):
        abort(409, description="Chỉ nhận lượt đã được lễ tân xác nhận đến phòng khám.")
    queue = db.session.scalar(db.select(QueueEntry).where(QueueEntry.appointmentID == appointment_id)
        .with_for_update(of=QueueEntry).execution_options(populate_existing=True))
    if queue is None or appointment.checkedInAt is None:
        abort(409, description="Lượt khám chưa có đủ dữ liệu check-in từ lễ tân.")
    visit = db.session.scalar(db.select(MedicalVisit).where(MedicalVisit.appointmentID == appointment_id)
        .with_for_update(of=MedicalVisit).execution_options(populate_existing=True))
    participants = [] if visit is None else list(db.session.scalars(db.select(VisitVeterinarian)
        .where(VisitVeterinarian.visitID == visit.visitID).with_for_update()
        .execution_options(populate_existing=True)))
    primary = next((p for p in participants if p.participationRole == "PRIMARY"), None)
    own = next((p for p in participants if p.veterinarianID == vet_id), None)
    if visit is not None and (visit.petID != appointment.petID or visit.status != "DRAFT"):
        abort(409, description="Ca khám hiện có không phù hợp hoặc đã hoàn tất.")
    if primary is not None and primary.veterinarianID != vet_id:
        abort(409, description="Ca khám đang có bác sĩ chính khác phụ trách.")
    if own is not None and own.participationRole != "PRIMARY":
        abort(403, description="Bác sĩ hỗ trợ không được tự nhận quyền bác sĩ chính.")
    if appointment.status == "IN_PROGRESS":
        if visit is None or primary is None or queue.status != "IN_SERVICE" or queue.startedAt is None:
            abort(409, description="Trạng thái ca khám không đồng bộ; cần kiểm tra trước khi tiếp tục.")
        db.session.commit()  # Release locks without resetting the original start time.
        return visit
    if queue.status not in ("WAITING", "CALLED") or queue.startedAt is not None or queue.completedAt is not None:
        abort(409, description="Hàng đợi không còn ở trạng thái chờ khám.")
    if lock_start_capacity(appointment, vet_id):
        abort(409, description="Bác sĩ hoặc thú cưng còn ca cấp cứu đang khám. Cần phối hợp trước khi nhận ca mới.")
    if appointment.appointmentType == "EMERGENCY":
        if queue.queueDate != appointment.scheduledDate:
            abort(409, description="Ngày hàng đợi cấp cứu không khớp lượt tiếp nhận.")
        issue = emergency_issue(appointment, vet_id, lock=True)
        if issue:
            abort(409, description=issue)
    now = datetime.now(timezone.utc)
    if visit is None:
        reason = (appointment.reason or "").strip()
        if not reason:
            abort(409, description="Lịch hẹn chưa có lý do khám hợp lệ.")
        visit = MedicalVisit(appointmentID=appointment_id, petID=appointment.petID,
            visitDate=now.astimezone(LOCAL_TZ).date(), visitCode="VM" + uuid4().hex[:16].upper(),
            chiefComplaint=reason, status="DRAFT", startedAt=now)
        db.session.add(visit)
        db.session.flush()
    else:
        visit.startedAt = now
        visit.visitDate = now.astimezone(LOCAL_TZ).date()
    if primary is None:
        db.session.add(VisitVeterinarian(visitID=visit.visitID, veterinarianID=vet_id,
                                       participationRole="PRIMARY", assignedAt=now))
    appointment.status = "IN_PROGRESS"
    queue.status = "IN_SERVICE"
    queue.startedAt = now
    db.session.commit()
    return visit
