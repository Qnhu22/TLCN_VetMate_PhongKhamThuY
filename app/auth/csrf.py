
import hmac
import secrets

from flask import abort, request, session


def get_activation_csrf_token():
    token = session.get("activation_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["activation_csrf_token"] = token

    return token


def validate_activation_csrf():
    expected = session.get("activation_csrf_token")
    submitted = request.form.get("csrf_token", "")

    if (
        not expected
        or not submitted
        or not hmac.compare_digest(expected, submitted)
    ):
        abort(400, description="CSRF token không hợp lệ.")
