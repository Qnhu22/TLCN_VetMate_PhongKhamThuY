from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    userID = db.Column(
        "userID",
        db.BigInteger,
        primary_key=True,
    )

    email = db.Column(
        "email",
        db.String(255),
        nullable=False,
        unique=True,
    )

    passwordHash = db.Column(
        "passwordHash",
        db.String(255),
        nullable=False,
    )

    fullName = db.Column(
        "fullName",
        db.String(150),
        nullable=False,
    )

    phone = db.Column(
        "phone",
        db.String(20),
        nullable=True,
    )

    avatarUrl = db.Column(
        "avatarUrl",
        db.Text,
        nullable=True,
    )

    status = db.Column(
        "status",
        db.String(30),
        nullable=False,
    )

    lastLoginAt = db.Column(
        "lastLoginAt",
        db.DateTime(timezone=True),
        nullable=True,
    )

    createdAt = db.Column(
    "createdAt",
    db.DateTime(timezone=True),
    nullable=False,
    server_default=db.func.now(),
)

    updatedAt = db.Column(
    "updatedAt",
    db.DateTime(timezone=True),
    nullable=False,
    server_default=db.func.now(),
    onupdate=db.func.now(),
)
    
    roles = db.relationship(
    "Role",
    secondary="auth.userRoles",
    lazy="selectin",
)

    def get_id(self):
        return str(self.userID)
    
    def has_role(self, role_code):
        return any(
            role.roleCode == role_code
            and role.isActive
            for role in self.roles
        )
        
    def has_permission(self, permission_code):
        return any(
            permission.permissionCode == permission_code
            and permission.isActive
            for role in self.roles
            if role.isActive
            for permission in role.permissions
        )