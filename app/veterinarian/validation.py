from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
LEAVE_STATUSES = {"PENDING": "Chờ duyệt", "APPROVED": "Đã duyệt",
                  "REJECTED": "Từ chối", "CANCELLED": "Đã hủy"}


def today():
    return datetime.now(LOCAL_TZ).date()


def schedule_range(raw, view):
    day = date.fromisoformat(raw) if raw else today()
    if not 1900 <= day.year <= 9998:
        raise ValueError("Ngày ngoài phạm vi hỗ trợ.")
    start = day - timedelta(days=day.weekday()) if view == "week" else day
    return start, start + timedelta(days=6) if view == "week" else start


def validate_leave(form):
    errors = {}
    first = last = None
    try:
        first = date.fromisoformat(form.get("startDate", ""))
        last = date.fromisoformat(form.get("endDate", ""))
        if first < today() or last < first or last.year > 9998:
            raise ValueError
    except ValueError:
        errors["dates"] = "Chọn ngày nghỉ từ hôm nay; ngày kết thúc không trước ngày bắt đầu."
    reason = form.get("reason", "").strip()
    if not 1 <= len(reason) <= 2000:
        errors["reason"] = "Lý do nghỉ phải từ 1 đến 2.000 ký tự."
    if errors:
        return None, errors
    # Full working days, including both selected dates; stored as UTC instants.
    return {"startAt": datetime.combine(first, time(7, 30), LOCAL_TZ).astimezone(timezone.utc),
            "endAt": datetime.combine(last, time(17), LOCAL_TZ).astimezone(timezone.utc),
            "reason": reason}, {}
