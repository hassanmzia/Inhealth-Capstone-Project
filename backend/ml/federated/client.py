"""
Federated learning client — represents a single tenant's local training process.
Handles local model training, gradient computation, and differential privacy.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .privacy import DifferentialPrivacy

logger = logging.getLogger("ml.federated.client")


@dataclass
class LocalTrainingResult:
    """Result of a local training round."""

    client_id: str
    tenant_id: str
    round_number: int
    gradients: np.ndarray | None = None
    sample_count: int = 0
    metrics: dict = field(default_factory=dict)
    success: bool = True
    error: str | None = None


class FederatedClient:
    """
    Represents a tenant's local training process in the federated learning system.
    Each tenant trains on their own data and shares only privatized gradient updates.
    """

    def __init__(
        self,
        tenant_id: str,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        max_grad_norm: float = 1.0,
        learning_rate: float = 0.01,
    ):
        self.client_id = str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.learning_rate = learning_rate
        self.dp = DifferentialPrivacy(
            epsilon=epsilon,
            delta=delta,
            max_grad_norm=max_grad_norm,
        )
        self.current_model_weights: np.ndarray | None = None
        self.round_number = 0

    def receive_global_model(self, weights: np.ndarray) -> None:
        """
        Receive the latest global model weights from the coordinator.

        Args:
            weights: Global model weight array to use as the starting point
                     for local training.
        """
        self.current_model_weights = weights.copy()
        logger.info(
            "Client %s (tenant=%s) received global model (shape=%s)",
            self.client_id[:8],
            self.tenant_id[:8],
            weights.shape,
        )

    def train_local_model(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        epochs: int = 5,
        batch_size: int = 32,
    ) -> LocalTrainingResult:
        """
        Train the model locally on tenant-specific data.

        Args:
            features: Training feature matrix (n_samples, n_features).
            labels: Training label vector (n_samples,).
            epochs: Number of local training epochs.
            batch_size: Mini-batch size for SGD.

        Returns:
            LocalTrainingResult with privatized gradients and metrics.
        """
        self.round_number += 1

        if self.current_model_weights is None:
            return LocalTrainingResult(
                client_id=self.client_id,
                tenant_id=self.tenant_id,
                round_number=self.round_number,
                success=False,
                error="No global model received. Call receive_global_model() first.",
            )

        try:
            n_samples = features.shape[0]
            weights = self.current_model_weights.copy()

            # Mini-batch SGD training
            epoch_losses = []
            for epoch in range(epochs):
                indices = np.random.permutation(n_samples)
                epoch_loss = 0.0
                n_batches = 0

                for start in range(0, n_samples, batch_size):
                    batch_idx = indices[start : start + batch_size]
                    X_batch = features[batch_idx]
                    y_batch = labels[batch_idx]

                    # Forward pass: linear model y_hat = X @ w
                    y_hat = X_batch @ weights
                    residuals = y_hat - y_batch

                    # MSE loss
                    batch_loss = np.mean(residuals ** 2)
                    epoch_loss += batch_loss
                    n_batches += 1

                    # Gradient: d(MSE)/dw = (2/n) * X^T @ (y_hat - y)
                    grad = (2.0 / len(batch_idx)) * (X_batch.T @ residuals)
                    weights -= self.learning_rate * grad

                epoch_losses.append(epoch_loss / max(n_batches, 1))

            # Compute overall gradient as weight delta
            raw_gradients = weights - self.current_model_weights

            # Apply differential privacy
            private_gradients = self.apply_differential_privacy(raw_gradients)

            metrics = {
                "final_loss": float(epoch_losses[-1]) if epoch_losses else 0.0,
                "epochs_completed": epochs,
                "samples_used": n_samples,
            }

            logger.info(
                "Client %s (tenant=%s) completed local training: loss=%.4f, samples=%d",
                self.client_id[:8],
                self.tenant_id[:8],
                metrics["final_loss"],
                n_samples,
            )

            return LocalTrainingResult(
                client_id=self.client_id,
                tenant_id=self.tenant_id,
                round_number=self.round_number,
                gradients=private_gradients,
                sample_count=n_samples,
                metrics=metrics,
            )

        except Exception as exc:
            logger.error("Local training failed for client %s: %s", self.client_id[:8], exc)
            return LocalTrainingResult(
                client_id=self.client_id,
                tenant_id=self.tenant_id,
                round_number=self.round_number,
                success=False,
                error=str(exc),
            )

    def compute_gradients(self, features: np.ndarray, labels: np.ndarray) -> np.ndarray:
        """
        Compute raw gradients on the given data without updating weights.

        Args:
            features: Feature matrix (n_samples, n_features).
            labels: Label vector (n_samples,).

        Returns:
            Raw gradient array.
        """
        if self.current_model_weights is None:
            raise ValueError("No model weights loaded. Call receive_global_model() first.")

        y_hat = features @ self.current_model_weights
        residuals = y_hat - labels
        grad = (2.0 / features.shape[0]) * (features.T @ residuals)
        return grad

    def apply_differential_privacy(self, gradients: np.ndarray) -> np.ndarray:
        """
        Apply differential privacy to gradient updates via clipping and noise.

        Args:
            gradients: Raw gradient array.

        Returns:
            Privatized gradient array satisfying (epsilon, delta)-DP.
        """
        return self.dp.add_noise(gradients)
