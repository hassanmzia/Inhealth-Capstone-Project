#!/usr/bin/env python3
"""
IoT Device Simulator — generates realistic wearable vital-sign data
and sends it to the InHealth backend API.

Supported devices:
  - cgm          Continuous Glucose Monitor (blood glucose mg/dL)
  - smartwatch   Heart rate, SpO2, temperature, activity
  - pulse_ox     Pulse oximeter (SpO2, pulse rate)
  - bp_monitor   Blood pressure (systolic / diastolic mmHg)

Usage:
    python scripts/iot_simulator.py \
        --patient-id <uuid> \
        --device-type cgm \
        --interval 30 \
        --duration 300 \
        --api-url http://localhost:8000/api/v1/clinical/vitals/ \
        --anomaly-chance 0.05
"""

import argparse
import json
import logging
import math
import random
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("iot_simulator")

# ---------------------------------------------------------------------------
# Physiological ranges
# ---------------------------------------------------------------------------
VITAL_RANGES = {
    "heart_rate": {"min": 60, "max": 100, "unit": "bpm", "loinc": "8867-4"},
    "spo2": {"min": 94, "max": 100, "unit": "%", "loinc": "59408-5"},
    "systolic_bp": {"min": 110, "max": 140, "unit": "mmHg", "loinc": "8480-6"},
    "diastolic_bp": {"min": 70, "max": 90, "unit": "mmHg", "loinc": "8462-4"},
    "glucose": {"min": 70, "max": 180, "unit": "mg/dL", "loinc": "2339-0"},
    "temperature": {"min": 36.1, "max": 37.2, "unit": "Cel", "loinc": "8310-5"},
}

# Device-to-vital mapping
DEVICE_VITALS = {
    "cgm": ["glucose"],
    "smartwatch": ["heart_rate", "spo2", "temperature"],
    "pulse_ox": ["spo2", "heart_rate"],
    "bp_monitor": ["systolic_bp", "diastolic_bp"],
}

# Anomaly definitions: how much to shift the value
ANOMALY_SHIFTS = {
    "heart_rate": {"spike": 50, "deteriorate": 3},
    "spo2": {"spike": -8, "deteriorate": -0.5},
    "systolic_bp": {"spike": 40, "deteriorate": 2},
    "diastolic_bp": {"spike": 20, "deteriorate": 1},
    "glucose": {"spike": 120, "deteriorate": 5},
    "temperature": {"spike": 2.5, "deteriorate": 0.15},
}


class VitalSignGenerator:
    """Generates physiologically realistic vital sign readings with optional anomalies."""

    def __init__(self, device_type: str, noise_std: float = 0.02, anomaly_chance: float = 0.0):
        if device_type not in DEVICE_VITALS:
            raise ValueError(f"Unknown device type '{device_type}'. Choose from: {list(DEVICE_VITALS.keys())}")

        self.device_type = device_type
        self.vitals = DEVICE_VITALS[device_type]
        self.noise_std = noise_std
        self.anomaly_chance = anomaly_chance

        # Circadian-like baseline tracking
        self._baselines: dict[str, float] = {}
        self._step = 0
        self._anomaly_mode: str | None = None  # None, "spike", or "deteriorate"
        self._deterioration_accum: dict[str, float] = {v: 0.0 for v in self.vitals}

        for vital in self.vitals:
            r = VITAL_RANGES[vital]
            self._baselines[vital] = (r["min"] + r["max"]) / 2.0

    def generate(self) -> list[dict]:
        """
        Generate one set of vital sign readings.

        Returns:
            List of dicts, each with: vital_type, value, unit, loinc_code, timestamp.
        """
        self._step += 1
        readings = []

        # Decide if an anomaly should start
        if self._anomaly_mode is None and random.random() < self.anomaly_chance:
            self._anomaly_mode = random.choice(["spike", "deteriorate"])
            logger.warning("Anomaly triggered: %s at step %d", self._anomaly_mode, self._step)

        # Spikes last only one reading
        if self._anomaly_mode == "spike":
            anomaly_this_step = "spike"
            self._anomaly_mode = None  # reset after spike
        elif self._anomaly_mode == "deteriorate":
            anomaly_this_step = "deteriorate"
            # Gradual deterioration lasts 5-15 steps
            if random.random() < 0.1:
                self._anomaly_mode = None
                self._deterioration_accum = {v: 0.0 for v in self.vitals}
        else:
            anomaly_this_step = None

        now = datetime.now(timezone.utc).isoformat()

        for vital in self.vitals:
            r = VITAL_RANGES[vital]
            baseline = self._baselines[vital]

            # Add circadian variation (sinusoidal)
            circadian = math.sin(self._step * 0.05) * (r["max"] - r["min"]) * 0.1

            # Add noise
            noise = random.gauss(0, self.noise_std * (r["max"] - r["min"]))

            value = baseline + circadian + noise

            # Apply anomaly
            if anomaly_this_step and vital in ANOMALY_SHIFTS:
                shift_cfg = ANOMALY_SHIFTS[vital]
                if anomaly_this_step == "spike":
                    value += shift_cfg["spike"]
                elif anomaly_this_step == "deteriorate":
                    self._deterioration_accum[vital] += shift_cfg["deteriorate"]
                    value += self._deterioration_accum[vital]

            # Clamp to physically possible range (allow anomalies to exceed normal range)
            hard_min = r["min"] * 0.5
            hard_max = r["max"] * 1.8
            value = max(hard_min, min(hard_max, value))

            # Round appropriately
            if vital == "temperature":
                value = round(value, 1)
            elif vital == "spo2":
                value = round(min(value, 100.0), 1)
            else:
                value = round(value, 0)

            readings.append({
                "vital_type": vital,
                "value": value,
                "unit": r["unit"],
                "loinc_code": r["loinc"],
                "timestamp": now,
            })

        return readings


