from functools import wraps

from flask import abort, current_app, flash, g, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.models import ClinicStaff, DiagnosticOrder, FollowUp, MedicalVisit, PetWeightHistory, Prescription, User, VaccinationRecord, Veterinarian, VisitVeterinarian
from app.veterinarian import veterinarian_bp
from app.veterinarian.csrf import validate_csrf
from app.veterinarian.medical_records import (NUMBER_LABELS, TEXT_FIELDS, form_values,
    revision_token, save_record)
from app.veterinarian.phase2_routes import paginate, phase2_ready, selected_day
from app.veterinarian.policies import veterinarian_required
from app.veterinarian.visits import visit_scope


def phase3_page(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            if not inspect(db.session.connection()).has_table("petWeightHistory", schema="medical"):
                return render_template("veterinarian/setup_required.html"), 503
            return view(*args, **kwargs)
        except HTTPException as exc:
            db.session.rollback()
            return render_template("veterinarian/record_error.html", message=exc.description), exc.code
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Không thể xử lý bệnh án bác sĩ")
            return render_template("veterinarian/record_error.html",
                message="Không thể xử lý bệnh án lúc này. Thay đổi chưa được lưu, vui lòng thử lại."), 503
    return wrapped


def accessible_visit(visit_id):
    return MedicalVisit.query.filter(MedicalVisit.visitID == visit_id,
        visit_scope(g.veterinarian.veterinarianID)).first_or_404()


def primary_editable(visit):
    own = db.session.get(VisitVeterinarian, (visit.visitID, g.veterinarian.veterinarianID))
    if own is None or own.participationRole != "PRIMARY":
        abort(403, description="Chỉ bác sĩ chính được cập nhật bệnh án.")
    appointment = visit.appointment
    queue = None if appointment is None else appointment.queueEntry
    if (visit.status != "DRAFT" or appointment is None or appointment.status != "IN_PROGRESS"
        or appointment.veterinarianID != g.veterinarian.veterinarianID
        or appointment.petID != visit.petID or queue is None or queue.status != "IN_SERVICE"
        or queue.startedAt is None or queue.completedAt is not None):
        abort(409, description="Bệnh án đã khóa hoặc lượt khám chưa ở trạng thái đang khám.")


def editor(visit, values, revision, errors=None):
    return render_template("veterinarian/visit_edit.html", visit=visit,
        form_data=values, revision=revision, errors=errors or {},
        text_fields=TEXT_FIELDS, number_labels=NUMBER_LABELS)


def after_save(visit_id, endpoint):
    return redirect(url_for(endpoint, **({"visit_id": visit_id} if endpoint != "main.home" else {})), code=303)


def history_doctors(visits):
    ids = [visit.visitID for visit in visits]
    if not ids:
        return {}
    rows = db.session.execute(db.select(VisitVeterinarian.visitID, User.fullName)
        .join(Veterinarian, Veterinarian.veterinarianID == VisitVeterinarian.veterinarianID)
        .join(ClinicStaff, ClinicStaff.staffID == Veterinarian.staffID)
        .join(User, User.userID == ClinicStaff.userID)
        .where(VisitVeterinarian.visitID.in_(ids), VisitVeterinarian.participationRole == "PRIMARY"))
    return dict(rows.all())


@veterinarian_bp.route("/visits/<int:visit_id>/edit", methods=["GET", "POST"])
@veterinarian_required("VISIT_UPDATE_ASSIGNED")
@phase2_ready
@phase3_page
def visit_edit(visit_id):
    visit = accessible_visit(visit_id)
    if request.method == "GET":
        primary_editable(visit)
        return editor(visit, form_values(visit), revision_token(visit))
    validate_csrf()
    target = "veterinarian.visit_detail" if current_user.has_permission("VISIT_VIEW_ASSIGNED") else "main.home"
    saved, errors = save_record(visit_id, g.veterinarian.veterinarianID, g.vet_staff.staffID, request.form)
    if errors:
        return editor(visit, request.form, request.form.get("revision", ""), errors), 422
    flash("Đã lưu bệnh án nháp.", "success")
    return after_save(saved, target)


@veterinarian_bp.post("/visits/<int:visit_id>/complete")
@veterinarian_required("VISIT_COMPLETE")
@phase2_ready
@phase3_page
def visit_complete(visit_id):
    # Completion submits the form as well, so writing permission is also required.
    if not current_user.has_permission("VISIT_UPDATE_ASSIGNED"):
        abort(403)
    validate_csrf()
    visit = accessible_visit(visit_id)
    target = "veterinarian.visit_detail" if current_user.has_permission("VISIT_VIEW_ASSIGNED") else "main.home"
    saved, errors = save_record(visit_id, g.veterinarian.veterinarianID, g.vet_staff.staffID,
                               request.form, complete=True)
    if errors:
        return editor(visit, request.form, request.form.get("revision", ""), errors), 422
    flash("Đã hoàn tất ca khám. Thanh toán được theo dõi riêng.", "success")
    return after_save(saved, target)


@veterinarian_bp.get("/visits/<int:visit_id>/history")
@veterinarian_required("PET_HISTORY_VIEW_FOR_CARE")
@phase2_ready
@phase3_page
def pet_history(visit_id):
    context = accessible_visit(visit_id)
    day = selected_day()
    query = MedicalVisit.query.filter(MedicalVisit.petID == context.petID,
        MedicalVisit.visitID != context.visitID,
        MedicalVisit.startedAt < context.startedAt,
        db.or_(MedicalVisit.status == "COMPLETED", visit_scope(g.veterinarian.veterinarianID)))
    if day:
        query = query.filter(MedicalVisit.visitDate == day)
    pagination = paginate(query.order_by(MedicalVisit.visitDate.desc(), MedicalVisit.visitID.desc()))
    weights = PetWeightHistory.query.filter_by(petID=context.petID).order_by(
        PetWeightHistory.measuredAt.desc(), PetWeightHistory.weightID.desc()).limit(50).all()
    return render_template("veterinarian/pet_history.html", context=context,
        pagination=pagination, weights=weights, day=day, doctor_names=history_doctors(pagination.items))


@veterinarian_bp.get("/visits/<int:visit_id>/history/<int:history_id>")
@veterinarian_required("PET_HISTORY_VIEW_FOR_CARE")
@phase2_ready
@phase3_page
def pet_history_detail(visit_id, history_id):
    context = accessible_visit(visit_id)
    history = MedicalVisit.query.filter(MedicalVisit.visitID == history_id,
        MedicalVisit.petID == context.petID,
        MedicalVisit.startedAt < context.startedAt,
        db.or_(MedicalVisit.status == "COMPLETED", visit_scope(g.veterinarian.veterinarianID))).first_or_404()
    diagnostics = []
    if (current_user.has_permission("DIAGNOSTIC_ORDER_VIEW")
            and inspect(db.session.connection()).has_table("diagnosticOrders", schema="medical")):
        diagnostics = DiagnosticOrder.query.filter_by(visitID=history_id).order_by(
            DiagnosticOrder.orderedAt.desc()).limit(100).all()
    prescriptions = []
    if (current_user.has_permission("PRESCRIPTION_VIEW")
            and all(inspect(db.session.connection()).has_table(name, schema="medical")
                    for name in ("prescriptions", "prescriptionItems"))):
        prescriptions = Prescription.query.filter_by(visitID=history_id).order_by(
            Prescription.prescribedAt.desc()).limit(100).all()
    vaccinations, follow_ups = [], []
    inspector = inspect(db.session.connection())
    if (current_user.has_permission("VACCINATION_RECORD_VIEW")
            and all(inspector.has_table(name, schema="medical") for name in ("vaccines", "vaccinationRecords"))):
        vaccinations = VaccinationRecord.query.filter_by(visitID=history_id, petID=history.petID).order_by(
            VaccinationRecord.vaccinationDate.desc(), VaccinationRecord.vaccinationID.desc()).limit(100).all()
    if current_user.has_permission("FOLLOW_UP_VIEW") and inspector.has_table("followUps", schema="medical"):
        follow_ups = FollowUp.query.filter_by(visitID=history_id, petID=history.petID).order_by(
            FollowUp.scheduledDate.desc(), FollowUp.followUpID.desc()).limit(100).all()
    return render_template("veterinarian/history_detail.html", context=context, visit=history,
        doctor_name=history_doctors([history]).get(history.visitID), diagnostics=diagnostics,
        prescriptions=prescriptions, vaccinations=vaccinations, follow_ups=follow_ups)
