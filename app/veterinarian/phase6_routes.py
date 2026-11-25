from functools import wraps

from flask import abort, flash, g, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import inspect

from app.extensions import db
from app.models import Appointment, ClinicStaff, FollowUp, MedicalVisit, User, VaccinationRecord, Vaccine, Veterinarian, VisitVeterinarian
from app.veterinarian import veterinarian_bp
from app.veterinarian.csrf import validate_csrf
from app.veterinarian.medical_records import revision_token
from app.veterinarian.phase2_routes import paginate, phase2_ready
from app.veterinarian.phase3_routes import accessible_visit, phase3_page, primary_editable
from app.veterinarian.policies import veterinarian_required
from app.veterinarian.preventive_care import (FOLLOW_UP_STATUSES, active_doctors_query,
    follow_token, follow_values, procedure_allowed, save_follow_up, save_vaccination)
from app.veterinarian.validation import today
from app.veterinarian.visits import visit_scope


def care_ready(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        inspector = inspect(db.session.connection())
        if any(not inspector.has_table(name, schema="medical")
               for name in ("vaccines", "vaccinationRecords", "followUps")):
            return render_template("veterinarian/care_setup.html"), 503
        return view(*args, **kwargs)
    return wrapped


@veterinarian_bp.context_processor
def preventive_context():
    return {"follow_up_statuses": FOLLOW_UP_STATUSES}


def primary(visit):
    own = db.session.get(VisitVeterinarian, (visit.visitID, g.veterinarian.veterinarianID))
    return own is not None and own.participationRole == "PRIMARY"


def care_doctors(ids):
    if not ids:
        return {}
    return dict(db.session.execute(db.select(Veterinarian.veterinarianID, User.fullName)
        .join(ClinicStaff, ClinicStaff.staffID == Veterinarian.staffID)
        .join(User, User.userID == ClinicStaff.userID).where(Veterinarian.veterinarianID.in_(ids))).all())


def vaccination_history_query(context):
    # No records from another doctor's unfinished visit or after this context.
    visible = db.select(MedicalVisit.visitID).where(MedicalVisit.petID == context.petID,
        MedicalVisit.startedAt <= context.startedAt,
        db.or_(MedicalVisit.status == "COMPLETED", visit_scope(g.veterinarian.veterinarianID)))
    return VaccinationRecord.query.filter(VaccinationRecord.petID == context.petID,
        VaccinationRecord.vaccinationDate <= context.visitDate,
        db.or_(VaccinationRecord.visitID.in_(visible), VaccinationRecord.visitID.is_(None)))


@veterinarian_bp.get("/visits/<int:visit_id>/vaccinations")
@veterinarian_required("VACCINATION_RECORD_VIEW")
@phase2_ready
@phase3_page
@care_ready
def vaccinations(visit_id):
    visit = accessible_visit(visit_id)
    if request.args.get("history") == "1":
        if not current_user.has_permission("PET_HISTORY_VIEW_FOR_CARE"):
            abort(403)
        query = vaccination_history_query(visit)
        historical = True
    else:
        query = VaccinationRecord.query.filter_by(visitID=visit_id, petID=visit.petID)
        historical = False
    own = db.session.get(VisitVeterinarian, (visit_id, g.veterinarian.veterinarianID))
    pagination = paginate(query.order_by(VaccinationRecord.vaccinationDate.desc(), VaccinationRecord.vaccinationID.desc()))
    return render_template("veterinarian/vaccinations.html", visit=visit, historical=historical,
        pagination=pagination, doctor_names=care_doctors({row.veterinarianID for row in pagination.items}),
        can_create=own.participationRole in ("PRIMARY", "PROCEDURE") and visit.status == "DRAFT"
            and current_user.has_permission("VACCINATION_RECORD_CREATE"))


@veterinarian_bp.route("/visits/<int:visit_id>/vaccinations/create", methods=["GET", "POST"])
@veterinarian_required("VACCINATION_RECORD_CREATE")
@phase2_ready
@phase3_page
@care_ready
def vaccination_create(visit_id):
    visit = accessible_visit(visit_id)
    procedure_allowed(visit_id, g.veterinarian.veterinarianID)
    if visit.status != "DRAFT" or visit.appointment is None or visit.appointment.status != "IN_PROGRESS":
        abort(409, description="Ca đã chốt hoặc chưa ở trạng thái đang khám.")
    errors = {}
    if request.method == "POST":
        validate_csrf()
        target = (url_for("veterinarian.vaccinations", visit_id=visit_id)
                  if current_user.has_permission("VACCINATION_RECORD_VIEW") else url_for("main.home"))
        saved, errors = save_vaccination(visit_id, g.veterinarian.veterinarianID, request.form)
        if saved:
            flash("Đã ghi nhận tiêm phòng.", "success")
            return redirect(target, code=303)
        values, revision = request.form, request.form.get("revision", "")
    else:
        values, revision = {"vaccinationDate": visit.visitDate.isoformat()}, revision_token(visit)
    return render_template("veterinarian/vaccination_create.html", visit=visit, errors=errors,
        form_data=values, revision=revision, vaccines=Vaccine.query.filter_by(isActive=True).order_by(Vaccine.name).all()), (422 if errors else 200)


@veterinarian_bp.get("/visits/<int:visit_id>/follow-ups")
@veterinarian_required("FOLLOW_UP_VIEW")
@phase2_ready
@phase3_page
@care_ready
def follow_ups(visit_id):
    visit = accessible_visit(visit_id)
    status = request.args.get("status", "")
    if status and status not in FOLLOW_UP_STATUSES:
        abort(400)
    query = FollowUp.query.filter_by(visitID=visit_id, petID=visit.petID)
    if status:
        query = query.filter_by(status=status)
    pagination = paginate(query.order_by(FollowUp.scheduledDate.desc(), FollowUp.followUpID.desc()))
    return render_template("veterinarian/follow_ups.html", visit=visit, primary=primary(visit),
        doctor_names=care_doctors({row.veterinarianID for row in pagination.items if row.veterinarianID}),
        selected_status=status, day=today(), pagination=pagination)


def follow_editor(visit, row=None):
    if not primary(visit):
        abort(403, description="Chỉ bác sĩ chính được quản lý yêu cầu tái khám.")
    if row is None or visit.status == "DRAFT":
        primary_editable(visit)
    elif visit.status != "COMPLETED":
        abort(409)
    if row is not None and row.status in ("COMPLETED", "CANCELLED"):
        abort(409, description="Yêu cầu đã hoàn tất/hủy, không thể sửa.")
    errors = {}
    if request.method == "POST":
        validate_csrf()
        target = (url_for("veterinarian.follow_ups", visit_id=visit.visitID)
                  if current_user.has_permission("FOLLOW_UP_VIEW") else url_for("main.home"))
        saved, errors = save_follow_up(visit.visitID, g.veterinarian.veterinarianID,
            request.form, row.followUpID if row else None)
        if saved:
            flash("Đã lưu yêu cầu tái khám. Lịch hẹn và thông báo được theo dõi riêng.", "success")
            return redirect(target, code=303)
        values, revision = request.form, request.form.get("revision", "")
    else:
        values = follow_values(row) if row else {}
        revision = follow_token(row) if row else revision_token(visit)
    candidates = []
    if row:
        candidates = Appointment.query.filter(Appointment.petID == visit.petID,
            Appointment.appointmentID != visit.appointmentID,
            Appointment.scheduledDate > visit.visitDate).order_by(Appointment.scheduledDate.desc(), Appointment.appointmentID.desc()).limit(100).all()
        if row.appointmentID and all(item.appointmentID != row.appointmentID for item in candidates):
            existing = db.session.get(Appointment, row.appointmentID)
            if existing and existing.petID == visit.petID:
                candidates.append(existing)
    doctors = db.session.execute(active_doctors_query().order_by(User.fullName)).all()
    return render_template("veterinarian/follow_up_edit.html", visit=visit, follow_up=row,
        form_data=values, revision=revision, errors=errors, doctors=doctors, doctor_ids={doctor.veterinarianID for doctor, _ in doctors},
        candidates=candidates), (422 if errors else 200)


@veterinarian_bp.route("/visits/<int:visit_id>/follow-ups/create", methods=["GET", "POST"])
@veterinarian_required("FOLLOW_UP_CREATE")
@phase2_ready
@phase3_page
@care_ready
def follow_up_create(visit_id):
    return follow_editor(accessible_visit(visit_id))


@veterinarian_bp.route("/follow-ups/<int:follow_id>/edit", methods=["GET", "POST"])
@veterinarian_required("FOLLOW_UP_UPDATE")
@phase2_ready
@phase3_page
@care_ready
def follow_up_edit(follow_id):
    row = db.session.get(FollowUp, follow_id)
    if row is None:
        abort(404)
    visit = accessible_visit(row.visitID)
    if row.petID != visit.petID:
        abort(409, description="Pet của yêu cầu không khớp ca khám.")
    return follow_editor(visit, row)
