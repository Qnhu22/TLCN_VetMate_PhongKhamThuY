
import hmac
import secrets

from flask import abort, request, session


def get_customer_csrf_token():
    token = session.get("customer_create_csrf")

    if not token:
        token = secrets.token_urlsafe(32)
        session["customer_create_csrf"] = token

    return token


def validate_customer_csrf():
    expected = session.get("customer_create_csrf")
    submitted = request.form.get("csrf_token", "")

    if (
        not expected
        or not submitted
        or not hmac.compare_digest(expected, submitted)
    ):
        abort(400, description="CSRF token không hợp lệ.")
