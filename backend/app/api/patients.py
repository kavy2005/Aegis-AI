from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import User, Patient, Report
from app.schemas.schemas import PatientOut, PatientContextUpdate, HistoryPoint
from app.security import get_current_user

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me", response_model=PatientOut)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Patient).filter(Patient.user_id == current_user.id).first()


@router.put("/me", response_model=PatientOut)
def update_my_profile(
    payload: PatientContextUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/me/history", response_model=list[HistoryPoint])
def get_my_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    points = []
    for report in sorted(patient.reports, key=lambda r: r.uploaded_at):
        if not report.assessment:
            continue
        params = {
            p.canonical_parameter: p.value
            for p in report.parameters
            if p.canonical_parameter and p.value is not None
        }
        points.append(HistoryPoint(
            report_id=report.id,
            date=report.uploaded_at,
            level=report.assessment.level,
            score=report.assessment.score,
            parameters=params,
        ))
    return points
