import re
from datetime import datetime, timezone

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
    session,
    current_app,
)
from flask_login import (
    current_user,
    login_user,
    logout_user,
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from app.auth.otp_service import (
    EMAIL_VERIFICATION,
    OTP_RESEND_COOLDOWN_SECONDS,
    PASSWORD_RESET,
    CUSTOMER_ACTIVATION,
    create_otp_token,
    get_active_token,
    mark_token_used,
    verify_otp,
    verify_customer_activation_otp,
    can_resend_customer_activation,
)

from app.auth.csrf import (
    get_activation_csrf_token,
    validate_activation_csrf,
)

from app.auth.email_service import (
    send_verification_otp,
    send_password_reset_otp,
    send_customer_activation_otp,
)
from app.auth import auth_bp
from app.extensions import db
from app.models import (
    Role,
    User,
    OwnerProfile,
)
from app.models.verification_token import VerificationToken

def get_default_route(user):
    if user.has_role("SYSTEM_ADMIN"):
        return url_for("admin.dashboard")

    return url_for("main.home")

def get_password_reset_user():
    """Lấy user đang thực hiện quy trình reset mật khẩu."""

    user_id = session.get(
        "password_reset_user_id"
    )

    if not user_id:
        return None

    return db.session.get(
        User,
        user_id,
    )


def clear_password_reset_session():
    """Xóa trạng thái reset mật khẩu khỏi session."""

    session.pop(
        "password_reset_user_id",
        None,
    )

    session.pop(
        "password_reset_verified",
        None,
    )
    
EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def is_valid_email(email):
    """Kiểm tra định dạng email cơ bản."""

    if not email:
        return False

    return bool(
        EMAIL_PATTERN.fullmatch(
            email.strip()
        )
    )

@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    """Đăng nhập vào VetMate."""

    if current_user.is_authenticated:
        return redirect(
            get_default_route(current_user)
        )

    if request.method == "POST":
        email = (
            request.form
            .get("email", "")
            .strip()
            .lower()
        )

        password = request.form.get(
            "password",
            "",
        )

        remember = (
            request.form.get("remember")
            == "on"
        )

        if not email or not password:
            flash(
                "Vui lòng nhập email và mật khẩu.",
                "error",
            )

            return render_template(
                "auth/login.html"
            )

        user = User.query.filter_by(
            email=email
        ).first()

        if (
            user is None
            or not check_password_hash(
                user.passwordHash,
                password,
            )
        ):
            flash(
                "Email hoặc mật khẩu không đúng.",
                "error",
            )

            return render_template(
                "auth/login.html"
            )

        if user.status == "PENDING_VERIFICATION":
            flash(
                "Tài khoản chưa xác minh email.",
                "warning",
            )

            return render_template(
                "auth/login.html"
            )

        if user.status == "LOCKED":
            flash(
                "Tài khoản đang bị khóa.",
                "error",
            )

            return render_template(
                "auth/login.html"
            )

        if user.status == "INACTIVE":
            flash(
                "Tài khoản hiện không hoạt động.",
                "error",
            )

            return render_template(
                "auth/login.html"
            )

        login_user(user, remember=remember)

        user.lastLoginAt = datetime.now(timezone.utc)
        db.session.commit()

        return redirect(get_default_route(user))

    return render_template(
        "auth/login.html"
    )
    
@auth_bp.route(
    "/forgot-password",
    methods=["GET", "POST"],
)
def forgot_password():
    if current_user.is_authenticated:
        return redirect(
            get_default_route(
                current_user
            )
        )

    if request.method == "GET":
        clear_password_reset_session()

        return render_template(
            "auth/forgot_password.html",
            email="",
        )

    email = (
        request.form.get(
            "email",
            ""
        )
        .strip()
        .lower()
    )

    if not email:
        return render_template(
            "auth/forgot_password.html",
            email=email,
            error="Vui lòng nhập email.",
        )

    if not is_valid_email(email):
        return render_template(
            "auth/forgot_password.html",
            email=email,
            error=(
                "Vui lòng nhập địa chỉ "
                "email hợp lệ."
            ),
        )

    user = (
        User.query
        .filter(
            db.func.lower(
                User.email
            )
            == email
        )
        .first()
    )

    # Không tiết lộ email có tồn tại hay không.
    if user is None:
        flash(
            (
                "Nếu email này được đăng ký "
                "với VetMate, mã xác minh "
                "sẽ được gửi đến email đó."
            ),
            "success",
        )

        return render_template(
            "auth/forgot_password.html",
            email="",
        )

    # Reset mật khẩu không được dùng để
    # vượt qua trạng thái khóa/vô hiệu hóa.
    if user.status in {
        "LOCKED",
        "INACTIVE",
    }:
        flash(
            (
                "Nếu tài khoản đủ điều kiện "
                "khôi phục, VetMate sẽ gửi "
                "hướng dẫn đến email đã đăng ký."
            ),
            "success",
        )

        return render_template(
            "auth/forgot_password.html",
            email="",
        )

    # Tài khoản chưa xác minh email không đi
    # qua quy trình reset password.
    if user.status == "PENDING_VERIFICATION":
        flash(
            (
                "Tài khoản này chưa hoàn tất "
                "xác minh email."
            ),
            "warning",
        )

        return render_template(
            "auth/forgot_password.html",
            email=email,
        )

    try:
        otp, token = create_otp_token(
            user.userID,
            PASSWORD_RESET,
        )

        send_password_reset_otp(
            recipient_email=user.email,
            full_name=user.fullName,
            otp=otp,
        )

        db.session.commit()

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Không thể gửi OTP reset password."
        )

        return render_template(
            "auth/forgot_password.html",
            email=email,
            error=(
                "VetMate chưa thể gửi mã "
                "xác minh lúc này. "
                "Vui lòng thử lại."
            ),
        )

    clear_password_reset_session()

    session[
        "password_reset_user_id"
    ] = user.userID

    session[
        "password_reset_verified"
    ] = False

    return redirect(
        url_for(
            "auth.verify_reset_otp"
        )
    )

