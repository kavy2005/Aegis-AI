from fastapi import APIRouter

from app.risk_engine.parameter_dictionary import PARAMETER_DICTIONARY

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/status")
def health_status():
    return {"status": "ok", "service": "AEGIS AI backend"}


@router.get("/parameters")
def list_parameters():
    return PARAMETER_DICTIONARY
