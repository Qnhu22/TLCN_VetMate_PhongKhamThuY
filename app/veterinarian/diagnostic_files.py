"""Private, normalized image attachments. No original filename becomes a path."""
import io
import re
import warnings
from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000


def directory():
    return Path(current_app.config.get("VET_DIAGNOSTIC_UPLOAD_DIR",
        Path(current_app.instance_path) / "private" / "diagnostics"))


def private_path(key):
    if not key or not re.fullmatch(r"[a-f0-9]{32}\.webp", key):
        return None
    root = directory().resolve()
    path = (root / key).resolve()
    return path if path.parent == root else None


def delete_attachment(key):
    path = private_path(key)
    if path:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Không thể dọn tệp kết quả xét nghiệm")


def save_attachment(file):
    if file is None or not file.filename:
        return None
    if Path(file.filename).suffix.lower() not in (".jpg", ".jpeg", ".png"):
        raise ValueError("Tệp kết quả chỉ hỗ trợ ảnh JPG/PNG, tối đa 5 MB.")
    data = file.stream.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Ảnh kết quả trống hoặc vượt quá 5 MB.")
    key = uuid4().hex + ".webp"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ("JPEG", "PNG") or image.width * image.height > MAX_PIXELS:
                    raise ValueError("Nội dung ảnh hoặc độ phân giải không hợp lệ.")
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                normalized.load()
                directory().mkdir(parents=True, exist_ok=True)
                # Keep resolution for legibility; re-encode to strip metadata/payload.
                normalized.save(directory() / key, "WEBP", lossless=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        delete_attachment(key)
        raise ValueError("Không thể lưu ảnh kết quả hợp lệ. Vui lòng chọn ảnh JPG/PNG khác.") from exc
    return key