@auth_bp.route(
    "/register",
    methods=["GET", "POST"],
)
def register():
    """Đăng ký tài khoản chủ nuôi VetMate."""

    if current_user.is_authenticated:
        return redirect(
            get_default_route(current_user)
        )

    errors = {}

    form_data = {
        "fullName": "",
        "email": "",
        "phone": "",
    }

    if request.method == "POST":

        full_name = (
            request.form
            .get("fullName", "")
            .strip()
        )

        email = (
            request.form
            .get("email", "")
            .strip()
            .lower()
        )

        phone = (
            request.form
            .get("phone", "")
            .strip()
        )

        password = request.form.get(
            "password",
            "",
        )

        confirm_password = request.form.get(
            "confirmPassword",
            "",
        )

        terms_accepted = (
            request.form.get("termsAccepted")
            == "on"
        )

        form_data = {
            "fullName": full_name,
            "email": email,
            "phone": phone,
        }


        # =============================================
        # FULL NAME
        # =============================================

        if len(full_name) < 2:
            errors["fullName"] = (
                "Họ và tên phải có ít nhất 2 ký tự."
            )

        elif len(full_name) > 150:
            errors["fullName"] = (
                "Họ và tên không được vượt quá "
                "150 ký tự."
            )


        # =============================================
        # EMAIL
        # =============================================

        if not is_valid_email(email):
            errors["email"] = (
                "Vui lòng nhập email hợp lệ."
            )


        # =============================================
        # PHONE
        # =============================================

        if not re.fullmatch(
            r"0\d{9}",
            phone,
        ):
            errors["phone"] = (
                "Số điện thoại phải gồm 10 số "
                "và bắt đầu bằng 0."
            )


        # =============================================
        # PASSWORD
        # =============================================

        if len(password) < 8:
            errors["password"] = (
                "Mật khẩu phải có ít nhất 8 ký tự."
            )


        # =============================================
        # CONFIRM PASSWORD
        # =============================================

        if confirm_password != password:
            errors["confirmPassword"] = (
                "Mật khẩu xác nhận không khớp."
            )


        # =============================================
        # TERMS
        # =============================================

        if not terms_accepted:
            errors["terms"] = (
                "Bạn cần đồng ý với điều khoản "
                "để tiếp tục."
            )


        # =============================================
        # EXISTING EMAIL
        # =============================================

        existing_user = None

        if "email" not in errors:

            existing_user = (
                User.query
                .filter_by(email=email)
                .first()
            )

            if existing_user:

                if (
                    existing_user.status
                    == "PENDING_VERIFICATION"
                ):
                    session[
                        "verification_user_id"
                    ] = existing_user.userID

                    flash(
                        "Email này đang chờ xác minh. "
                        "Bạn có thể tiếp tục nhập OTP "
                        "hoặc gửi lại mã.",
                        "warning",
                    )

                    return redirect(
                        url_for("auth.verify_email")
                    )

                else:
                    errors["email"] = (
                        "Email này đã được sử dụng."
                    )


        # =============================================
        # VALIDATION FAILED
        # =============================================

        if errors:
            return render_template(
                "auth/register.html",
                errors=errors,
                form_data=form_data,
                terms_accepted=terms_accepted,
            )


        # =============================================
        # CREATE USER
        # =============================================

        try:
            user = User(
                email=email,
                passwordHash=generate_password_hash(
                    password
                ),
                fullName=full_name,
                phone=phone,
                status="PENDING_VERIFICATION",
            )

            db.session.add(user)
            db.session.flush()

            otp, verification_token = (
                create_otp_token(
                    user.userID,
                    EMAIL_VERIFICATION,
                )
            )

            db.session.commit()

        except Exception as exc:
            db.session.rollback()

            print(
                "[REGISTER ERROR]",
                repr(exc),
            )

            errors["general"] = (
                "Không thể tạo tài khoản lúc này. "
                "Vui lòng thử lại."
            )

            return render_template(
                "auth/register.html",
                errors=errors,
                form_data=form_data,
                terms_accepted=terms_accepted,
            )

        try:
            send_verification_otp(
                recipient_email=user.email,
                full_name=user.fullName,
                otp=otp,
            )

        except Exception as exc:
            print(
                "[MAIL ERROR]",
                repr(exc),
            )

            errors["general"] = (
                "Tài khoản đã được tạo nhưng "
                "chưa thể gửi mã xác minh. "
                "Vui lòng thử gửi lại OTP."
            )

            return render_template(
                "auth/register.html",
                errors=errors,
                form_data=form_data,
                terms_accepted=terms_accepted,
            )

        # =============================================
        # TEMPORARY SUCCESS
        # =============================================

        flash(
            "Tài khoản đã được tạo và đang chờ "
            "xác minh email.",
            "success",
        )

        session["verification_user_id"] = (
            user.userID
        )

        return redirect(
            url_for("auth.verify_email")
        )


    return render_template(
        "auth/register.html",
        errors={},
        form_data=form_data,
        terms_accepted=False,
    )
    
