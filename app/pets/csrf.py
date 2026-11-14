
import hmac
import secrets

from flask import abort, request, session


def pet_csrf_token():
    token = session.get("pets_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["pets_csrf_token"] = token

    return token


def validate_pet_csrf():
    expected = session.get("pets_csrf_token")
    received = request.form.get("csrf_token", "")

    if (
        not expected
        or not received
        or not hmac.compare_digest(expected, received)
    ):
        abort(400, description="CSRF token không hợp lệ.")
