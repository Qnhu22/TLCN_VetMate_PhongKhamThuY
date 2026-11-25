"""Internal integration query. Caller MUST authorize the visit before using it.

Only ACTIVE prescriptions; no dispensing, prices, stock movement or billing writes.
Inventory must implement its own unique dispense linkage/idempotency policy.
"""
from app.extensions import db
from app.models import Prescription, PrescriptionItem


def active_prescription_items(visit_id):
    return list(db.session.execute(db.select(
        Prescription.prescriptionID, Prescription.prescriptionNumber,
        PrescriptionItem.prescriptionItemID, PrescriptionItem.productID,
        PrescriptionItem.quantity, PrescriptionItem.dose, PrescriptionItem.frequency,
        PrescriptionItem.durationDays, PrescriptionItem.route, PrescriptionItem.instruction)
        .join(PrescriptionItem, PrescriptionItem.prescriptionID == Prescription.prescriptionID)
        .where(Prescription.visitID == visit_id, Prescription.status == "ACTIVE")
        .order_by(Prescription.prescriptionID, PrescriptionItem.prescriptionItemID)).mappings())
