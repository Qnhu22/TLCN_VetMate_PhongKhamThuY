
import re

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from app.account import account_bp
from app.extensions import db
from app.models import OwnerProfile


def get_owner_profile():
    return OwnerProfile.query.filter_by(
        userID=current_user.userID
    ).first()


@account_bp.route(
    "/profile",
    methods=["GET", "POST"],
)
@login_required
def profile():
    owner = get_owner_profile()

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "update_profile":
            return update_profile(owner)

        if action == "change_password":
            return change_password()

        flash("Yêu cầu không hợp lệ.", "error")
        return redirect(url_for("account.profile"))

    return render_template(
        "account/profile.html",
        owner=owner,
    )


def update_profile(owner):
    full_name = request.form.get(
        "fullName", ""
    ).strip()

    phone = request.form.get(
        "phone", ""
    ).strip()

    address = request.form.get(
        "address", ""
    ).strip()

    emergency_phone = request.form.get(
        "emergencyPhone", ""
    ).strip()

    note = request.form.get(
        "note", ""
    ).strip()

    allow_public_phone = (
        request.form.get("allowPublicPhone")
        == "on"
    )

    if not 2 <= len(full_name) <= 150:
        flash(
            "Họ tên phải từ 2 đến 150 ký tự.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileInfoSection")
        )

    if phone and not re.fullmatch(r"0\d{9}", phone):
        flash(
            "Số điện thoại phải gồm 10 số "
            "và bắt đầu bằng 0.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileInfoSection")
        )

    if emergency_phone and not re.fullmatch(
        r"0\d{9}", emergency_phone
    ):
        flash(
            "Số điện thoại khẩn cấp không hợp lệ.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileInfoSection")
        )

    if len(address) > 500:
        flash(
            "Địa chỉ không được vượt quá 500 ký tự.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileInfoSection")
        )

    if len(note) > 1000:
        flash(
            "Ghi chú không được vượt quá 1000 ký tự.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileInfoSection")
        )

    try:
        current_user.fullName = full_name
        current_user.phone = phone or None

        # Chỉ tạo OwnerProfile khi có thông tin
        # bổ sung cần lưu.
        has_owner_data = any([
            address,
            emergency_phone,
            note,
            allow_public_phone,
        ])

        if owner is None and has_owner_data:
            owner = OwnerProfile(
                userID=current_user.userID
            )
            db.session.add(owner)

        if owner is not None:
            owner.address = address or None
            owner.emergencyPhone = (
                emergency_phone or None
            )
            owner.note = note or None
            owner.allowPublicPhone = (
                allow_public_phone
            )

        db.session.commit()

    except Exception:
        db.session.rollback()

        flash(
            "Không thể cập nhật hồ sơ. "
            "Vui lòng thử lại.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileInfoSection")
        )

    flash(
        "Cập nhật hồ sơ thành công.",
        "success",
    )
    return redirect(
        url_for("account.profile", _anchor="profileInfoSection")
    )


def change_password():
    old_password = request.form.get(
        "oldPassword", ""
    )

    new_password = request.form.get(
        "newPassword", ""
    )

    confirm_password = request.form.get(
        "confirmPassword", ""
    )

    if not check_password_hash(
        current_user.passwordHash,
        old_password,
    ):
        flash(
            "Mật khẩu hiện tại không chính xác.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileSecuritySection")
        )

    if len(new_password) < 8:
        flash(
            "Mật khẩu mới phải có ít nhất 8 ký tự.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileSecuritySection")
        )

    if new_password != confirm_password:
        flash(
            "Xác nhận mật khẩu không khớp.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileSecuritySection")
        )

    if check_password_hash(
        current_user.passwordHash,
        new_password,
    ):
        flash(
            "Mật khẩu mới phải khác mật khẩu cũ.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileSecuritySection")
        )

    try:
        current_user.passwordHash = (
            generate_password_hash(new_password)
        )

        db.session.commit()

    except Exception:
        db.session.rollback()

        flash(
            "Không thể đổi mật khẩu lúc này.",
            "error",
        )
        return redirect(
            url_for("account.profile", _anchor="profileSecuritySection")
        )

    flash(
        "Đổi mật khẩu thành công.",
        "success",
    )
    return redirect(
        url_for("account.profile", _anchor="profileSecuritySection")
    )
