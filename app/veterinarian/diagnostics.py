import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import abort, current_app
from itsdangerous import BadSignature, URLSafeSerializer

from app.extensions import db
from app.models import (ClinicStaff, DiagnosticOrder, DiagnosticResultItem, Service,
    User, Veterinarian, VisitVeterinarian)
from app.veterinarian.diagnostic_files import delete_attachment, save_attachment
from app.veterinarian.medical_records import lock_record, validate_revision

ORDER_STATUSES = {"PENDING":"Chờ thực hiện", "PROCESSING":"Đang xử lý",
                  "COMPLETED":"Đã có kết quả", "CANCELLED":"Đã hủy"}
ITEM_FIELDS = ("parameterName", "valueText", "valueNumeric", "unit", "referenceRange", "abnormalFlag", "note")


def performers(visit_id):
    rows = db.session.execute(db.select(ClinicStaff, User)
        .join(Veterinarian, Veterinarian.staffID == ClinicStaff.staffID)
        .join(User, User.userID == ClinicStaff.userID)
        .join(VisitVeterinarian, VisitVeterinarian.veterinarianID == Veterinarian.veterinarianID)
        .where(VisitVeterinarian.visitID == visit_id, ClinicStaff.status == "ACTIVE",
               ClinicStaff.staffType == "VETERINARIAN", Veterinarian.status == "ACTIVE", User.status == "ACTIVE")
        .order_by(User.fullName)).all()
    return [(staff, user) for staff, user in rows
            if user.has_role("VETERINARIAN") and user.has_permission("DIAGNOSTIC_RESULT_UPDATE")]


def available_services():
    # No isBookable/requiresVeterinarian filter: a diagnostic need not be online-bookable.
    return db.session.scalars(db.select(Service).where(Service.status == "ACTIVE",
        Service.isEmergency.is_(False)).order_by(Service.name)).all()


def result_items(order_id):
    return list(db.session.scalars(db.select(DiagnosticResultItem).where(
        DiagnosticResultItem.diagnosticOrderID == order_id)
        .order_by(DiagnosticResultItem.resultItemID).execution_options(populate_existing=True)))


def order_revision(order):
    values = {key: str(getattr(order, key)) for key in ("diagnosticOrderID", "visitID", "serviceID",
        "performedByStaffID", "status", "resultSummary", "conclusion", "fileUrl", "note")}
    values["items"] = [{key: str(getattr(item, key)) for key in ITEM_FIELDS} for item in result_items(order.diagnosticOrderID)]
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def result_revision_token(order):
    return URLSafeSerializer(current_app.secret_key, salt="diagnostic-result-revision").dumps(
        {"id": order.diagnosticOrderID, "digest": order_revision(order)})


def check_result_revision(order, token):
    try:
        if not token or len(token) > 1000:
            raise BadSignature("Missing revision")
        data = URLSafeSerializer(current_app.secret_key, salt="diagnostic-result-revision").loads(token)
        if not isinstance(data, dict) or data.get("id") != order.diagnosticOrderID:
            raise BadSignature("Wrong order")
    except BadSignature:
        abort(400, description="Phiên bản chỉ định không hợp lệ. Vui lòng mở lại.")
    if data.get("digest") != order_revision(order):
        abort(409, description="Chỉ định đã được cập nhật ở cửa sổ khác. Mở lại để kiểm tra.")


def submitted_items(form):
    columns = {key: form.getlist("item_" + key) for key in ITEM_FIELDS}
    count = max((len(values) for values in columns.values()), default=0)
    return [{key: columns[key][i] if i < len(columns[key]) else "" for key in ITEM_FIELDS} for i in range(min(count, 31))]


def validate_results(form):
    errors, items = {}, []
    action = form.get("action", "")
    if action not in ("save", "complete"):
        errors["action"] = "Thao tác không hợp lệ."
    summary = form.get("resultSummary", "").strip()
    conclusion = form.get("conclusion", "").strip()
    if len(summary) > 10000 or len(conclusion) > 10000:
        errors["summary"] = "Kết quả và kết luận tối đa 10.000 ký tự mỗi trường."
    if action == "complete" and (not summary or not conclusion):
        errors["summary"] = "Hoàn tất cần có kết quả tổng quát và kết luận."
    rows = submitted_items(form)
    if len(rows) > 30:
        errors["items"] = "Mỗi chỉ định tối đa 30 chỉ số chi tiết."
    for i, raw in enumerate(rows, 1):
        row = {key: value.strip() for key, value in raw.items()}
        if not any(row.values()):
            continue
        if not row["parameterName"] or len(row["parameterName"]) > 150:
            errors[f"item{i}"] = f"Dòng {i}: tên chỉ số bắt buộc, tối đa 150 ký tự."
        for key, maximum in (("valueText",2000),("unit",50),("referenceRange",150),("abnormalFlag",30),("note",2000)):
            if len(row[key]) > maximum:
                errors[f"item{i}"] = f"Dòng {i}: nội dung quá dài."
        number = None
        if row["valueNumeric"]:
            try:
                if len(row["valueNumeric"]) > 50:
                    raise ValueError
                number = Decimal(row["valueNumeric"])
                if (not number.is_finite() or abs(number) > Decimal("999999999999.999999")
                        or number != number.quantize(Decimal("0.000001"))):
                    raise ValueError
            except (InvalidOperation, ValueError):
                errors[f"item{i}"] = f"Dòng {i}: giá trị số không hợp lệ, tối đa 6 chữ số thập phân."
        if number is None and not row["valueText"]:
            errors[f"item{i}"] = f"Dòng {i}: cần giá trị chữ hoặc số."
        items.append({**{key: value or None for key, value in row.items()}, "valueNumeric": number})
    return summary or None, conclusion or None, items, errors


