"""Mappings for database/10_medical_visits.sql; no automatic schema creation."""
from app.extensions import db


class MedicalVisit(db.Model):
    __tablename__ = "medicalVisits"
    __table_args__ = (
        db.CheckConstraint('length(trim("visitCode")) > 0'),
        db.CheckConstraint('length(trim("chiefComplaint")) > 0'),
        db.CheckConstraint('"weightKg" > 0'),
        db.CheckConstraint('"temperatureC" > 0'),
        db.CheckConstraint('"heartRate" > 0'),
        db.CheckConstraint('"respiratoryRate" > 0'),
        db.CheckConstraint('"status" IN (\'DRAFT\', \'COMPLETED\')'),
        db.CheckConstraint('("status" = \'DRAFT\' AND "completedAt" IS NULL) OR '
            '("status" = \'COMPLETED\' AND "completedAt" IS NOT NULL AND "completedAt" >= "startedAt")', name="ckMedicalVisitCompletion"),
        db.Index("idxMedicalVisitsPetDate", "petID", db.desc("visitDate")),
        db.Index("idxMedicalVisitsDateStatus", "visitDate", "status"),
        {"schema": "medical"},
    )
    visitID = db.Column(db.BigInteger, primary_key=True)
    appointmentID = db.Column(db.BigInteger, db.ForeignKey("booking.appointments.appointmentID", ondelete="RESTRICT"), unique=True)
    petID = db.Column(db.BigInteger, db.ForeignKey("medical.pets.petID", ondelete="RESTRICT"), nullable=False)
    visitDate = db.Column(db.Date, nullable=False)
    visitCode = db.Column(db.String(30), nullable=False, unique=True)
    chiefComplaint = db.Column(db.Text, nullable=False)
    symptoms = db.Column(db.Text)
    weightKg = db.Column(db.Numeric(8, 3))
    temperatureC = db.Column(db.Numeric(5, 2))
    heartRate = db.Column(db.Integer)
    respiratoryRate = db.Column(db.Integer)
    clinicalExamination = db.Column(db.Text)
    preliminaryDiagnosis = db.Column(db.Text)
    finalDiagnosis = db.Column(db.Text)
    treatmentPlan = db.Column(db.Text)
    careInstructions = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, server_default="DRAFT")
    startedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    completedAt = db.Column(db.DateTime(timezone=True))
    createdAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updatedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    pet = db.relationship("Pet", lazy="selectin")
    appointment = db.relationship("Appointment", lazy="selectin")
    participants = db.relationship("VisitVeterinarian", back_populates="visit", lazy="selectin")


class VisitVeterinarian(db.Model):
    __tablename__ = "visitVeterinarians"
    __table_args__ = (
        db.CheckConstraint('"participationRole" IN (\'PRIMARY\', \'ASSISTING\', \'CONSULTING\', \'PROCEDURE\')'),
        db.Index("uqVisitPrimaryVeterinarian", "visitID", unique=True,
                 postgresql_where=db.text('"participationRole" = \'PRIMARY\''),
                 sqlite_where=db.text('"participationRole" = \'PRIMARY\'')),
        db.Index("idxVisitVeterinariansVeterinarian", "veterinarianID", "visitID"),
        {"schema": "medical"},
    )
    visitID = db.Column(db.BigInteger, db.ForeignKey("medical.medicalVisits.visitID", ondelete="RESTRICT"), primary_key=True)
    veterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="RESTRICT"), primary_key=True)
    participationRole = db.Column(db.String(20), nullable=False)
    assignedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    note = db.Column(db.Text)
    visit = db.relationship("MedicalVisit", back_populates="participants")


class PetWeightHistory(db.Model):
    __tablename__ = "petWeightHistory"
    __table_args__ = (
        db.CheckConstraint('"weightKg" > 0'),
        db.Index("idxPetWeightHistoryPetMeasured", "petID", db.desc("measuredAt")),
        {"schema": "medical"},
    )
    weightID = db.Column(db.BigInteger, primary_key=True)
    petID = db.Column(db.BigInteger, db.ForeignKey("medical.pets.petID", ondelete="RESTRICT"), nullable=False)
    weightKg = db.Column(db.Numeric(8, 3), nullable=False)
    measuredAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    recordedByStaffID = db.Column(db.BigInteger, db.ForeignKey("clinic.clinicStaff.staffID", ondelete="RESTRICT"))
    note = db.Column(db.Text)
