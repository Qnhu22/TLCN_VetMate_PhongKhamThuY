
from app.extensions import db


class Veterinarian(db.Model):
    __tablename__ = "veterinarians"
    __table_args__ = {"schema": "clinic"}

    veterinarianID = db.Column("veterinarianID", db.BigInteger, primary_key=True)
    staffID = db.Column(
        "staffID",
        db.BigInteger,
        db.ForeignKey("clinic.clinicStaff.staffID", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    licenseNumber = db.Column("licenseNumber", db.String(100))
    bio = db.Column("bio", db.Text)
    yearsExperience = db.Column("yearsExperience", db.Integer)
    consultationNote = db.Column("consultationNote", db.Text)
    status = db.Column("status", db.String(20), nullable=False, server_default="ACTIVE")