@auth_bp.route(
    "/verify-email",
    methods=["GET", "POST"],
)
def verify_email():
    """Xác minh email bằng OTP."""

    if current_user.is_authenticated:
        return redirect(
            get_default_route(current_user)
        )

    user_id = session.get(
        "verification_user_id"
    )

    if not user_id:
        flash(
            "Phiên xác minh không hợp lệ. "
            "Vui lòng đăng ký hoặc đăng nhập lại.",
            "warning",
        )

        return redirect(
            url_for("auth.register")
        )

    user = db.session.get(
        User,
        user_id,
    )

    if user is None:
        session.pop(
            "verification_user_id",
            None,
        )

        return redirect(
            url_for("auth.register")
        )

    if (
        user.status
        != "PENDING_VERIFICATION"
    ):
        session.pop(
            "verification_user_id",
            None,
        )

        return redirect(
            url_for("auth.login")
        )

    error = None

    if request.method == "POST":

        otp = (
            request.form
            .get("otp", "")
            .strip()
        )

        if (
            not otp.isdigit()
            or len(otp) != 6
        ):
            error = (
                "Vui lòng nhập đầy đủ "
                "mã xác minh gồm 6 chữ số."
            )

        else:
            valid, result = verify_otp(
                user.userID,
                EMAIL_VERIFICATION,
                otp,
            )

            if not valid:

                if result == "EXPIRED":
                    error = (
                        "Mã xác minh đã hết hạn. "
                        "Vui lòng gửi lại mã mới."
                    )

                elif result == "NOT_FOUND":
                    error = (
                        "Không tìm thấy mã xác minh "
                        "còn hiệu lực. "
                        "Vui lòng gửi lại mã."
                    )

                else:
                    error = (
                        "Mã xác minh không chính xác."
                    )

            else:
                token = get_active_token(
                user.userID,
                EMAIL_VERIFICATION,
                )

                if token is None:
                    error = (
                        "Mã xác minh không còn "
                        "hiệu lực."
                    )

                else:
                    try:
                        pet_owner_role = (
                            Role.query
                            .filter_by(
                                roleCode="PET_OWNER",
                                isActive=True,
                            )
                            .first()
                        )

                        if pet_owner_role is None:
                            raise RuntimeError(
                                "Không tìm thấy role "
                                "PET_OWNER đang hoạt động."
                            )

                        # Đánh dấu OTP đã sử dụng.
                        mark_token_used(token)

                        # Kích hoạt tài khoản.
                        user.status = "ACTIVE"

                        # Public registration luôn là PET_OWNER.
                        if not user.has_role("PET_OWNER"):
                            user.roles.append(pet_owner_role)

                        # Tự động tạo hồ sơ chủ nuôi sau khi xác minh OTP.
                        owner = OwnerProfile.query.filter_by(
                            userID=user.userID
                        ).first()

                        if owner is None:
                            owner = OwnerProfile(
                                userID=user.userID
                            )
                            db.session.add(owner)

                        db.session.commit()

                    except Exception as exc:
                        db.session.rollback()

                        print(
                            "[VERIFY EMAIL ERROR]",
                            repr(exc),
                        )

                        error = (
                            "Không thể hoàn tất xác minh "
                            "tài khoản lúc này. "
                            "Vui lòng thử lại."
                        )

                    else:
                        session.pop(
                            "verification_user_id",
                            None,
                        )

                        session[
                            "registration_completed_user_id"
                        ] = user.userID

                        return redirect(
                            url_for(
                                "auth.register_success"
                            )
                        )

    token = get_active_token(
        user.userID,
        EMAIL_VERIFICATION,
    )

    expires_at = None
    resend_available_at = None

    if token is not None:
        expires_at = (
            token.expiresAt.isoformat()
        )

        if token.createdAt:
            created_at = token.createdAt

            if created_at.tzinfo is None:
                created_at = (
                    created_at.replace(
                        tzinfo=timezone.utc
                    )
                )

            resend_available_at = (
                created_at.timestamp()
                + OTP_RESEND_COOLDOWN_SECONDS
            )

    return render_template(
        "auth/verify_email.html",
        user=user,
        error=error,
        expires_at=expires_at,
        resend_available_at=resend_available_at,
    )
    
