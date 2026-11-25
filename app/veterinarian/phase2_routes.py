from datetime import date
from functools import wraps

from flask import abort, current_app, g, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import inspect, or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.models import MedicalVisit, Pet, QueueEntry, Service, VisitVeterinarian
from app.veterinarian import veterinarian_bp
from app.veterinarian.csrf import validate_csrf
from app.veterinarian.policies import veterinarian_required
from app.veterinarian.validation import today
from app.veterinarian.emergency import coordination_candidates, emergency_issue
from app.veterinarian.visits import (APPOINTMENT_STATUSES, APPOINTMENT_TYPES,
    appointment_query, start_visit, visit_scope)


def phase2_ready(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        inspector = inspect(db.engine)
        if any(not inspector.has_table(name, schema="medical")
               for name in ("medicalVisits", "visitVeterinarians")):
            return render_template("veterinarian/setup_required.html"), 503
        return view(*args, **kwargs)
    return wrapped


def selected_day(default=None):
    raw = request.args.get("date", default or "").strip()
    if not raw:
        return None
    try:
        day = date.fromisoformat(raw)
        if not 1900 <= day.year <= 9998:
            raise ValueError
        return day
    except ValueError:
        abort(400, description="Ngày không hợp lệ.")


def selected_type():
    value = request.args.get("type", "")
    if value and value not in APPOINTMENT_TYPES:
        abort(400, description="Loại lượt khám không hợp lệ.")
    return value


def paginate(query):
    return query.paginate(page=max(request.args.get("page", 1, type=int) or 1, 1),
                          per_page=10, error_out=False)


def service_names(pagination):
    ids = {row.serviceID for row in pagination.items}
    if not ids:
        return {}
    return dict(db.session.execute(db.select(Service.serviceID, Service.name)
                                  .where(Service.serviceID.in_(ids))).all())


@veterinarian_bp.context_processor
def phase2_context():
    return {"appointment_statuses": APPOINTMENT_STATUSES, "appointment_types": APPOINTMENT_TYPES}


@veterinarian_bp.get("/appointments")
@veterinarian_required("APPOINTMENT_VIEW_ASSIGNED")
@phase2_ready
def appointments():
    from app.models import Appointment
    day = selected_day()
    status = request.args.get("status", "").strip()
    keyword = request.args.get("q", "").strip()[:100]
    if status and status not in APPOINTMENT_STATUSES:
        abort(400)
    query = appointment_query(g.veterinarian.veterinarianID).join(Pet)
    kind = selected_type()
    if kind:
        query = query.filter(Appointment.appointmentType == kind)
    if day:
        query = query.filter(Appointment.scheduledDate == day)
    if status:
        query = query.filter(Appointment.status == status)
    if keyword:
        query = query.filter(or_(Pet.name.ilike(f"%{keyword}%"),
            Pet.petCode.ilike(f"%{keyword}%"), Appointment.appointmentCode.ilike(f"%{keyword}%")))
    pagination = paginate(query.order_by(Appointment.scheduledDate.desc(), Appointment.startTime, Appointment.appointmentID))
    return render_template("veterinarian/appointments.html", pagination=pagination,
        day=day, selected_status=status, selected_type=kind, keyword=keyword, service_names=service_names(pagination))


@veterinarian_bp.get("/appointments/<int:appointment_id>")
@veterinarian_required("APPOINTMENT_VIEW_ASSIGNED")
@phase2_ready
def appointment_detail(appointment_id):
    from app.models import Appointment
    appointment = appointment_query(g.veterinarian.veterinarianID).filter(
        Appointment.appointmentID == appointment_id).first_or_404()
    visit = db.session.scalar(db.select(MedicalVisit).where(MedicalVisit.appointmentID == appointment_id))
    primary = None if visit is None else db.session.scalar(db.select(VisitVeterinarian).where(
        VisitVeterinarian.visitID == visit.visitID, VisitVeterinarian.participationRole == "PRIMARY"))
    own = None if visit is None else db.session.get(VisitVeterinarian, (visit.visitID, g.veterinarian.veterinarianID))
    queue = appointment.queueEntry
    can_start = (current_user.has_permission("VISIT_START")
        and appointment.veterinarianID == g.veterinarian.veterinarianID
        and appointment.status == "CHECKED_IN" and appointment.checkedInAt is not None
        and queue is not None and queue.status in ("WAITING", "CALLED") and queue.startedAt is None
        and (visit is None or (visit.status == "DRAFT" and visit.petID == appointment.petID))
        and (primary is None or primary.veterinarianID == g.veterinarian.veterinarianID)
        and (own is None or own.participationRole == "PRIMARY"))
    # A newly assigned doctor may see appointment administration, not another doctor's visit.
    visible_visit = visit if own is not None else None
    issue = None
    if can_start and appointment.appointmentType == "EMERGENCY":
        issue = emergency_issue(appointment, g.veterinarian.veterinarianID)
        can_start = issue is None
    return render_template("veterinarian/appointment_detail.html", appointment=appointment,
        service=db.session.get(Service, appointment.serviceID), visit=visible_visit, can_start=can_start,
        emergency_issue=issue)


@veterinarian_bp.get("/queue")
@veterinarian_required("QUEUE_VIEW_ASSIGNED")
@phase2_ready
def queue():
    from app.models import Appointment
    day = selected_day(today().isoformat()) or today()
    query = appointment_query(g.veterinarian.veterinarianID).join(QueueEntry).filter(
        Appointment.status == "CHECKED_IN", QueueEntry.queueDate == day,
        QueueEntry.status.in_(("WAITING", "CALLED")))
    kind = selected_type()
    if kind:
        query = query.filter(Appointment.appointmentType == kind)
    pagination = paginate(query.order_by((Appointment.appointmentType == "EMERGENCY").desc(), (Appointment.priority == "URGENT").desc(),
        QueueEntry.queueNumber, QueueEntry.checkedInAt))
    return render_template("veterinarian/queue.html", pagination=pagination, day=day, selected_type=kind,
                           service_names=service_names(pagination))


@veterinarian_bp.post("/appointments/<int:appointment_id>/start")
@veterinarian_required("VISIT_START")
@phase2_ready
def appointment_start(appointment_id):
    validate_csrf()
    try:
        visit = start_visit(appointment_id, g.veterinarian.veterinarianID)
    except HTTPException:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Không thể bắt đầu ca khám")
        abort(503, description="Không thể bắt đầu ca khám. Chưa lưu thay đổi; vui lòng thử lại.")
    if current_user.has_permission("VISIT_VIEW_ASSIGNED"):
        return redirect(url_for("veterinarian.visit_detail", visit_id=visit.visitID), code=303)
    if current_user.has_permission("APPOINTMENT_VIEW_ASSIGNED"):
        return redirect(url_for("veterinarian.appointment_detail", appointment_id=appointment_id), code=303)
    return redirect(url_for("main.home"), code=303)


@veterinarian_bp.get("/visits")
@veterinarian_required("VISIT_VIEW_ASSIGNED")
@phase2_ready
def visits():
    day = selected_day()
    status = request.args.get("status", "")
    if status and status not in ("DRAFT", "COMPLETED"):
        abort(400)
    query = MedicalVisit.query.filter(visit_scope(g.veterinarian.veterinarianID))
    if day:
        query = query.filter(MedicalVisit.visitDate == day)
    if status:
        query = query.filter(MedicalVisit.status == status)
    return render_template("veterinarian/visits.html", pagination=paginate(
        query.order_by(MedicalVisit.startedAt.desc(), MedicalVisit.visitID.desc())), day=day, selected_status=status)


@veterinarian_bp.get("/visits/<int:visit_id>")
@veterinarian_required("VISIT_VIEW_ASSIGNED")
@phase2_ready
def visit_detail(visit_id):
    visit = MedicalVisit.query.filter(MedicalVisit.visitID == visit_id,
        visit_scope(g.veterinarian.veterinarianID)).first_or_404()
    own = db.session.get(VisitVeterinarian, (visit_id, g.veterinarian.veterinarianID))
    coordination = []
    if (visit.appointment and visit.appointment.appointmentType == "EMERGENCY" and visit.status == "DRAFT"
            and own.participationRole == "PRIMARY" and current_user.has_permission("APPOINTMENT_VIEW_ASSIGNED")):
        coordination = coordination_candidates(visit.appointment, g.veterinarian.veterinarianID)
    return render_template("veterinarian/visit_detail.html", visit=visit, participation=own.participationRole,
        coordination=coordination)
