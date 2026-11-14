from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def role_required(*role_codes):
    def decorator(view_func):

        @wraps(view_func)
        @login_required
        def wrapped_view(*args, **kwargs):

            if not any(
                current_user.has_role(role_code)
                for role_code in role_codes
            ):
                abort(403)

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def permission_required(*permission_codes):
    def decorator(view_func):

        @wraps(view_func)
        @login_required
        def wrapped_view(*args, **kwargs):

            if not all(
                current_user.has_permission(permission_code)
                for permission_code in permission_codes
            ):
                abort(403)

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator