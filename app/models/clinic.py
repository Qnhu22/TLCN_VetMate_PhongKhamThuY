"""Shared ORM mappings for the existing database/07_clinic.sql tables."""
from app.extensions import db


class ClinicStaff(db.Model):
    __tablename__ = "clinicStaff"
    __table_args__ = (
        db.CheckConstraint('"staffType" IN (\'CLINIC_MANAGER\', \'RECEPTIONIST\', \'VETERINARIAN\', \'LAB_TECHNICIAN\', \'ASSISTANT\', \'OTHER\')'),
        db.CheckConstraint('"status" IN (\'ACTIVE\', \'INACTIVE\')'),
        {"schema": "clinic"},
    )
    staffID = db.Column(db.BigInteger, primary_key=True)
    userID = db.Column(db.BigInteger, db.ForeignKey("auth.users.userID", ondelete="RESTRICT"), nullable=False, unique=True)
    staffCode = db.Column(db.String(30), nullable=False, unique=True)
    staffType = db.Column(db.String(30), nullable=False)
    hireDate = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, server_default="ACTIVE")
    note = db.Column(db.Text)
    createdAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updatedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), onupdate=db.func.now())


class Veterinarian(db.Model):
    __tablename__ = "veterinarians"
    __table_args__ = (
        db.CheckConstraint('"yearsExperience" IS NULL OR "yearsExperience" >= 0'),
        db.CheckConstraint('"status" IN (\'ACTIVE\', \'INACTIVE\')'),
        {"schema": "clinic"},
    )
    veterinarianID = db.Column(db.BigInteger, primary_key=True)
    staffID = db.Column(db.BigInteger, db.ForeignKey("clinic.clinicStaff.staffID", ondelete="RESTRICT"), nullable=False, unique=True)
    licenseNumber = db.Column(db.String(100))
    bio = db.Column(db.Text)
    yearsExperience = db.Column(db.Integer)
    consultationNote = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, server_default="ACTIVE")


class Specialty(db.Model):
    __tablename__ = "specialties"
    __table_args__ = {"schema": "clinic"}
    specialtyID = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    isActive = db.Column(db.Boolean, nullable=False, server_default=db.true())


class VeterinarianSpecialty(db.Model):
    __tablename__ = "veterinarianSpecialties"
    __table_args__ = (
        db.Index("uqVetPrimarySpecialty", "veterinarianID", unique=True,
                 postgresql_where=db.text('"isPrimary" = true'), sqlite_where=db.text('"isPrimary" = true')),
        {"schema": "clinic"},
    )
    veterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="CASCADE"), primary_key=True)
    specialtyID = db.Column(db.BigInteger, db.ForeignKey("clinic.specialties.specialtyID", ondelete="RESTRICT"), primary_key=True)
    isPrimary = db.Column(db.Boolean, nullable=False, server_default=db.false())


class ServiceCategory(db.Model):
    __tablename__ = "serviceCategories"
    __table_args__ = {"schema": "clinic"}
    categoryID = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    isActive = db.Column(db.Boolean, nullable=False, server_default=db.true())


class Service(db.Model):
    __tablename__ = "services"
    __table_args__ = (
        db.CheckConstraint('"price" >= 0'),
        db.CheckConstraint('"defaultDurationMinutes" > 0 AND "defaultDurationMinutes" % 15 = 0'),
        db.CheckConstraint('"status" IN (\'ACTIVE\', \'INACTIVE\')'),
        db.CheckConstraint('NOT "isEmergency" OR NOT "isBookable"', name="ckEmergencyNotBookable"),
        {"schema": "clinic"},
    )
    serviceID = db.Column(db.BigInteger, primary_key=True)
    categoryID = db.Column(db.BigInteger, db.ForeignKey("clinic.serviceCategories.categoryID", ondelete="RESTRICT"), nullable=False)
    serviceCode = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(14, 2), nullable=False, server_default="0")
    defaultDurationMinutes = db.Column(db.Integer, nullable=False, server_default="30")
    requiresVeterinarian = db.Column(db.Boolean, nullable=False, server_default=db.true())
    isBookable = db.Column(db.Boolean, nullable=False, server_default=db.true())
    isEmergency = db.Column(db.Boolean, nullable=False, server_default=db.false())
    status = db.Column(db.String(20), nullable=False, server_default="ACTIVE")
    createdAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updatedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), onupdate=db.func.now())


