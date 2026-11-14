from app.extensions import db


class Permission(db.Model):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "auth"}

    permissionID = db.Column(
        "permissionID",
        db.BigInteger,
        primary_key=True,
    )

    permissionCode = db.Column(
        "permissionCode",
        db.String(100),
        nullable=False,
        unique=True,
    )

    name = db.Column(
        "name",
        db.String(150),
        nullable=False,
    )

    description = db.Column(
        "description",
        db.Text,
        nullable=True,
    )

    module = db.Column(
        "module",
        db.String(50),
        nullable=False,
    )
    
    isActive = db.Column(
        "isActive",
        db.Boolean,
        nullable=False,
        server_default=db.true(),
    )