"""
Differential privacy utilities for federated learning.
Implements basic (epsilon, delta)-differential privacy with Gaussian noise.
"""

import math
import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("ml.federated.privacy")


@dataclass
class PrivacyBudget:
    """Tracks cumulative privacy expenditure across training rounds."""

    epsilon_total: float = 0.0
    delta_total: float = 0.0
    rounds_consumed: int = 0
    max_epsilon: float = 10.0
    max_delta: float = 1e-5
    per_round_epsilon: list = field(default_factory=list)

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.max_epsilon - self.epsilon_total)

    @property
    def is_exhausted(self) -> bool:
        return self.epsilon_total >= self.max_epsilon


class DifferentialPrivacy:
    """
    Implements (epsilon, delta)-differential privacy for gradient updates.
    Uses the Gaussian mechanism for noise addition and gradient clipping
    to bound sensitivity.
    """

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        max_grad_norm: float = 1.0,
        noise_multiplier: float | None = None,
    ):
        self.epsilon = epsilon
        self.delta = delta
        self.max_grad_norm = max_grad_norm
        # Compute noise multiplier from epsilon/delta if not provided
        self.noise_multiplier = noise_multiplier or self._compute_noise_multiplier()
        self.budget = PrivacyBudget(max_epsilon=epsilon * 100)

    def _compute_noise_multiplier(self) -> float:
        """
        Compute the Gaussian noise multiplier sigma satisfying
        (epsilon, delta)-DP via the analytic Gaussian mechanism.
        sigma >= max_grad_norm * sqrt(2 * ln(1.25 / delta)) / epsilon
        """
        return self.max_grad_norm * math.sqrt(2.0 * math.log(1.25 / self.delta)) / self.epsilon

    def clip_gradients(self, gradients: np.ndarray) -> np.ndarray:
        """
        Clip per-sample gradients to bound L2 sensitivity.

        Args:
            gradients: Array of gradient values.

        Returns:
            Clipped gradient array with L2 norm <= max_grad_norm.
        """
        grad_norm = np.linalg.norm(gradients)
        if grad_norm > self.max_grad_norm:
            gradients = gradients * (self.max_grad_norm / grad_norm)
        return gradients

    def add_noise(self, gradients: np.ndarray) -> np.ndarray:
        """
        Add calibrated Gaussian noise to clipped gradients.

        Args:
            gradients: Clipped gradient array.

        Returns:
            Noisy gradient array satisfying (epsilon, delta)-DP.
        """
        clipped = self.clip_gradients(gradients)
        noise = np.random.normal(
            loc=0.0,
            scale=self.noise_multiplier,
            size=clipped.shape,
        )
        noisy_gradients = clipped + noise
        logger.debug(
            "Added DP noise: sigma=%.4f, grad_norm=%.4f",
            self.noise_multiplier,
            np.linalg.norm(noisy_gradients),
        )
        return noisy_gradients

    def compute_privacy_budget(self, num_rounds: int, sample_rate: float = 1.0) -> PrivacyBudget:
        """
        Compute cumulative privacy budget using simple composition theorem.
        For advanced composition, consider using the moments accountant (Abadi et al.).

        Args:
            num_rounds: Number of training rounds completed.
            sample_rate: Fraction of data sampled per round (Poisson subsampling).

        Returns:
            PrivacyBudget with cumulative epsilon and delta.
        """
        # Simple composition: epsilon grows linearly, delta grows linearly
        # Advanced composition: epsilon grows as O(sqrt(T)), delta grows linearly
        # Using advanced (strong) composition theorem
        effective_epsilon = self.epsilon * math.sqrt(2.0 * num_rounds * math.log(1.0 / self.delta))
        effective_epsilon += num_rounds * self.epsilon * (math.exp(self.epsilon) - 1.0)
        effective_delta = num_rounds * self.delta + self.delta

        # Apply subsampling amplification
        if sample_rate < 1.0:
            effective_epsilon *= sample_rate
            effective_delta *= sample_rate

        budget = PrivacyBudget(
            epsilon_total=effective_epsilon,
            delta_total=effective_delta,
            rounds_consumed=num_rounds,
            max_epsilon=self.epsilon * 100,
            max_delta=self.delta * num_rounds * 2,
        )

        logger.info(
            "Privacy budget after %d rounds: eps=%.4f, delta=%.2e (remaining=%.4f)",
            num_rounds,
            budget.epsilon_total,
            budget.delta_total,
            budget.budget_remaining,
        )
        return budget
