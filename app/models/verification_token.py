from app.extensions import db


class VerificationToken(db.Model):
    __tablename__ = "verificationTokens"
    __table_args__ = {"schema": "auth"}

    verificationTokenID = db.Column(
        "verificationTokenID",
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

    purpose = db.Column(
        "purpose",
        db.String(30),
        nullable=False,
    )

    tokenHash = db.Column(
        "tokenHash",
        db.String(255),
        nullable=False,
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
    
    failedAttempts = db.Column(
        "failedAttempts",
        db.Integer,
        nullable=False,
        server_default="0",
    )