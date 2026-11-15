
import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import CustomerActivationLink


ACTIVATION_LINK_HOURS = 24


def utc_now():
    return datetime.now(timezone.utc)


def aware_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def hash_activation_token(raw_token):
    return hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()


def create_activation_link(user_id):
    """
    Tạo liên kết mới.
    Phải được gọi trong transaction.
    Hàm không tự commit.
    """

    now = utc_now()

    old_links = (
        CustomerActivationLink.query
        .filter(
            CustomerActivationLink.userID == user_id,
            CustomerActivationLink.usedAt.is_(None),
        )
        .all()
    )

    for link in old_links:
        link.usedAt = now

    db.session.flush()

    raw_token = secrets.token_urlsafe(32)

    link = CustomerActivationLink(
        userID=user_id,
        tokenHash=hash_activation_token(raw_token),
        expiresAt=now + timedelta(
            hours=ACTIVATION_LINK_HOURS
        ),
    )

    db.session.add(link)
    db.session.flush()

    return raw_token, link


def find_activation_link(raw_token):
    """
    Chỉ trả về liên kết hợp lệ.
    Không tự commit.
    """

    if (
        not raw_token
        or len(raw_token) > 128
        or not raw_token.isascii()
    ):
        return None

    link = CustomerActivationLink.query.filter_by(
        tokenHash=hash_activation_token(raw_token)
    ).first()

    if link is None or link.usedAt is not None:
        return None

    if aware_utc(link.expiresAt) <= utc_now():
        return None

    return link


def consume_activation_link(link):
    link.usedAt = utc_now()
