from app.extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"
    __table_args__ = {"schema": "booking"}

    appointmentID = db.Column("appointmentID", db.BigInteger, primary_key=True)
    appointmentCode = db.Column("appointmentCode", db.String(30), nullable=False, unique=True)
    petID = db.Column("petID", db.BigInteger, db.ForeignKey("medical.pets.petID", ondelete="RESTRICT"), nullable=False)
    serviceID = db.Column("serviceID", db.BigInteger, db.ForeignKey("clinic.services.serviceID", ondelete="RESTRICT"), nullable=False)
    veterinarianID = db.Column("veterinarianID", db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="RESTRICT"))
    appointmentType = db.Column("appointmentType", db.String(20), nullable=False, server_default="SCHEDULED")
    bookingSource = db.Column("bookingSource", db.String(20))
    priority = db.Column("priority", db.String(20), nullable=False, server_default="NORMAL")
    scheduledDate = db.Column("scheduledDate", db.Date, nullable=False)
    startTime = db.Column("startTime", db.Time, nullable=False)
    endTime = db.Column("endTime", db.Time)
    reason = db.Column("reason", db.Text, nullable=False)
    ownerNote = db.Column("ownerNote", db.Text)
    status = db.Column("status", db.String(20), nullable=False, server_default="PENDING")
    confirmedByStaffID = db.Column("confirmedByStaffID", db.BigInteger, db.ForeignKey("clinic.clinicStaff.staffID", ondelete="SET NULL"))
    confirmedAt = db.Column("confirmedAt", db.DateTime(timezone=True))
    cancelledAt = db.Column("cancelledAt", db.DateTime(timezone=True))
    cancelReason = db.Column("cancelReason", db.Text)
    checkedInAt = db.Column("checkedInAt", db.DateTime(timezone=True))
    createdByUserID = db.Column("createdByUserID", db.BigInteger, db.ForeignKey("auth.users.userID", ondelete="RESTRICT"), nullable=False)
    createdAt = db.Column("createdAt", db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updatedAt = db.Column("updatedAt", db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    pet = db.relationship("Pet", lazy="selectin")
    creator = db.relationship("User", foreign_keys=[createdByUserID], lazy="selectin")
    queueEntry = db.relationship("QueueEntry", back_populates="appointment", uselist=False, lazy="selectin")
