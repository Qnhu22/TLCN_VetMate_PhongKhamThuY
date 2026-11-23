
from app.extensions import db


class ClinicStaff(db.Model):
    __tablename__ = "clinicStaff"
    __table_args__ = {"schema": "clinic"}

    staffID = db.Column("staffID", db.BigInteger, primary_key=True)
    userID = db.Column(
        "userID",
        db.BigInteger,
        db.ForeignKey("auth.users.userID", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    staffCode = db.Column("staffCode", db.String(30), nullable=False, unique=True)
    staffType = db.Column("staffType", db.String(30), nullable=False)
    hireDate = db.Column("hireDate", db.Date)
    status = db.Column("status", db.String(20), nullable=False, server_default="ACTIVE")
    note = db.Column("note", db.Text)
    createdAt = db.Column("createdAt", db.DateTime(timezone=True), server_default=db.func.now())
    updatedAt = db.Column("updatedAt", db.DateTime(timezone=True), server_default=db.func.now())
