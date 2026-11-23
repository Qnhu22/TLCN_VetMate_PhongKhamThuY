
from app.extensions import db


class Service(db.Model):
    __tablename__ = "services"
    __table_args__ = {"schema": "clinic"}

    serviceID = db.Column("serviceID", db.BigInteger, primary_key=True)
    categoryID = db.Column("categoryID", db.BigInteger, nullable=False)
    serviceCode = db.Column("serviceCode", db.String(30), nullable=False, unique=True)
    name = db.Column("name", db.String(200), nullable=False)
    description = db.Column("description", db.Text)
    price = db.Column("price", db.Numeric(14, 2), nullable=False)
    defaultDurationMinutes = db.Column("defaultDurationMinutes", db.Integer, nullable=False)
    requiresVeterinarian = db.Column("requiresVeterinarian", db.Boolean, nullable=False)
    isBookable = db.Column("isBookable", db.Boolean, nullable=False)
    isEmergency = db.Column("isEmergency", db.Boolean, nullable=False)
    status = db.Column("status", db.String(20), nullable=False)
    createdAt = db.Column("createdAt", db.DateTime(timezone=True))
    updatedAt = db.Column("updatedAt", db.DateTime(timezone=True))
