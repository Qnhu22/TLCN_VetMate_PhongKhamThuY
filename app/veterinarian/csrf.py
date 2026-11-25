import hmac
import secrets

from flask import abort, request, session


def csrf_token():
    if "veterinarian_csrf" not in session:
        session["veterinarian_csrf"] = secrets.token_urlsafe(32)
    return session["veterinarian_csrf"]


def validate_csrf():
    expected = session.get("veterinarian_csrf", "")
    received = request.form.get("csrf_token", "")
    if not expected or not received.isascii() or not hmac.compare_digest(expected, received):
        abort(400, description="CSRF token không hợp lệ.")
