from datetime import timezone

from flask import abort, current_app, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user

from app.extensions import db
from app.models import StaffLeave
from app.veterinarian import veterinarian_bp
from app.veterinarian.csrf import csrf_token, validate_csrf
from app.veterinarian.policies import veterinarian_required
from app.veterinarian.queries import daily_stats, schedules, specialties
from app.veterinarian.services import cancel_leave, create_leave
from app.veterinarian.validation import LEAVE_STATUSES, LOCAL_TZ, schedule_range, today, validate_leave


@veterinarian_bp.app_template_filter("vet_local")
def vet_local(value):
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")


@veterinarian_bp.context_processor
def template_context():
    return {"vet_csrf_token": csrf_token, "leave_statuses": LEAVE_STATUSES}


@veterinarian_bp.get("/")
@veterinarian_required("VET_DASHBOARD_VIEW")
def dashboard():
    day = today()
    return render_template("veterinarian/dashboard.html", day=day,
        stats=daily_stats(g.veterinarian.veterinarianID, day),
        schedules=schedules(g.veterinarian.veterinarianID, day, day),
        specialties=specialties(g.veterinarian.veterinarianID))


@veterinarian_bp.get("/schedules")
@veterinarian_required("VET_SCHEDULE_VIEW_SELF")
def working_schedules():
    view = request.args.get("view", "week")
    if view not in ("day", "week"):
        abort(400)
    raw = request.args.get("date", "")
    try:
        first, last = schedule_range(raw, view)
    except (ValueError, OverflowError):
        abort(400, description="Ngày không hợp lệ.")
    return render_template("veterinarian/schedules.html", view=view, selected_date=raw or today().isoformat(),
        first=first, last=last, schedules=schedules(g.veterinarian.veterinarianID, first, last),
        specialties=specialties(g.veterinarian.veterinarianID))


@veterinarian_bp.get("/leaves")
@veterinarian_required("VET_LEAVE_VIEW_SELF")
def leaves():
    status = request.args.get("status", "")
    if status and status not in LEAVE_STATUSES:
        abort(400)
    query = StaffLeave.query.filter_by(staffID=g.vet_staff.staffID)
    if status:
        query = query.filter_by(status=status)
    pagination = query.order_by(StaffLeave.createdAt.desc(), StaffLeave.leaveID.desc()).paginate(
        page=max(request.args.get("page", 1, type=int) or 1, 1), per_page=10, error_out=False)
    return render_template("veterinarian/leaves.html", pagination=pagination, selected_status=status)


@veterinarian_bp.route("/leaves/create", methods=["GET", "POST"])
@veterinarian_required("VET_LEAVE_CREATE_SELF")
def leave_create():
    errors = {}
    if request.method == "POST":
        validate_csrf()
        data, errors = validate_leave(request.form)
        if not errors:
            try:
                create_leave(g.vet_staff.staffID, data)
            except ValueError as exc:
                db.session.rollback()
                errors["general"] = str(exc)
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception("Không thể gửi yêu cầu nghỉ bác sĩ")
                errors["general"] = "Không thể lưu yêu cầu. Vui lòng thử lại."
            else:
                flash("Đã gửi yêu cầu nghỉ, chờ quản lý xét duyệt.", "success")
                if current_user.has_permission("VET_LEAVE_VIEW_SELF"):
                    return redirect(url_for("veterinarian.leaves"), code=303)
                return redirect(url_for("veterinarian.leave_create"), code=303)
    return render_template("veterinarian/leave_create.html", errors=errors, form_data=request.form, today=today())


@veterinarian_bp.post("/leaves/<int:leave_id>/cancel")
@veterinarian_required("VET_LEAVE_CANCEL_SELF")
def leave_cancel(leave_id):
    validate_csrf()
    try:
        cancel_leave(g.vet_staff.staffID, leave_id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Không thể hủy yêu cầu nghỉ bác sĩ")
        abort(503, description="Chưa thể hủy yêu cầu, vui lòng thử lại.")
    flash("Đã hủy yêu cầu nghỉ.", "success")
    endpoint = "veterinarian.leaves" if current_user.has_permission("VET_LEAVE_VIEW_SELF") else "main.home"
    return redirect(url_for(endpoint), code=303)
