"""Backend configuration; every path and deployment value comes from env."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ARTIFACT_DIR = Path(os.getenv("EHI_ARTIFACT_DIR", BASE_DIR / "artifacts"))
MODEL_PATH = ARTIFACT_DIR / "happiness_model.joblib"
SUMMARY_PATH = ARTIFACT_DIR / "dashboard_happiness_summary.json"

# Comma-separated origins allowed by flask-cors.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("EHI_CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

PORT = int(os.getenv("PORT", "5000"))
