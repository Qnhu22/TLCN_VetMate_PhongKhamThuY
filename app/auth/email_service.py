from flask_mail import Message

from app.extensions import mail


def send_verification_otp(
    recipient_email,
    full_name,
    otp,
):
    """Gửi OTP xác minh email đăng ký."""

    subject = (
        "Mã xác minh tài khoản VetMate"
    )

    body = f"""
Xin chào {full_name},

Mã xác minh VetMate của bạn là:

{otp}

Mã này có hiệu lực trong 5 phút.

Nếu bạn không thực hiện yêu cầu này,
vui lòng bỏ qua email.

VetMate
""".strip()

    message = Message(
        subject=subject,
        recipients=[
            recipient_email
        ],
        body=body,
    )

    mail.send(message)
    
def send_password_reset_otp(
    recipient_email,
    full_name,
    otp,
):
    """Gửi OTP đặt lại mật khẩu."""

    subject = (
        "Mã đặt lại mật khẩu VetMate"
    )

    body = f"""
Xin chào {full_name},

VetMate đã nhận được yêu cầu
đặt lại mật khẩu cho tài khoản của bạn.

Mã OTP xác minh của bạn là:

{otp}

Mã này có hiệu lực trong 5 phút.

Nếu bạn không yêu cầu đặt lại mật khẩu,
vui lòng bỏ qua email này.
Mật khẩu hiện tại của bạn sẽ không bị thay đổi.

VetMate
""".strip()

    message = Message(
        subject=subject,
        recipients=[
            recipient_email
        ],
        body=body,
    )

    mail.send(message)
    

def send_customer_activation_otp(
    recipient_email,
    full_name,
    otp,
    activation_url,
):
    """Gửi OTP kích hoạt tài khoản do lễ tân tạo."""

    subject = "Kích hoạt tài khoản VetMate"

    body = f"""
Xin chào {full_name},

Phòng khám VetMate đã tạo hồ sơ khách hàng
cho bạn bằng địa chỉ email này.

Để xác minh email và tự thiết lập mật khẩu,
vui lòng truy cập:

{activation_url}

Mã OTP kích hoạt của bạn là:

{otp}

Mã OTP có hiệu lực trong 5 phút.

Nếu mã hết hạn, bạn có thể yêu cầu gửi lại
mã mới tại trang kích hoạt.

Nếu bạn không yêu cầu tạo tài khoản này,
vui lòng liên hệ phòng khám VetMate.

Trân trọng,
VetMate
""".strip()

    message = Message(
        subject=subject,
        recipients=[recipient_email],
        body=body,
    )

    mail.send(message)
