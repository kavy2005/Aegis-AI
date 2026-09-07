# AEGIS AI

### AI-Powered Health Report Intelligence

AEGIS AI transforms laboratory reports into structured, understandable health insights.

Users can upload a report, extract and normalize laboratory values, identify results outside report-provided reference ranges, receive an explainable AEGIS Signal, ask questions through an AI Copilot, track reports over time, and compare recent results.

> AEGIS AI is an informational prototype and does not provide medical diagnosis or replace qualified healthcare professionals.

## Features

- **Lab Report Analysis** — Extracts and structures laboratory parameters from reports.
- **OCR & Parsing** — Processes report text and converts it into structured data.
- **Parameter Normalization** — Maps different laboratory labels to canonical parameters.
- **Reference-Range Analysis** — Uses reference ranges provided by the report when available.
- **AEGIS Signal** — Generates a prototype risk score and risk level from detected findings.
- **Explainable Results** — Presents important findings in understandable language.
- **AI Copilot** — Ask questions about the current report and its results.
- **Dynamic Suggestions** — Copilot questions adapt to the report's attention findings.
- **Health Memory** — Maintains a timeline of previously analysed reports.
- **Report Comparison** — Compares recent reports and highlights changes over time.
- **Authentication** — Protected user accounts and report data.

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- React Router
- CSS

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT
- bcrypt

### AI & Processing

- PyMuPDF
- Tesseract OCR
- Pillow
- Anthropic API
- Custom parameter normalization
- Custom reference-range interpretation
- Custom risk-scoring engine

### Database

- SQLite for local development
- PostgreSQL for production

### Testing

- pytest
- FastAPI TestClient
- Unit and API tests

## Project Structure

```text
Aegis-AI/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── database/
│   │   ├── models/
│   │   ├── ocr/
│   │   ├── risk_engine/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-optional.txt
│
├── frontend/
│   ├── public/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── context/
│       ├── pages/
│       └── styles/
│
└── ml/
                    AEGIS AI
                       |
             React + TypeScript
                       |
                    FastAPI
                       |
        +--------------+--------------+
        |              |              |
     Extraction      Parser        AI Layer
        |              |              |
       OCR       Normalization     Copilot
                       |
                 Risk Engine
                       |
             +---------+---------+
             |                   |
        AEGIS Signal       Explanation
             |                   |
             +---------+---------+
                       |
                Health Memory
                       |
                Report Comparison