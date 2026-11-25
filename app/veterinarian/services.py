from flask import abort

from app.extensions import db
from app.models import ClinicStaff, StaffLeave


def create_leave(staff_id, data):
    # Serialize submissions per staff member, then check overlapping live requests.
    db.session.execute(db.select(ClinicStaff).where(ClinicStaff.staffID == staff_id).with_for_update()).scalar_one()
    overlap = db.session.scalar(db.select(StaffLeave.leaveID).where(
        StaffLeave.staffID == staff_id, StaffLeave.status.in_(("PENDING", "APPROVED")),
        StaffLeave.startAt < data["endAt"], StaffLeave.endAt > data["startAt"]
    ).limit(1))
    if overlap is not None:
        raise ValueError("Khoảng nghỉ trùng với yêu cầu đang chờ hoặc đã được duyệt.")
    db.session.add(StaffLeave(staffID=staff_id, status="PENDING", **data))
    db.session.commit()


def cancel_leave(staff_id, leave_id):
    leave = db.session.scalar(db.select(StaffLeave).where(
        StaffLeave.leaveID == leave_id, StaffLeave.staffID == staff_id
    ).with_for_update())
    if leave is None:
        abort(404)
    if leave.status != "PENDING":
        abort(409, description="Chỉ có thể hủy yêu cầu đang chờ duyệt.")
    leave.status = "CANCELLED"
    db.session.commit()
