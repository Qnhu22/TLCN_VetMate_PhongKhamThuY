-- VetMate | 09_booking_workflow.sql
-- Chay SAU 06_booking.sql, 07_clinic.sql, 08_booking_clinic_fk.sql.
-- Migration bo sung WALK_IN va kenh tao lich. KHONG xoa bang/du lieu.
-- PostgreSQL: ten bang/cot camelCase phai co dau ngoac kep.

BEGIN;

-- 1. Mo rong appointmentType, giu nguyen SCHEDULED va EMERGENCY.
ALTER TABLE booking."appointments"
    DROP CONSTRAINT IF EXISTS "ckAppointmentsType";

ALTER TABLE booking."appointments"
    ADD CONSTRAINT "ckAppointmentsType"
    CHECK ("appointmentType" IN ('SCHEDULED', 'WALK_IN', 'EMERGENCY'));

-- 2. Kenh tao lich:
-- ONLINE: chu nuoi tu dat; RECEPTION: le tan tai quay;
-- PHONE: le tan nhan yeu cau qua dien thoai.
-- NULL cho ban ghi CU (khong the suy ra nguon chinh xac tu du lieu cu).
-- Backend BAT BUOC truyen bookingSource khi tao lich MOI.
ALTER TABLE booking."appointments"
    ADD COLUMN IF NOT EXISTS "bookingSource" VARCHAR(20);

ALTER TABLE booking."appointments"
    DROP CONSTRAINT IF EXISTS "ckAppointmentsBookingSource";

ALTER TABLE booking."appointments"
    ADD CONSTRAINT "ckAppointmentsBookingSource"
    CHECK ("bookingSource" IS NULL OR
           "bookingSource" IN ('ONLINE', 'RECEPTION', 'PHONE'));

-- 3. Loai tiep nhan tai cho chi do le tan thuc hien (khong dat online).
ALTER TABLE booking."appointments"
    DROP CONSTRAINT IF EXISTS "ckAppointmentsWalkInSource";

ALTER TABLE booking."appointments"
    ADD CONSTRAINT "ckAppointmentsWalkInSource"
    CHECK (
        "appointmentType" = 'SCHEDULED'
        OR "bookingSource" IS NULL -- ban ghi cu
        OR "bookingSource" = 'RECEPTION'
    );

-- 4. Luot WALK_IN va EMERGENCY khong can endTime truoc khi bac si
-- danh gia; SCHEDULED van bat buoc co endTime (constraint cu giu nguyen).
-- Quy tac trang thai (PENDING -> CONFIRMED; WALK_IN/EMERGENCY
-- -> CHECKED_IN) xu ly tai backend, khong sua constraint status.

CREATE INDEX IF NOT EXISTS "idxAppointmentsTypeDate"
    ON booking."appointments" ("appointmentType", "scheduledDate");

CREATE INDEX IF NOT EXISTS "idxAppointmentsBookingSource"
    ON booking."appointments" ("bookingSource");

COMMENT ON COLUMN booking."appointments"."appointmentType" IS
    'SCHEDULED: dat truoc; WALK_IN: khach den truc tiep; EMERGENCY: cap cuu trong gio hoat dong';
COMMENT ON COLUMN booking."appointments"."bookingSource" IS
    'ONLINE: chu nuoi; RECEPTION: le tan tai quay; PHONE: le tan nhan qua dien thoai; NULL: du lieu cu chua xac dinh';
COMMENT ON TABLE booking."appointments" IS
    'Lich hen dat truoc va luot tiep nhan truc tiep/cap cuu; lien ket queueEntries khi check-in';

COMMIT;

-- KIEM TRA:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema='booking' AND table_name='appointments'
--   AND column_name IN ('appointmentType', 'bookingSource', 'priority');
-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint WHERE conrelid='booking."appointments"'::regclass
--   AND conname IN ('ckAppointmentsType','ckAppointmentsBookingSource','ckAppointmentsWalkInSource');
