
from app.extensions import db


class Pet(db.Model):
    __tablename__ = "pets"

    __table_args__ = (
        db.ForeignKeyConstraint(
            ["breedID", "speciesID"],
            [
                "medical.breeds.breedID",
                "medical.breeds.speciesID",
            ],
            name="fkPetsBreedSpecies",
            ondelete="RESTRICT",
        ),
        {"schema": "medical"},
    )

    petID = db.Column(
        "petID",
        db.BigInteger,
        primary_key=True,
    )

    ownerID = db.Column(
        "ownerID",
        db.BigInteger,
        db.ForeignKey(
            "medical.ownerProfiles.ownerID",
            ondelete="RESTRICT",
        ),
        nullable=False,
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

    breedID = db.Column(
        "breedID",
        db.BigInteger,
        nullable=True,
    )

    name = db.Column(
        "name",
        db.String(150),
        nullable=False,
    )

    petCode = db.Column(
        "petCode",
        db.String(30),
        nullable=False,
        unique=True,
    )

    sex = db.Column(
        "sex",
        db.String(10),
        nullable=False,
        server_default="UNKNOWN",
    )

    dateOfBirth = db.Column(
        "dateOfBirth",
        db.Date,
        nullable=True,
    )

    color = db.Column(
        "color",
        db.String(100),
        nullable=True,
    )

    sterilized = db.Column(
        "sterilized",
        db.Boolean,
        nullable=True,
    )

    microchipNumber = db.Column(
        "microchipNumber",
        db.String(100),
        nullable=True,
        unique=True,
    )

    photoUrl = db.Column(
        "photoUrl",
        db.Text,
        nullable=True,
    )

    allergies = db.Column(
        "allergies",
        db.Text,
        nullable=True,
    )

    chronicConditions = db.Column(
        "chronicConditions",
        db.Text,
        nullable=True,
    )

    publicToken = db.Column(
        "publicToken",
        db.String(128),
        nullable=False,
        unique=True,
    )

    status = db.Column(
        "status",
        db.String(20),
        nullable=False,
        server_default="ACTIVE",
    )

    note = db.Column(
        "note",
        db.Text,
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

    owner = db.relationship(
        "OwnerProfile",
        back_populates="pets",
        lazy="selectin",
    )

    species = db.relationship(
        "Species",
        foreign_keys=[speciesID],
        lazy="selectin",
    )

    breed = db.relationship(
        "Breed",
        primaryjoin=(
            "and_("
            "Pet.breedID == Breed.breedID, "
            "Pet.speciesID == Breed.speciesID"
            ")"
        ),
        foreign_keys=[breedID, speciesID],
        viewonly=True,
        lazy="selectin",
    )
