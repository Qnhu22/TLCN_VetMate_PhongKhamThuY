
from app.extensions import db


class CustomerActivationLink(db.Model):
    __tablename__ = "customerActivationLinks"
    __table_args__ = {"schema": "auth"}

    activationLinkID = db.Column(
        "activationLinkID",
        db.BigInteger,
        primary_key=True,
    )

    userID = db.Column(
        "userID",
        db.BigInteger,
        db.ForeignKey(
            "auth.users.userID",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    tokenHash = db.Column(
        "tokenHash",
        db.String(64),
        nullable=False,
        unique=True,
    )

    expiresAt = db.Column(
        "expiresAt",
        db.DateTime(timezone=True),
        nullable=False,
    )

    usedAt = db.Column(
        "usedAt",
        db.DateTime(timezone=True),
        nullable=True,
    )

    createdAt = db.Column(
        "createdAt",
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
