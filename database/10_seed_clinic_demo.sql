-- VetMate DEMO ONLY. Chay trong pgAdmin tren DB dev/test da sao luu.
-- Khong xoa hay sua tai khoan hien co. Chay lai khong tao trung.
BEGIN;
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM auth."users" WHERE "userID"=4 AND "status"='ACTIVE')
    OR NOT EXISTS (SELECT 1 FROM auth."userRoles" ur JOIN auth.roles r ON r."roleID"=ur."roleID" WHERE ur."userID"=4 AND r."roleCode"='RECEPTIONIST') THEN
  RAISE EXCEPTION 'Khong tim thay le tan userID=4 dang ACTIVE; dung script va kiem tra lai';
 END IF;
END $$;

INSERT INTO clinic."clinicStaff" ("userID","staffCode","staffType","status","note")
VALUES (4,'DEMO-REC-004','RECEPTIONIST','ACTIVE','Ho so le tan phuc vu demo')
ON CONFLICT ("userID") DO NOTHING;

-- Tao tai khoan bac si PHI DANG NHAP, chi de dat lich. Khong chia se mat khau demo.
-- Hash khong hop le voi Werkzeug nen tai khoan nay khong dung de dang nhap.
INSERT INTO auth."users" ("email","passwordHash","fullName","status")
VALUES ('vet-demo@vetmate.invalid','DEMO_NON_LOGIN_ACCOUNT','BS. Nguyen Minh An (Demo)','ACTIVE')
ON CONFLICT ("email") DO NOTHING;

DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM auth."users" WHERE "email"='vet-demo@vetmate.invalid' AND "fullName" <> 'BS. Nguyen Minh An (Demo)') THEN
  RAISE EXCEPTION 'Email demo da duoc su dung boi tai khoan khac';
 END IF;
END $$;

INSERT INTO auth."userRoles" ("userID","roleID")
SELECT u."userID",r."roleID" FROM auth."users" u CROSS JOIN auth.roles r
WHERE u."email"='vet-demo@vetmate.invalid' AND r."roleCode"='VETERINARIAN'
ON CONFLICT DO NOTHING;

INSERT INTO clinic."clinicStaff" ("userID","staffCode","staffType","status","note")
SELECT "userID",'DEMO-VET-001','VETERINARIAN','ACTIVE','Bac si mau de test lich hen'
FROM auth."users" WHERE "email"='vet-demo@vetmate.invalid'
ON CONFLICT ("userID") DO NOTHING;

INSERT INTO clinic."veterinarians" ("staffID","status","bio")
SELECT "staffID",'ACTIVE','Bac si demo cho quy trinh dat lich'
FROM clinic."clinicStaff" WHERE "staffCode"='DEMO-VET-001'
ON CONFLICT ("staffID") DO NOTHING;

INSERT INTO clinic."specialties" ("name","description")
VALUES ('Khám tổng quát (Demo)','Chuyên khoa phuc vu demo dat lich')
ON CONFLICT ("name") DO NOTHING;

INSERT INTO clinic."serviceCategories" ("name","description")
VALUES ('Khám bệnh (Demo)','Danh muc dich vu phuc vu demo')
ON CONFLICT ("name") DO NOTHING;

INSERT INTO clinic."services" ("categoryID","serviceCode","name","description","price","defaultDurationMinutes","requiresVeterinarian","isBookable","isEmergency","status")
SELECT c."categoryID",'DEMO-KHAM-001','Khám tổng quát thú cưng (Demo)','Dich vu mau cho dat lich',150000,30,true,true,false,'ACTIVE'
FROM clinic."serviceCategories" c WHERE c."name"='Khám bệnh (Demo)'
ON CONFLICT ("serviceCode") DO NOTHING;

INSERT INTO clinic."serviceSpecialties" ("serviceID","specialtyID")
SELECT s."serviceID",sp."specialtyID"
FROM clinic."services" s CROSS JOIN clinic."specialties" sp
WHERE s."serviceCode"='DEMO-KHAM-001' AND sp."name"='Khám tổng quát (Demo)'
ON CONFLICT DO NOTHING;

INSERT INTO clinic."veterinarianSpecialties" ("veterinarianID","specialtyID","isPrimary")
SELECT v."veterinarianID",sp."specialtyID",true
FROM clinic."veterinarians" v
JOIN clinic."clinicStaff" st ON st."staffID"=v."staffID"
CROSS JOIN clinic."specialties" sp
WHERE st."staffCode"='DEMO-VET-001' AND sp."name"='Khám tổng quát (Demo)'
ON CONFLICT ("veterinarianID","specialtyID") DO NOTHING;

-- Tao lich 30 ngay ke tu ngay mai, khong ghi de lich da co.
INSERT INTO clinic."workingSchedules" ("veterinarianID","workDate","status","note")
SELECT v."veterinarianID", current_date + g.day_offset,'AVAILABLE','Lich lam viec demo'
FROM clinic."veterinarians" v
JOIN clinic."clinicStaff" st ON st."staffID"=v."staffID"
CROSS JOIN generate_series(1,30) AS g(day_offset)
WHERE st."staffCode"='DEMO-VET-001'
ON CONFLICT ("veterinarianID","workDate") DO NOTHING;
COMMIT;

-- Kiem tra sau khi chay
SELECT 'Le tan' AS nhom, count(*) AS so_luong FROM clinic."clinicStaff" WHERE "userID"=4
UNION ALL SELECT 'Bac si demo',count(*) FROM clinic."veterinarians" v JOIN clinic."clinicStaff" st ON st."staffID"=v."staffID" WHERE st."staffCode"='DEMO-VET-001'
UNION ALL SELECT 'Dich vu demo',count(*) FROM clinic."services" WHERE "serviceCode"='DEMO-KHAM-001'
UNION ALL SELECT 'Lich demo',count(*) FROM clinic."workingSchedules" w JOIN clinic."veterinarians" v ON v."veterinarianID"=w."veterinarianID" JOIN clinic."clinicStaff" st ON st."staffID"=v."staffID" WHERE st."staffCode"='DEMO-VET-001';
