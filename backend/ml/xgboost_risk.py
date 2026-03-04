"""
XGBoost 7-day hospitalization risk scoring model.
Predicts probability of hospitalization/ED visit within 7 days.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.xgboost_risk")


class XGBoostRiskModel:
    """
    XGBoost model for 7-day hospitalization risk prediction.

    Features: clinical labs, vitals, demographics, utilization history, medications.
    Output: probability score 0.0 - 1.0
    """

    # Feature names in order (must match training)
    FEATURE_NAMES = [
        # Demographics
        "age", "gender_encoded", "num_chronic_conditions",
        # Lab values
        "a1c_latest", "a1c_trend_90d", "glucose_latest", "glucose_avg_7d", "glucose_variability",
        "bp_systolic_latest", "bp_diastolic_latest", "bp_avg_30d",
        "creatinine_latest", "egfr_latest", "bun_latest",
        "wbc_latest", "hemoglobin_latest", "potassium_latest",
        "bnp_latest", "troponin_latest",
        # Medications
        "num_active_medications", "num_high_risk_medications", "medication_adherence_score",
        # Utilization
        "ed_visits_90d", "hospitalizations_180d", "readmission_30d_flag",
        # Vitals trends
        "weight_change_kg_30d", "heart_rate_avg_7d", "spo2_avg_7d",
        # Social
        "sdoh_risk_score", "engagement_score",
        # Care gaps
        "num_open_care_gaps", "days_since_last_visit",
    ]

    def __init__(self, model_path: str = None):
        self.model = None
        self.model_path = model_path
        self.version = "xgboost_7day_v2"
        self._is_loaded = False

    def load(self):
        """Load trained XGBoost model from disk."""
        import xgboost as xgb
        try:
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=10,  # Handle class imbalance
                eval_metric="auc",
                use_label_encoder=False,
            )
            if self.model_path:
                self.model.load_model(self.model_path)
                logger.info(f"XGBoost model loaded from {self.model_path}")
            self._is_loaded = True
        except Exception as e:
            logger.error(f"XGBoost model load failed: {e}")

    def extract_features(self, patient) -> Dict[str, float]:
        """
        Extract feature values from a FHIRPatient Django model instance.
        Returns dict with feature_name → value.
        """
        from django.utils import timezone
        from datetime import timedelta

        features = {}
        now = timezone.now()

        # Demographics
        features["age"] = patient.age or 0
        features["gender_encoded"] = 1 if patient.gender == "male" else 0
        features["num_chronic_conditions"] = patient.conditions.filter(
            clinical_status="active"
        ).count()

        # Lab values — get most recent
        def get_latest_obs(loinc_code: str, days_back: int = 90) -> Optional[float]:
            obs = patient.observations.filter(
                code=loinc_code,
                effective_datetime__gte=now - timedelta(days=days_back),
                status="final",
            ).order_by("-effective_datetime").first()
            return obs.value_quantity if obs else None

        features["a1c_latest"] = get_latest_obs("4548-4") or 0
        features["glucose_latest"] = get_latest_obs("2339-0", days_back=7) or 100

        # Glucose variability (standard deviation of 7-day readings)
        glucose_7d = list(patient.observations.filter(
            code="2339-0",
            effective_datetime__gte=now - timedelta(days=7),
            status="final",
        ).values_list("value_quantity", flat=True))
        features["glucose_variability"] = float(np.std(glucose_7d)) if len(glucose_7d) >= 3 else 0
        features["glucose_avg_7d"] = float(np.mean(glucose_7d)) if glucose_7d else 100

        # A1C trend (difference from 6 months ago)
        old_a1c = patient.observations.filter(
            code="4548-4",
            effective_datetime__gte=now - timedelta(days=180),
            effective_datetime__lt=now - timedelta(days=90),
            status="final",
        ).order_by("-effective_datetime").first()
        current_a1c = features["a1c_latest"]
        features["a1c_trend_90d"] = (current_a1c - old_a1c.value_quantity) if old_a1c and current_a1c else 0

        # Blood pressure
        bp = patient.observations.filter(
            code="55284-4",  # BP panel
            status="final",
        ).order_by("-effective_datetime").first()
        if bp and bp.components:
            for comp in bp.components:
                code = comp.get("code", {}).get("coding", [{}])[0].get("code", "")
                if code == "8480-6":  # Systolic
                    features["bp_systolic_latest"] = comp.get("valueQuantity", {}).get("value", 120)
                elif code == "8462-4":  # Diastolic
                    features["bp_diastolic_latest"] = comp.get("valueQuantity", {}).get("value", 80)
        features.setdefault("bp_systolic_latest", 120)
        features.setdefault("bp_diastolic_latest", 80)
        features["bp_avg_30d"] = features["bp_systolic_latest"]

        # Kidney function
        features["creatinine_latest"] = get_latest_obs("2160-0") or 1.0
        features["egfr_latest"] = get_latest_obs("48642-3") or 60
        features["bun_latest"] = get_latest_obs("3094-0") or 15

        # CBC
        features["wbc_latest"] = get_latest_obs("6690-2") or 7.0
        features["hemoglobin_latest"] = get_latest_obs("718-7") or 13.0
        features["potassium_latest"] = get_latest_obs("2823-3") or 4.0

        # Cardiac
        features["bnp_latest"] = get_latest_obs("42637-9") or 0
        features["troponin_latest"] = get_latest_obs("6598-7") or 0

        # Medications
        features["num_active_medications"] = patient.medication_requests.filter(status="active").count()
        features["num_high_risk_medications"] = 0  # TODO: check against high-risk drug list
        features["medication_adherence_score"] = 0.8  # Default — can be calculated from refill history

        # Utilization (from FHIR encounters)
        features["ed_visits_90d"] = patient.fhir_encounters.filter(
            encounter_class="EMER",
            period_start__gte=now - timedelta(days=90),
        ).count()
        features["hospitalizations_180d"] = patient.fhir_encounters.filter(
            encounter_class="IMP",
            period_start__gte=now - timedelta(days=180),
        ).count()
        features["readmission_30d_flag"] = 1 if patient.fhir_encounters.filter(
            encounter_class="IMP",
            period_start__gte=now - timedelta(days=30),
        ).count() >= 2 else 0

        # Vitals
        features["weight_change_kg_30d"] = 0  # TODO: calculate from weight observations
        features["heart_rate_avg_7d"] = get_latest_obs("8867-4") or 72
        features["spo2_avg_7d"] = get_latest_obs("59408-5") or 98

        # SDOH
        try:
            sdoh = patient.sdoh_assessments.order_by("-assessment_date").first()
            features["sdoh_risk_score"] = sdoh.total_score if sdoh else 0
        except Exception:
            features["sdoh_risk_score"] = 0

        # Engagement
        try:
            features["engagement_score"] = patient.engagement.engagement_score
        except Exception:
            features["engagement_score"] = 50

        # Care gaps
        from apps.clinical.models import CareGap
        features["num_open_care_gaps"] = CareGap.objects.filter(
            patient=patient, status=CareGap.Status.OPEN
        ).count()

        # Days since last visit
        last_enc = patient.fhir_encounters.order_by("-period_start").first()
        if last_enc:
            features["days_since_last_visit"] = (now.date() - last_enc.period_start.date()).days
        else:
            features["days_since_last_visit"] = 365

        return features

    def predict(self, features: Dict[str, float]) -> float:
        """
        Predict 7-day hospitalization risk.
        Returns probability score 0.0 - 1.0.
        """
        if not self._is_loaded:
            self.load()

        # Convert features dict to array in the correct order
        feature_vector = np.array([
            features.get(name, 0.0) for name in self.FEATURE_NAMES
        ]).reshape(1, -1)

        if self.model is None:
            # Heuristic fallback when model isn't trained
            return self._heuristic_score(features)

        try:
            proba = self.model.predict_proba(feature_vector)[0][1]
            return float(proba)
        except Exception as e:
            logger.error(f"XGBoost prediction failed: {e}")
            return self._heuristic_score(features)

    def _heuristic_score(self, features: Dict[str, float]) -> float:
        """Simple heuristic risk score when ML model is unavailable."""
        score = 0.1  # Base risk

        # High A1C
        a1c = features.get("a1c_latest", 0)
        if a1c > 10:
            score += 0.25
        elif a1c > 8:
            score += 0.10

        # Elevated BP
        if features.get("bp_systolic_latest", 120) > 160:
            score += 0.15

        # Recent ED/hospital utilization
        score += features.get("ed_visits_90d", 0) * 0.10
        score += features.get("hospitalizations_180d", 0) * 0.15
        score += features.get("readmission_30d_flag", 0) * 0.20

        # Number of conditions
        score += min(0.20, features.get("num_chronic_conditions", 0) * 0.04)

        # Care gaps
        score += min(0.10, features.get("num_open_care_gaps", 0) * 0.02)

        return min(1.0, score)

    def get_feature_importance(self) -> Dict[str, float]:
        """Return feature importances from the trained model."""
        if self.model is None or not self._is_loaded:
            return {}
        try:
            importances = self.model.feature_importances_
            return dict(sorted(
                zip(self.FEATURE_NAMES, importances.tolist()),
                key=lambda x: x[1],
                reverse=True,
            ))
        except Exception:
            return {}