def send_readings(
    api_url: str,
    patient_id: str,
    device_type: str,
    readings: list[dict],
    token: str | None = None,
) -> bool:
    """POST readings to the backend API."""
    payload = {
        "patient_id": patient_id,
        "device_type": device_type,
        "device_id": f"sim-{device_type}-{patient_id[:8]}",
        "readings": readings,
    }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            logger.info("Sent %d readings (HTTP %d)", len(readings), resp.status_code)
            return True
        else:
            logger.error("API returned HTTP %d: %s", resp.status_code, resp.text[:200])
            return False
    except requests.RequestException as exc:
        logger.error("Failed to send readings: %s", exc)
        return False


def main():
    parser = argparse.ArgumentParser(description="InHealth IoT Device Simulator")
    parser.add_argument("--patient-id", required=True, help="Patient UUID")
    parser.add_argument(
        "--device-type",
        required=True,
        choices=list(DEVICE_VITALS.keys()),
        help="Type of wearable device to simulate",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Seconds between readings (default: 30)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Total simulation duration in seconds (default: 300)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/api/v1/clinical/vitals/",
        help="Backend API endpoint for vital signs",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="JWT bearer token for authentication",
    )
    parser.add_argument(
        "--anomaly-chance",
        type=float,
        default=0.0,
        help="Probability of anomaly per reading (0.0 - 1.0, default: 0.0)",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.02,
        help="Noise standard deviation as fraction of range (default: 0.02)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print readings to stdout instead of sending to API",
    )

    args = parser.parse_args()

    generator = VitalSignGenerator(
        device_type=args.device_type,
        noise_std=args.noise,
        anomaly_chance=args.anomaly_chance,
    )

    logger.info(
        "Starting %s simulator for patient %s (interval=%ds, duration=%ds)",
        args.device_type,
        args.patient_id,
        args.interval,
        args.duration,
    )

    elapsed = 0
    readings_sent = 0

    while elapsed < args.duration:
        readings = generator.generate()

        if args.dry_run:
            for r in readings:
                print(json.dumps(r, indent=2))
        else:
            success = send_readings(
                api_url=args.api_url,
                patient_id=args.patient_id,
                device_type=args.device_type,
                readings=readings,
                token=args.token,
            )
            if success:
                readings_sent += len(readings)

        elapsed += args.interval
        if elapsed < args.duration:
            time.sleep(args.interval)

    logger.info("Simulation complete. Total readings sent: %d", readings_sent)


if __name__ == "__main__":
    main()
