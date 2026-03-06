"""
Federated learning coordinator — manages training rounds across tenant clients.
Implements privacy-preserving weighted aggregation with differential privacy noise.
"""

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from .client import FederatedClient, LocalTrainingResult
from .privacy import DifferentialPrivacy

logger = logging.getLogger("ml.federated.coordinator")


class RoundStatus(str, Enum):
    INITIALIZING = "initializing"
    DISTRIBUTING = "distributing"
    TRAINING = "training"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrainingRound:
    """State of a single federated training round."""

    round_id: str
    round_number: int
    status: RoundStatus = RoundStatus.INITIALIZING
    participating_tenants: list[str] = field(default_factory=list)
    updates_received: list[LocalTrainingResult] = field(default_factory=list)
    aggregated_weights: np.ndarray | None = None
    metrics: dict = field(default_factory=dict)
    error: str | None = None


class FederatedCoordinator:
    """
    Coordinates federated learning across multiple tenant organizations.
    Manages the training lifecycle: distribute model -> collect privatized
    updates -> aggregate with DP noise -> repeat.

    Ensures tenant isolation: raw data never leaves the tenant boundary;
    only differentially private gradient updates are collected.
    """

    def __init__(
        self,
        model_shape: tuple[int, ...],
        epsilon: float = 1.0,
        delta: float = 1e-5,
        max_grad_norm: float = 1.0,
        min_clients_per_round: int = 2,
        aggregation_noise_multiplier: float = 0.1,
    ):
        self.model_shape = model_shape
        self.global_weights = np.zeros(model_shape)
        self.dp = DifferentialPrivacy(
            epsilon=epsilon,
            delta=delta,
            max_grad_norm=max_grad_norm,
        )
        self.min_clients_per_round = min_clients_per_round
        self.aggregation_noise_multiplier = aggregation_noise_multiplier

        self.clients: dict[str, FederatedClient] = {}  # tenant_id -> client
        self.rounds: list[TrainingRound] = []
        self.current_round: TrainingRound | None = None

    def register_client(self, tenant_id: str, **kwargs) -> FederatedClient:
        """
        Register a tenant as a federated learning participant.

        Args:
            tenant_id: The tenant organization ID.

        Returns:
            FederatedClient instance for the tenant.
        """
        client = FederatedClient(tenant_id=tenant_id, **kwargs)
        self.clients[tenant_id] = client
        logger.info("Registered federated client for tenant %s", tenant_id[:8])
        return client

    def initialize_round(self, participating_tenants: list[str] | None = None) -> TrainingRound:
        """
        Initialize a new training round.

        Args:
            participating_tenants: Subset of tenant IDs to include. If None,
                                   all registered clients participate.

        Returns:
            TrainingRound describing the new round.
        """
        round_number = len(self.rounds) + 1
        tenants = participating_tenants or list(self.clients.keys())

        if len(tenants) < self.min_clients_per_round:
            raise ValueError(
                f"Need at least {self.min_clients_per_round} clients, "
                f"but only {len(tenants)} available."
            )

        training_round = TrainingRound(
            round_id=str(uuid.uuid4()),
            round_number=round_number,
            status=RoundStatus.INITIALIZING,
            participating_tenants=tenants,
        )
        self.current_round = training_round
        self.rounds.append(training_round)

        logger.info(
            "Initialized round %d (id=%s) with %d tenants",
            round_number,
            training_round.round_id[:8],
            len(tenants),
        )
        return training_round

    def distribute_model(self) -> dict[str, bool]:
        """
        Distribute the current global model weights to all participating clients.

        Returns:
            Dict mapping tenant_id -> success boolean.
        """
        if self.current_round is None:
            raise RuntimeError("No active round. Call initialize_round() first.")

        self.current_round.status = RoundStatus.DISTRIBUTING
        results = {}

        for tenant_id in self.current_round.participating_tenants:
            client = self.clients.get(tenant_id)
            if client is None:
                logger.warning("Tenant %s not registered, skipping", tenant_id[:8])
                results[tenant_id] = False
                continue
            client.receive_global_model(self.global_weights)
            results[tenant_id] = True

        self.current_round.status = RoundStatus.TRAINING
        logger.info("Distributed global model to %d/%d clients", sum(results.values()), len(results))
        return results

    def collect_update(self, result: LocalTrainingResult) -> None:
        """
        Collect a privatized training update from a client.

        Args:
            result: LocalTrainingResult from a client's local training.
        """
        if self.current_round is None:
            raise RuntimeError("No active round.")

        if result.tenant_id not in self.current_round.participating_tenants:
            raise ValueError(f"Tenant {result.tenant_id} is not participating in the current round.")

        self.current_round.updates_received.append(result)
        logger.info(
            "Collected update from tenant %s (round %d): %d/%d received",
            result.tenant_id[:8],
            self.current_round.round_number,
            len(self.current_round.updates_received),
            len(self.current_round.participating_tenants),
        )

    def aggregate_updates(self) -> np.ndarray:
        """
        Aggregate client updates using weighted averaging with differential
        privacy noise. Weights are proportional to each client's sample count.

        Returns:
            Updated global model weights.
        """
        if self.current_round is None:
            raise RuntimeError("No active round.")

        self.current_round.status = RoundStatus.AGGREGATING

        successful_updates = [u for u in self.current_round.updates_received if u.success and u.gradients is not None]

        if len(successful_updates) < self.min_clients_per_round:
            self.current_round.status = RoundStatus.FAILED
            self.current_round.error = (
                f"Only {len(successful_updates)} successful updates; "
                f"need {self.min_clients_per_round}."
            )
            raise RuntimeError(self.current_round.error)

        # Weighted average based on sample count
        total_samples = sum(u.sample_count for u in successful_updates)
        aggregated_gradients = np.zeros(self.model_shape)

        for update in successful_updates:
            weight = update.sample_count / total_samples if total_samples > 0 else 1.0 / len(successful_updates)
            aggregated_gradients += weight * update.gradients

        # Add server-side DP noise for additional privacy
        server_noise = np.random.normal(
            loc=0.0,
            scale=self.aggregation_noise_multiplier,
            size=aggregated_gradients.shape,
        )
        aggregated_gradients += server_noise

        # Apply aggregated update to global weights
        self.global_weights = self.global_weights + aggregated_gradients

        self.current_round.aggregated_weights = self.global_weights.copy()
        self.current_round.status = RoundStatus.COMPLETED
        self.current_round.metrics = {
            "clients_participated": len(successful_updates),
            "total_samples": total_samples,
            "aggregated_grad_norm": float(np.linalg.norm(aggregated_gradients)),
            "server_noise_scale": self.aggregation_noise_multiplier,
        }

        logger.info(
            "Round %d aggregation complete: %d clients, %d total samples, grad_norm=%.4f",
            self.current_round.round_number,
            len(successful_updates),
            total_samples,
            self.current_round.metrics["aggregated_grad_norm"],
        )

        return self.global_weights

    def get_round_status(self, round_number: int | None = None) -> dict[str, Any]:
        """
        Get the status of a training round.

        Args:
            round_number: 1-indexed round number. If None, returns the current round.

        Returns:
            Dict with round status, metrics, and participation info.
        """
        if round_number is not None:
            if round_number < 1 or round_number > len(self.rounds):
                raise ValueError(f"Round {round_number} does not exist (have {len(self.rounds)} rounds).")
            training_round = self.rounds[round_number - 1]
        else:
            if self.current_round is None:
                return {"status": "no_active_round", "total_rounds": len(self.rounds)}
            training_round = self.current_round

        return {
            "round_id": training_round.round_id,
            "round_number": training_round.round_number,
            "status": training_round.status.value,
            "participating_tenants": training_round.participating_tenants,
            "updates_received": len(training_round.updates_received),
            "metrics": training_round.metrics,
            "error": training_round.error,
        }

    def get_privacy_report(self) -> dict[str, Any]:
        """
        Get a summary of cumulative privacy expenditure across all rounds.
        """
        budget = self.dp.compute_privacy_budget(
            num_rounds=len([r for r in self.rounds if r.status == RoundStatus.COMPLETED]),
        )
        return {
            "total_rounds": len(self.rounds),
            "completed_rounds": len([r for r in self.rounds if r.status == RoundStatus.COMPLETED]),
            "epsilon_total": budget.epsilon_total,
            "delta_total": budget.delta_total,
            "budget_remaining": budget.budget_remaining,
            "is_exhausted": budget.is_exhausted,
        }
