from flask import render_template

from app.main import main_bp


@main_bp.get("/")
def home():
    """Hiển thị trang chủ công khai của VetMate."""

    hero_slides = [
        {
            "image": "images/home/hero-01.jpg",
            "position": "center 42%",
            "eyebrow": "Chăm sóc bằng cả trái tim",
            "title": "Nơi tình yêu và sức khỏe thú cưng gặp nhau",
            "description": (
                "VetMate đồng hành cùng bạn trong việc khám bệnh, "
                "tiêm phòng và theo dõi sức khỏe thú cưng."
            ),
        },
        {
            "image": "images/home/hero-02.jpg",
            "position": "center 38%",
            "eyebrow": "Đội ngũ tận tâm",
            "title": "Chăm sóc chuyên nghiệp cho người bạn nhỏ",
            "description": (
                "Dễ dàng lựa chọn dịch vụ, bác sĩ và thời gian khám "
                "phù hợp với nhu cầu của bạn."
            ),
        },
        {
            "image": "images/home/hero-03.jpg",
            "position": "center 45%",
            "eyebrow": "Theo dõi sức khỏe lâu dài",
            "title": "Mỗi thú cưng đều xứng đáng được yêu thương",
            "description": (
                "Lưu trữ hồ sơ sức khỏe, lịch sử điều trị, "
                "lịch tiêm phòng và các mốc chăm sóc quan trọng."
            ),
        },
    ]

    return render_template(
        "main/home.html",
        hero_slides=hero_slides,
    )