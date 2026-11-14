import secrets
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from sqlalchemy import select, func

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


from app.extensions import db
from app.models import VerificationToken


OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 30

EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
PASSWORD_RESET = "PASSWORD_RESET"
CUSTOMER_ACTIVATION = "CUSTOMER_ACTIVATION"


def generate_otp():
    """Sinh OTP gồm 6 chữ số."""

    return "".join(
        str(secrets.randbelow(10))
        for _ in range(OTP_LENGTH)
    )


def create_otp_token(
    user_id,
    purpose,
):
    """
    Tạo OTP mới cho một mục đích.

    Token cũ chưa sử dụng của cùng user/purpose
    sẽ được vô hiệu hóa.
    """

    if purpose not in {
        EMAIL_VERIFICATION,
        PASSWORD_RESET,
        CUSTOMER_ACTIVATION,
    }:
        raise ValueError(
            "OTP purpose không hợp lệ."
        )

    now = datetime.now(timezone.utc)

    # Vô hiệu hóa OTP cũ còn hiệu lực.
    (
        VerificationToken.query
        .filter_by(
            userID=user_id,
            purpose=purpose,
            usedAt=None,
        )
        .update(
            {
                VerificationToken.usedAt:
                    now
            },
            synchronize_session=False,
        )
    )

    otp = generate_otp()

    token = VerificationToken(
        userID=user_id,
        purpose=purpose,
        tokenHash=generate_password_hash(
            otp
        ),
        expiresAt=(
            now
            + timedelta(
                minutes=OTP_EXPIRE_MINUTES
            )
        ),
    )

    db.session.add(token)

    # Chỉ flush, chưa commit.
    db.session.flush()

    return otp, token


def get_active_token(
    user_id,
    purpose,
):
    """Lấy OTP mới nhất chưa sử dụng."""

    return (
        VerificationToken.query
        .filter_by(
            userID=user_id,
            purpose=purpose,
            usedAt=None,
        )
        .order_by(
            VerificationToken.createdAt.desc(),
            VerificationToken.verificationTokenID.desc(),
        )
        .first()
    )


def verify_otp(
    user_id,
    purpose,
    otp,
):
    """
    Kiểm tra OTP.

    Return:
        (True, "VALID")
        (False, "NOT_FOUND")
        (False, "EXPIRED")
        (False, "INVALID")
    """

    token = get_active_token(
        user_id,
        purpose,
    )

    if token is None:
        return False, "NOT_FOUND"

    now = datetime.now(timezone.utc)

    expires_at = token.expiresAt

    # PostgreSQL thường trả aware datetime vì
    # column đang dùng timezone=True.
    # Đoạn này bảo vệ trường hợp driver trả naive.
    if (
        expires_at is not None
        and expires_at.tzinfo is None
    ):
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if (
        expires_at is None
        or expires_at <= now
    ):
        return False, "EXPIRED"

    if not check_password_hash(
        token.tokenHash,
        otp,
    ):
        return False, "INVALID"

    return True, "VALID"


def mark_token_used(token):
    """Đánh dấu token đã được sử dụng."""

    token.usedAt = datetime.now(
        timezone.utc
    )


def verify_customer_activation_otp(user_id, otp):
    """
    Xác minh OTP kích hoạt khách hàng.
    Tối đa 5 lần nhập sai cho mỗi mã OTP.

    Hàm này thay đổi dữ liệu trong session.
    Route gọi hàm phải commit hoặc rollback.
    """

    now = datetime.now(timezone.utc)

    token = db.session.execute(
        select(VerificationToken)
        .where(
            VerificationToken.userID == user_id,
            VerificationToken.purpose == CUSTOMER_ACTIVATION,
            VerificationToken.usedAt.is_(None),
        )
        .order_by(
            VerificationToken.createdAt.desc(),
            VerificationToken.verificationTokenID.desc(),
        )
        .with_for_update()
    ).scalars().first()

    if token is None:
        return False, "NOT_FOUND", None

    expires_at = token.expiresAt

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= now:
        return False, "EXPIRED", None

    if token.failedAttempts >= 5:
        token.usedAt = now
        return False, "TOO_MANY_ATTEMPTS", None

    if not check_password_hash(token.tokenHash, otp):
        token.failedAttempts += 1

        if token.failedAttempts >= 5:
            token.usedAt = now
            return False, "TOO_MANY_ATTEMPTS", None

        return False, "INVALID", None

    return True, "VALID", token


CUSTOMER_ACTIVATION_MAX_RESENDS = 5
CUSTOMER_ACTIVATION_RESEND_WINDOW_HOURS = 1


def can_resend_customer_activation(user_id):
    """
    Kiểm tra giới hạn gửi lại OTP kích hoạt.

    - Cách lần gửi gần nhất ít nhất 30 giây.
    - Tối đa 5 OTP trong 1 giờ.
    """

    now = datetime.now(timezone.utc)

    latest_token = (
        VerificationToken.query
        .filter_by(
            userID=user_id,
            purpose=CUSTOMER_ACTIVATION,
        )
        .order_by(
            VerificationToken.createdAt.desc(),
            VerificationToken.verificationTokenID.desc(),
        )
        .first()
    )

    if latest_token is not None:
        created_at = latest_token.createdAt

        if created_at.tzinfo is None:
            created_at = created_at.replace(
                tzinfo=timezone.utc
            )

        elapsed = (now - created_at).total_seconds()

        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            return False, "COOLDOWN"

    window_start = now - timedelta(
        hours=CUSTOMER_ACTIVATION_RESEND_WINDOW_HOURS
    )

    token_count = (
        db.session.query(
            func.count(VerificationToken.verificationTokenID)
        )
        .filter(
            VerificationToken.userID == user_id,
            VerificationToken.purpose == CUSTOMER_ACTIVATION,
            VerificationToken.createdAt >= window_start,
        )
        .scalar()
    ) or 0

    if token_count >= CUSTOMER_ACTIVATION_MAX_RESENDS:
        return False, "HOURLY_LIMIT"

    return True, "ALLOWED"
