from functools import wraps

from flask import abort, flash, g, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from sqlalchemy import inspect

from app.extensions import db
from app.models import ClinicStaff, DiagnosticOrder, MedicalVisit, User, VisitVeterinarian
from app.veterinarian import veterinarian_bp
from app.veterinarian.csrf import validate_csrf
from app.veterinarian.diagnostic_files import private_path
from app.veterinarian.diagnostics import (ITEM_FIELDS, ORDER_STATUSES, available_services,
    cancel_order, create_order, performers, result_items, result_revision_token,
    save_results, submitted_items)
from app.veterinarian.medical_records import revision_token
from app.veterinarian.phase2_routes import paginate, phase2_ready
from app.veterinarian.phase3_routes import accessible_visit, phase3_page, primary_editable
from app.veterinarian.policies import veterinarian_required


def diagnostics_ready(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if any(not inspect(db.session.connection()).has_table(table, schema="medical")
               for table in ("diagnosticOrders", "diagnosticResultItems")):
            return render_template("veterinarian/diagnostic_setup.html"), 503
        return view(*args, **kwargs)
    return wrapped


@veterinarian_bp.context_processor
def diagnostic_context():
    return {"diagnostic_statuses": ORDER_STATUSES}


def visible_order(order_id):
    order = db.session.get(DiagnosticOrder, order_id)
    if order is None:
        abort(404)
    return order, accessible_visit(order.visitID)


def diagnostic_redirect(order_id):
    if current_user.has_permission("DIAGNOSTIC_ORDER_VIEW"):
        return url_for("veterinarian.diagnostic_detail", order_id=order_id)
    return url_for("main.home")


@veterinarian_bp.get("/visits/<int:visit_id>/diagnostics")
@veterinarian_required("DIAGNOSTIC_ORDER_VIEW")
@phase2_ready
@phase3_page
@diagnostics_ready
def diagnostic_orders(visit_id):
    visit = accessible_visit(visit_id)
    status = request.args.get("status", "")
    if status and status not in ORDER_STATUSES:
        abort(400)
    query = DiagnosticOrder.query.filter_by(visitID=visit_id)
    if status:
        query = query.filter_by(status=status)
    own = db.session.get(VisitVeterinarian, (visit_id, g.veterinarian.veterinarianID))
    return render_template("veterinarian/diagnostic_orders.html", visit=visit,
        pagination=paginate(query.order_by(DiagnosticOrder.orderedAt.desc(), DiagnosticOrder.diagnosticOrderID.desc())),
        selected_status=status, primary=own.participationRole == "PRIMARY", historical=False)


@veterinarian_bp.route("/visits/<int:visit_id>/diagnostics/create", methods=["GET", "POST"])
@veterinarian_required("DIAGNOSTIC_ORDER_CREATE")
@phase2_ready
@phase3_page
@diagnostics_ready
def diagnostic_create(visit_id):
    visit = accessible_visit(visit_id)
    primary_editable(visit)
    errors = {}
    revision = revision_token(visit) if request.method == "GET" else request.form.get("revision", "")
    if request.method == "POST":
        validate_csrf()
        can_view = current_user.has_permission("DIAGNOSTIC_ORDER_VIEW")
        order_id, errors = create_order(visit_id, g.veterinarian.veterinarianID, request.form)
        if not errors:
            target = url_for("veterinarian.diagnostic_detail", order_id=order_id) if can_view else url_for("main.home")
            flash("Đã tạo chỉ định và giao người thực hiện.", "success")
            return redirect(target, code=303)
    return render_template("veterinarian/diagnostic_create.html", visit=visit, services=available_services(),
        performers=performers(visit_id), errors=errors, form_data=request.form, revision=revision), (422 if errors else 200)


def detail_page(order, visit, historical=False, context=None):
    own = db.session.get(VisitVeterinarian, (visit.visitID, g.veterinarian.veterinarianID))
    mutable = (not historical and visit.status == "DRAFT" and visit.appointment
        and visit.appointment.status == "IN_PROGRESS" and order.status in ("PENDING", "PROCESSING"))
    worker = db.session.get(ClinicStaff, order.performedByStaffID) if order.performedByStaffID else None
    worker_user = db.session.get(User, worker.userID) if worker else None
    return render_template("veterinarian/diagnostic_detail.html", order=order, visit=visit,
        worker=worker_user, items=result_items(order.diagnosticOrderID), historical=historical, context=context,
        can_update=mutable and order.performedByStaffID == g.vet_staff.staffID and current_user.has_permission("DIAGNOSTIC_RESULT_UPDATE"),
        can_cancel=mutable and own is not None and own.participationRole == "PRIMARY" and current_user.has_permission("DIAGNOSTIC_ORDER_CANCEL"),
        revision=result_revision_token(order))


@veterinarian_bp.get("/diagnostics/<int:order_id>")
@veterinarian_required("DIAGNOSTIC_ORDER_VIEW")
@phase2_ready
@phase3_page
@diagnostics_ready
def diagnostic_detail(order_id):
    order, visit = visible_order(order_id)
    return detail_page(order, visit)


@veterinarian_bp.route("/diagnostics/<int:order_id>/results", methods=["GET", "POST"])
@veterinarian_required("DIAGNOSTIC_RESULT_UPDATE")
@phase2_ready
@phase3_page
@diagnostics_ready
def diagnostic_results(order_id):
    order, visit = visible_order(order_id)
    if order.performedByStaffID != g.vet_staff.staffID:
        abort(403, description="Chỉ người được giao thực hiện mới được nhập kết quả.")
    if (visit.status != "DRAFT" or visit.appointment is None
            or visit.appointment.status != "IN_PROGRESS"
            or order.status not in ("PENDING", "PROCESSING")):
        abort(409, description="Ca hoặc chỉ định đã khóa.")
    errors = {}
    if request.method == "POST":
        validate_csrf()
        target = diagnostic_redirect(order_id)
        try:
            saved, errors = save_results(order_id, g.veterinarian.veterinarianID,
                g.vet_staff.staffID, request.form, request.files.get("resultFile"))
        except ValueError as exc:
            db.session.rollback()
            saved, errors = False, {"file":str(exc)}
        if saved:
            flash("Đã lưu kết quả chỉ định.", "success")
            return redirect(target, code=303)
        values = request.form
        items = submitted_items(request.form)
        revision = request.form.get("revision", "")
    else:
        values = {"resultSummary":order.resultSummary or "", "conclusion":order.conclusion or ""}
        items = [{key: "" if getattr(item,key) is None else str(getattr(item,key)) for key in ITEM_FIELDS}
                 for item in result_items(order_id)]
        revision = result_revision_token(order)
    if not items:
        items = [{key:"" for key in ITEM_FIELDS}]
    return render_template("veterinarian/diagnostic_results.html", order=order, visit=visit,
        form_data=values, items=items, revision=revision, errors=errors), (422 if errors else 200)


@veterinarian_bp.post("/diagnostics/<int:order_id>/cancel")
@veterinarian_required("DIAGNOSTIC_ORDER_CANCEL")
@phase2_ready
@phase3_page
@diagnostics_ready
def diagnostic_cancel(order_id):
    validate_csrf()
    visible_order(order_id)
    target = diagnostic_redirect(order_id)
    cancel_order(order_id, g.veterinarian.veterinarianID, request.form)
    flash("Đã hủy chỉ định và ghi nhận lý do.", "success")
    return redirect(target, code=303)


def attachment_response(order):
    path = private_path(order.fileUrl)
    if path is None or not path.is_file():
        abort(404)
    response = send_file(path, mimetype="image/webp", as_attachment=True,
        download_name=f"ket-qua-{order.diagnosticOrderID}.webp", conditional=False)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@veterinarian_bp.get("/diagnostics/<int:order_id>/file")
@veterinarian_required("DIAGNOSTIC_ORDER_VIEW")
@phase2_ready
@phase3_page
@diagnostics_ready
def diagnostic_file(order_id):
    order, _ = visible_order(order_id)
    return attachment_response(order)


def history_visit(context_id, history_id):
    if not current_user.has_permission("PET_HISTORY_VIEW_FOR_CARE"):
        abort(403)
    context = accessible_visit(context_id)
    history = MedicalVisit.query.filter(MedicalVisit.visitID == history_id,
        MedicalVisit.petID == context.petID, MedicalVisit.startedAt < context.startedAt,
        MedicalVisit.status == "COMPLETED").first_or_404()
    return context, history


@veterinarian_bp.get("/visits/<int:visit_id>/history/<int:history_id>/diagnostics/<int:order_id>")
@veterinarian_required("DIAGNOSTIC_ORDER_VIEW")
@phase2_ready
@phase3_page
@diagnostics_ready
def historical_diagnostic(visit_id, history_id, order_id):
    context, history = history_visit(visit_id, history_id)
    order = DiagnosticOrder.query.filter_by(diagnosticOrderID=order_id, visitID=history_id).first_or_404()
    return detail_page(order, history, historical=True, context=context)


@veterinarian_bp.get("/visits/<int:visit_id>/history/<int:history_id>/diagnostics/<int:order_id>/file")
@veterinarian_required("DIAGNOSTIC_ORDER_VIEW")
@phase2_ready
@phase3_page
@diagnostics_ready
def historical_diagnostic_file(visit_id, history_id, order_id):
    history_visit(visit_id, history_id)
    order = DiagnosticOrder.query.filter_by(diagnosticOrderID=order_id, visitID=history_id).first_or_404()
    return attachment_response(order)
