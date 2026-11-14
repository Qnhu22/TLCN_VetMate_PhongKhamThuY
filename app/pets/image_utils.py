import warnings
import io
import uuid
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class PetImageError(ValueError):
    pass


def pet_image_directory():
    directory = (
        Path(current_app.static_folder)
        / "uploads"
        / "pets"
    )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_pet_image(file):
    if file is None or not file.filename:
        return None

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise PetImageError(
            "Chỉ chấp nhận ảnh JPG, PNG hoặc WebP."
        )

    # Đọc tối đa 5 MB + 1 byte để phát hiện file quá lớn.
    data = file.stream.read(MAX_IMAGE_BYTES + 1)

    if len(data) > MAX_IMAGE_BYTES:
        raise PetImageError(
            "Dung lượng ảnh không được vượt quá 5 MB."
        )

    if not data:
        raise PetImageError("File ảnh đang trống.")

    
    try:
        # Biến cảnh báo ảnh quá lớn thành lỗi.
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            # Kiểm tra file ảnh thực sự hợp lệ.
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in ALLOWED_FORMATS:
                    raise PetImageError(
                        "Nội dung file không phải ảnh hợp lệ."
                    )

                source.verify()

            # Mở lại ảnh để xử lý.
            with Image.open(io.BytesIO(data)) as source:
                image = ImageOps.exif_transpose(source)
                image.load()

                if (
                    image.width * image.height
                    > MAX_IMAGE_PIXELS
                ):
                    raise PetImageError(
                        "Độ phân giải ảnh quá lớn."
                    )

                # Chuẩn hóa ảnh thành RGB.
                if image.mode in ("RGBA", "LA") or (
                    image.mode == "P"
                    and "transparency" in image.info
                ):
                    rgba = image.convert("RGBA")

                    background = Image.new(
                        "RGBA",
                        rgba.size,
                        (255, 255, 255, 255),
                    )

                    background.alpha_composite(rgba)
                    image = background.convert("RGB")
                else:
                    image = image.convert("RGB")

                # Giới hạn kích thước ảnh đầu ra.
                image.thumbnail((1600, 1600))

                # Đổi tên ngẫu nhiên.
                filename = f"{uuid.uuid4().hex}.webp"

                destination = (
                    pet_image_directory() / filename
                )

                image.save(
                    destination,
                    format="WEBP",
                    quality=85,
                    method=4,
                )

    except PetImageError:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise PetImageError(
            "Không thể xử lý ảnh. "
            "Vui lòng chọn ảnh hợp lệ khác."
        ) from exc

    return f"uploads/pets/{filename}"



def delete_pet_image(photo_url):
    if not photo_url:
        return

    prefix = "uploads/pets/"

    if not photo_url.startswith(prefix):
        return

    filename = photo_url[len(prefix):]

    # Không xóa file ngoài thư mục quản lý.
    if (
        Path(filename).name != filename
        or not filename.endswith(".webp")
    ):
        return

    try:
        (pet_image_directory() / filename).unlink(
            missing_ok=True
        )
    except OSError:
        current_app.logger.exception(
            "Không thể dọn ảnh thú cưng: %s",
            filename,
        )
