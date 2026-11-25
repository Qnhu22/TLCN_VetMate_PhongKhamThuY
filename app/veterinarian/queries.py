from app.extensions import db
from app.models import Appointment, Specialty, VeterinarianSpecialty, WorkingSchedule


def completed_diagnostic_services(visit_id):
    """Internal handoff to billing; caller must authorize access to the visit.

    Each order ID is a distinct performed service reference. This does not create
    invoices, choose historical prices or mark payment; billing owns those rules.
    """
    from app.models import DiagnosticOrder, Service
    return db.session.execute(db.select(
        DiagnosticOrder.diagnosticOrderID, DiagnosticOrder.visitID,
        DiagnosticOrder.serviceID, Service.name.label("serviceName"),
        DiagnosticOrder.performedAt, DiagnosticOrder.performedByStaffID
    ).join(Service, Service.serviceID == DiagnosticOrder.serviceID).where(
        DiagnosticOrder.visitID == visit_id, DiagnosticOrder.status == "COMPLETED"
    ).order_by(DiagnosticOrder.diagnosticOrderID)).mappings().all()


def schedules(vet_id, first, last):
    return db.session.scalars(db.select(WorkingSchedule).where(
        WorkingSchedule.veterinarianID == vet_id,
        WorkingSchedule.workDate.between(first, last)
    ).order_by(WorkingSchedule.workDate)).all()


def specialties(vet_id):
    return db.session.execute(db.select(Specialty.name, VeterinarianSpecialty.isPrimary)
        .join(VeterinarianSpecialty, Specialty.specialtyID == VeterinarianSpecialty.specialtyID)
        .where(VeterinarianSpecialty.veterinarianID == vet_id, Specialty.isActive.is_(True))
        .order_by(VeterinarianSpecialty.isPrimary.desc(), Specialty.name)).all()


def daily_stats(vet_id, day):
    rows = db.session.execute(db.select(Appointment.status, db.func.count())
        .where(Appointment.veterinarianID == vet_id, Appointment.scheduledDate == day)
        .group_by(Appointment.status)).all()
    counts = dict(rows)
    return {"total": sum(counts.values()), "waiting": counts.get("CHECKED_IN", 0),
            "in_progress": counts.get("IN_PROGRESS", 0), "completed": counts.get("COMPLETED", 0)}