class ServiceSpecialty(db.Model):
    __tablename__ = "serviceSpecialties"
    __table_args__ = {"schema": "clinic"}
    serviceID = db.Column(db.BigInteger, db.ForeignKey("clinic.services.serviceID", ondelete="CASCADE"), primary_key=True)
    specialtyID = db.Column(db.BigInteger, db.ForeignKey("clinic.specialties.specialtyID", ondelete="RESTRICT"), primary_key=True)


class VeterinarianService(db.Model):
    __tablename__ = "veterinarianServices"
    __table_args__ = (
        db.CheckConstraint('"customDurationMinutes" IS NULL OR ("customDurationMinutes" > 0 AND "customDurationMinutes" % 15 = 0)'),
        {"schema": "clinic"},
    )
    veterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="CASCADE"), primary_key=True)
    serviceID = db.Column(db.BigInteger, db.ForeignKey("clinic.services.serviceID", ondelete="RESTRICT"), primary_key=True)
    customDurationMinutes = db.Column(db.Integer)
    isActive = db.Column(db.Boolean, nullable=False, server_default=db.true())
    note = db.Column(db.Text)


class WorkingSchedule(db.Model):
    __tablename__ = "workingSchedules"
    __table_args__ = (
        db.UniqueConstraint("veterinarianID", "workDate", name="uqVetWorkDate"),
        db.CheckConstraint('"status" IN (\'AVAILABLE\', \'UNAVAILABLE\')'),
        db.CheckConstraint('"morningStartTime" < "morningEndTime" AND "morningEndTime" <= "afternoonStartTime" AND "afternoonStartTime" < "afternoonEndTime"', name="ckWorkDayTimes"),
        db.CheckConstraint('NOT "isEmergencyLead" OR "status" = \'AVAILABLE\'', name="ckEmergencyLeadAvailable"),
        db.Index("uqEmergencyLeadPerDay", "workDate", unique=True,
                 postgresql_where=db.text('"isEmergencyLead" AND "status" = \'AVAILABLE\''),
                 sqlite_where=db.text('"isEmergencyLead" AND "status" = \'AVAILABLE\'')),
        db.Index("idxWorkSchedulesDateStatus", "workDate", "status"),
        {"schema": "clinic"},
    )
    scheduleID = db.Column(db.BigInteger, primary_key=True)
    veterinarianID = db.Column(db.BigInteger, db.ForeignKey("clinic.veterinarians.veterinarianID", ondelete="RESTRICT"), nullable=False)
    workDate = db.Column(db.Date, nullable=False)
    morningStartTime = db.Column(db.Time, nullable=False, server_default=db.text("'07:30'"))
    morningEndTime = db.Column(db.Time, nullable=False, server_default=db.text("'11:30'"))
    afternoonStartTime = db.Column(db.Time, nullable=False, server_default=db.text("'13:00'"))
    afternoonEndTime = db.Column(db.Time, nullable=False, server_default=db.text("'17:00'"))
    status = db.Column(db.String(20), nullable=False, server_default="AVAILABLE")
    isEmergencyLead = db.Column(db.Boolean, nullable=False, server_default=db.false())
    assignedByStaffID = db.Column(db.BigInteger, db.ForeignKey("clinic.clinicStaff.staffID", ondelete="SET NULL"))
    note = db.Column(db.Text)
    createdAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updatedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), onupdate=db.func.now())


class StaffLeave(db.Model):
    __tablename__ = "staffLeaves"
    __table_args__ = (
        db.CheckConstraint('"endAt" > "startAt"', name="ckStaffLeaveRange"),
        db.CheckConstraint('"status" IN (\'PENDING\', \'APPROVED\', \'REJECTED\', \'CANCELLED\')'),
        db.Index("idxStaffLeavesStaffStatus", "staffID", "status", "startAt"),
        {"schema": "clinic"},
    )
    leaveID = db.Column(db.BigInteger, primary_key=True)
    staffID = db.Column(db.BigInteger, db.ForeignKey("clinic.clinicStaff.staffID", ondelete="RESTRICT"), nullable=False)
    startAt = db.Column(db.DateTime(timezone=True), nullable=False)
    endAt = db.Column(db.DateTime(timezone=True), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(25), nullable=False, server_default="PENDING")
    reviewedByStaffID = db.Column(db.BigInteger, db.ForeignKey("clinic.clinicStaff.staffID", ondelete="SET NULL"))
    reviewedAt = db.Column(db.DateTime(timezone=True))
    reviewNote = db.Column(db.Text)
    createdAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updatedAt = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), onupdate=db.func.now())
