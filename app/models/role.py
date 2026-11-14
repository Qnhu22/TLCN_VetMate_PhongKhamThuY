from app.extensions import db


class Role(db.Model):
    __tablename__ = "roles"
    __table_args__ = {"schema": "auth"}

    roleID = db.Column(
        "roleID",
        db.BigInteger,
        primary_key=True,
    )

    roleCode = db.Column(
        "roleCode",
        db.String(50),
        nullable=False,
        unique=True,
    )

    name = db.Column(
        "name",
        db.String(100),
        nullable=False,
    )

    description = db.Column(
        "description",
        db.Text,
        nullable=True,
    )

    isActive = db.Column(
        "isActive",
        db.Boolean,
        nullable=False,
        server_default=db.true(),
    )
    
    permissions = db.relationship(
        "Permission",
        secondary="auth.rolePermissions",
        lazy="selectin",
    )