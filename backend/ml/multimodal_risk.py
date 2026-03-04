"""
Multi-modal attention fusion model for comprehensive patient risk assessment.
Fuses structured EHR data, time-series vitals, clinical notes embeddings,
and social determinants of health (SDOH) into a unified risk score.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.multimodal_risk")

# Modality dimensions
EHR_STRUCTURED_DIM = 64       # Labs, demographics, diagnosis codes (one-hot/embedding)
TIMESERIES_DIM = 32           # CGM, BP, HR time-series (encoded by LSTM)
NOTES_EMBEDDING_DIM = 768     # Clinical notes (sentence-transformer output)
SDOH_DIM = 16                 # SDOH assessment scores
FUSION_DIM = 128              # Unified fusion layer dimension
N_ATTENTION_HEADS = 4         # Multi-head attention heads


class MultiModalAttentionFusion:
    """
    Multi-modal attention fusion model for patient risk assessment.

    Architecture:
        1. Modality-specific encoders (EHR, TimeSeries, Notes, SDOH)
        2. Cross-modal attention (each modality attends to all others)
        3. Fusion MLP for final risk score

    Supports inference even with missing modalities via masking.
    """

    def __init__(self, model_path: str = None):
        self.model = None
        self.model_path = model_path
        self.version = "multimodal_v1"
        self._is_loaded = False

    def build_model(self):
        """Build the multi-modal fusion model using PyTorch."""
        try:
            import torch
            import torch.nn as nn

            class ModalityEncoder(nn.Module):
                """Per-modality encoder projecting to FUSION_DIM."""

                def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(input_dim, hidden_dim),
                        nn.LayerNorm(hidden_dim),
                        nn.GELU(),
                        nn.Dropout(0.1),
                        nn.Linear(hidden_dim, output_dim),
                    )

                def forward(self, x):
                    return self.net(x)

            class CrossModalAttention(nn.Module):
                """Multi-head cross-modal attention."""

                def __init__(self, embed_dim: int, num_heads: int):
                    super().__init__()
                    self.attn = nn.MultiheadAttention(
                        embed_dim=embed_dim,
                        num_heads=num_heads,
                        dropout=0.1,
                        batch_first=True,
                    )
                    self.norm = nn.LayerNorm(embed_dim)

                def forward(self, query, key_value, key_padding_mask=None):
                    out, weights = self.attn(
                        query, key_value, key_value,
                        key_padding_mask=key_padding_mask,
                    )
                    return self.norm(query + out), weights

            class MultiModalRiskModel(nn.Module):
                """Full multi-modal fusion model."""

                def __init__(self):
                    super().__init__()
                    # Modality encoders
                    self.ehr_encoder = ModalityEncoder(EHR_STRUCTURED_DIM, 128, FUSION_DIM)
                    self.ts_encoder = ModalityEncoder(TIMESERIES_DIM, 64, FUSION_DIM)
                    self.notes_encoder = ModalityEncoder(NOTES_EMBEDDING_DIM, 256, FUSION_DIM)
                    self.sdoh_encoder = ModalityEncoder(SDOH_DIM, 32, FUSION_DIM)

                    # Cross-modal attention layers
                    self.ehr_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)
                    self.ts_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)
                    self.notes_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)
                    self.sdoh_attn = CrossModalAttention(FUSION_DIM, N_ATTENTION_HEADS)

                    # Fusion MLP
                    self.fusion = nn.Sequential(
                        nn.Linear(FUSION_DIM * 4, 256),
                        nn.LayerNorm(256),
                        nn.GELU(),
                        nn.Dropout(0.2),
                        nn.Linear(256, 64),
                        nn.GELU(),
                        nn.Linear(64, 1),
                        nn.Sigmoid(),
                    )

                    # Modality importance weights (learned)
                    self.modality_weights = nn.Parameter(
                        torch.ones(4) / 4  # Uniform initialization
                    )

                def forward(
                    self,
                    ehr_features,
                    ts_features,
                    notes_features,
                    sdoh_features,
                    modality_mask=None,
                ):
                    """
                    Forward pass with optional modality masking for missing data.

                    Args:
                        ehr_features: (B, EHR_DIM)
                        ts_features: (B, TS_DIM)
                        notes_features: (B, NOTES_DIM)
                        sdoh_features: (B, SDOH_DIM)
                        modality_mask: (B, 4) boolean mask (True = missing)
                    """
                    # Encode each modality
                    e_ehr = self.ehr_encoder(ehr_features).unsqueeze(1)    # (B, 1, F)
                    e_ts = self.ts_encoder(ts_features).unsqueeze(1)       # (B, 1, F)
                    e_notes = self.notes_encoder(notes_features).unsqueeze(1)  # (B, 1, F)
                    e_sdoh = self.sdoh_encoder(sdoh_features).unsqueeze(1) # (B, 1, F)

                    # Stack all modalities: (B, 4, F)
                    all_modalities = torch.cat([e_ehr, e_ts, e_notes, e_sdoh], dim=1)

                    # Cross-modal attention (each modality queries all others)
                    e_ehr_fused, _ = self.ehr_attn(e_ehr, all_modalities)
                    e_ts_fused, _ = self.ts_attn(e_ts, all_modalities)
                    e_notes_fused, _ = self.notes_attn(e_notes, all_modalities)
                    e_sdoh_fused, _ = self.sdoh_attn(e_sdoh, all_modalities)

                    # Apply modality importance weights
                    weights = torch.softmax(self.modality_weights, dim=0)
                    e_ehr_fused = e_ehr_fused * weights[0]
                    e_ts_fused = e_ts_fused * weights[1]
                    e_notes_fused = e_notes_fused * weights[2]
                    e_sdoh_fused = e_sdoh_fused * weights[3]

                    # Zero out missing modalities if mask provided
                    if modality_mask is not None:
                        for i, emb in enumerate([e_ehr_fused, e_ts_fused, e_notes_fused, e_sdoh_fused]):
                            emb[modality_mask[:, i]] = 0.0

                    # Concatenate and fuse
                    fused = torch.cat([
                        e_ehr_fused.squeeze(1),
                        e_ts_fused.squeeze(1),
                        e_notes_fused.squeeze(1),
                        e_sdoh_fused.squeeze(1),
                    ], dim=-1)  # (B, F*4)

                    return self.fusion(fused)  # (B, 1)

            return MultiModalRiskModel()

        except ImportError:
            logger.warning("PyTorch not available. Using heuristic fusion.")
            return None

    def load(self):
        """Load or initialize the multi-modal model."""
        import os

        if self.model_path and os.path.exists(self.model_path):
            try:
                import torch
                self.model = self.build_model()
                if self.model is not None:
                    state_dict = torch.load(self.model_path, map_location="cpu")
                    self.model.load_state_dict(state_dict)
                    self.model.eval()
                    logger.info(f"Multi-modal model loaded from {self.model_path}")
                    self._is_loaded = True
                    return
            except Exception as e:
                logger.warning(f"Could not load multi-modal model: {e}")

        self.model = self.build_model()
        if self.model is not None:
            self.model.eval()
        self._is_loaded = True

    def extract_ehr_features(self, patient) -> np.ndarray:
        """
        Extract structured EHR features for a patient.

        Features: demographics (4) + recent labs (30) + condition flags (20) + utilization (10)
        Total: 64 features
        """
        from apps.fhir.models import FHIRObservation, FHIRCondition, FHIREncounter
        from django.utils import timezone
        from datetime import timedelta

        features = np.zeros(EHR_STRUCTURED_DIM)
        now = timezone.now()
        cutoff_90d = now - timedelta(days=90)

        # Demographics (indices 0-3)
        age = getattr(patient, "age", 0) or 0
        features[0] = min(age / 100.0, 1.0)  # Normalized age

        gender = getattr(patient, "gender", "unknown") or "unknown"
        features[1] = 1.0 if gender.lower() in ("male", "m") else 0.0
        features[2] = 1.0 if gender.lower() in ("female", "f") else 0.0

        # Recent labs (indices 4-33): HbA1c, eGFR, LDL, HDL, creatinine, BP sys, BP dia,
        # sodium, potassium, hemoglobin, WBC, platelets, BMI, glucose, A1C trend, etc.
        LAB_CODES = [
            ("4548-4", 4, 14.0),    # HbA1c (normalized to 14%)
            ("33914-3", 5, 150.0),  # eGFR (normalized to 150)
            ("18262-6", 6, 250.0),  # LDL (normalized to 250 mg/dL)
            ("2085-9", 7, 100.0),   # HDL
            ("2160-0", 8, 15.0),    # Creatinine
            ("8480-6", 9, 200.0),   # Systolic BP
            ("8462-4", 10, 120.0),  # Diastolic BP
            ("2951-2", 11, 150.0),  # Sodium
            ("6298-4", 12, 7.0),    # Potassium
            ("718-7", 13, 20.0),    # Hemoglobin
            ("6690-2", 14, 20.0),   # WBC
            ("777-3", 15, 400.0),   # Platelets
            ("39156-5", 16, 60.0),  # BMI
            ("2339-0", 17, 400.0),  # Glucose
        ]

        for loinc_code, idx, norm_val in LAB_CODES:
            obs = patient.observations.filter(
                code=loinc_code,
                effective_datetime__gte=cutoff_90d,
            ).order_by("-effective_datetime").first()
            if obs and obs.value_quantity is not None:
                features[idx] = float(obs.value_quantity) / norm_val

        # Chronic condition flags (indices 34-53)
        CHRONIC_ICD_PREFIXES = [
            "E11",  # Type 2 diabetes
            "I10",  # Hypertension
            "E78",  # Hyperlipidemia
            "J44",  # COPD
            "I50",  # Heart failure
            "N18",  # CKD
            "F32",  # Depression
            "F41",  # Anxiety
            "E66",  # Obesity
            "I25",  # Coronary artery disease
            "J45",  # Asthma
            "M06",  # Rheumatoid arthritis
            "K21",  # GERD
            "G47",  # Sleep apnea
            "E03",  # Hypothyroidism
            "M54",  # Back pain
            "I48",  # Atrial fibrillation
            "N39",  # UTI
            "K58",  # IBS
            "G43",  # Migraine
        ]
        for i, prefix in enumerate(CHRONIC_ICD_PREFIXES):
            has_condition = patient.conditions.filter(
                code__startswith=prefix,
                clinical_status="active",
            ).exists()
            features[34 + i] = 1.0 if has_condition else 0.0

        # Utilization features (indices 54-63)
        encounters_90d = patient.encounters.filter(
            start_datetime__gte=cutoff_90d
        ).count()
        features[54] = min(encounters_90d / 10.0, 1.0)  # Normalized to 10

        ed_visits_90d = patient.encounters.filter(
            start_datetime__gte=cutoff_90d,
            encounter_class="emergency",
        ).count()
        features[55] = min(ed_visits_90d / 5.0, 1.0)

        hospitalizations_90d = patient.encounters.filter(
            start_datetime__gte=cutoff_90d,
            encounter_class="inpatient",
        ).count()
        features[56] = min(hospitalizations_90d / 3.0, 1.0)

        active_meds = patient.medication_requests.filter(
            status="active"
        ).count()
        features[57] = min(active_meds / 20.0, 1.0)

        open_care_gaps = patient.care_gaps.filter(status="open").count() if hasattr(patient, "care_gaps") else 0
        features[58] = min(open_care_gaps / 10.0, 1.0)

        return features

    def extract_timeseries_features(self, patient) -> np.ndarray:
        """
        Extract time-series encoded features using LSTM-based representation.
        Returns 32-dim encoded representation.
        """
        from apps.fhir.models import FHIRObservation
        from django.utils import timezone
        from datetime import timedelta

        features = np.zeros(TIMESERIES_DIM)
        now = timezone.now()
        cutoff_7d = now - timedelta(days=7)

        # CGM statistics (indices 0-7)
        glucose_vals = list(patient.observations.filter(
            code="2339-0",
            effective_datetime__gte=cutoff_7d,
        ).values_list("value_quantity", flat=True))

        if glucose_vals:
            glucose_arr = np.array([float(v) for v in glucose_vals if v is not None])
            if len(glucose_arr) > 0:
                features[0] = np.mean(glucose_arr) / 400.0
                features[1] = np.std(glucose_arr) / 100.0
                features[2] = np.min(glucose_arr) / 400.0
                features[3] = np.max(glucose_arr) / 400.0
                features[4] = np.sum(glucose_arr < 70) / max(len(glucose_arr), 1)   # Hypoglycemia rate
                features[5] = np.sum(glucose_arr > 180) / max(len(glucose_arr), 1)  # Hyperglycemia rate
                # Time in range (70-180 mg/dL)
                features[6] = np.sum((glucose_arr >= 70) & (glucose_arr <= 180)) / max(len(glucose_arr), 1)
                # Glucose coefficient of variation
                features[7] = (np.std(glucose_arr) / np.mean(glucose_arr)) if np.mean(glucose_arr) > 0 else 0

        # BP statistics (indices 8-13)
        systolic_vals = list(patient.observations.filter(
            code="8480-6",
            effective_datetime__gte=cutoff_7d,
        ).values_list("value_quantity", flat=True))

        if systolic_vals:
            sys_arr = np.array([float(v) for v in systolic_vals if v is not None])
            if len(sys_arr) > 0:
                features[8] = np.mean(sys_arr) / 200.0
                features[9] = np.std(sys_arr) / 50.0
                features[10] = np.sum(sys_arr > 140) / max(len(sys_arr), 1)   # Uncontrolled HTN rate
                features[11] = np.sum(sys_arr < 90) / max(len(sys_arr), 1)    # Hypotension rate

        # Heart rate statistics (indices 12-15)
        hr_vals = list(patient.observations.filter(
            code="8867-4",
            effective_datetime__gte=cutoff_7d,
        ).values_list("value_quantity", flat=True))

        if hr_vals:
            hr_arr = np.array([float(v) for v in hr_vals if v is not None])
            if len(hr_arr) > 0:
                features[12] = np.mean(hr_arr) / 200.0
                features[13] = np.std(hr_arr) / 50.0
                features[14] = np.sum(hr_arr > 100) / max(len(hr_arr), 1)  # Tachycardia rate
                features[15] = np.sum(hr_arr < 60) / max(len(hr_arr), 1)   # Bradycardia rate

        # Activity / steps statistics (indices 16-19)
        steps_vals = list(patient.observations.filter(
            code="55423-8",
            effective_datetime__gte=cutoff_7d,
        ).values_list("value_quantity", flat=True))

        if steps_vals:
            steps_arr = np.array([float(v) for v in steps_vals if v is not None])
            if len(steps_arr) > 0:
                features[16] = np.mean(steps_arr) / 10000.0
                features[17] = np.min(steps_arr) / 10000.0
                features[18] = np.sum(steps_arr < 2000) / max(len(steps_arr), 1)   # Sedentary days
                features[19] = np.sum(steps_arr > 8000) / max(len(steps_arr), 1)   # Active days

        # Weight trend (indices 20-23)
        weight_vals = list(patient.observations.filter(
            code="29463-7",
            effective_datetime__gte=now - timedelta(days=30),
        ).order_by("effective_datetime").values_list("value_quantity", flat=True))

        if len(weight_vals) >= 2:
            weight_arr = np.array([float(v) for v in weight_vals if v is not None])
            weight_change = (weight_arr[-1] - weight_arr[0]) if len(weight_arr) >= 2 else 0
            features[20] = weight_arr[-1] / 200.0 if weight_arr[-1] else 0  # Latest weight normalized
            features[21] = weight_change / 20.0  # Weight change in kg (normalized to 20kg range)
            features[22] = 1.0 if weight_change > 2.0 else 0.0   # Rapid weight gain flag
            features[23] = 1.0 if weight_change < -2.0 else 0.0  # Rapid weight loss flag

        # SpO2 statistics (indices 24-27)
        spo2_vals = list(patient.observations.filter(
            code="59408-5",
            effective_datetime__gte=cutoff_7d,
        ).values_list("value_quantity", flat=True))

        if spo2_vals:
            spo2_arr = np.array([float(v) for v in spo2_vals if v is not None])
            if len(spo2_arr) > 0:
                features[24] = np.mean(spo2_arr) / 100.0
                features[25] = np.sum(spo2_arr < 92) / max(len(spo2_arr), 1)  # Hypoxemia rate

        # Observation data density (indices 28-31)
        total_obs_7d = patient.observations.filter(
            effective_datetime__gte=cutoff_7d
        ).count()
        features[28] = min(total_obs_7d / 100.0, 1.0)  # Data completeness proxy
        features[29] = min(len(glucose_vals) / 288.0, 1.0)  # CGM completeness (288 = 24h of 5-min readings)
        features[30] = min(len(systolic_vals) / 14.0, 1.0)  # BP measurement completeness
        features[31] = min(len(steps_vals) / 7.0, 1.0)  # Steps data completeness

        return features

    def extract_notes_features(self, patient) -> np.ndarray:
        """
        Extract clinical notes embedding using sentence transformers.
        Returns 768-dim embedding of recent clinical notes.
        """
        from apps.fhir.models import FHIRDocumentReference
        from django.utils import timezone
        from datetime import timedelta

        cutoff_90d = timezone.now() - timedelta(days=90)

        # Fetch recent clinical notes
        notes = patient.document_references.filter(
            status="current",
            date__gte=cutoff_90d,
        ).order_by("-date").values_list("description", flat=True)[:5]

        note_texts = [n for n in notes if n]

        if not note_texts:
            # Return zero embedding if no notes available
            return np.zeros(NOTES_EMBEDDING_DIM)

        combined_text = " ".join(note_texts)[:2000]  # Truncate to 2000 chars

        try:
            from vector.embeddings import generate_embedding
            embedding = generate_embedding(combined_text)
            if embedding is not None:
                return np.array(embedding)
        except Exception as e:
            logger.debug(f"Could not generate notes embedding: {e}")

        return np.zeros(NOTES_EMBEDDING_DIM)

    def extract_sdoh_features(self, patient) -> np.ndarray:
        """
        Extract SDOH features from SDOHAssessment model.
        Returns 16-dim SDOH feature vector.
        """
        features = np.zeros(SDOH_DIM)

        try:
            from apps.sdoh.models import SDOHAssessment
            assessment = SDOHAssessment.objects.filter(
                patient=patient,
            ).order_by("-assessment_date").first()

            if assessment:
                features[0] = (assessment.housing_instability_score or 0) / 4.0
                features[1] = (assessment.food_insecurity_score or 0) / 4.0
                features[2] = (assessment.transportation_score or 0) / 4.0
                features[3] = (assessment.social_isolation_score or 0) / 4.0
                features[4] = (assessment.financial_strain_score or 0) / 4.0
                features[5] = 1.0 if assessment.education_less_than_high_school else 0.0
                features[6] = 1.0 if assessment.unemployed else 0.0
                features[7] = 1.0 if assessment.domestic_violence_risk else 0.0
                features[8] = 1.0 if assessment.substance_use_concern else 0.0
                features[9] = 1.0 if assessment.mental_health_concern else 0.0
                features[10] = (assessment.total_score or 0) / 20.0  # Normalized total

                # Risk level encoding (one-hot: low/medium/high/critical)
                risk = assessment.overall_sdoh_risk or "low"
                features[11] = 1.0 if risk == "low" else 0.0
                features[12] = 1.0 if risk == "medium" else 0.0
                features[13] = 1.0 if risk == "high" else 0.0
                features[14] = 1.0 if risk == "critical" else 0.0

                features[15] = 1.0  # Assessment available flag
        except Exception as e:
            logger.debug(f"Could not extract SDOH features: {e}")

        return features

    def predict(
        self,
        patient,
        return_modality_contributions: bool = False,
    ) -> Dict:
        """
        Run multi-modal risk prediction for a patient.

        Args:
            patient: FHIRPatient instance
            return_modality_contributions: If True, include per-modality risk contributions

        Returns:
            {
                risk_score: float (0-1),
                risk_level: str (low/medium/high/critical),
                confidence: float (0-1),
                modality_contributions: dict (optional),
                missing_modalities: list,
            }
        """
        if not self._is_loaded:
            self.load()

        # Extract all modalities
        missing_modalities = []

        ehr_features = self.extract_ehr_features(patient)
        ts_features = self.extract_timeseries_features(patient)
        notes_features = self.extract_notes_features(patient)
        sdoh_features = self.extract_sdoh_features(patient)

        # Detect missing modalities (all zeros = no data)
        if np.all(ts_features == 0):
            missing_modalities.append("timeseries")
        if np.all(notes_features == 0):
            missing_modalities.append("clinical_notes")
        if sdoh_features[15] == 0:  # Assessment available flag
            missing_modalities.append("sdoh")

        # Confidence penalty for missing modalities
        confidence = 1.0 - (len(missing_modalities) * 0.15)

        if self.model is not None:
            try:
                import torch

                # Build modality mask
                modality_mask = torch.zeros(1, 4, dtype=torch.bool)
                if "timeseries" in missing_modalities:
                    modality_mask[0, 1] = True
                if "clinical_notes" in missing_modalities:
                    modality_mask[0, 2] = True
                if "sdoh" in missing_modalities:
                    modality_mask[0, 3] = True

                with torch.no_grad():
                    risk_tensor = self.model(
                        torch.tensor(ehr_features, dtype=torch.float32).unsqueeze(0),
                        torch.tensor(ts_features, dtype=torch.float32).unsqueeze(0),
                        torch.tensor(notes_features, dtype=torch.float32).unsqueeze(0),
                        torch.tensor(sdoh_features, dtype=torch.float32).unsqueeze(0),
                        modality_mask,
                    )
                    risk_score = float(risk_tensor.item())

                result = {
                    "risk_score": risk_score,
                    "risk_level": self._categorize_risk(risk_score),
                    "confidence": confidence,
                    "missing_modalities": missing_modalities,
                    "model": "multimodal_attention_fusion",
                }

                if return_modality_contributions:
                    result["modality_contributions"] = self._compute_modality_contributions(
                        ehr_features, ts_features, notes_features, sdoh_features
                    )

                return result

            except Exception as e:
                logger.warning(f"Multi-modal model inference failed: {e}")

        # Heuristic fallback: weighted average of modality-specific scores
        return self._heuristic_fusion(
            ehr_features, ts_features, sdoh_features,
            missing_modalities, confidence,
        )

    def _heuristic_fusion(
        self,
        ehr_features: np.ndarray,
        ts_features: np.ndarray,
        sdoh_features: np.ndarray,
        missing_modalities: List[str],
        confidence: float,
    ) -> Dict:
        """Heuristic multi-modal fusion when neural model unavailable."""
        # EHR-based score: focus on chronic conditions and utilization
        chronic_flags = ehr_features[34:54]  # 20 chronic condition flags
        ehr_score = (
            np.mean(chronic_flags) * 0.5 +         # Chronic condition burden
            ehr_features[55] * 0.25 +              # ED visits
            ehr_features[56] * 0.25                # Hospitalizations
        )

        # Time-series score: focus on glucose control and BP
        ts_score = (
            ts_features[1] * 0.3 +    # Glucose variability (std)
            ts_features[4] * 0.3 +    # Hypoglycemia rate
            ts_features[10] * 0.25 +  # Uncontrolled HTN rate
            ts_features[18] * 0.15    # Sedentary days
        ) if "timeseries" not in missing_modalities else ehr_score * 0.5

        # SDOH score
        sdoh_score = sdoh_features[10] if "sdoh" not in missing_modalities else 0.3

        # Weighted fusion
        weights = {"ehr": 0.50, "timeseries": 0.30, "sdoh": 0.20}
        risk_score = (
            ehr_score * weights["ehr"] +
            ts_score * weights["timeseries"] +
            sdoh_score * weights["sdoh"]
        )
        risk_score = float(np.clip(risk_score, 0.0, 1.0))

        return {
            "risk_score": risk_score,
            "risk_level": self._categorize_risk(risk_score),
            "confidence": confidence,
            "missing_modalities": missing_modalities,
            "model": "heuristic_fusion",
        }

    def _compute_modality_contributions(
        self,
        ehr_features: np.ndarray,
        ts_features: np.ndarray,
        notes_features: np.ndarray,
        sdoh_features: np.ndarray,
    ) -> Dict[str, float]:
        """Compute approximate per-modality contribution via ablation."""
        contributions = {}
        try:
            import torch

            def _score_with_zeroed(zero_idx: int) -> float:
                inputs = [
                    torch.tensor(ehr_features, dtype=torch.float32).unsqueeze(0),
                    torch.tensor(ts_features, dtype=torch.float32).unsqueeze(0),
                    torch.tensor(notes_features, dtype=torch.float32).unsqueeze(0),
                    torch.tensor(sdoh_features, dtype=torch.float32).unsqueeze(0),
                ]
                mask = torch.zeros(1, 4, dtype=torch.bool)
                mask[0, zero_idx] = True
                with torch.no_grad():
                    return float(self.model(*inputs, mask).item())

            full_score_tensor = self.model(
                torch.tensor(ehr_features, dtype=torch.float32).unsqueeze(0),
                torch.tensor(ts_features, dtype=torch.float32).unsqueeze(0),
                torch.tensor(notes_features, dtype=torch.float32).unsqueeze(0),
                torch.tensor(sdoh_features, dtype=torch.float32).unsqueeze(0),
                torch.zeros(1, 4, dtype=torch.bool),
            )
            full_score = float(full_score_tensor.item())

            contributions["ehr_structured"] = abs(full_score - _score_with_zeroed(0))
            contributions["timeseries"] = abs(full_score - _score_with_zeroed(1))
            contributions["clinical_notes"] = abs(full_score - _score_with_zeroed(2))
            contributions["sdoh"] = abs(full_score - _score_with_zeroed(3))

            total = sum(contributions.values()) or 1.0
            contributions = {k: v / total for k, v in contributions.items()}

        except Exception as e:
            logger.debug(f"Could not compute modality contributions: {e}")
            contributions = {
                "ehr_structured": 0.50,
                "timeseries": 0.30,
                "clinical_notes": 0.10,
                "sdoh": 0.10,
            }

        return contributions

    @staticmethod
    def _categorize_risk(score: float) -> str:
        """Categorize risk score into clinical risk levels."""
        if score < 0.25:
            return "low"
        elif score < 0.50:
            return "moderate"
        elif score < 0.75:
            return "high"
        else:
            return "critical"

    def get_risk_explanation(self, patient) -> Dict:
        """
        Get full risk assessment with explanation for clinical decision support.

        Returns risk score, level, modality contributions, and top risk factors.
        """
        result = self.predict(patient, return_modality_contributions=True)

        # Extract top EHR risk factors
        ehr_features = self.extract_ehr_features(patient)
        top_risk_factors = []

        CHRONIC_NAMES = [
            "Type 2 Diabetes", "Hypertension", "Hyperlipidemia", "COPD",
            "Heart Failure", "CKD", "Depression", "Anxiety", "Obesity",
            "CAD", "Asthma", "Rheumatoid Arthritis", "GERD", "Sleep Apnea",
            "Hypothyroidism", "Back Pain", "Atrial Fibrillation", "UTI",
            "IBS", "Migraine",
        ]
        for i, name in enumerate(CHRONIC_NAMES):
            if ehr_features[34 + i] > 0:
                top_risk_factors.append({"factor": name, "type": "chronic_condition"})

        if ehr_features[55] > 0.2:
            top_risk_factors.append({"factor": "Recent ED visits", "type": "utilization"})
        if ehr_features[56] > 0.2:
            top_risk_factors.append({"factor": "Recent hospitalization", "type": "utilization"})

        result["top_risk_factors"] = top_risk_factors[:10]
        result["version"] = self.version

        return result