def create_order(visit_id, vet_id, form):
    visit, _, _ = lock_record(visit_id, vet_id)
    validate_revision(visit, form.get("revision", ""))
    errors = {}
    try:
        service_id = int(form.get("serviceID", ""))
        staff_id = int(form.get("performedByStaffID", ""))
    except (ValueError, TypeError):
        service_id = staff_id = None
    service = db.session.get(Service, service_id) if service_id is not None else None
    if service is None or service.status != "ACTIVE" or service.isEmergency:
        errors["service"] = "Chọn dịch vụ đang hoạt động, không phải tiếp nhận cấp cứu."
    if staff_id not in {staff.staffID for staff, _ in performers(visit_id)}:
        errors["performer"] = "Người thực hiện phải là bác sĩ hoạt động tham gia ca và có quyền nhập kết quả."
    note = form.get("note", "").strip()
    if len(note) > 2000:
        errors["note"] = "Ghi chú tối đa 2.000 ký tự."
    if errors:
        db.session.rollback()
        return None, errors
    now = datetime.now(timezone.utc)
    order = DiagnosticOrder(visitID=visit_id, serviceID=service_id, orderedByVeterinarianID=vet_id,
        performedByStaffID=staff_id, status="PENDING", orderedAt=now, note=note or None)
    db.session.add(order)
    visit.updatedAt = now
    db.session.flush()
    order_id = order.diagnosticOrderID
    db.session.commit()
    return order_id, {}


def lock_order(order_id, vet_id, primary=False):
    visit_id = db.session.scalar(db.select(DiagnosticOrder.visitID).where(DiagnosticOrder.diagnosticOrderID == order_id))
    if visit_id is None:
        abort(404)
    visit, _, _ = lock_record(visit_id, vet_id, require_primary=primary)
    order = db.session.scalar(db.select(DiagnosticOrder).where(DiagnosticOrder.diagnosticOrderID == order_id)
        .with_for_update(of=DiagnosticOrder).execution_options(populate_existing=True))
    if order is None or order.visitID != visit.visitID:
        abort(404)
    if order.status not in ("PENDING", "PROCESSING"):
        abort(409, description="Chỉ định đã hoàn tất hoặc đã hủy, không thể chỉnh sửa.")
    return visit, order


def save_results(order_id, vet_id, staff_id, form, upload):
    visit, order = lock_order(order_id, vet_id)
    if order.performedByStaffID != staff_id:
        abort(403, description="Chỉ người được giao thực hiện mới được nhập kết quả.")
    check_result_revision(order, form.get("revision", ""))
    summary, conclusion, items, errors = validate_results(form)
    if errors:
        db.session.rollback()
        return False, errors
    old_key, new_key = order.fileUrl, None
    try:
        new_key = save_attachment(upload)
        if new_key:
            order.fileUrl = new_key
        order.resultSummary, order.conclusion = summary, conclusion
        db.session.execute(db.delete(DiagnosticResultItem).where(DiagnosticResultItem.diagnosticOrderID == order_id))
        db.session.add_all([DiagnosticResultItem(diagnosticOrderID=order_id, **item) for item in items])
        order.status = "COMPLETED" if form.get("action") == "complete" else "PROCESSING"
        now = datetime.now(timezone.utc)
        order.performedAt = now if order.status == "COMPLETED" else None
        visit.updatedAt = now
        db.session.commit()
    except Exception:
        db.session.rollback()
        if new_key:
            delete_attachment(new_key)
        raise
    if new_key and old_key != new_key:
        delete_attachment(old_key)
    return True, {}


def cancel_order(order_id, vet_id, form):
    visit, order = lock_order(order_id, vet_id, primary=True)
    check_result_revision(order, form.get("revision", ""))
    reason = form.get("cancelReason", "").strip()
    if not 1 <= len(reason) <= 2000:
        abort(422, description="Nhập lý do hủy từ 1 đến 2.000 ký tự.")
    order.status = "CANCELLED"
    order.note = ((order.note or "") + "\nLý do hủy: " + reason).strip()
    visit.updatedAt = datetime.now(timezone.utc)
    db.session.commit()
