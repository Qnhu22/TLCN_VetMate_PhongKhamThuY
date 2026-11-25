from functools import wraps

from flask import abort, current_app, flash, g, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import inspect

from app.extensions import db
from app.models import Prescription, VisitVeterinarian
from app.veterinarian import veterinarian_bp
from app.veterinarian.csrf import validate_csrf
from app.veterinarian.medical_records import revision_token
from app.veterinarian.medicine_catalog import inventory_catalog_ready, medicine_options, product_labels
from app.veterinarian.phase2_routes import paginate, phase2_ready
from app.veterinarian.phase3_routes import accessible_visit, history_doctors, phase3_page, primary_editable
from app.veterinarian.phase4_routes import history_visit
from app.veterinarian.policies import veterinarian_required
from app.veterinarian.prescriptions import (ITEM_FIELDS, cancel_prescription, prescription_items,
    prescription_token, require_inventory_fk, save_prescription, submitted_items)


def prescriptions_ready(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        inspector = inspect(db.session.connection())
        if any(not inspector.has_table(name, schema="medical") for name in ("prescriptions", "prescriptionItems")):
            return render_template("veterinarian/prescription_setup.html"), 503
        if not inventory_catalog_ready():
            return render_template("veterinarian/prescription_setup.html"), 503
        return view(*args, **kwargs)
    return wrapped


def visible_prescription(rx_id):
    rx = db.session.get(Prescription, rx_id)
    if rx is None:
        abort(404)
    return rx, accessible_visit(rx.visitID)


def rx_target(rx_id):
    return url_for("veterinarian.prescription_detail", rx_id=rx_id) if current_user.has_permission("PRESCRIPTION_VIEW") else url_for("main.home")


@veterinarian_bp.get("/visits/<int:visit_id>/prescriptions")
@veterinarian_required("PRESCRIPTION_VIEW")
@phase2_ready
@phase3_page
@prescriptions_ready
def prescription_list(visit_id):
    visit = accessible_visit(visit_id)
    status = request.args.get("status", "")
    if status not in ("", "ACTIVE", "CANCELLED"):
        abort(400)
    query = Prescription.query.filter_by(visitID=visit_id)
    if status:
        query = query.filter_by(status=status)
    own = db.session.get(VisitVeterinarian, (visit_id, g.veterinarian.veterinarianID))
    return render_template("veterinarian/prescription_list.html", visit=visit, selected_status=status,
        primary=own.participationRole == "PRIMARY", pagination=paginate(query.order_by(
            Prescription.prescribedAt.desc(), Prescription.prescriptionID.desc())))


def rx_editor(visit, rx=None):
    primary_editable(visit)
    require_inventory_fk()
    if rx is not None:
        if rx.veterinarianID != g.veterinarian.veterinarianID:
            abort(403)
        if rx.status != "ACTIVE":
            abort(409, description="Đơn đã hủy, không thể sửa.")
        if not callable(current_app.config.get("VET_PRESCRIPTION_MUTATION_CHECK")):
            abort(409, description="Chưa có xác nhận chưa cấp phát; chưa thể sửa đơn thuốc.")
    errors = {}
    if request.method == "POST":
        validate_csrf()
        can_view = current_user.has_permission("PRESCRIPTION_VIEW")
        saved, errors = save_prescription(visit.visitID, g.veterinarian.veterinarianID,
            request.form, rx.prescriptionID if rx else None)
        if not errors:
            flash("Đã lưu đơn thuốc. Cấp phát và thanh toán được theo dõi riêng.", "success")
            return redirect(url_for("veterinarian.prescription_detail", rx_id=saved) if can_view else url_for("main.home"), code=303)
        rows = submitted_items(request.form)
        values, revision = request.form, request.form.get("revision", "")
    else:
        rows = [{key: str(getattr(row, key)) if getattr(row, key) is not None else "" for key in ITEM_FIELDS}
                for row in prescription_items(rx.prescriptionID)] if rx else []
        values = {"generalInstruction": rx.generalInstruction or ""} if rx else {}
        revision = prescription_token(rx) if rx else revision_token(visit)
    rows = rows or [{key: "" for key in ITEM_FIELDS}]
    selected = {int(row["productID"]) for row in rows if row["productID"].isdigit() and len(row["productID"]) < 19}
    keyword = request.args.get("q", "").strip()[:100]
    return render_template("veterinarian/prescription_edit.html", visit=visit, rx=rx, rows=rows,
        form_data=values, revision=revision, errors=errors, keyword=keyword,
        medicines=medicine_options(keyword, selected)), (422 if errors else 200)


@veterinarian_bp.route("/visits/<int:visit_id>/prescriptions/create", methods=["GET", "POST"])
@veterinarian_required("PRESCRIPTION_CREATE")
@phase2_ready
@phase3_page
@prescriptions_ready
def prescription_create(visit_id):
    return rx_editor(accessible_visit(visit_id))


def rx_detail(rx, visit, historical=False, context=None):
    rows = prescription_items(rx.prescriptionID)
    own = db.session.get(VisitVeterinarian, (visit.visitID, g.veterinarian.veterinarianID))
    mutable = (not historical and own is not None and own.participationRole == "PRIMARY"
        and rx.veterinarianID == g.veterinarian.veterinarianID and rx.status == "ACTIVE"
        and visit.status == "DRAFT" and visit.appointment and visit.appointment.status == "IN_PROGRESS"
        and visit.appointment.veterinarianID == g.veterinarian.veterinarianID)
    ready = callable(current_app.config.get("VET_PRESCRIPTION_MUTATION_CHECK"))
    return render_template("veterinarian/prescription_detail.html", rx=rx, visit=visit, rows=rows,
        labels=product_labels({row.productID for row in rows}), historical=historical, context=context,
        can_edit=mutable and ready and current_user.has_permission("PRESCRIPTION_UPDATE"),
        can_cancel=mutable and ready and current_user.has_permission("PRESCRIPTION_CANCEL"),
        mutation_blocked=mutable and not ready, revision=prescription_token(rx),
        doctor_name=history_doctors([visit]).get(visit.visitID))


@veterinarian_bp.get("/prescriptions/<int:rx_id>")
@veterinarian_required("PRESCRIPTION_VIEW")
@phase2_ready
@phase3_page
@prescriptions_ready
def prescription_detail(rx_id):
    rx, visit = visible_prescription(rx_id)
    return rx_detail(rx, visit)


@veterinarian_bp.route("/prescriptions/<int:rx_id>/edit", methods=["GET", "POST"])
@veterinarian_required("PRESCRIPTION_UPDATE")
@phase2_ready
@phase3_page
@prescriptions_ready
def prescription_edit(rx_id):
    rx, visit = visible_prescription(rx_id)
    return rx_editor(visit, rx)


@veterinarian_bp.post("/prescriptions/<int:rx_id>/cancel")
@veterinarian_required("PRESCRIPTION_CANCEL")
@phase2_ready
@phase3_page
@prescriptions_ready
def prescription_cancel(rx_id):
    validate_csrf()
    visible_prescription(rx_id)
    target = rx_target(rx_id)
    cancel_prescription(rx_id, g.veterinarian.veterinarianID, request.form)
    flash("Đã hủy đơn thuốc và ghi nhận lý do.", "success")
    return redirect(target, code=303)


@veterinarian_bp.get("/visits/<int:visit_id>/history/<int:history_id>/prescriptions/<int:rx_id>")
@veterinarian_required("PRESCRIPTION_VIEW")
@phase2_ready
@phase3_page
@prescriptions_ready
def historical_prescription(visit_id, history_id, rx_id):
    context, history = history_visit(visit_id, history_id)
    rx = Prescription.query.filter_by(prescriptionID=rx_id, visitID=history_id).first_or_404()
    return rx_detail(rx, history, historical=True, context=context)
