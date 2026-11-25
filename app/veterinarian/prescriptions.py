import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import abort, current_app
from itsdangerous import BadSignature, URLSafeSerializer

from app.extensions import db
from app.models import Prescription, PrescriptionItem
from app.veterinarian.medical_records import lock_record, validate_revision
from app.veterinarian.medicine_catalog import inventory_fk_ready, lock_medicines

ITEM_FIELDS = ("productID","quantity","dose","frequency","durationDays","route","instruction")


def submitted_items(form):
    columns={key:form.getlist("rx_"+key) for key in ITEM_FIELDS}
    count=max((len(values) for values in columns.values()),default=0)
    return [{key:columns[key][i] if i<len(columns[key]) else "" for key in ITEM_FIELDS} for i in range(min(count,31))]


def validate_prescription(form):
    errors,items={},[]
    general=form.get("generalInstruction","").strip()
    if len(general)>10000:
        errors["general"]="Hướng dẫn chung tối đa 10.000 ký tự."
    rows=submitted_items(form)
    if len(rows)>30:
        errors["items"]="Mỗi đơn tối đa 30 dòng thuốc."
    for index,raw in enumerate(rows,1):
        row={key:value.strip() for key,value in raw.items()}
        if not any(row.values()):
            continue
        try:
            if len(row["productID"])>19 or len(row["durationDays"])>10 or len(row["quantity"])>40:
                raise ValueError
            product_id=int(row["productID"])
            days=int(row["durationDays"])
            quantity=Decimal(row["quantity"])
            if (not 0<product_id<=9223372036854775807 or not 0<days<=2147483647
                or not quantity.is_finite() or not 0<quantity<=Decimal("999999999.999")
                or quantity!=quantity.quantize(Decimal("0.001"))):
                raise ValueError
        except (ValueError,InvalidOperation,OverflowError):
            errors[f"row{index}"]=f"Dòng {index}: thuốc, số lượng hoặc số ngày không hợp lệ."
            continue
        for field,maximum in (("dose",150),("frequency",150),("route",100)):
            if not row[field] or len(row[field])>maximum:
                errors[f"row{index}"]=f"Dòng {index}: cần liều dùng, tần suất, đường dùng với độ dài hợp lệ."
        if len(row["instruction"])>2000:
            errors[f"row{index}"]=f"Dòng {index}: hướng dẫn riêng tối đa 2.000 ký tự."
        items.append({"productID":product_id,"quantity":quantity,"durationDays":days,
            "dose":row["dose"],"frequency":row["frequency"],"route":row["route"],"instruction":row["instruction"] or None})
    if not items:
        errors["items"]="Đơn thuốc cần ít nhất một dòng thuốc hợp lệ."
    return general or None,items,errors


def prescription_items(rx_id):
    return list(db.session.scalars(db.select(PrescriptionItem).where(PrescriptionItem.prescriptionID==rx_id)
        .order_by(PrescriptionItem.prescriptionItemID).execution_options(populate_existing=True)))


def digest(rx):
    rows=[]
    for row in prescription_items(rx.prescriptionID):
        values={key:str(getattr(row,key)) for key in ITEM_FIELDS}
        values["quantity"]=str(Decimal(values["quantity"]).normalize())
        rows.append(values)
    data={"id":rx.prescriptionID,"visitID":rx.visitID,"vetID":rx.veterinarianID,
          "status":rx.status,"general":rx.generalInstruction,"items":rows}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def prescription_token(rx):
    return URLSafeSerializer(current_app.secret_key,salt="prescription-revision").dumps(
        {"id":rx.prescriptionID,"digest":digest(rx)})


def check_revision(rx,token):
    try:
        if not token or len(token)>1000:
            raise BadSignature("Missing revision")
        data=URLSafeSerializer(current_app.secret_key,salt="prescription-revision").loads(token)
        if not isinstance(data,dict) or data.get("id")!=rx.prescriptionID:
            raise BadSignature("Wrong prescription")
    except BadSignature:
        abort(400,description="Phiên bản đơn thuốc không hợp lệ. Vui lòng mở lại đơn.")
    if data.get("digest")!=digest(rx):
        abort(409,description="Đơn thuốc đã thay đổi. Mở lại để kiểm tra trước khi lưu.")


