"""API blueprint for health, options, summary and prediction."""

import math

from flask import Blueprint, abort, current_app, jsonify, request

api = Blueprint("api", __name__)


def _service():
    return current_app.extensions["model_service"]


def _validate(data):
    """Collect per-field validation errors for a prediction request."""
    if not isinstance(data, dict):
        return {"body": "Body harus berupa JSON object."}

    errors = {}
    for field in ("department", "job_title"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "wajib diisi."

    salary = data.get("salary_inr")
    if (
        isinstance(salary, bool)
        or not isinstance(salary, (int, float))
        or not math.isfinite(salary)
        or salary <= 0
    ):
        errors["salary_inr"] = "harus angka lebih dari 0."

    for field in ("experience_years", "tenure_years"):
        value = data.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors[field] = "harus integer lebih dari atau sama dengan 0."
    return errors


@api.get("/health")
def health():
    """Report service status and the loaded model name."""
    service = _service()
    if not service.available:
        return jsonify({"status": "error", "model": None}), 503
    return jsonify({"status": "ok", "model": service.model_name})


@api.get("/options")
def options():
    """Return departments and job titles seen in training."""
    service = _service()
    if not service.available:
        return jsonify({"error": "Model artifact belum tersedia."}), 503
    return jsonify(service.options())


@api.get("/summary")
def summary():
    """Serve the dashboard summary JSON as-is."""
    data = _service().summary()
    if data is None:
        abort(404, description="dashboard_happiness_summary.json tidak ditemukan.")
    return jsonify(data)


@api.post("/predict")
def predict():
    """Validate input and return a happiness prediction with warnings."""
    errors = _validate(request.get_json(silent=True))
    if errors:
        return jsonify({"error": "Input tidak valid.", "details": errors}), 400

    service = _service()
    if not service.available:
        return jsonify({"error": "Model artifact belum tersedia."}), 503
    try:
        return jsonify(service.predict(request.get_json()))
    except Exception:
        current_app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed."}), 500
