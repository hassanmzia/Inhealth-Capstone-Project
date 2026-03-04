"""
LSTM model for continuous glucose prediction.
Predicts 30/60/120-minute glucose values from CGM time series.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.lstm_glucose")

# Model architecture constants
SEQUENCE_LENGTH = 24       # 2 hours of 5-minute CGM readings
PREDICTION_HORIZONS = [6, 12, 24]  # 30min, 60min, 120min ahead
INPUT_FEATURES = 4         # [glucose, rate_of_change, insulin_on_board, carbs_on_board]
HIDDEN_SIZE = 128
NUM_LAYERS = 2
OUTPUT_SIZE = len(PREDICTION_HORIZONS)


class LSTMGlucoseModel:
    """
    Bidirectional LSTM for glucose trajectory prediction.

    Architecture:
    - Input: (batch, sequence_length, input_features)
    - BiLSTM layers with dropout
    - Attention mechanism over hidden states
    - Linear output for multi-step prediction
    """

    def __init__(self, model_path: str = None):
        self.model = None
        self.scaler = None
        self.model_path = model_path
        self.version = "lstm_glucose_v1"
        self._is_loaded = False

    def build_model(self):
        """Build the LSTM architecture using PyTorch."""
        import torch
        import torch.nn as nn

        class GlucoseLSTM(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, output_size):
                super().__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers

                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    batch_first=True,
                    dropout=0.2,
                    bidirectional=True,
                )

                # Attention mechanism
                self.attention = nn.Sequential(
                    nn.Linear(hidden_size * 2, hidden_size),
                    nn.Tanh(),
                    nn.Linear(hidden_size, 1),
                    nn.Softmax(dim=1),
                )

                self.fc = nn.Sequential(
                    nn.Linear(hidden_size * 2, hidden_size),
                    nn.ReLU(),
                    nn.Dropout(0.1),
                    nn.Linear(hidden_size, output_size),
                )

            def forward(self, x):
                # x: (batch, seq_len, input_size)
                lstm_out, _ = self.lstm(x)
                # lstm_out: (batch, seq_len, hidden_size * 2)

                # Attention
                attn_weights = self.attention(lstm_out)  # (batch, seq_len, 1)
                context = (attn_weights * lstm_out).sum(dim=1)  # (batch, hidden_size * 2)

                output = self.fc(context)  # (batch, output_size)
                return output

        return GlucoseLSTM(INPUT_FEATURES, HIDDEN_SIZE, NUM_LAYERS, OUTPUT_SIZE)

    def load(self):
        """Load the trained model from disk."""
        import torch
        try:
            self.model = self.build_model()
            if self.model_path:
                state_dict = torch.load(self.model_path, map_location="cpu")
                self.model.load_state_dict(state_dict)
                self.model.eval()
                self._is_loaded = True
                logger.info(f"LSTM glucose model loaded from {self.model_path}")
            else:
                # Initialize with random weights (untrained — for development)
                self.model.eval()
                logger.warning("LSTM glucose model loaded with random weights (no trained model path)")
        except Exception as e:
            logger.error(f"Failed to load LSTM model: {e}")

    def preprocess(self, glucose_readings: List[float], timestamps: List = None) -> np.ndarray:
        """
        Preprocess raw CGM data into model-ready format.

        Args:
            glucose_readings: List of glucose values (mg/dL), last 2 hours, 5-min intervals
            timestamps: Optional list of datetime timestamps

        Returns:
            np.ndarray of shape (1, SEQUENCE_LENGTH, INPUT_FEATURES)
        """
        readings = np.array(glucose_readings[-SEQUENCE_LENGTH:], dtype=np.float32)

        # Pad if fewer readings than needed
        if len(readings) < SEQUENCE_LENGTH:
            readings = np.pad(readings, (SEQUENCE_LENGTH - len(readings), 0), mode="edge")

        # Feature engineering
        rate_of_change = np.gradient(readings)  # mg/dL per 5 minutes

        # Normalize
        glucose_norm = (readings - 100) / 80  # Normalize around 100 mg/dL
        roc_norm = rate_of_change / 5  # Normalize rate of change

        # Stack features: [glucose, roc, insulin_on_board, carbs_on_board]
        # IOB and COB are 0 if not provided (can be extended)
        features = np.stack([
            glucose_norm,
            roc_norm,
            np.zeros(SEQUENCE_LENGTH),  # IOB placeholder
            np.zeros(SEQUENCE_LENGTH),  # COB placeholder
        ], axis=1)

        return features.reshape(1, SEQUENCE_LENGTH, INPUT_FEATURES)

    def predict(
        self, glucose_readings: List[float], timestamps: List = None
    ) -> Dict[str, float]:
        """
        Predict future glucose values.

        Returns:
            {
                "30min": predicted_glucose,
                "60min": predicted_glucose,
                "120min": predicted_glucose,
                "trend": "rising/falling/stable",
                "hypoglycemia_risk": 0.0-1.0,
                "hyperglycemia_risk": 0.0-1.0,
            }
        """
        import torch

        if not self._is_loaded:
            self.load()

        features = self.preprocess(glucose_readings, timestamps)
        current_glucose = glucose_readings[-1] if glucose_readings else 100

        with torch.no_grad():
            input_tensor = torch.tensor(features, dtype=torch.float32)
            predictions = self.model(input_tensor).numpy()[0]

        # Denormalize predictions
        predicted_values = predictions * 80 + 100

        # Map to horizon labels
        results = {}
        horizon_labels = ["30min", "60min", "120min"]
        for i, label in enumerate(horizon_labels):
            results[label] = max(40.0, min(400.0, float(predicted_values[i])))

        # Determine trend
        short_term_trend = results["30min"] - current_glucose
        if short_term_trend > 10:
            results["trend"] = "rising"
        elif short_term_trend < -10:
            results["trend"] = "falling"
        else:
            results["trend"] = "stable"

        # Risk scores
        results["hypoglycemia_risk"] = max(0.0, min(1.0, (70 - results["60min"]) / 30)) if results["60min"] < 70 else 0.0
        results["hyperglycemia_risk"] = max(0.0, min(1.0, (results["60min"] - 250) / 100)) if results["60min"] > 250 else 0.0

        return results

    def predict_batch(self, patient_readings_batch: List[List[float]]) -> List[Dict]:
        """Batch prediction for multiple patients."""
        import torch

        if not self._is_loaded:
            self.load()

        batch_features = np.vstack([self.preprocess(r) for r in patient_readings_batch])
        with torch.no_grad():
            input_tensor = torch.tensor(batch_features, dtype=torch.float32)
            predictions = self.model(input_tensor).numpy()

        return [
            {label: float(pred[i] * 80 + 100) for i, label in enumerate(["30min", "60min", "120min"])}
            for pred in predictions
        ]
