
from app.extensions import db


class OwnerProfile(db.Model):
    __tablename__ = "ownerProfiles"
    __table_args__ = {"schema": "medical"}

    ownerID = db.Column(
        "ownerID",
        db.BigInteger,
        primary_key=True,
    )

    userID = db.Column(
        "userID",
        db.BigInteger,
        db.ForeignKey(
            "auth.users.userID",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
    )

    address = db.Column(
        "address",
        db.Text,
        nullable=True,
    )

    emergencyPhone = db.Column(
        "emergencyPhone",
        db.String(20),
        nullable=True,
    )

    allowPublicPhone = db.Column(
        "allowPublicPhone",
        db.Boolean,
        nullable=False,
        server_default=db.false(),
    )

    note = db.Column(
        "note",
        db.Text,
        nullable=True,
    )

    user = db.relationship(
        "User",
        lazy="selectin",
    )

    pets = db.relationship(
        "Pet",
        back_populates="owner",
        lazy="selectin",
    )
