from app.extensions import db


class QueueEntry(db.Model):
    __tablename__ = "queueEntries"
    __table_args__ = {"schema": "booking"}

    queueEntryID = db.Column("queueEntryID", db.BigInteger, primary_key=True)
    appointmentID = db.Column("appointmentID", db.BigInteger, db.ForeignKey("booking.appointments.appointmentID", ondelete="RESTRICT"), nullable=False, unique=True)
    queueDate = db.Column("queueDate", db.Date, nullable=False)
    queueNumber = db.Column("queueNumber", db.Integer, nullable=False)
    checkedInAt = db.Column("checkedInAt", db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    calledAt = db.Column("calledAt", db.DateTime(timezone=True))
    startedAt = db.Column("startedAt", db.DateTime(timezone=True))
    completedAt = db.Column("completedAt", db.DateTime(timezone=True))
    status = db.Column("status", db.String(20), nullable=False, server_default="WAITING")

    appointment = db.relationship("Appointment", back_populates="queueEntry", lazy="selectin")
