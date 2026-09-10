from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import User, Patient, Report, ExtractedParameter, RiskAssessment
from app.schemas.schemas import (
    ReportUploadResponse,
    ExtractedParameterOut,
    AnalyzeRequest,
    ReportAnalysisResponse,
    RiskAssessmentOut,
    ReportSummaryOut,
)
from app.security import get_current_user
from app.services.report_service import extract_and_normalize, analyze_findings
from app.ocr.extraction import OCRUnavailableError

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_patient(current_user: User, db: Session) -> Patient:
    return db.query(Patient).filter(Patient.user_id == current_user.id).first()


@router.post("/upload", response_model=ReportUploadResponse)
async def upload_report(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    print("UPLOAD DEBUG 1: entered upload_report", flush=True)
    print(f"UPLOAD DEBUG 2: filename={file.filename}", flush=True)

    patient = _get_patient(current_user, db)
    print(
        f"UPLOAD DEBUG 3: patient_id={patient.id if patient else None}",
        flush=True,
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found",
        )

    file_bytes = await file.read()

    print(
        f"UPLOAD DEBUG 4: file read, bytes={len(file_bytes)}",
        flush=True,
    )

    try:
        print(
            "UPLOAD DEBUG 5: starting extract_and_normalize",
            flush=True,
        )

        result = extract_and_normalize(
            file_bytes,
            file.filename,
        )

        print(
            f"UPLOAD DEBUG 6: extraction complete, "
            f"method={result.get('extraction_method')}, "
            f"rows={len(result.get('rows', []))}, "
            f"text_length={len(result.get('raw_text', ''))}",
            flush=True,
        )

    except OCRUnavailableError as e:
        print(
            f"UPLOAD DEBUG ERROR: OCR unavailable: {e}",
            flush=True,
        )
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )

    except ValueError as e:
        print(
            f"UPLOAD DEBUG ERROR: ValueError: {e}",
            flush=True,
        )
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        print(
            f"UPLOAD DEBUG ERROR: extraction failed: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process the uploaded report.",
        )

    print(
        "UPLOAD DEBUG 7: creating Report",
        flush=True,
    )

    report = Report(
        patient_id=patient.id,
        filename=file.filename,
        raw_text=result["raw_text"],
    )

    db.add(report)

    print(
        "UPLOAD DEBUG 8: committing Report",
        flush=True,
    )

    db.commit()
    db.refresh(report)

    print(
        f"UPLOAD DEBUG 9: report created, id={report.id}",
        flush=True,
    )

    param_rows = []

    for row in result["rows"]:
        param = ExtractedParameter(
            report_id=report.id,
            raw_label=row["raw_label"],
            canonical_parameter=row.get("canonical_parameter"),
            value=row.get("value"),
            unit=row.get("unit"),
            reference_low=row.get("reference_low"),
            reference_high=row.get("reference_high"),
        )

        db.add(param)
        param_rows.append(param)

    print(
        f"UPLOAD DEBUG 10: added {len(param_rows)} parameters, committing",
        flush=True,
    )

    db.commit()

    print(
        "UPLOAD DEBUG 11: parameters committed",
        flush=True,
    )

    for p in param_rows:
        db.refresh(p)

    print(
        "UPLOAD DEBUG 12: refresh complete, returning response",
        flush=True,
    )

    return ReportUploadResponse(
        report_id=report.id,
        filename=report.filename,
        raw_text_preview=result["raw_text"][:500],
        parameters_detected=len(param_rows),
        parameters=[
            ExtractedParameterOut.model_validate(p)
            for p in param_rows
        ],
    )


@router.post("/{report_id}/analyze", response_model=ReportAnalysisResponse)
def analyze_report(
    report_id: int,
    payload: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = _get_patient(current_user, db)

    report = (
        db.query(Report)
        .filter(
            Report.id == report_id,
            Report.patient_id == patient.id,
        )
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    if payload and payload.corrections:
        by_label = {
            c.raw_label: c
            for c in payload.corrections
        }

        for param in report.parameters:
            if param.raw_label in by_label:
                correction = by_label[param.raw_label]

                param.value = correction.value
                param.unit = correction.unit or param.unit
                param.canonical_parameter = (
                    correction.canonical_parameter
                    or param.canonical_parameter
                )
                param.user_corrected = True

        db.commit()

    if not report.parameters:
        raise HTTPException(
            status_code=422,
            detail=(
                "No parameters could be extracted from this report, "
                "so there is nothing to analyze. This usually means "
                "the scan quality was too low for OCR, or the report "
                "layout wasn't recognized. Try a clearer scan or a "
                "text-based PDF."
            ),
        )

    rows = [
        {
            "raw_label": p.raw_label,
            "canonical_parameter": p.canonical_parameter,
            "value": p.value,
            "unit": p.unit,
            "reference_low": p.reference_low,
            "reference_high": p.reference_high,
        }
        for p in report.parameters
    ]

    result = analyze_findings(
        rows,
        sex=patient.sex,
        language=report.language or "en",
    )

    for param, finding in zip(
        report.parameters,
        result["findings"],
    ):
        param.reference_low = finding.get("reference_low")
        param.reference_high = finding.get("reference_high")
        param.reference_source = finding.get("reference_source")
        param.flag = finding.get("flag")
        param.severity = finding.get("severity")

    db.commit()

    risk = result["risk"]

    assessment = (
        db.query(RiskAssessment)
        .filter(
            RiskAssessment.report_id == report.id
        )
        .first()
    )

    if not assessment:
        assessment = RiskAssessment(
            report_id=report.id
        )
        db.add(assessment)

    assessment.score = risk["score"]
    assessment.level = risk["level"]
    assessment.label = risk["label"]
    assessment.abnormal_count = risk["abnormal_count"]
    assessment.critical_breach = risk["critical_breach"]
    assessment.summary = result["explanation"]["summary"]
    assessment.explanation_json = result["explanation"]

    db.commit()
    db.refresh(assessment)

    return ReportAnalysisResponse(
        report_id=report.id,
        filename=report.filename,
        raw_text_preview=(report.raw_text or "")[:2000],
        risk=RiskAssessmentOut.model_validate(assessment),
        parameters=[
            ExtractedParameterOut.model_validate(p)
            for p in report.parameters
        ],
        explanation=result["explanation"],
    )


@router.get(
    "",
    response_model=list[ReportSummaryOut],
)
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = _get_patient(current_user, db)

    return sorted(
        patient.reports,
        key=lambda r: r.uploaded_at,
        reverse=True,
    )


@router.get(
    "/{report_id}",
    response_model=ReportAnalysisResponse,
)
def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = _get_patient(current_user, db)

    report = (
        db.query(Report)
        .filter(
            Report.id == report_id,
            Report.patient_id == patient.id,
        )
        .first()
    )

    if not report or not report.assessment:
        raise HTTPException(
            status_code=404,
            detail="Report or analysis not found",
        )

    return ReportAnalysisResponse(
        report_id=report.id,
        filename=report.filename,
        raw_text_preview=(report.raw_text or "")[:2000],
        risk=RiskAssessmentOut.model_validate(
            report.assessment
        ),
        parameters=[
            ExtractedParameterOut.model_validate(p)
            for p in report.parameters
        ],
        explanation=report.assessment.explanation_json,
    )