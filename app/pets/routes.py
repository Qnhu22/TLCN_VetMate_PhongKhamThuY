from app.pets.csrf import pet_csrf_token, validate_pet_csrf
from datetime import date
from sqlalchemy import or_

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)


from app.pets.image_utils import (
    PetImageError,
    save_pet_image,
    delete_pet_image,
)
from app.pets.validation import (
    PetValidationError,
    validate_pet_form,
)

from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import OwnerProfile, Pet, Species, Breed
from app.pets import pets_bp


def require_pet_owner():
    if not current_user.has_role("PET_OWNER"):
        abort(403)

    if current_user.status != "ACTIVE":
        abort(403)


def get_owner():
    return OwnerProfile.query.filter_by(
        userID=current_user.userID
    ).first()

@pets_bp.get("/")
@login_required
def index():
    require_pet_owner()

    owner = get_owner()

    # Lấy tham số tìm kiếm và bộ lọc
    keyword = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    species_id = request.args.get("species", "").strip()

    allowed_statuses = {"ACTIVE", "INACTIVE", "DECEASED"}

    if status not in allowed_statuses:
        status = ""

    # Danh sách loài để hiển thị bộ lọc
    species_list = (
        Species.query
        .order_by(Species.name)
        .all()
    )

    pets = []
    total_pets = 0

    if owner is not None:
        query = Pet.query.filter(
            Pet.ownerID == owner.ownerID
        )

        # Đếm tổng hồ sơ trước khi lọc
        total_pets = query.count()

        # Tìm theo tên hoặc mã thú cưng
        if keyword:
            query = query.filter(
                or_(
                    Pet.name.ilike(f"%{keyword}%"),
                    Pet.petCode.ilike(f"%{keyword}%"),
                )
            )

        # Lọc theo trạng thái
        if status:
            query = query.filter(
                Pet.status == status
            )

        # Lọc theo loài
        if species_id.isdigit():
            query = query.filter(
                Pet.speciesID == int(species_id)
            )
        else:
            species_id = ""

        pets = (
            query
            .order_by(
                Pet.createdAt.desc(),
                Pet.petID.desc()
            )
            .all()
        )

    return render_template(
        "pets/index.html",
        pets=pets,
        species_list=species_list,
        keyword=keyword,
        selected_status=status,
        selected_species=species_id,
        total_pets=total_pets,
        today=date.today(),
    )

@pets_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    require_pet_owner()

    species_list = (
        Species.query
        .filter_by(isActive=True)
        .order_by(Species.name)
        .all()
    )

    breeds = (
        Breed.query
        .filter_by(isActive=True)
        .order_by(Breed.name)
        .all()
    )

    if request.method == "POST":
        # Kiểm tra CSRF trước khi xử lý dữ liệu.
        validate_pet_csrf()

        new_photo = None

        try:
            # Kiểm tra dữ liệu thú cưng.
            data = validate_pet_form(request.form)

            # Kiểm tra và lưu ảnh nếu người dùng chọn.
            photo_file = request.files.get("photo")

            if photo_file and photo_file.filename:
                new_photo = save_pet_image(photo_file)

            # Lấy hồ sơ chủ nuôi.
            owner = get_owner()

            if owner is None:
                owner = OwnerProfile(
                    userID=current_user.userID
                )
                db.session.add(owner)
                db.session.flush()

            # Tạo thú cưng.
            pet = Pet(
                ownerID=owner.ownerID,
                **data,
                photoUrl=new_photo,
            )

            db.session.add(pet)
            db.session.commit()

        except (PetValidationError, PetImageError) as exc:
            db.session.rollback()
            flash(str(exc), "error")

        except IntegrityError:
            db.session.rollback()
            flash(
                "Dữ liệu thú cưng bị trùng "
                "hoặc không hợp lệ.",
                "error",
            )

        except Exception:
            db.session.rollback()
            flash(
                "Không thể thêm thú cưng. "
                "Vui lòng thử lại.",
                "error",
            )

        else:
            flash(
                "Thêm thú cưng thành công!",
                "success",
            )

            return redirect(
                url_for("pets.index")
            )

        # Chỉ chạy khi lưu thất bại.
        # Xóa file mới để tránh ảnh rác.
        if new_photo:
            delete_pet_image(new_photo)

    return render_template(
        "pets/create.html",
        species_list=species_list,
        breeds=breeds,
        form_data=(
            request.form
            if request.method == "POST"
            else {}
        ),
        csrf_token=pet_csrf_token(),
    )


