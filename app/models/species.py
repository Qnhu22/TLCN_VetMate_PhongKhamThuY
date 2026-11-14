
from app.extensions import db


class Species(db.Model):
    __tablename__ = "species"
    __table_args__ = {"schema": "medical"}

    speciesID = db.Column(
        "speciesID",
        db.BigInteger,
        primary_key=True,
    )

    name = db.Column(
        "name",
        db.String(100),
        nullable=False,
        unique=True,
    )

    isActive = db.Column(
        "isActive",
        db.Boolean,
        nullable=False,
        server_default=db.true(),
    )

    breeds = db.relationship(
        "Breed",
        back_populates="species",
        lazy="selectin",
    )
