import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Patient context ----------

class PatientContextUpdate(BaseModel):
    age: Optional[int] = None
    sex: Optional[str] = None
    pregnant: Optional[bool] = False
    known_conditions: Optional[str] = None
    medications: Optional[str] = None
    allergies: Optional[str] = None
    lifestyle_notes: Optional[str] = None


class PatientOut(PatientContextUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Reports / extraction ----------

class ExtractedParameterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    raw_label: str
    canonical_parameter: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_source: Optional[str] = None
    flag: Optional[str] = None
    severity: Optional[int] = None


class ParameterCorrection(BaseModel):
    raw_label: str
    canonical_parameter: Optional[str] = None
    value: float
    unit: Optional[str] = None


class ReportUploadResponse(BaseModel):
    report_id: int
    filename: str
    raw_text_preview: str
    parameters_detected: int
    parameters: List[ExtractedParameterOut]


class AnalyzeRequest(BaseModel):
    corrections: Optional[List[ParameterCorrection]] = None
    symptoms: Optional[List[str]] = None


class RiskAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score: int
    level: int
    label: str
    abnormal_count: int
    critical_breach: bool
    summary: str


class ReportAnalysisResponse(BaseModel):
    report_id: int
    risk: RiskAssessmentOut
    parameters: List[ExtractedParameterOut]
    explanation: dict
    disclaimer: str = (
        "This is an AI-assisted informational assessment, not a medical diagnosis. "
        "Please consult a qualified healthcare professional to confirm any finding."
    )


class ReportSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    uploaded_at: datetime.datetime
    is_demo: bool


class HistoryPoint(BaseModel):
    report_id: int
    date: datetime.datetime
    level: int
    score: int
    parameters: dict


# ---------- ML ----------

class MLPredictRequest(BaseModel):
    age: int
    sex: str
    hemoglobin: Optional[float] = None
    fasting_glucose: Optional[float] = None
    hba1c: Optional[float] = None
    ldl: Optional[float] = None
    hdl: Optional[float] = None
    triglycerides: Optional[float] = None
    creatinine: Optional[float] = None
    alt: Optional[float] = None
    ast: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    bmi: Optional[float] = None


class MLPredictResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_available: bool
    predicted_level: Optional[int] = None
    probabilities: Optional[dict] = None
    top_contributors: Optional[List[dict]] = None
    message: Optional[str] = None


# ---------- Copilot ----------

class CopilotMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class CopilotReportContext(BaseModel):
    """Shape matches ReportAnalysisResponse's relevant fields exactly, so the
    frontend can pass its already-fetched analysis response straight through
    without reshaping anything."""
    filename: Optional[str] = None
    risk: Optional[RiskAssessmentOut] = None
    parameters: List[ExtractedParameterOut] = []
    explanation: Optional[dict] = None


class CopilotChatRequest(BaseModel):
    message: str
    report_context: Optional[CopilotReportContext] = None
    history: Optional[List[CopilotMessage]] = None


class CopilotChatResponse(BaseModel):
    reply: str
    source: str  # "llm" or "rule_based"
    disclaimer: str = (
        "AEGIS AI Copilot shares general information only, not medical advice or a diagnosis. "
        "Always consult a qualified healthcare professional about your results."
    )
