from functools import wraps

from flask import abort, g
from flask_login import current_user

from app.auth.decorators import permission_required
from app.extensions import db
from app.models import ClinicStaff, Veterinarian


def veterinarian_required(permission):
    """Permission plus active clinical identity; never accept a staff ID from forms."""
    def decorate(view):
        @wraps(view)
        @permission_required(permission)
        def wrapped(*args, **kwargs):
            if current_user.status != "ACTIVE" or not current_user.has_role("VETERINARIAN"):
                abort(403)
            identity = db.session.execute(
                db.select(ClinicStaff, Veterinarian)
                .join(Veterinarian, Veterinarian.staffID == ClinicStaff.staffID)
                .where(ClinicStaff.userID == current_user.userID,
                       ClinicStaff.staffType == "VETERINARIAN",
                       ClinicStaff.status == "ACTIVE", Veterinarian.status == "ACTIVE")
            ).first()
            if identity is None:
                abort(403, description="Hồ sơ bác sĩ chưa được thiết lập hoặc không hoạt động.")
            g.vet_staff, g.veterinarian = identity
            return view(*args, **kwargs)
        return wrapped
    return decorate
