"""Shared scheduling queries for receptionist and future owner booking."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import text
from app.extensions import db

LOCAL_TZ = ZoneInfo('Asia/Ho_Chi_Minh')

SERVICES_SQL = text('''SELECT "serviceID", "name", "price", "defaultDurationMinutes"
 FROM clinic."services" WHERE "status"='ACTIVE' AND "isBookable"=true
 AND "isEmergency"=false AND "requiresVeterinarian"=true ORDER BY "name"''')

VETS_SQL = text('''SELECT v."veterinarianID" AS id, u."fullName" AS name,
 w."morningStartTime" AS morning_start, w."morningEndTime" AS morning_end,
 w."afternoonStartTime" AS afternoon_start, w."afternoonEndTime" AS afternoon_end,
 st."staffID" AS staff_id
 FROM clinic."veterinarians" v JOIN clinic."clinicStaff" st ON st."staffID"=v."staffID"
 JOIN auth."users" u ON u."userID"=st."userID"
 JOIN clinic."workingSchedules" w ON w."veterinarianID"=v."veterinarianID"
 WHERE v."status"='ACTIVE' AND st."status"='ACTIVE' AND u."status"='ACTIVE'
 AND w."status"='AVAILABLE' AND w."workDate"=:day
 AND EXISTS (SELECT 1 FROM clinic."serviceSpecialties" ss
 JOIN clinic."veterinarianSpecialties" vs ON vs."specialtyID"=ss."specialtyID"
 JOIN clinic."specialties" sp ON sp."specialtyID"=ss."specialtyID" AND sp."isActive"=true
 WHERE ss."serviceID"=:service_id AND vs."veterinarianID"=v."veterinarianID")
 ORDER BY u."fullName",v."veterinarianID"''')

BUSY_SQL = text("""
    SELECT "startTime", "endTime"
    FROM booking."appointments"
    WHERE "scheduledDate" = :day
      AND "status" IN (
          'PENDING',
          'CONFIRMED',
          'CHECKED_IN',
          'IN_PROGRESS'
      )
      AND (
          "veterinarianID" = :vet_id
          OR "petID" = :pet_id
      )
""")

LEAVE_SQL = text('''SELECT 1 FROM clinic."staffLeaves" WHERE "staffID"=:staff_id
 AND "status"='APPROVED' AND "startAt" < :end_at AND "endAt" > :start_at LIMIT 1''')


def available_slots(service_id, day, pet_id, vet_id):
    service = db.session.execute(SERVICES_SQL).mappings().all()
    item = next((s for s in service if s['serviceID'] == service_id), None)
    if not item or day < datetime.now(LOCAL_TZ).date():
        return []
    vet = next((v for v in db.session.execute(VETS_SQL, {'day':day, 'service_id':service_id}).mappings()
                if v['id'] == vet_id), None)
    if not vet:
        return []
    duration = timedelta(minutes=item['defaultDurationMinutes'])
    busy = db.session.execute(BUSY_SQL, {'day':day,'vet_id':vet_id,'pet_id':pet_id}).mappings().all()
    slots = []
    for begin, finish in ((vet['morning_start'],vet['morning_end']),
                          (vet['afternoon_start'],vet['afternoon_end'])):
        cursor = datetime.combine(day, begin, LOCAL_TZ)
        limit = datetime.combine(day, finish, LOCAL_TZ)
        while cursor + duration <= limit:
            end = cursor + duration
            conflict = any(
                (
                    b["endTime"] is None
                    or (
                        cursor.time() < b["endTime"]
                        and end.time() > b["startTime"]
                    )
                )
                for b in busy
            )
            leave = db.session.execute(LEAVE_SQL, {'staff_id':vet['staff_id'],
                'start_at':cursor.astimezone(timezone.utc),
                'end_at':end.astimezone(timezone.utc)}).first()
            if not conflict and not leave and cursor > datetime.now(LOCAL_TZ):
                slots.append(cursor.strftime('%H:%M'))
            cursor += timedelta(minutes=15)
    return slots
