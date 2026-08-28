from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.db import Base, engine
from app.models import models  # noqa: F401 -- ensures models are registered before create_all
from app.api import auth, reports, patients, health, ml

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AEGIS AI",
    description="Your Personal AI Health Guardian -- informational health-report analysis. "
                 "Not a medical diagnosis system.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(patients.router)
app.include_router(health.router)
app.include_router(ml.router)


@app.get("/")
def root():
    return {
        "service": "AEGIS AI",
        "tagline": "Your Personal AI Health Guardian",
        "docs": "/docs",
        "disclaimer": "Informational only. Not a medical diagnosis. Always consult a qualified professional.",
    }
