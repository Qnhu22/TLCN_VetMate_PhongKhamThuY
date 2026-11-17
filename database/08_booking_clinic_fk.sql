-- VetMate | 07_booking_clinic_fk.sql
-- Chay SAU 06_booking.sql va 06_clinic.sql (ca hai da tao bang).
-- Dung ten constraint co dinh de co the chay lai ma khong tao trung.
BEGIN;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fkAppointmentsService' AND conrelid='booking."appointments"'::regclass) THEN
  ALTER TABLE booking."appointments" ADD CONSTRAINT "fkAppointmentsService" FOREIGN KEY ("serviceID") REFERENCES clinic."services"("serviceID") ON DELETE RESTRICT;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fkAppointmentsVeterinarian' AND conrelid='booking."appointments"'::regclass) THEN
  ALTER TABLE booking."appointments" ADD CONSTRAINT "fkAppointmentsVeterinarian" FOREIGN KEY ("veterinarianID") REFERENCES clinic."veterinarians"("veterinarianID") ON DELETE RESTRICT;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fkAppointmentsConfirmedByStaff' AND conrelid='booking."appointments"'::regclass) THEN
  ALTER TABLE booking."appointments" ADD CONSTRAINT "fkAppointmentsConfirmedByStaff" FOREIGN KEY ("confirmedByStaffID") REFERENCES clinic."clinicStaff"("staffID") ON DELETE SET NULL;
 END IF;
END $$;
CREATE INDEX IF NOT EXISTS "idxAppointmentsService" ON booking."appointments" ("serviceID");
COMMIT;
