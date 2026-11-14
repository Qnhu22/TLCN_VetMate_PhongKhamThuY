
from datetime import date

from app.extensions import db
from app.models import Breed, Species


class PetValidationError(ValueError):
    pass


def validate_pet_form(form, current_pet=None):
    name = form.get("name", "").strip()
    species_raw = form.get("speciesID", "").strip()
    breed_raw = form.get("breedID", "").strip()
    sex = form.get("sex", "UNKNOWN").strip()
    birth_raw = form.get("dateOfBirth", "").strip()
    color = form.get("color", "").strip()
    sterilized_raw = form.get("sterilized", "").strip()
    microchip = form.get("microchipNumber", "").strip()
    allergies = form.get("allergies", "").strip()
    chronic = form.get("chronicConditions", "").strip()
    note = form.get("note", "").strip()

    if not 1 <= len(name) <= 150:
        raise PetValidationError(
            "Tên thú cưng phải từ 1 đến 150 ký tự."
        )

    try:
        species_id = int(species_raw)
    except (ValueError, TypeError):
        raise PetValidationError("Vui lòng chọn loài hợp lệ.")

    species = db.session.get(Species, species_id)

    if species is None or not species.isActive:
        raise PetValidationError("Loài không hợp lệ.")

    breed = None

    if breed_raw:
        try:
            breed_id = int(breed_raw)
        except (ValueError, TypeError):
            raise PetValidationError("Giống không hợp lệ.")

        breed = db.session.get(Breed, breed_id)

        if (
            breed is None
            or not breed.isActive
            or breed.speciesID != species.speciesID
        ):
            raise PetValidationError(
                "Giống không thuộc loài đã chọn."
            )

    if sex not in {"MALE", "FEMALE", "UNKNOWN"}:
        raise PetValidationError("Giới tính không hợp lệ.")

    birth_date = None

    if birth_raw:
        try:
            birth_date = date.fromisoformat(birth_raw)
        except ValueError:
            raise PetValidationError("Ngày sinh không hợp lệ.")

        if birth_date > date.today():
            raise PetValidationError(
                "Ngày sinh không được ở tương lai."
            )

    if len(color) > 100:
        raise PetValidationError(
            "Màu lông không được quá 100 ký tự."
        )

    if sterilized_raw not in {"", "true", "false"}:
        raise PetValidationError(
            "Trạng thái triệt sản không hợp lệ."
        )

    sterilized = (
        None if sterilized_raw == ""
        else sterilized_raw == "true"
    )

    if len(microchip) > 100:
        raise PetValidationError(
            "Mã microchip không được quá 100 ký tự."
        )

    if microchip:
        from app.models import Pet

        existing = Pet.query.filter_by(
            microchipNumber=microchip
        ).first()

        if existing and (
            current_pet is None
            or existing.petID != current_pet.petID
        ):
            raise PetValidationError(
                "Mã microchip đã được sử dụng."
            )

    if len(allergies) > 2000:
        raise PetValidationError(
            "Thông tin dị ứng quá dài."
        )

    if len(chronic) > 2000:
        raise PetValidationError(
            "Thông tin bệnh mãn tính quá dài."
        )

    if len(note) > 2000:
        raise PetValidationError(
            "Ghi chú không được quá 2000 ký tự."
        )

    return {
        "name": name,
        "speciesID": species.speciesID,
        "breedID": breed.breedID if breed else None,
        "sex": sex,
        "dateOfBirth": birth_date,
        "color": color or None,
        "sterilized": sterilized,
        "microchipNumber": microchip or None,
        "allergies": allergies or None,
        "chronicConditions": chronic or None,
        "note": note or None,
    }
