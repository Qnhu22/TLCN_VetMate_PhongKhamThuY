
from app.extensions import db


class Breed(db.Model):
    __tablename__ = "breeds"
    __table_args__ = (
        db.UniqueConstraint(
            "speciesID",
            "name",
            name="uqBreedsSpeciesName",
        ),
        db.UniqueConstraint(
            "breedID",
            "speciesID",
            name="uqBreedsIDSpecies",
        ),
        {"schema": "medical"},
    )

    breedID = db.Column(
        "breedID",
        db.BigInteger,
        primary_key=True,
    )

    speciesID = db.Column(
        "speciesID",
        db.BigInteger,
        db.ForeignKey(
            "medical.species.speciesID",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    name = db.Column(
        "name",
        db.String(120),
        nullable=False,
    )

    isActive = db.Column(
        "isActive",
        db.Boolean,
        nullable=False,
        server_default=db.true(),
    )

    species = db.relationship(
        "Species",
        back_populates="breeds",
        lazy="selectin",
    )
