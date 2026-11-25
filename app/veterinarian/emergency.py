"""Emergency admission policy using existing clinic/booking tables only."""
from datetime import datetime, timezone

from app.extensions import db
from app.models import (Appointment, ClinicStaff, Service, ServiceSpecialty, Specialty,
    StaffLeave, User, Veterinarian, VeterinarianService, VeterinarianSpecialty, WorkingSchedule)
from app.veterinarian.validation import LOCAL_TZ


def utc_now():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def lock_start_capacity(appointment, vet_id):
    """All new starts coordinate on doctor and pet, including routine cases."""
    from app.models import Pet
    db.session.scalar(db.select(Veterinarian.veterinarianID).where(Veterinarian.veterinarianID == vet_id)
        .with_for_update())
    db.session.scalar(db.select(Pet.petID).where(Pet.petID == appointment.petID).with_for_update())
    active_emergency = db.session.scalar(db.select(Appointment.appointmentID).where(
        db.or_(Appointment.veterinarianID == vet_id, Appointment.petID == appointment.petID),
        Appointment.status == "IN_PROGRESS", Appointment.appointmentType == "EMERGENCY",
        Appointment.appointmentID != appointment.appointmentID).limit(1))
    return active_emergency is not None


def emergency_issue(appointment, vet_id, lock=False):
    """Return an explanation when a NEW emergency admission must be refused.

    isEmergencyLead is a coordination preference, not permission to take another
    doctor's case. Assignment + matching active specialty are always required.
    Continuing an already started case is handled by start_visit before this check.
    """
    now = utc_now()
    local = now.astimezone(LOCAL_TZ)
    if (appointment.veterinarianID != vet_id or appointment.bookingSource != "RECEPTION"
            or appointment.priority != "URGENT" or appointment.scheduledDate != local.date()
            or appointment.checkedInAt is None
            or aware(appointment.checkedInAt) > now
            or aware(appointment.checkedInAt).astimezone(LOCAL_TZ).date() != local.date()):
        return "Cấp cứu phải được lễ tân tiếp nhận trực tiếp trong ngày và phân công đúng bác sĩ."
    identity = db.select(Veterinarian).join(ClinicStaff, ClinicStaff.staffID == Veterinarian.staffID)
    identity = identity.join(User, User.userID == ClinicStaff.userID).where(
        Veterinarian.veterinarianID == vet_id, Veterinarian.status == "ACTIVE",
        ClinicStaff.status == "ACTIVE", ClinicStaff.staffType == "VETERINARIAN", User.status == "ACTIVE")
    if lock:
        identity = identity.with_for_update(of=(Veterinarian, ClinicStaff, User))
    vet = db.session.scalar(identity.execution_options(populate_existing=True))
    if vet is None:
        return "Hồ sơ bác sĩ/nhân viên không còn hoạt động."
    service_query = db.select(Service).where(Service.serviceID == appointment.serviceID)
    schedule_query = db.select(WorkingSchedule).where(WorkingSchedule.veterinarianID == vet_id,
        WorkingSchedule.workDate == local.date())
    if lock:
        service_query = service_query.with_for_update(of=Service)
        schedule_query = schedule_query.with_for_update(of=WorkingSchedule)
    service = db.session.scalar(service_query.execution_options(populate_existing=True))
    schedule = db.session.scalar(schedule_query.execution_options(populate_existing=True))
    if (service is None or service.status != "ACTIVE" or not service.isEmergency
            or service.isBookable or not service.requiresVeterinarian):
        return "Dịch vụ tiếp nhận cấp cứu phải đang hoạt động, đánh dấu cấp cứu và không đặt online."
    if schedule is None or schedule.status != "AVAILABLE":
        return "Chưa có lịch làm việc AVAILABLE của bác sĩ hôm nay; cần quản lý/lễ tân kiểm tra phân công."
    clock = local.time().replace(tzinfo=None)
    if not (schedule.morningStartTime <= clock < schedule.morningEndTime
            or schedule.afternoonStartTime <= clock < schedule.afternoonEndTime):
        return "Chỉ nhận ca cấp cứu mới trong giờ làm việc đã được phân công, không trong giờ nghỉ/ngoài giờ."
    checkin_clock = aware(appointment.checkedInAt).astimezone(LOCAL_TZ).time().replace(tzinfo=None)
    if not (schedule.morningStartTime <= checkin_clock < schedule.morningEndTime
            or schedule.afternoonStartTime <= checkin_clock < schedule.afternoonEndTime):
        return "Thời điểm tiếp nhận cấp cứu không nằm trong giờ làm; cần lễ tân kiểm tra dữ liệu."
    leave_query = db.select(StaffLeave.leaveID).where(StaffLeave.staffID == vet.staffID,
        StaffLeave.status == "APPROVED", StaffLeave.startAt <= now, StaffLeave.endAt > now)
    if lock:
        leave_query = leave_query.with_for_update()
    if db.session.scalar(leave_query.limit(1)) is not None:
        return "Bác sĩ đang trong khoảng nghỉ đã duyệt; cần lễ tân/quản lý phân công lại."
    specialty_query = db.select(Specialty.specialtyID).join(ServiceSpecialty,
        ServiceSpecialty.specialtyID == Specialty.specialtyID).join(VeterinarianSpecialty,
        VeterinarianSpecialty.specialtyID == Specialty.specialtyID).where(Specialty.isActive.is_(True),
        ServiceSpecialty.serviceID == service.serviceID, VeterinarianSpecialty.veterinarianID == vet_id)
    if lock:
        specialty_query = specialty_query.with_for_update(of=(Specialty, ServiceSpecialty, VeterinarianSpecialty))
    if db.session.scalar(specialty_query.limit(1)) is None:
        return "Bác sĩ chưa có chuyên môn hoạt động phù hợp dịch vụ cấp cứu."
    capability_query = db.select(VeterinarianService).where(VeterinarianService.veterinarianID == vet_id,
        VeterinarianService.serviceID == service.serviceID)
    if lock:
        capability_query = capability_query.with_for_update()
    capability = db.session.scalar(capability_query.execution_options(populate_existing=True))
    if capability is not None and not capability.isActive:
        return "Khả năng thực hiện dịch vụ này của bác sĩ đã bị tắt."
    # The active vet row serializes starts through this policy. Do not silently
    # abandon a case already in progress to accept a second emergency.
    busy = db.session.scalar(db.select(Appointment.appointmentID).where(
        db.or_(Appointment.veterinarianID == vet_id, Appointment.petID == appointment.petID),
        Appointment.status == "IN_PROGRESS",
        Appointment.appointmentID != appointment.appointmentID).limit(1))
    if busy is not None:
        return "Bác sĩ còn ca đang khám. Cần phối hợp lễ tân/quản lý, không tự đổi lịch hoặc bỏ ca đang thực hiện."
    return None


def coordination_candidates(appointment, actor_vet_id):
    """Read-only, own assigned future appointments; never reschedule/cancel here."""
    if appointment.veterinarianID != actor_vet_id:
        return []
    local = utc_now().astimezone(LOCAL_TZ)
    return Appointment.query.filter(Appointment.veterinarianID == actor_vet_id,
        Appointment.appointmentID != appointment.appointmentID,
        Appointment.scheduledDate == local.date(), Appointment.status.in_(("PENDING", "CONFIRMED")),
        db.or_(Appointment.endTime.is_(None), Appointment.endTime > local.time().replace(tzinfo=None))
    ).order_by(Appointment.startTime, Appointment.appointmentID).limit(50).all()
