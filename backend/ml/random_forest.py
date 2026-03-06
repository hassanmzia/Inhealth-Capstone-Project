"""
Random Forest classifier for chronic disease classification.
Multi-label classification: COPD, Diabetes, CVD, CKD, Heart Failure.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.random_forest")


class RandomForestDiseaseClassifier:
    """
    Random Forest model for chronic disease risk classification.

    Takes patient clinical features and outputs probability of each
    chronic disease category. Used by Tier 3 risk agents for
    multi-condition risk assessment.
    """

    DISEASE_LABELS = [
        "diabetes_type2",
        "copd",
        "cardiovascular_disease",
        "chronic_kidney_disease",
        "heart_failure",
    ]

    FEATURE_NAMES = [
        # Demographics
        "age", "gender_encoded", "bmi",
        # Vitals
        "bp_systolic", "bp_diastolic", "heart_rate", "spo2", "respiratory_rate",
        # Labs
        "a1c", "fasting_glucose", "total_cholesterol", "ldl", "hdl", "triglycerides",
        "creatinine", "egfr", "bun", "potassium", "sodium",
        "wbc", "hemoglobin", "platelets",
        "bnp", "troponin_i", "d_dimer", "crp",
        # Pulmonary
        "fev1_percent", "fvc_percent", "fev1_fvc_ratio",
        # History flags
        "family_hx_diabetes", "family_hx_cvd", "family_hx_ckd",
        "smoking_pack_years", "alcohol_drinks_per_week",
        "prior_mi", "prior_stroke", "prior_cabg_pci",
    ]

    def __init__(self, model_path: str = None, n_estimators: int = 300):
        self.model = None
        self.model_path = model_path
        self.n_estimators = n_estimators
        self.version = "rf_disease_v1"
        self._is_loaded = False

    def load(self):
        """Load or initialize Random Forest model."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.multioutput import MultiOutputClassifier

        try:
            if self.model_path:
                import joblib
                self.model = joblib.load(self.model_path)
                logger.info(f"Random Forest model loaded from {self.model_path}")
            else:
                base_rf = RandomForestClassifier(
                    n_estimators=self.n_estimators,
                    max_depth=12,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                )
                self.model = MultiOutputClassifier(base_rf)
            self._is_loaded = True
        except Exception as e:
            logger.error(f"Random Forest model load failed: {e}")

    def extract_features(self, patient) -> Dict[str, float]:
        """
        Extract feature values from a FHIRPatient Django model instance.
        Returns dict with feature_name -> value.
        """
        from django.utils import timezone
        from datetime import timedelta

        features = {}
        now = timezone.now()

        # Demographics
        features["age"] = patient.age or 0
        features["gender_encoded"] = 1 if patient.gender == "male" else 0

        # BMI from observations
        def get_latest_obs(loinc_code: str, days_back: int = 180) -> Optional[float]:
            obs = patient.observations.filter(
                code=loinc_code,
                effective_datetime__gte=now - timedelta(days=days_back),
                status="final",
            ).order_by("-effective_datetime").first()
            return obs.value_quantity if obs else None

        features["bmi"] = get_latest_obs("39156-5") or 25.0

        # Vitals
        features["bp_systolic"] = get_latest_obs("8480-6") or 120
        features["bp_diastolic"] = get_latest_obs("8462-4") or 80
        features["heart_rate"] = get_latest_obs("8867-4") or 72
        features["spo2"] = get_latest_obs("59408-5") or 98
        features["respiratory_rate"] = get_latest_obs("9279-1") or 16

        # Metabolic labs
        features["a1c"] = get_latest_obs("4548-4") or 5.5
        features["fasting_glucose"] = get_latest_obs("1558-6") or 95
        features["total_cholesterol"] = get_latest_obs("2093-3") or 180
        features["ldl"] = get_latest_obs("2089-1") or 100
        features["hdl"] = get_latest_obs("2085-9") or 50
        features["triglycerides"] = get_latest_obs("2571-8") or 130

        # Renal
        features["creatinine"] = get_latest_obs("2160-0") or 1.0
        features["egfr"] = get_latest_obs("48642-3") or 90
        features["bun"] = get_latest_obs("3094-0") or 15
        features["potassium"] = get_latest_obs("2823-3") or 4.0
        features["sodium"] = get_latest_obs("2951-2") or 140

        # CBC
        features["wbc"] = get_latest_obs("6690-2") or 7.0
        features["hemoglobin"] = get_latest_obs("718-7") or 14.0
        features["platelets"] = get_latest_obs("777-3") or 250

        # Cardiac biomarkers
        features["bnp"] = get_latest_obs("42637-9") or 50
        features["troponin_i"] = get_latest_obs("6598-7") or 0.01
        features["d_dimer"] = get_latest_obs("48065-7") or 0.3
        features["crp"] = get_latest_obs("1988-5") or 1.0

        # Pulmonary function
        features["fev1_percent"] = get_latest_obs("20150-9") or 95
        features["fvc_percent"] = get_latest_obs("19868-9") or 95
        fev1 = features["fev1_percent"]
        fvc = features["fvc_percent"]
        features["fev1_fvc_ratio"] = (fev1 / fvc) if fvc > 0 else 0.8

        # Family history flags (from conditions/notes — simplified)
        features["family_hx_diabetes"] = 0
        features["family_hx_cvd"] = 0
        features["family_hx_ckd"] = 0

        # Lifestyle (defaults — can be enriched from SDOH assessment)
        features["smoking_pack_years"] = 0
        features["alcohol_drinks_per_week"] = 0

        # Prior events
        conditions = set(
            patient.conditions.filter(clinical_status="active")
            .values_list("code", flat=True)
        )
        features["prior_mi"] = 1 if "I21" in conditions or "I21.9" in conditions else 0
        features["prior_stroke"] = 1 if "I63" in conditions or "I63.9" in conditions else 0
        features["prior_cabg_pci"] = 0  # Would need procedure history

        return features

    def predict(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Predict chronic disease probabilities.
        Returns dict of disease_label -> probability (0.0 - 1.0).
        """
        if not self._is_loaded:
            self.load()

        feature_vector = np.array([
            features.get(name, 0.0) for name in self.FEATURE_NAMES
        ]).reshape(1, -1)

        if self.model is None:
            return self._heuristic_classify(features)

        try:
            # MultiOutputClassifier returns list of arrays
            probas = self.model.predict_proba(feature_vector)
            results = {}
            for i, label in enumerate(self.DISEASE_LABELS):
                # predict_proba returns [prob_class_0, prob_class_1]
                results[label] = float(probas[i][0][1]) if len(probas[i][0]) > 1 else 0.0
            return results
        except Exception as e:
            logger.error(f"Random Forest prediction failed: {e}")
            return self._heuristic_classify(features)

    def _heuristic_classify(self, features: Dict[str, float]) -> Dict[str, float]:
        """Rule-based fallback classification when model is unavailable."""
        results = {}

        # Diabetes Type 2
        dm_score = 0.05
        a1c = features.get("a1c", 5.5)
        if a1c >= 6.5:
            dm_score += 0.50
        elif a1c >= 5.7:
            dm_score += 0.20
        if features.get("fasting_glucose", 95) >= 126:
            dm_score += 0.25
        if features.get("bmi", 25) >= 30:
            dm_score += 0.10
        if features.get("family_hx_diabetes", 0):
            dm_score += 0.10
        results["diabetes_type2"] = min(1.0, dm_score)

        # COPD
        copd_score = 0.05
        fev1_fvc = features.get("fev1_fvc_ratio", 0.8)
        if fev1_fvc < 0.70:
            copd_score += 0.50
        if features.get("smoking_pack_years", 0) > 20:
            copd_score += 0.25
        if features.get("spo2", 98) < 92:
            copd_score += 0.15
        results["copd"] = min(1.0, copd_score)

        # CVD
        cvd_score = 0.05
        if features.get("bp_systolic", 120) >= 140:
            cvd_score += 0.15
        if features.get("ldl", 100) >= 160:
            cvd_score += 0.15
        if features.get("total_cholesterol", 180) >= 240:
            cvd_score += 0.10
        if features.get("prior_mi", 0) or features.get("prior_stroke", 0):
            cvd_score += 0.35
        if features.get("age", 0) >= 65:
            cvd_score += 0.10
        results["cardiovascular_disease"] = min(1.0, cvd_score)

        # CKD
        ckd_score = 0.05
        egfr = features.get("egfr", 90)
        if egfr < 30:
            ckd_score += 0.55
        elif egfr < 60:
            ckd_score += 0.30
        elif egfr < 90:
            ckd_score += 0.10
        if features.get("creatinine", 1.0) > 1.5:
            ckd_score += 0.15
        results["chronic_kidney_disease"] = min(1.0, ckd_score)

        # Heart Failure
        hf_score = 0.05
        bnp = features.get("bnp", 50)
        if bnp > 400:
            hf_score += 0.45
        elif bnp > 100:
            hf_score += 0.20
        if features.get("prior_mi", 0):
            hf_score += 0.20
        if features.get("bp_systolic", 120) >= 160:
            hf_score += 0.10
        results["heart_failure"] = min(1.0, hf_score)

        return results

    def get_feature_importance(self) -> Dict[str, Dict[str, float]]:
        """Return per-disease feature importances from the trained model."""
        if self.model is None or not self._is_loaded:
            return {}
        try:
            result = {}
            for i, label in enumerate(self.DISEASE_LABELS):
                importances = self.model.estimators_[i].feature_importances_
                result[label] = dict(sorted(
                    zip(self.FEATURE_NAMES, importances.tolist()),
                    key=lambda x: x[1],
                    reverse=True,
                ))
            return result
        except Exception:
            return {}

    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the model on labeled data. X: (n_samples, n_features), y: (n_samples, n_diseases)."""
        if not self._is_loaded:
            self.load()
        self.model.fit(X, y)
        logger.info(f"Random Forest trained on {X.shape[0]} samples")

    def save(self, path: str):
        """Save trained model to disk."""
        import joblib
        joblib.dump(self.model, path)
        logger.info(f"Random Forest model saved to {path}")
