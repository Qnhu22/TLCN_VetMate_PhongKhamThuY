"""Internal allowlisted data for owner/notification integration.

Caller MUST authorize access to the visit (and publication policy) first.
No internal note/reaction, contact data, email dispatch or appointment creation.
"""
from app.extensions import db
from app.models import FollowUp, VaccinationRecord, Vaccine


def care_summary(visit_id):
    vaccines = db.session.execute(db.select(Vaccine.name, VaccinationRecord.vaccinationDate,
        VaccinationRecord.dose, VaccinationRecord.nextDueDate).join(Vaccine,
        Vaccine.vaccineID == VaccinationRecord.vaccineID).where(VaccinationRecord.visitID == visit_id)
        .order_by(VaccinationRecord.vaccinationID)).mappings().all()
    follow_ups = db.session.execute(db.select(FollowUp.followUpID, FollowUp.scheduledDate,
        FollowUp.reason, FollowUp.status, FollowUp.appointmentID).where(FollowUp.visitID == visit_id)
        .order_by(FollowUp.followUpID)).mappings().all()
    return {"vaccinations": [dict(row) for row in vaccines], "followUps": [dict(row) for row in follow_ups]}