@auth_bp.post("/resend-verification")
def resend_verification():
    """Gửi lại OTP xác minh email."""

    user_id = session.get(
        "verification_user_id"
    )

    if not user_id:
        return redirect(
            url_for("auth.register")
        )

    user = db.session.get(
        User,
        user_id,
    )

    if (
        user is None
        or user.status
        != "PENDING_VERIFICATION"
    ):
        session.pop(
            "verification_user_id",
            None,
        )

        return redirect(
            url_for("auth.register")
        )

    active_token = get_active_token(
        user.userID,
        EMAIL_VERIFICATION,
    )

    now = datetime.now(
        timezone.utc
    )

    # =============================================
    # RESEND COOLDOWN - 30 SECONDS
    # =============================================

    if (
        active_token is not None
        and active_token.createdAt
    ):
        created_at = (
            active_token.createdAt
        )

        if created_at.tzinfo is None:
            created_at = (
                created_at.replace(
                    tzinfo=timezone.utc
                )
            )

        elapsed = (
            now - created_at
        ).total_seconds()

        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            return redirect(
                url_for(
                    "auth.verify_email"
                )
            )

    # =============================================
    # CREATE NEW OTP
    # =============================================

    try:
        otp, token = create_otp_token(
            user.userID,
            EMAIL_VERIFICATION,
        )

        db.session.commit()

    except Exception as exc:
        db.session.rollback()

        print(
            "[OTP RESEND ERROR]",
            repr(exc),
        )

        flash(
            "Không thể tạo mã xác minh mới.",
            "error",
        )

        return redirect(
            url_for("auth.verify_email")
        )

    # =============================================
    # SEND EMAIL
    # =============================================

    try:
        send_verification_otp(
            recipient_email=user.email,
            full_name=user.fullName,
            otp=otp,
        )

    except Exception as exc:

        print(
            "[MAIL RESEND ERROR]",
            repr(exc),
        )

        flash(
            "Chưa thể gửi mã xác minh. "
            "Vui lòng thử lại sau.",
            "error",
        )

        return redirect(
            url_for("auth.verify_email")
        )

    flash(
        "Mã xác minh mới đã được gửi.",
        "success",
    )

    return redirect(
        url_for("auth.verify_email")
    )
    