def require_inventory_fk():
    if not inventory_fk_ready():
        abort(503,description="Chưa xác nhận khóa ngoại đơn thuốc với danh mục kho. Chưa thể ghi đơn.")


def mutation_guard(rx,action):
    """Inventory-owned hook: return True ONLY after verifying not dispensed.

    Called while holding the visit/prescription transaction locks. The integration
    must coordinate dispensing locks in the same transaction. Missing hook blocks.
    """
    checker=current_app.config.get("VET_PRESCRIPTION_MUTATION_CHECK")
    if not callable(checker) or checker(rx.prescriptionID,action) is not True:
        abort(409,description="Chưa xác nhận đơn chưa cấp phát. Liên hệ bộ phận thuốc trước khi sửa/hủy.")


def lock_prescription(rx_id,vet_id):
    visit_id=db.session.scalar(db.select(Prescription.visitID).where(Prescription.prescriptionID==rx_id))
    if visit_id is None:
        abort(404)
    visit,_,_=lock_record(visit_id,vet_id)
    rx=db.session.scalar(db.select(Prescription).where(Prescription.prescriptionID==rx_id)
        .with_for_update(of=Prescription).execution_options(populate_existing=True))
    if rx is None or rx.visitID!=visit_id:
        abort(404)
    if rx.veterinarianID!=vet_id:
        abort(403,description="Chỉ bác sĩ kê đơn được sửa/hủy đơn của mình.")
    if rx.status!="ACTIVE":
        abort(409,description="Đơn thuốc đã bị hủy, không thể chỉnh sửa.")
    return visit,rx


def save_prescription(visit_id,vet_id,form,rx_id=None):
    require_inventory_fk()
    if rx_id is None:
        visit,_,_=lock_record(visit_id,vet_id)
        validate_revision(visit,form.get("revision",""))
        rx=None
    else:
        visit,rx=lock_prescription(rx_id,vet_id)
        if visit.visitID!=visit_id:
            abort(404)
        check_revision(rx,form.get("revision",""))
        mutation_guard(rx,"update")
    general,items,errors=validate_prescription(form)
    if not errors:
        ids={item["productID"] for item in items}
        if lock_medicines(ids)!=ids:
            errors["medicine"]="Có thuốc không hoạt động hoặc không có hồ sơ thuốc. Vui lòng chọn lại."
    if errors:
        db.session.rollback()
        return None,errors
    now=datetime.now(timezone.utc)
    if rx is None:
        rx=Prescription(visitID=visit_id,veterinarianID=vet_id,prescriptionNumber="RX"+uuid4().hex[:16].upper(),
                        generalInstruction=general,status="ACTIVE",prescribedAt=now)
        db.session.add(rx)
        db.session.flush()
    else:
        rx.generalInstruction=general
        db.session.execute(db.delete(PrescriptionItem).where(PrescriptionItem.prescriptionID==rx_id))
    db.session.add_all([PrescriptionItem(prescriptionID=rx.prescriptionID,**row) for row in items])
    visit.updatedAt=now
    saved_id=rx.prescriptionID
    db.session.commit()
    return saved_id,{}


def cancel_prescription(rx_id,vet_id,form):
    require_inventory_fk()
    visit,rx=lock_prescription(rx_id,vet_id)
    check_revision(rx,form.get("revision",""))
    mutation_guard(rx,"cancel")
    reason=form.get("cancelReason","").strip()
    if not 1<=len(reason)<=2000:
        abort(422,description="Nhập lý do hủy từ 1 đến 2.000 ký tự.")
    rx.status="CANCELLED"
    rx.generalInstruction=((rx.generalInstruction or "")+"\nLý do hủy đơn: "+reason).strip()
    visit.updatedAt=datetime.now(timezone.utc)
    db.session.commit()
