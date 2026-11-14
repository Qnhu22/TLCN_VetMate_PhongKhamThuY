from app.extensions import db


class UserRole(db.Model):
    __tablename__ = "userRoles"
    __table_args__ = {"schema": "auth"}

    userID = db.Column(
        "userID",
        db.BigInteger,
        db.ForeignKey(
            "auth.users.userID",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    roleID = db.Column(
        "roleID",
        db.BigInteger,
        db.ForeignKey(
            "auth.roles.roleID",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    assignedAt = db.Column(
        "assignedAt",
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )