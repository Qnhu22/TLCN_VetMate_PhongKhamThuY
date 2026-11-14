from flask import Blueprint


main_bp = Blueprint(
    "main",
    __name__,
)


# Phải import routes sau khi tạo main_bp
from app.main import routes