@pets_bp.get("/<int:pet_id>")
@login_required
def detail(pet_id):
    require_pet_owner()

    owner = get_owner()

    if owner is None:
        abort(404)

    pet = (
        Pet.query
        .filter_by(
            petID=pet_id,
            ownerID=owner.ownerID,
        )
        .first_or_404()
    )

    return render_template(
        "pets/detail.html",
        pet=pet,
        csrf_token=pet_csrf_token(),
    )


@pets_bp.route(
    "/<int:pet_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit(pet_id):
    require_pet_owner()

    owner = get_owner()

    if owner is None:
        abort(404)

    pet = (
        Pet.query
        .filter_by(
            petID=pet_id,
            ownerID=owner.ownerID,
        )
        .first_or_404()
    )

    species_list = (
        Species.query
        .filter_by(isActive=True)
        .order_by(Species.name)
        .all()
    )

    breeds = (
        Breed.query
        .filter_by(isActive=True)
        .order_by(Breed.name)
        .all()
    )

    if request.method == "POST":
        validate_pet_csrf()
        new_photo = None
        old_photo = pet.photoUrl

        try:
            data = validate_pet_form(
                request.form,
                current_pet=pet,
            )

            photo_file = request.files.get("photo")
            remove_photo = (
                request.form.get("removePhoto") == "1"
            )

            if photo_file and photo_file.filename:
                new_photo = save_pet_image(photo_file)

            for field, value in data.items():
                setattr(pet, field, value)

            if new_photo:
                pet.photoUrl = new_photo
            elif remove_photo:
                pet.photoUrl = None

            db.session.commit()

        except PetValidationError as exc:
            db.session.rollback()
            flash(str(exc), "error")

        except PetImageError as exc:
            db.session.rollback()
            flash(str(exc), "error")

        except IntegrityError:
            db.session.rollback()
            flash(
                "Dữ liệu bị trùng hoặc không hợp lệ.",
                "error",
            )

        except Exception:
            db.session.rollback()
            flash(
                "Không thể cập nhật thú cưng.",
                "error",
            )

        else:
            if old_photo and old_photo != pet.photoUrl:
                delete_pet_image(old_photo)

            flash(
                "Cập nhật hồ sơ thú cưng thành công!",
                "success",
            )
            return redirect(
                url_for("pets.detail", pet_id=pet.petID)
            )

        # Nếu giao dịch thất bại, xóa ảnh mới
        # để không để lại file rác.
        if new_photo:
            delete_pet_image(new_photo)

    return render_template(
        "pets/edit.html",
        csrf_token=pet_csrf_token(),
        pet=pet,
        species_list=species_list,
        breeds=breeds,
        form_data=(
            request.form
            if request.method == "POST"
            else None
        ),
    )


@pets_bp.post("/<int:pet_id>/status")
@login_required
def change_status(pet_id):
    require_pet_owner()
    validate_pet_csrf()

    owner = get_owner()

    if owner is None:
        abort(404)

    pet = (
        Pet.query
        .filter_by(
            petID=pet_id,
            ownerID=owner.ownerID,
        )
        .first_or_404()
    )

    action = request.form.get("action", "").strip()

    if action == "deactivate":
        if pet.status != "ACTIVE":
            flash(
                "Hồ sơ thú cưng không ở trạng thái hoạt động.",
                "warning",
            )
            return redirect(
                url_for("pets.detail", pet_id=pet.petID)
            )

        pet.status = "INACTIVE"
        success_message = (
            "Đã ngừng quản lý hồ sơ thú cưng."
        )

    elif action == "activate":
        if pet.status != "INACTIVE":
            flash(
                "Hồ sơ thú cưng không ở trạng thái "
                "có thể khôi phục.",
                "warning",
            )
            return redirect(
                url_for("pets.detail", pet_id=pet.petID)
            )

        pet.status = "ACTIVE"
        success_message = (
            "Đã khôi phục hồ sơ thú cưng thành công!"
        )

    else:
        abort(400, description="Thao tác không hợp lệ.")

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()
        flash(
            "Không thể cập nhật trạng thái thú cưng. "
            "Vui lòng thử lại.",
            "error",
        )

    else:
        flash(success_message, "success")

    return redirect(
        url_for("pets.detail", pet_id=pet.petID)
    )
