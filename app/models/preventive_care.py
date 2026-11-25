"""Mappings for database/12_medical_vaccinations_followups.sql."""
from app.extensions import db


class Vaccine(db.Model):
    __tablename__ = "vaccines"
    __table_args__ = (
        db.CheckConstraint('length(trim("name")) > 0'),
        db.CheckConstraint('length(trim("targetDisease")) > 0'),
        db.CheckConstraint('"recommendedIntervalDays" > 0'),
        {"schema": "medical"},
    )
    vaccineID = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    manufacturer = db.Column(db.String(200))
    targetDisease = db.Column(db.Text, nullable=False)
    recommendedIntervalDays = db.Column(db.Integer)
    isActive = db.Column(db.Boolean, nullable=False, server_default=db.true())


class VaccinationRecord(db.Model):
    __tablename__ = "vaccinationRecords"
    __table_args__ = (
        db.CheckConstraint('length(trim("dose")) > 0'),
        db.CheckConstraint('"nextDueDate" IS NULL OR "nextDueDate" > "vaccinationDate"', name="ckVaccinationNextDate"),
        db.Index("idxVaccinationRecordsPetDate", "petID", db.desc("vaccinationDate")),
        db.Index("idxVaccinationRecordsVisit", "visitID"),
        db.Index("idxVaccinationRecordsVaccine", "vaccineID"),
        db.Index("idxVaccinationRecordsVet", "veterinarianID"),
        {"schema": "medical"},
    )
    vaccinationID = db.Column(db.BigInteger, primary_key=True)
    petID = db.Column(db.BigInteger, db.ForeignKey("medical.pets.petID", ondelete="RESTRICT"), nullable=False)
    visitID = db.Column(db.BigInteger, db.ForeignKey("medical.medicalVisits.visitID", ondelete="RESTRICT"))
    vaccineID = db.Column(db.BigInteger, db.ForeignKey("medical.vaccines.vaccineID", ondelete="RESTRICT"), nullable=False)
    veterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="RESTRICT"), nullable=False)
    vaccinationDate = db.Column(db.Date, nullable=False)
    dose = db.Column(db.String(150), nullable=False)
    lotNumber = db.Column(db.String(100))
    nextDueDate = db.Column(db.Date)
    reaction = db.Column(db.Text)
    note = db.Column(db.Text)
    vaccine = db.relationship("Vaccine", lazy="selectin")


class FollowUp(db.Model):
    __tablename__ = "followUps"
    __table_args__ = (
        db.CheckConstraint('length(trim("reason")) > 0'),
        db.CheckConstraint('"status" IN (\'UPCOMING\', \'COMPLETED\', \'CANCELLED\', \'OVERDUE\')'),
        db.Index("idxFollowUpsPetDate", "petID", "scheduledDate"),
        db.Index("idxFollowUpsVisit", "visitID"),
        db.Index("idxFollowUpsVet", "veterinarianID"),
        db.Index("idxFollowUpsAppointment", "appointmentID"),
        db.Index("idxFollowUpsStatusDate", "status", "scheduledDate"),
        {"schema": "medical"},
    )
    followUpID = db.Column(db.BigInteger, primary_key=True)
    visitID = db.Column(db.BigInteger, db.ForeignKey("medical.medicalVisits.visitID", ondelete="RESTRICT"), nullable=False)
    petID = db.Column(db.BigInteger, db.ForeignKey("medical.pets.petID", ondelete="RESTRICT"), nullable=False)
    veterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="RESTRICT"))
    scheduledDate = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, server_default="UPCOMING")
    appointmentID = db.Column(db.BigInteger, db.ForeignKey("booking.appointments.appointmentID", ondelete="RESTRICT"))
    appointment = db.relationship("Appointment", lazy="selectin")
