"""Load the Colab artifacts once and build prediction features."""

import json
import logging
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)


class ModelService:
    """Owns the loaded model artifact and the cached dashboard summary."""

    def __init__(self, model_path, summary_path):
        self.model_path = Path(model_path)
        self.summary_path = Path(summary_path)
        self.artifact = None
        self._summary = None
        try:
            self.artifact = joblib.load(self.model_path)
        except FileNotFoundError:
            logger.error("Model artifact tidak ditemukan: %s", self.model_path)

    @property
    def available(self):
        """Whether the model artifact was loaded successfully."""
        return self.artifact is not None

    @property
    def model_name(self):
        """Name stored in the exported artifact, if loaded."""
        return self.artifact["model_name"] if self.available else None

    def options(self):
        """List departments and their job titles from role_mean_train."""
        titles_by_department = {}
        for department, job_title in self.artifact["role_mean_train"]:
            titles_by_department.setdefault(department, set()).add(job_title)
        return {
            "departments": sorted(titles_by_department),
            "job_titles_by_department": {
                department: sorted(titles)
                for department, titles in titles_by_department.items()
            },
        }

    def summary(self):
        """Return the dashboard summary, loaded once and cached in memory."""
        if self._summary is None and self.summary_path.is_file():
            with self.summary_path.open(encoding="utf-8") as summary_file:
                self._summary = json.load(summary_file)
        return self._summary

    def predict(self, data):
        """Compute the six notebook features and return a labeled prediction."""
        artifact = self.artifact
        salary = float(data["salary_inr"])
        experience = data["experience_years"]
        tenure = data["tenure_years"]
        global_mean = artifact["global_mean_train"]

        warnings = []
        role_key = (data["department"], data["job_title"])
        role_mean = artifact["role_mean_train"].get(role_key)
        if role_mean is None:
            role_mean = global_mean
            warnings.append(
                f"Role {role_key} tidak ada di role_mean_train; "
                "memakai rata-rata gaji global."
            )

        exp_mean = artifact["exp_mean_train"].get(experience)
        if exp_mean is None:
            exp_mean = global_mean
            warnings.append(
                f"Experience {experience} tahun tidak ada di exp_mean_train; "
                "memakai rata-rata gaji global."
            )

        features = {
            "Salary_INR": salary,
            "Experience_Years": experience,
            "Tenure_Years": tenure,
            "Salary_Disparity_Index": salary / role_mean,
            "Salary_Ratio_By_Year": salary / exp_mean,
            "Salary_Per_Tenure": salary / (tenure + 1),
        }
        values = np.array(
            [[np.float32(features[name]) for name in artifact["feature_names"]]],
            dtype=np.float32,
        )
        model = artifact["model"]
        label_code = int(model.predict(values)[0])
        probabilities = {
            label: float(probability)
            for label, probability in zip(
                artifact["class_labels"], model.predict_proba(values)[0]
            )
        }
        return {
            "label": artifact["class_labels"][label_code],
            "label_code": label_code,
            "probabilities": probabilities,
            "features": features,
            "warnings": warnings,
        }
