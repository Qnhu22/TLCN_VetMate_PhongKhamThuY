from app.extensions import db


class RolePermission(db.Model):
    __tablename__ = "rolePermissions"
    __table_args__ = {"schema": "auth"}

    roleID = db.Column(
        "roleID",
        db.BigInteger,
        db.ForeignKey(
            "auth.roles.roleID",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    permissionID = db.Column(
        "permissionID",
        db.BigInteger,
        db.ForeignKey(
            "auth.permissions.permissionID",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )