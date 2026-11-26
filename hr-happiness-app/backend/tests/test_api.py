"""Tests for /api/predict against a real joblib artifact in a temp dir."""

import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.dummy import DummyClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402

CLASS_LABELS = ["Tidak Bahagia", "Cukup Bahagia", "Bahagia"]
FEATURE_NAMES = [
    "Salary_INR",
    "Experience_Years",
    "Tenure_Years",
    "Salary_Disparity_Index",
    "Salary_Ratio_By_Year",
    "Salary_Per_Tenure",
]
PAYLOAD = {
    "department": "Engineering",
    "job_title": "Engineer",
    "salary_inr": 1_200_000,
    "experience_years": 3,
    "tenure_years": 2,
}


@pytest.fixture()
def client(tmp_path):
    """Build the same artifact shape the Colab notebook exports."""
    model = DummyClassifier(strategy="uniform", random_state=0)
    model.fit(np.zeros((3, 6), dtype=np.float32), np.array([0, 1, 2]))
    artifact = {
        "model_name": "dummy-classifier",
        "model": model,
        "feature_names": FEATURE_NAMES,
        "class_labels": CLASS_LABELS,
        "role_mean_train": {
            ("Engineering", "Engineer"): 1_000_000.0,
            ("Sales", "Salesman"): 800_000.0,
        },
        "exp_mean_train": {3: 900_000.0},
        "global_mean_train": 950_000.0,
    }
    model_path = tmp_path / "happiness_model.joblib"
    joblib.dump(artifact, model_path)
    app = create_app(
        {
            "TESTING": True,
            "MODEL_PATH": model_path,
            "SUMMARY_PATH": tmp_path / "dashboard_happiness_summary.json",
        }
    )
    return app.test_client()


def test_predict_returns_label_features_and_probabilities(client):
    response = client.post("/api/predict", json=PAYLOAD)

    assert response.status_code == 200
    body = response.get_json()
    assert body["label"] in CLASS_LABELS
    assert body["label_code"] in (0, 1, 2)
    assert set(body["probabilities"]) == set(CLASS_LABELS)
    assert sum(body["probabilities"].values()) == pytest.approx(1.0)
    assert body["features"] == {
        "Salary_INR": 1_200_000.0,
        "Experience_Years": 3,
        "Tenure_Years": 2,
        "Salary_Disparity_Index": 1.2,
        "Salary_Ratio_By_Year": pytest.approx(1_200_000 / 900_000),
        "Salary_Per_Tenure": 400_000.0,
    }
    assert body["warnings"] == []


def test_predict_rejects_invalid_input_with_details(client):
    response = client.post(
        "/api/predict",
        json={
            "department": "",
            "job_title": "Engineer",
            "salary_inr": 0,
            "experience_years": -1,
            "tenure_years": -2,
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]
    assert set(body["details"]) >= {
        "department",
        "salary_inr",
        "experience_years",
        "tenure_years",
    }


def test_predict_unknown_job_title_uses_global_mean_and_warns(client):
    response = client.post("/api/predict", json={**PAYLOAD, "job_title": "Unknown"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["warnings"]
    assert "global" in body["warnings"][0].lower()
    assert body["features"]["Salary_Disparity_Index"] == pytest.approx(
        1_200_000 / 950_000
    )
