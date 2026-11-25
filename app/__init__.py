import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from app.extensions import (
    db,
    login_manager,
    mail,
    limiter,
)

load_dotenv()
def create_app() -> Flask:
    """Khởi tạo ứng dụng VetMate."""

    load_dotenv()

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "vetmate-development-secret-key",
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    app.config["MAX_CONTENT_LENGTH"] = (
    6 * 1024 * 1024
)
    
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower()
        == "true"
    )
    
    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(error):
        if request.path.startswith("/pets/"):
            flash(
                "Ảnh hoặc dữ liệu gửi lên quá lớn. "
                "Vui lòng chọn ảnh dưới 5 MB.",
                "error",
            )
            return redirect(url_for("pets.index")), 303

        return (
            "Dữ liệu gửi lên vượt quá giới hạn cho phép.",
            413,
        )


    db.init_app(app)
    login_manager.init_app(app)

    # Lưu bộ đếm giới hạn yêu cầu trong RAM khi phát triển
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"

    limiter.init_app(app)
    
    app.config["MAIL_SERVER"] = os.getenv(
        "MAIL_SERVER",
        "smtp.gmail.com",
    )

    app.config["MAIL_PORT"] = int(
        os.getenv(
            "MAIL_PORT",
            "587",
        )
    )

    app.config["MAIL_USE_TLS"] = (
        os.getenv(
            "MAIL_USE_TLS",
            "true",
        ).lower()
        == "true"
    )

    app.config["MAIL_USERNAME"] = os.getenv(
        "MAIL_USERNAME"
    )

    app.config["MAIL_PASSWORD"] = os.getenv(
        "MAIL_PASSWORD"
    )

    app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
        "MAIL_DEFAULT_SENDER"
    )
    mail.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(
            User,
            int(user_id),
        )

    from app.main import main_bp
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.account import account_bp
    from app.pets import pets_bp
    from app.receptionist import receptionist_bp
    from app.veterinarian import veterinarian_bp
    from app.booking import booking_bp

    from app.booking import routes as booking_routes

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(pets_bp)
    app.register_blueprint(receptionist_bp)
    app.register_blueprint(veterinarian_bp)
    app.register_blueprint(booking_bp)

    return app