@auth_bp.get("/register-success")
def register_success():
    """Trang hoàn tất đăng ký."""

    if current_user.is_authenticated:
        return redirect(
            get_default_route(
                current_user
            )
        )

    user_id = session.get(
        "registration_completed_user_id"
    )

    if not user_id:
        return redirect(
            url_for("auth.login")
        )

    user = db.session.get(
        User,
        user_id,
    )

    if (
        user is None
        or user.status != "ACTIVE"
        or not user.has_role("PET_OWNER")
    ):
        session.pop(
            "registration_completed_user_id",
            None,
        )

        return redirect(
            url_for("auth.login")
        )

    response = render_template(
        "auth/register_success.html",
        user=user,
    )

    return response

@auth_bp.route(
    "/forgot-password/verify",
    methods=["GET", "POST"],
)
def verify_reset_otp():
    if current_user.is_authenticated:
        return redirect(
            get_default_route(
                current_user
            )
        )

    user = get_password_reset_user()

    if user is None:
        clear_password_reset_session()

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    # Đã xác minh thì không cho quay lại
    # sử dụng màn OTP cũ.
    if session.get(
        "password_reset_verified"
    ):
        return redirect(
            url_for(
                "auth.reset_password"
            )
        )

    token = get_active_token(
        user.userID,
        PASSWORD_RESET,
    )

    if token is None:
        flash(
            (
                "Phiên xác minh không còn "
                "hiệu lực. Vui lòng gửi "
                "mã mới."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    if request.method == "POST":
        otp = (
            request.form.get(
                "otp",
                ""
            )
            .strip()
        )

        if (
            len(otp) != 6
            or not otp.isdigit()
        ):
            error = (
                "Vui lòng nhập đầy đủ "
                "6 chữ số OTP."
            )

        else:
            is_valid, reason = verify_otp(
                user.userID,
                PASSWORD_RESET,
                otp,
            )

            if is_valid:
                active_token = (
                    get_active_token(
                        user.userID,
                        PASSWORD_RESET,
                    )
                )

                if active_token is None:
                    error = (
                        "Mã xác minh không "
                        "còn hiệu lực."
                    )

                else:
                    mark_token_used(
                        active_token
                    )

                    session[
                        "password_reset_verified"
                    ] = True

                    db.session.commit()

                    return redirect(
                        url_for(
                            "auth.reset_password"
                        )
                    )

            elif reason == "EXPIRED":
                error = (
                    "Mã OTP đã hết hạn. "
                    "Vui lòng gửi lại mã mới."
                )

            elif reason == "INVALID":
                error = (
                    "Mã OTP không chính xác. "
                    "Vui lòng kiểm tra lại."
                )

            else:
                error = (
                    "Mã OTP không còn hiệu lực. "
                    "Vui lòng gửi lại mã."
                )

    else:
        error = None

    token = get_active_token(
        user.userID,
        PASSWORD_RESET,
    )

    if token is None:
        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    expires_at = (
        token.expiresAt.timestamp()
    )

    created_at = token.createdAt

    if created_at.tzinfo is None:
        created_at = created_at.replace(
            tzinfo=timezone.utc
        )

    resend_available_at = (
        created_at.timestamp()
        + OTP_RESEND_COOLDOWN_SECONDS
    )

    return render_template(
        "auth/forgot_password_otp.html",
        user=user,
        error=error,
        expires_at=expires_at,
        resend_available_at=(
            resend_available_at
        ),
    )
    
@auth_bp.post(
    "/forgot-password/resend"
)
def resend_reset_otp():
    if current_user.is_authenticated:
        return redirect(
            get_default_route(
                current_user
            )
        )

    user = get_password_reset_user()

    if user is None:
        clear_password_reset_session()

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    if session.get(
        "password_reset_verified"
    ):
        return redirect(
            url_for(
                "auth.reset_password"
            )
        )

    token = get_active_token(
        user.userID,
        PASSWORD_RESET,
    )

    if token is not None:
        created_at = token.createdAt

        if created_at.tzinfo is None:
            created_at = (
                created_at.replace(
                    tzinfo=timezone.utc
                )
            )

        elapsed = (
            datetime.now(
                timezone.utc
            )
            - created_at
        ).total_seconds()

        if (
            elapsed
            < OTP_RESEND_COOLDOWN_SECONDS
        ):
            # Không flash cảnh báo.
            # Countdown trên UI đã đủ.
            return redirect(
                url_for(
                    "auth.verify_reset_otp"
                )
            )

    try:
        otp, _ = create_otp_token(
            user.userID,
            PASSWORD_RESET,
        )

        send_password_reset_otp(
            recipient_email=user.email,
            full_name=user.fullName,
            otp=otp,
        )

        db.session.commit()

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Không thể gửi lại OTP reset password."
        )

        flash(
            (
                "Chưa thể gửi lại mã lúc này. "
                "Vui lòng thử lại."
            ),
            "error",
        )

        return redirect(
            url_for(
                "auth.verify_reset_otp"
            )
        )

    flash(
        (
            "VetMate đã gửi một mã OTP "
            "mới đến email của bạn."
        ),
        "success",
    )

    return redirect(
        url_for(
            "auth.verify_reset_otp"
        )
    )
    
@auth_bp.route(
    "/reset-password",
    methods=["GET", "POST"],
)
def reset_password():
    if current_user.is_authenticated:
        return redirect(
            get_default_route(
                current_user
            )
        )

    user = get_password_reset_user()

    if (
        user is None
        or not session.get(
            "password_reset_verified"
        )
    ):
        clear_password_reset_session()

        flash(
            (
                "Phiên đặt lại mật khẩu "
                "không hợp lệ hoặc đã hết hạn."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "auth.forgot_password"
            )
        )

    errors = {}

    if request.method == "POST":
        password = request.form.get(
            "password",
            "",
        )

        confirm_password = (
            request.form.get(
                "confirmPassword",
                "",
            )
        )

        # =============================================
        # PASSWORD
        # =============================================
        if len(password) < 8:
            errors["password"] = (
                "Mật khẩu phải có ít nhất "
                "8 ký tự."
            )

        # =============================================
        # CONFIRM PASSWORD
        # =============================================
        if confirm_password != password:
            errors["confirmPassword"] = (
                "Mật khẩu xác nhận "
                "không khớp."
            )

        if errors:
            return render_template(
                "auth/reset_password.html",
                user=user,
                errors=errors,
            )

        try:
            user.passwordHash = (
                generate_password_hash(
                    password
                )
            )

            db.session.commit()

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Không thể cập nhật mật khẩu."
            )

            errors["general"] = (
                "VetMate chưa thể cập nhật "
                "mật khẩu lúc này. "
                "Vui lòng thử lại."
            )

            return render_template(
                "auth/reset_password.html",
                user=user,
                errors=errors,
            )

        clear_password_reset_session()

        session[
            "password_reset_success_user_id"
        ] = user.userID

        return redirect(
            url_for(
                "auth.reset_password_success"
            )
        )

    return render_template(
        "auth/reset_password.html",
        user=user,
        errors={},
    )

