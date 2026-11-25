"""Medical prescription mappings from SQL 13; inventory FK is applied by SQL 14.

Inventory belongs to another module. Do not fabricate Product models/DDL here.
The application verifies the real cross-schema FK before enabling writes.
"""
from app.extensions import db


class Prescription(db.Model):
    __tablename__ = "prescriptions"
    __table_args__ = (
        db.CheckConstraint('length(trim("prescriptionNumber")) > 0'),
        db.CheckConstraint('"status" IN (\'ACTIVE\', \'CANCELLED\')'),
        db.Index("idxPrescriptionsVisit", "visitID"),
        db.Index("idxPrescriptionsVetDate", "veterinarianID", "prescribedAt"),
        {"schema":"medical"},
    )
    prescriptionID = db.Column(db.BigInteger, primary_key=True)
    visitID = db.Column(db.BigInteger, db.ForeignKey("medical.medicalVisits.visitID", ondelete="RESTRICT"), nullable=False)
    veterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="RESTRICT"), nullable=False)
    prescriptionNumber = db.Column(db.String(30), nullable=False, unique=True)
    prescribedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    generalInstruction = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, server_default="ACTIVE")
    createdAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    items = db.relationship("PrescriptionItem", lazy="selectin", order_by="PrescriptionItem.prescriptionItemID")


class PrescriptionItem(db.Model):
    __tablename__ = "prescriptionItems"
    __table_args__ = (
        db.CheckConstraint('"productID" > 0'),
        db.CheckConstraint('"quantity" > 0'),
        db.CheckConstraint('length(trim("dose")) > 0'),
        db.CheckConstraint('length(trim("frequency")) > 0'),
        db.CheckConstraint('"durationDays" > 0'),
        db.CheckConstraint('length(trim("route")) > 0'),
        db.Index("idxPrescriptionItemsPrescription", "prescriptionID"),
        db.Index("idxPrescriptionItemsProduct", "productID"),
        {"schema":"medical"},
    )
    prescriptionItemID = db.Column(db.BigInteger, primary_key=True)
    prescriptionID = db.Column(db.BigInteger, db.ForeignKey("medical.prescriptions.prescriptionID", ondelete="RESTRICT"), nullable=False)
    productID = db.Column(db.BigInteger, nullable=False)
    quantity = db.Column(db.Numeric(12,3), nullable=False)
    dose = db.Column(db.String(150), nullable=False)
    frequency = db.Column(db.String(150), nullable=False)
    durationDays = db.Column(db.Integer, nullable=False)
    route = db.Column(db.String(100), nullable=False)
    instruction = db.Column(db.Text)
