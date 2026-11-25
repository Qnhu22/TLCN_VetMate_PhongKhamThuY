"""Mappings for database/11_medical_diagnostics.sql."""
from app.extensions import db


class DiagnosticOrder(db.Model):
    __tablename__ = "diagnosticOrders"
    __table_args__ = (
        db.CheckConstraint('"status" IN (\'PENDING\', \'PROCESSING\', \'COMPLETED\', \'CANCELLED\')'),
        db.CheckConstraint('"performedAt" IS NULL OR "performedAt" >= "orderedAt"', name="ckDiagnosticPerformedTime"),
        db.CheckConstraint('"status" <> \'COMPLETED\' OR ("performedAt" IS NOT NULL AND '
            '"performedByStaffID" IS NOT NULL AND "resultSummary" IS NOT NULL AND length(trim("resultSummary")) > 0 '
            'AND "conclusion" IS NOT NULL AND length(trim("conclusion")) > 0)', name="ckDiagnosticCompleted"),
        db.Index("idxDiagnosticOrdersVisit", "visitID"),
        db.Index("idxDiagnosticOrdersService", "serviceID"),
        db.Index("idxDiagnosticOrdersOrderedBy", "orderedByVeterinarianID"),
        db.Index("idxDiagnosticOrdersPerformerStatus", "performedByStaffID", "status"),
        {"schema": "medical"},
    )
    diagnosticOrderID = db.Column(db.BigInteger, primary_key=True)
    visitID = db.Column(db.BigInteger, db.ForeignKey("medical.medicalVisits.visitID", ondelete="RESTRICT"), nullable=False)
    serviceID = db.Column(db.BigInteger, db.ForeignKey("clinic.services.serviceID", ondelete="RESTRICT"), nullable=False)
    orderedByVeterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="RESTRICT"), nullable=False)
    # Assigned worker while pending; the same worker is recorded when completing.
    performedByStaffID = db.Column(db.BigInteger, db.ForeignKey("clinic.clinicStaff.staffID", ondelete="RESTRICT"))
    status = db.Column(db.String(20), nullable=False, server_default="PENDING")
    orderedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    performedAt = db.Column(db.DateTime(timezone=True))
    resultSummary = db.Column(db.Text)
    conclusion = db.Column(db.Text)
    fileUrl = db.Column(db.Text)
    note = db.Column(db.Text)
    service = db.relationship("Service", lazy="selectin")
    items = db.relationship("DiagnosticResultItem", lazy="selectin", order_by="DiagnosticResultItem.resultItemID")


class DiagnosticResultItem(db.Model):
    __tablename__ = "diagnosticResultItems"
    __table_args__ = (
        db.CheckConstraint('length(trim("parameterName")) > 0'),
        db.CheckConstraint('"valueNumeric" IS NOT NULL OR ("valueText" IS NOT NULL AND length(trim("valueText")) > 0)', name="ckDiagnosticResultValue"),
        db.Index("idxDiagnosticResultItemsOrder", "diagnosticOrderID"),
        {"schema": "medical"},
    )
    resultItemID = db.Column(db.BigInteger, primary_key=True)
    diagnosticOrderID = db.Column(db.BigInteger, db.ForeignKey("medical.diagnosticOrders.diagnosticOrderID", ondelete="RESTRICT"), nullable=False)
    parameterName = db.Column(db.String(150), nullable=False)
    valueText = db.Column(db.Text)
    valueNumeric = db.Column(db.Numeric(18, 6))
    unit = db.Column(db.String(50))
    referenceRange = db.Column(db.String(150))
    abnormalFlag = db.Column(db.String(30))
    note = db.Column(db.Text)