@auth_bp.get(
    "/reset-password/success"
)
def reset_password_success():
    if current_user.is_authenticated:
        return redirect(
            get_default_route(
                current_user
            )
        )

    user_id = session.pop(
        "password_reset_success_user_id",
        None,
    )

    if not user_id:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    return render_template(
        "auth/reset_password_success.html"
    )

@auth_bp.post("/logout")
def logout():
    """Đăng xuất khỏi VetMate."""

    if current_user.is_authenticated:
        logout_user()

    return redirect(
        url_for("main.home")
    )
    

@auth_bp.route(
    "/customer-activation",
    methods=["GET", "POST"],
)
def customer_activation():
    """Kích hoạt tài khoản do lễ tân tạo."""

    if current_user.is_authenticated:
        return redirect(
            get_default_route(current_user)
        )

    errors = {}

    form_data = {
        "email": request.args.get(
            "email", ""
        ).strip().lower(),
    }

    if request.method == "POST":
        validate_activation_csrf()
        email = request.form.get(
            "email", ""
        ).strip().lower()

        otp = request.form.get(
            "otp", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        confirm_password = request.form.get(
            "confirmPassword", ""
        )

        form_data["email"] = email

        if not is_valid_email(email):
            errors["email"] = (
                "Vui lòng nhập email hợp lệ."
            )

        if len(otp) != 6 or not otp.isascii() or not otp.isdigit():
            errors["otp"] = (
                "Mã OTP phải gồm 6 chữ số."
            )

        if len(password) < 8:
            errors["password"] = (
                "Mật khẩu phải có ít nhất 8 ký tự."
            )

        if password != confirm_password:
            errors["confirmPassword"] = (
                "Mật khẩu xác nhận không khớp."
            )

        if not errors:
            user = User.query.filter(
                db.func.lower(User.email) == email
            ).first()

            if (
                user is None
                or user.status != "PENDING_VERIFICATION"
                or not user.has_role("PET_OWNER")
            ):
                errors["general"] = (
                    "Thông tin kích hoạt không hợp lệ "
                    "hoặc tài khoản đã được kích hoạt."
                )

            else:
                try:
                    valid, reason, token = (
                        verify_customer_activation_otp(
                            user.userID,
                            otp,
                        )
                    )

                    if not valid:
                        db.session.commit()

                        if reason == "EXPIRED":
                            errors["otp"] = (
                                "OTP đã hết hạn. "
                                "Vui lòng yêu cầu mã mới."
                            )

                        elif reason == "TOO_MANY_ATTEMPTS":
                            errors["otp"] = (
                                "Bạn đã nhập sai OTP 5 lần. "
                                "Vui lòng yêu cầu mã mới."
                            )

                        else:
                            errors["otp"] = (
                                "OTP không chính xác "
                                "hoặc không còn hiệu lực."
                            )

                    else:
                        user.passwordHash = (
                            generate_password_hash(password)
                        )

                        user.status = "ACTIVE"

                        mark_token_used(token)

                        db.session.commit()

                        flash(
                            "Kích hoạt tài khoản thành công. "
                            "Bạn có thể đăng nhập.",
                            "success",
                        )

                        return redirect(
                            url_for("auth.login")
                        )

                except Exception:
                    db.session.rollback()

                    current_app.logger.exception(
                        "Lỗi xác minh OTP kích hoạt."
                    )

                    errors["general"] = (
                        "Không thể xử lý yêu cầu kích hoạt. "
                        "Vui lòng thử lại."
                    )

                if not valid:
                    if reason == "EXPIRED":
                        errors["otp"] = (
                            "OTP đã hết hạn. "
                            "Vui lòng yêu cầu mã mới."
                        )
                    else:
                        errors["otp"] = (
                            "Mã OTP không chính xác "
                            "hoặc không còn hiệu lực."
                        )

                else:
                    token = get_active_token(
                        user.userID,
                        CUSTOMER_ACTIVATION,
                    )

                    if token is None:
                        errors["otp"] = (
                            "OTP không còn hiệu lực."
                        )

                    else:
                        try:
                            user.passwordHash = (
                                generate_password_hash(
                                    password
                                )
                            )

                            user.status = "ACTIVE"

                            mark_token_used(token)

                            db.session.commit()

                        except Exception:
                            db.session.rollback()

                            current_app.logger.exception(
                                "Không thể kích hoạt khách hàng."
                            )

                            errors["general"] = (
                                "Không thể kích hoạt tài khoản. "
                                "Vui lòng thử lại."
                            )

                        else:
                            flash(
                                "Tài khoản đã được kích hoạt. "
                                "Bạn có thể đăng nhập.",
                                "success",
                            )

                            return redirect(
                                url_for("auth.login")
                            )

    return render_template(
        "auth/customer_activation.html",
        errors=errors,
        form_data=form_data,
        csrf_token=get_activation_csrf_token(),
    )



@auth_bp.post("/customer-activation/resend")
def resend_customer_activation():
    """Gửi lại OTP kích hoạt khách hàng."""

    validate_activation_csrf()

    email = (
        request.form.get("email", "")
        .strip()
        .lower()
    )

    redirect_url = url_for(
        "auth.customer_activation",
        email=email,
    )

    generic_message = (
        "Nếu tài khoản đủ điều kiện kích hoạt, "
        "VetMate sẽ gửi mã OTP đến email đã đăng ký."
    )

    if not is_valid_email(email):
        flash(generic_message, "success")
        return redirect(redirect_url)

    user = User.query.filter(
        db.func.lower(User.email) == email
    ).first()

    if (
        user is None
        or user.status != "PENDING_VERIFICATION"
        or not user.has_role("PET_OWNER")
    ):
        flash(generic_message, "success")
        return redirect(redirect_url)

    # Chỉ tài khoản có lịch sử OTP kích hoạt
    # mới được phép gửi lại qua chức năng này.
    previous_token = (
        VerificationToken.query
        .filter_by(
            userID=user.userID,
            purpose=CUSTOMER_ACTIVATION,
        )
        .first()
    )

    if previous_token is None:
        flash(generic_message, "success")
        return redirect(redirect_url)

    allowed, reason = can_resend_customer_activation(
        user.userID
    )

    if not allowed:
        flash(generic_message, "success")
        return redirect(redirect_url)

    try:
        otp, _ = create_otp_token(
            user.userID,
            CUSTOMER_ACTIVATION,
        )

        db.session.commit()

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Không thể tạo OTP kích hoạt mới."
        )

        flash(
            "Chưa thể xử lý yêu cầu lúc này.",
            "error",
        )

        return redirect(redirect_url)

    activation_url = url_for(
        "auth.customer_activation",
        email=user.email,
        _external=True,
    )

    try:
        send_customer_activation_otp(
            recipient_email=user.email,
            full_name=user.fullName,
            otp=otp,
            activation_url=activation_url,
        )

    except Exception:
        current_app.logger.exception(
            "Không thể gửi lại OTP kích hoạt."
        )

        flash(
            "Chưa thể gửi email kích hoạt. "
            "Vui lòng thử lại sau.",
            "error",
        )

        return redirect(redirect_url)

    flash(generic_message, "success")

    return redirect(redirect_url)

