"""
Patient Digital Twin — physiological simulation using differential equations.

Implements compartmental ODE models for:
  - Glucose-Insulin dynamics (Bergman Minimal Model)
  - Blood pressure dynamics (Windkessel Model)
  - Medication pharmacokinetics (1-compartment PK model)
  - Renal function trajectory (CKD progression model)

Used for:
  - "What-if" therapy simulations (e.g., adding metformin 500mg twice daily)
  - Hypoglycemia risk prediction for insulin dose adjustments
  - BP response to antihypertensive dose changes
  - CKD progression trajectory under different interventions
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ml.digital_twin")


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────

@dataclass
class PatientPhysiologyParams:
    """
    Physiological parameters calibrated to an individual patient.
    These are estimated from longitudinal lab and vital observations.
    """
    # Bergman Minimal Model parameters (glucose-insulin dynamics)
    glucose_effectiveness: float = 0.028     # Sg — insulin-independent glucose uptake [1/min]
    insulin_sensitivity: float = 0.00007     # Si — insulin-mediated glucose uptake [L/(mU·min²)]
    insulin_clearance: float = 0.025         # n — insulin clearance rate [1/min]
    remote_insulin_factor: float = 0.020     # p2 — rate of insulin action on remote compartment
    liver_glucose_production: float = 0.012  # Gb — basal endogenous glucose production [mmol/min]
    basal_glucose: float = 5.5              # Gb — basal plasma glucose [mmol/L]
    basal_insulin: float = 10.0             # Ib — basal plasma insulin [mU/L]
    glucose_distribution_volume: float = 13.0  # Vg — volume of glucose distribution [L]
    insulin_distribution_volume: float = 12.0  # Vi — volume of insulin distribution [L]

    # Windkessel BP model parameters
    arterial_compliance: float = 1.2        # C — arterial compliance [mL/mmHg]
    peripheral_resistance: float = 1.0     # R — peripheral vascular resistance [mmHg·s/mL]
    cardiac_output: float = 5000.0         # Q — cardiac output [mL/min]
    heart_rate: float = 70.0              # HR [bpm]

    # CKD progression parameters
    baseline_egfr: float = 75.0            # eGFR [mL/min/1.73m²]
    egfr_decline_rate: float = -1.5        # Annual eGFR decline [mL/min/year]
    proteinuria_factor: float = 1.0        # Multiplier for proteinuria effect on CKD progression

    # PK parameters (representative, overridden per medication)
    default_half_life: float = 8.0         # Hours
    default_bioavailability: float = 0.85


@dataclass
class SimulationScenario:
    """
    A clinical scenario to simulate (e.g., medication change, lifestyle intervention).
    """
    name: str
    duration_hours: float = 24.0
    dt_minutes: float = 5.0               # Simulation time step

    # Meal events: list of (time_minutes, carb_grams)
    meals: List[Tuple[float, float]] = field(default_factory=list)

    # Insulin doses: list of (time_minutes, dose_units)
    insulin_boluses: List[Tuple[float, float]] = field(default_factory=list)

    # Continuous insulin rate [units/hour]
    basal_insulin_rate: float = 0.0

    # Oral medications: list of (time_minutes, drug_name, dose_mg)
    oral_medications: List[Tuple[float, str, float]] = field(default_factory=list)

    # Lifestyle factors
    exercise_start_min: Optional[float] = None
    exercise_duration_min: float = 30.0
    exercise_intensity: float = 0.5       # 0-1 (0=rest, 1=maximal)

    # BP interventions
    antihypertensive_dose_factor: float = 1.0  # Multiplier (1.0 = current dose)


@dataclass
class SimulationResult:
    """Results from running a digital twin simulation."""
    scenario_name: str
    time_points: List[float]              # Minutes from start
    glucose_trajectory: List[float]       # mmol/L
    insulin_trajectory: List[float]       # mU/L
    systolic_bp_trajectory: List[float]   # mmHg
    diastolic_bp_trajectory: List[float]  # mmHg
    drug_concentration: Dict[str, List[float]]  # Drug name -> plasma concentration

    # Summary statistics
    mean_glucose: float = 0.0
    glucose_cv: float = 0.0              # Coefficient of variation
    time_in_range_pct: float = 0.0      # % time 70-180 mg/dL
    hypoglycemia_events: int = 0         # Number of events <70 mg/dL
    hyperglycemia_events: int = 0        # Number of events >180 mg/dL
    mean_systolic_bp: float = 0.0
    mean_diastolic_bp: float = 0.0
    egfr_1year: float = 0.0
    egfr_5year: float = 0.0

    warnings: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Medication PK Database
# ─────────────────────────────────────────────────────────────

MEDICATION_PK = {
    "metformin": {
        "half_life_hours": 6.5,
        "bioavailability": 0.55,
        "Vd_L_per_kg": 3.4,
        "glucose_lowering_effect": 0.85,  # Fraction of postprandial glucose peak reduction
        "insulin_sensitizing": True,
    },
    "glipizide": {
        "half_life_hours": 3.0,
        "bioavailability": 0.95,
        "Vd_L_per_kg": 0.3,
        "insulin_secretagogue": True,
        "insulin_release_units_per_mg": 0.15,
    },
    "insulin_glargine": {
        "half_life_hours": 12.0,
        "bioavailability": 1.0,
        "Vd_L_per_kg": 0.15,
        "peak_hours": None,  # Peakless
        "duration_hours": 24.0,
    },
    "insulin_lispro": {
        "half_life_hours": 1.0,
        "bioavailability": 1.0,
        "Vd_L_per_kg": 0.15,
        "onset_min": 15,
        "peak_hours": 1.0,
        "duration_hours": 4.0,
    },
    "lisinopril": {
        "half_life_hours": 12.0,
        "bioavailability": 0.25,
        "Vd_L_per_kg": 1.0,
        "bp_reduction_systolic": -10.0,  # mmHg at standard dose per day
        "bp_reduction_diastolic": -6.0,
        "renal_protective": True,
        "egfr_effect_per_year": +1.5,    # Slows CKD progression
    },
    "amlodipine": {
        "half_life_hours": 35.0,
        "bioavailability": 0.64,
        "Vd_L_per_kg": 21.0,
        "bp_reduction_systolic": -8.0,
        "bp_reduction_diastolic": -5.0,
    },
    "metoprolol": {
        "half_life_hours": 3.5,
        "bioavailability": 0.50,
        "Vd_L_per_kg": 5.6,
        "bp_reduction_systolic": -9.0,
        "bp_reduction_diastolic": -5.0,
        "hr_reduction_bpm": -12.0,
    },
    "atorvastatin": {
        "half_life_hours": 14.0,
        "bioavailability": 0.14,
        "Vd_L_per_kg": 381.0,
        "ldl_reduction_pct": -45.0,
    },
    "empagliflozin": {
        "half_life_hours": 12.4,
        "bioavailability": 0.78,
        "Vd_L_per_kg": 1.4,
        "glucose_lowering_effect": 0.70,
        "bp_reduction_systolic": -3.5,
        "bp_reduction_diastolic": -2.0,
        "egfr_effect_per_year": +2.0,    # Renal protective (EMPA-REG)
        "weight_loss_kg": -2.5,
    },
    "semaglutide": {
        "half_life_hours": 168.0,  # 7 days
        "bioavailability": 0.89,
        "Vd_L_per_kg": 0.12,
        "glucose_lowering_effect": 0.90,
        "weight_loss_kg": -5.0,
        "bp_reduction_systolic": -4.0,
        "insulin_release_boost": 0.30,
    },
}


# ─────────────────────────────────────────────────────────────
# ODE Models
# ─────────────────────────────────────────────────────────────

def bergman_minimal_model(
    state: np.ndarray,
    t: float,
    params: PatientPhysiologyParams,
    meal_rate: float,     # Glucose appearance rate from meal [mmol/min]
    insulin_input: float, # Exogenous insulin infusion rate [mU/min]
    exercise_effect: float = 0.0,  # Exercise-induced glucose uptake enhancement
) -> np.ndarray:
    """
    Bergman Minimal Model ODEs for glucose-insulin dynamics.

    State vector: [G, X, I]
        G — plasma glucose [mmol/L]
        X — remote insulin (interstitial compartment) [1/min]
        I — plasma insulin [mU/L]

    Reference: Bergman RN et al. J Clin Invest. 1981;68(6):1456-1467.
    """
    G, X, I = state

    p = params

    # Glucose dynamics: dG/dt
    dG = (
        -p.glucose_effectiveness * G          # Insulin-independent uptake
        - X * G                                # Remote insulin action
        + p.liver_glucose_production           # Hepatic glucose production
        + meal_rate / p.glucose_distribution_volume  # Meal absorption
        - exercise_effect * G * 0.5           # Exercise-enhanced uptake
    )

    # Remote insulin dynamics: dX/dt
    dX = (
        -p.remote_insulin_factor * X
        + p.insulin_sensitivity * (I - p.basal_insulin)
    )

    # Plasma insulin dynamics: dI/dt
    dI = (
        -p.insulin_clearance * (I - p.basal_insulin)
        + insulin_input / p.insulin_distribution_volume
    )

    return np.array([dG, dX, dI])


def windkessel_bp_model(
    state: np.ndarray,
    t: float,
    params: PatientPhysiologyParams,
    drug_bp_effect: float = 0.0,   # Drug-induced change in peripheral resistance
) -> np.ndarray:
    """
    2-element Windkessel model for arterial blood pressure dynamics.

    State vector: [P_a] — mean arterial pressure [mmHg]

    Simplified: dP/dt = (Q - P/R) / C + drug_effect
    where Q = cardiac output, R = peripheral resistance, C = arterial compliance.
    """
    P = state[0]

    p = params
    R_eff = p.peripheral_resistance * (1.0 + drug_bp_effect)

    dP = (p.cardiac_output / 60.0 - P / R_eff) / p.arterial_compliance

    return np.array([dP])


def ckd_progression_model(
    egfr: float,
    years: float,
    params: PatientPhysiologyParams,
    treatment_egfr_slope_modifier: float = 0.0,  # Positive = renal protective
) -> float:
    """
    Simple linear CKD progression model (Levey et al.).
    Calculates projected eGFR after 'years' under current treatment.

    Returns projected eGFR [mL/min/1.73m²].
    """
    annual_rate = params.egfr_decline_rate * params.proteinuria_factor + treatment_egfr_slope_modifier
    projected_egfr = egfr + annual_rate * years
    return max(projected_egfr, 0.0)  # eGFR cannot be negative


def one_compartment_pk(
    concentration: float,
    dose_rate: float,
    elimination_rate: float,
    volume: float,
) -> float:
    """
    1-compartment pharmacokinetic model ODE.
    dC/dt = (dose_rate / V) - k_el * C

    Args:
        concentration: Current drug concentration [mg/L]
        dose_rate: Rate of drug input [mg/min]
        elimination_rate: First-order elimination rate [1/min]
        volume: Volume of distribution [L]

    Returns: dC/dt
    """
    return (dose_rate / volume) - elimination_rate * concentration


# ─────────────────────────────────────────────────────────────
# RK4 ODE Solver
# ─────────────────────────────────────────────────────────────

def rk4_step(
    f,
    state: np.ndarray,
    t: float,
    dt: float,
    **kwargs,
) -> np.ndarray:
    """4th-order Runge-Kutta integration step."""
    k1 = f(state, t, **kwargs)
    k2 = f(state + 0.5 * dt * k1, t + 0.5 * dt, **kwargs)
    k3 = f(state + 0.5 * dt * k2, t + 0.5 * dt, **kwargs)
    k4 = f(state + dt * k3, t + dt, **kwargs)
    return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


# ─────────────────────────────────────────────────────────────
# Patient Digital Twin
# ─────────────────────────────────────────────────────────────

class PatientDigitalTwin:
    """
    Patient Digital Twin for physiological simulation.

    Workflow:
        1. Calibrate parameters from patient's longitudinal EHR data
        2. Run ODE simulation for a given clinical scenario
        3. Return time-series trajectories and clinical summaries
        4. Compare scenarios to guide therapy decisions

    Example usage:
        twin = PatientDigitalTwin(patient)
        twin.calibrate()

        # Current therapy
        baseline = twin.run_scenario(SimulationScenario(name="baseline"))

        # Add empagliflozin 10mg daily
        new_scenario = SimulationScenario(name="add_empa")
        new_scenario.oral_medications = [(480, "empagliflozin", 10)]  # Dose at 8am
        empa_result = twin.run_scenario(new_scenario)

        comparison = twin.compare_scenarios(baseline, empa_result)
    """

    def __init__(self, patient=None):
        self.patient = patient
        self.params = PatientPhysiologyParams()
        self.version = "digital_twin_v1"
        self._calibrated = False

    def calibrate(self) -> bool:
        """
        Calibrate physiological parameters from patient EHR data.
        Uses recent labs, vitals, and medication history.

        Returns True if calibration succeeded, False if insufficient data.
        """
        if self.patient is None:
            logger.warning("No patient provided for calibration.")
            return False

        try:
            self._calibrate_glucose_params()
            self._calibrate_bp_params()
            self._calibrate_ckd_params()
            self._calibrated = True
            logger.info(f"Digital twin calibrated for patient {getattr(self.patient, 'fhir_id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Digital twin calibration failed: {e}")
            return False

    def _calibrate_glucose_params(self):
        """Calibrate glucose-insulin model parameters from CGM and HbA1c data."""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        cutoff_90d = now - timedelta(days=90)

        # Get recent glucose readings
        glucose_vals = list(self.patient.observations.filter(
            code="2339-0",
            effective_datetime__gte=cutoff_90d,
        ).values_list("value_quantity", flat=True))

        if glucose_vals:
            glucose_arr = np.array([float(v) for v in glucose_vals if v is not None])
            mean_glucose = np.mean(glucose_arr)
            # Convert mg/dL to mmol/L
            self.params.basal_glucose = mean_glucose / 18.0
            glucose_cv = np.std(glucose_arr) / mean_glucose if mean_glucose > 0 else 0.15
            # Higher CV → lower insulin sensitivity
            self.params.insulin_sensitivity = max(0.00002, 0.0001 - glucose_cv * 0.0001)

        # Calibrate from HbA1c
        hba1c_obs = self.patient.observations.filter(
            code="4548-4",
            effective_datetime__gte=cutoff_90d,
        ).order_by("-effective_datetime").first()

        if hba1c_obs and hba1c_obs.value_quantity:
            hba1c = float(hba1c_obs.value_quantity)
            # Estimated Average Glucose: eAG (mg/dL) = 28.7 * A1C − 46.7
            eag_mgdl = 28.7 * hba1c - 46.7
            self.params.basal_glucose = eag_mgdl / 18.0
            # Higher A1C → reduced insulin sensitivity and increased hepatic glucose production
            self.params.insulin_sensitivity *= max(0.3, 1.0 - (hba1c - 5.7) * 0.08)
            self.params.liver_glucose_production *= min(2.0, 1.0 + (hba1c - 5.7) * 0.05)

    def _calibrate_bp_params(self):
        """Calibrate Windkessel BP parameters from recent BP readings."""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_30d = timezone.now() - timedelta(days=30)

        systolic_vals = list(self.patient.observations.filter(
            code="8480-6",
            effective_datetime__gte=cutoff_30d,
        ).values_list("value_quantity", flat=True))

        if systolic_vals:
            sys_arr = np.array([float(v) for v in systolic_vals if v is not None])
            mean_systolic = np.mean(sys_arr)
            # Back-calculate peripheral resistance from observed MAP
            # MAP ≈ DBP + (SBP - DBP) / 3 ≈ 0.33 * SBP + 0.67 * DBP
            # Use MAP as a proxy: R = MAP / (CO / 60)
            diastolic_vals = list(self.patient.observations.filter(
                code="8462-4",
                effective_datetime__gte=cutoff_30d,
            ).values_list("value_quantity", flat=True))

            if diastolic_vals:
                dia_arr = np.array([float(v) for v in diastolic_vals if v is not None])
                mean_diastolic = np.mean(dia_arr)
                map_mmhg = mean_diastolic + (mean_systolic - mean_diastolic) / 3.0
                co_ml_per_sec = self.params.cardiac_output / 60.0
                self.params.peripheral_resistance = map_mmhg / co_ml_per_sec

        # Heart rate calibration
        hr_vals = list(self.patient.observations.filter(
            code="8867-4",
            effective_datetime__gte=cutoff_30d,
        ).values_list("value_quantity", flat=True))

        if hr_vals:
            hr_arr = np.array([float(v) for v in hr_vals if v is not None])
            self.params.heart_rate = float(np.mean(hr_arr))

    def _calibrate_ckd_params(self):
        """Calibrate CKD progression model from longitudinal eGFR data."""
        from django.utils import timezone
        from datetime import timedelta
        import datetime

        now = timezone.now()
        cutoff_2y = now - timedelta(days=730)

        egfr_obs = list(self.patient.observations.filter(
            code="33914-3",
            effective_datetime__gte=cutoff_2y,
        ).order_by("effective_datetime").values("value_quantity", "effective_datetime"))

        if len(egfr_obs) >= 2:
            values = [float(o["value_quantity"]) for o in egfr_obs if o["value_quantity"] is not None]
            times = [o["effective_datetime"] for o in egfr_obs if o["value_quantity"] is not None]

            if len(values) >= 2:
                self.params.baseline_egfr = float(values[-1])
                # Estimate annual decline from linear regression
                days_elapsed = [(t - times[0]).days for t in times]
                if days_elapsed[-1] > 0:
                    slope_per_day = np.polyfit(days_elapsed, values, 1)[0]
                    self.params.egfr_decline_rate = slope_per_day * 365.0  # Annual rate
        elif egfr_obs:
            self.params.baseline_egfr = float(egfr_obs[-1]["value_quantity"] or 75.0)

        # Proteinuria increases CKD progression rate
        uacr_obs = self.patient.observations.filter(
            code="14959-1",  # UACR LOINC
            effective_datetime__gte=now - timedelta(days=90),
        ).order_by("-effective_datetime").first()

        if uacr_obs and uacr_obs.value_quantity:
            uacr = float(uacr_obs.value_quantity)
            if uacr > 300:       # Macroalbuminuria
                self.params.proteinuria_factor = 2.5
            elif uacr > 30:      # Microalbuminuria
                self.params.proteinuria_factor = 1.5

    def run_scenario(self, scenario: SimulationScenario) -> SimulationResult:
        """
        Run a physiological simulation for a given clinical scenario.

        Uses RK4 numerical integration at the specified time step.

        Returns SimulationResult with full time-series trajectories.
        """
        if not self._calibrated:
            self.calibrate()

        dt = scenario.dt_minutes                   # minutes
        total_steps = int(scenario.duration_hours * 60 / dt)
        time_points = [i * dt for i in range(total_steps)]

        # Initial states
        G0 = self.params.basal_glucose             # mmol/L
        X0 = 0.0                                   # Remote insulin (starts at baseline)
        I0 = self.params.basal_insulin             # mU/L
        P0 = self.params.peripheral_resistance * (self.params.cardiac_output / 60.0)  # MAP estimation

        glucose_traj = []
        insulin_traj = []
        systolic_traj = []
        diastolic_traj = []
        drug_concentrations = {name: [] for name in MEDICATION_PK.keys()}

        # State vectors
        glucose_state = np.array([G0, X0, I0])
        bp_state = np.array([P0])

        # Drug plasma concentrations [mg/L] for each medication
        drug_states = {}

        # Pre-compute drug elimination rates
        drug_elim_rates = {}
        drug_volumes = {}
        for drug_name, pk in MEDICATION_PK.items():
            t_half_min = pk["half_life_hours"] * 60.0
            drug_elim_rates[drug_name] = np.log(2) / t_half_min
            drug_volumes[drug_name] = pk.get("Vd_L_per_kg", 1.0) * 70.0  # Assume 70kg

        # Initialize drug states from scenario oral medications + current meds
        for t_min, drug_name, dose_mg in scenario.oral_medications:
            if drug_name not in drug_states:
                drug_states[drug_name] = 0.0

        # Compute cumulative drug BP and glucose effects from antihypertensives
        bp_drug_resistance_modifier = 0.0
        glucose_drug_effect = 0.0

        # Track drug steady-state effects from pre-existing medications
        for t_min, drug_name, dose_mg in scenario.oral_medications:
            if drug_name in MEDICATION_PK:
                pk = MEDICATION_PK[drug_name]
                if drug_name not in drug_states:
                    drug_states[drug_name] = 0.0

        warnings = []

        for step, t in enumerate(time_points):

            # ── Meal inputs ──────────────────────────────────────
            meal_rate_mmol_min = 0.0
            for meal_t, carb_g in scenario.meals:
                if abs(t - meal_t) < dt:
                    # Gaussian absorption: peak at 30 min, duration ~120 min
                    glucose_mmol = carb_g * 0.0556  # 1g carb ≈ 0.0556 mmol glucose
                    # Spread over 60 min: rate = total / 60
                    meal_rate_mmol_min = glucose_mmol / 60.0

            # ── Insulin inputs ───────────────────────────────────
            insulin_input_mU_min = scenario.basal_insulin_rate / 60.0  # Units/hr → mU/min * 1000
            for bolus_t, bolus_units in scenario.insulin_boluses:
                if abs(t - bolus_t) < dt:
                    # Bolus: spread over 5 minutes
                    insulin_input_mU_min += (bolus_units * 1000) / 5.0  # Convert to mU/min

            # ── Oral medication dosing and PK ────────────────────
            for dose_t, drug_name, dose_mg in scenario.oral_medications:
                if abs(t - dose_t) < dt and drug_name in MEDICATION_PK:
                    pk = MEDICATION_PK[drug_name]
                    bioavailability = pk.get("bioavailability", 0.80)
                    absorbed_dose = dose_mg * bioavailability
                    # Instantaneous absorption (simplified)
                    volume = drug_volumes.get(drug_name, 70.0)
                    if drug_name not in drug_states:
                        drug_states[drug_name] = 0.0
                    drug_states[drug_name] += absorbed_dose / volume

            # ── Update drug concentrations (PK elimination) ──────
            for drug_name in list(drug_states.keys()):
                k_el = drug_elim_rates.get(drug_name, 0.001)
                dose_rate = 0.0  # No ongoing infusion for oral drugs
                dC = one_compartment_pk(
                    concentration=drug_states[drug_name],
                    dose_rate=dose_rate,
                    elimination_rate=k_el,
                    volume=drug_volumes.get(drug_name, 70.0),
                )
                drug_states[drug_name] = max(0.0, drug_states[drug_name] + dC * dt)
                if drug_name in drug_concentrations:
                    drug_concentrations[drug_name].append(drug_states[drug_name])

            # ── Compute drug effects ─────────────────────────────
            # Glucose-lowering effects from oral antidiabetics
            total_glucose_reduction = 1.0  # Multiplicative factor
            for drug_name, concentration in drug_states.items():
                pk = MEDICATION_PK.get(drug_name, {})
                if pk.get("insulin_secretagogue") and concentration > 0.01:
                    # Sulfonylurea: stimulates insulin secretion
                    extra_insulin = pk.get("insulin_release_units_per_mg", 0.1) * concentration
                    insulin_input_mU_min += extra_insulin
                if pk.get("glucose_lowering_effect") and concentration > 0.01:
                    # Reduce hepatic glucose production (simplified)
                    factor = pk["glucose_lowering_effect"] * min(concentration / 0.5, 1.0)
                    total_glucose_reduction *= (1.0 - factor * 0.3)

            # Modify liver glucose production
            effective_hepatic_output = self.params.liver_glucose_production * total_glucose_reduction

            # BP drug effects
            total_bp_resistance_change = 0.0
            for drug_name, concentration in drug_states.items():
                pk = MEDICATION_PK.get(drug_name, {})
                if pk.get("bp_reduction_systolic") and concentration > 0.01:
                    # Scale effect by drug concentration relative to therapeutic range (~0.5 mg/L)
                    effect_fraction = min(concentration / 0.5, 1.0)
                    sbp_reduction = pk["bp_reduction_systolic"] * effect_fraction
                    # Convert to resistance change: ΔR = ΔP / (CO/60)
                    co_per_sec = self.params.cardiac_output / 60.0
                    if co_per_sec > 0:
                        total_bp_resistance_change += sbp_reduction / co_per_sec / 3.0  # Attenuated

            # ── Exercise effect ──────────────────────────────────
            exercise_effect = 0.0
            if scenario.exercise_start_min is not None:
                exercise_end = scenario.exercise_start_min + scenario.exercise_duration_min
                if scenario.exercise_start_min <= t < exercise_end:
                    exercise_effect = scenario.exercise_intensity

            # ── Integrate glucose-insulin ODE (RK4) ─────────────
            glucose_state_new = rk4_step(
                bergman_minimal_model,
                glucose_state,
                t,
                dt,
                params=self.params,
                meal_rate=meal_rate_mmol_min,
                insulin_input=insulin_input_mU_min,
                exercise_effect=exercise_effect,
            )
            # Clamp to physiologically plausible range
            glucose_state_new[0] = np.clip(glucose_state_new[0], 1.0, 30.0)  # 18-540 mg/dL
            glucose_state_new[1] = np.clip(glucose_state_new[1], 0.0, 1.0)
            glucose_state_new[2] = np.clip(glucose_state_new[2], 0.0, 500.0)
            glucose_state = glucose_state_new

            # ── Integrate BP ODE (RK4) ───────────────────────────
            bp_state = rk4_step(
                windkessel_bp_model,
                bp_state,
                t,
                dt,
                params=self.params,
                drug_bp_effect=total_bp_resistance_change,
            )
            bp_state[0] = np.clip(bp_state[0], 40.0, 250.0)  # MAP clamp

            # ── Record trajectories ──────────────────────────────
            glucose_mgdl = glucose_state[0] * 18.0  # mmol/L → mg/dL
            glucose_traj.append(glucose_mgdl)
            insulin_traj.append(glucose_state[2])

            # MAP → SBP/DBP approximation
            # MAP = DBP + (SBP - DBP)/3 → SBP = MAP + 2/3 * PP (Pulse Pressure)
            # Assume PP = 40 mmHg (population default, could be personalized)
            pulse_pressure = 40.0
            map_val = float(bp_state[0])
            systolic_traj.append(map_val + 2 * pulse_pressure / 3)
            diastolic_traj.append(map_val - pulse_pressure / 3)

        # Pad missing drug trajectories with zeros for drugs not in scenario
        for drug_name in list(drug_concentrations.keys()):
            if len(drug_concentrations[drug_name]) < total_steps:
                drug_concentrations[drug_name] = [0.0] * total_steps

        # ── Compute summary statistics ───────────────────────────
        glucose_arr = np.array(glucose_traj)
        mean_glucose = float(np.mean(glucose_arr))
        glucose_cv = float(np.std(glucose_arr) / mean_glucose) if mean_glucose > 0 else 0.0
        tir = float(np.sum((glucose_arr >= 70) & (glucose_arr <= 180)) / len(glucose_arr))
        hypo_events = int(np.sum(glucose_arr < 70))
        hyper_events = int(np.sum(glucose_arr > 250))

        systolic_arr = np.array(systolic_traj)
        mean_sbp = float(np.mean(systolic_arr))
        diastolic_arr = np.array(diastolic_traj)
        mean_dbp = float(np.mean(diastolic_arr))

        # CKD projections including renal-protective medications
        treatment_egfr_modifier = 0.0
        for drug_name in drug_states:
            pk = MEDICATION_PK.get(drug_name, {})
            treatment_egfr_modifier += pk.get("egfr_effect_per_year", 0.0)

        egfr_1year = ckd_progression_model(
            self.params.baseline_egfr, 1.0, self.params, treatment_egfr_modifier
        )
        egfr_5year = ckd_progression_model(
            self.params.baseline_egfr, 5.0, self.params, treatment_egfr_modifier
        )

        # ── Clinical warnings ────────────────────────────────────
        if hypo_events > 0:
            warnings.append(f"HYPOGLYCEMIA RISK: {hypo_events} time points below 70 mg/dL")
        if mean_glucose > 250:
            warnings.append(f"POOR GLYCEMIC CONTROL: Mean glucose {mean_glucose:.0f} mg/dL")
        if mean_sbp > 150:
            warnings.append(f"UNCONTROLLED HYPERTENSION: Mean SBP {mean_sbp:.0f} mmHg")
        if egfr_5year < 15:
            warnings.append(f"CKD PROGRESSION: Projected eGFR {egfr_5year:.0f} at 5 years (Stage 5)")
        elif egfr_5year < 30:
            warnings.append(f"CKD PROGRESSION: Projected eGFR {egfr_5year:.0f} at 5 years (Stage 4)")

        return SimulationResult(
            scenario_name=scenario.name,
            time_points=time_points,
            glucose_trajectory=glucose_traj,
            insulin_trajectory=insulin_traj,
            systolic_bp_trajectory=systolic_traj,
            diastolic_bp_trajectory=diastolic_traj,
            drug_concentration=drug_concentrations,
            mean_glucose=mean_glucose,
            glucose_cv=glucose_cv,
            time_in_range_pct=tir * 100.0,
            hypoglycemia_events=hypo_events,
            hyperglycemia_events=hyper_events,
            mean_systolic_bp=mean_sbp,
            mean_diastolic_bp=mean_dbp,
            egfr_1year=egfr_1year,
            egfr_5year=egfr_5year,
            warnings=warnings,
        )

    def compare_scenarios(
        self,
        baseline: SimulationResult,
        intervention: SimulationResult,
    ) -> Dict[str, Any]:
        """
        Compare two simulation scenarios and return delta metrics.
        Used for clinical decision support ("What if we add medication X?").
        """
        comparison = {
            "baseline_scenario": baseline.scenario_name,
            "intervention_scenario": intervention.scenario_name,
            "glucose_metrics": {
                "mean_glucose_change_mgdl": intervention.mean_glucose - baseline.mean_glucose,
                "tir_change_pct": intervention.time_in_range_pct - baseline.time_in_range_pct,
                "glucose_cv_change": intervention.glucose_cv - baseline.glucose_cv,
                "hypoglycemia_events_change": intervention.hypoglycemia_events - baseline.hypoglycemia_events,
            },
            "bp_metrics": {
                "systolic_change_mmhg": intervention.mean_systolic_bp - baseline.mean_systolic_bp,
                "diastolic_change_mmhg": intervention.mean_diastolic_bp - baseline.mean_diastolic_bp,
            },
            "renal_metrics": {
                "egfr_1year_change": intervention.egfr_1year - baseline.egfr_1year,
                "egfr_5year_change": intervention.egfr_5year - baseline.egfr_5year,
                "baseline_egfr_1year": baseline.egfr_1year,
                "baseline_egfr_5year": baseline.egfr_5year,
                "intervention_egfr_1year": intervention.egfr_1year,
                "intervention_egfr_5year": intervention.egfr_5year,
            },
            "intervention_warnings": intervention.warnings,
            "net_benefit": self._compute_net_benefit(baseline, intervention),
        }

        return comparison

    def _compute_net_benefit(
        self,
        baseline: SimulationResult,
        intervention: SimulationResult,
    ) -> Dict[str, Any]:
        """
        Compute a net clinical benefit score for an intervention.
        Balances glycemic improvement against hypoglycemia risk and BP benefit.
        """
        glucose_benefit = (
            (baseline.mean_glucose - intervention.mean_glucose) / baseline.mean_glucose
            if baseline.mean_glucose > 0 else 0
        ) * 0.4

        tir_benefit = (
            (intervention.time_in_range_pct - baseline.time_in_range_pct) / 100.0
        ) * 0.3

        hypo_penalty = (
            max(0, intervention.hypoglycemia_events - baseline.hypoglycemia_events) / 288.0
        ) * -0.5  # 288 = max possible 5-min readings in 24h

        bp_benefit = (
            max(0, baseline.mean_systolic_bp - intervention.mean_systolic_bp) / 20.0
        ) * 0.15

        renal_benefit = (
            max(0, intervention.egfr_5year - baseline.egfr_5year) / 15.0
        ) * 0.15

        net_score = float(np.clip(
            glucose_benefit + tir_benefit + hypo_penalty + bp_benefit + renal_benefit,
            -1.0, 1.0,
        ))

        return {
            "net_benefit_score": net_score,
            "recommendation": (
                "Intervention likely beneficial" if net_score > 0.1
                else "Intervention may increase risk" if net_score < -0.1
                else "Marginal benefit — clinical judgment required"
            ),
            "components": {
                "glucose_benefit": round(glucose_benefit, 3),
                "tir_benefit": round(tir_benefit, 3),
                "hypo_penalty": round(hypo_penalty, 3),
                "bp_benefit": round(bp_benefit, 3),
                "renal_benefit": round(renal_benefit, 3),
            },
        }

    def simulate_medication_addition(
        self,
        drug_name: str,
        dose_mg: float,
        dosing_times_hours: List[float] = None,
        duration_hours: float = 24.0,
    ) -> Dict:
        """
        Convenience method: simulate adding a new medication.

        Args:
            drug_name: Drug name (must be in MEDICATION_PK)
            dose_mg: Dose in mg
            dosing_times_hours: List of dosing times (default: [8.0] = 8am)
            duration_hours: Simulation duration in hours

        Returns:
            {baseline, intervention, comparison} dict.
        """
        if drug_name not in MEDICATION_PK:
            return {"error": f"Drug '{drug_name}' not in pharmacokinetics database"}

        if dosing_times_hours is None:
            dosing_times_hours = [8.0]

        # Baseline scenario (typical meals, current meds, no new drug)
        baseline_scenario = SimulationScenario(
            name="current_therapy",
            duration_hours=duration_hours,
            meals=[
                (7 * 60, 60),   # Breakfast: 60g carbs at 7am
                (12 * 60, 75),  # Lunch: 75g carbs at noon
                (18 * 60, 70),  # Dinner: 70g carbs at 6pm
            ],
            basal_insulin_rate=self._get_current_basal_rate(),
        )

        # Intervention scenario: add new medication
        dosing_events = [
            (int(h * 60), drug_name, dose_mg)
            for h in dosing_times_hours
        ]
        intervention_scenario = SimulationScenario(
            name=f"add_{drug_name}_{dose_mg}mg",
            duration_hours=duration_hours,
            meals=baseline_scenario.meals,
            basal_insulin_rate=baseline_scenario.basal_insulin_rate,
            oral_medications=dosing_events,
        )

        baseline_result = self.run_scenario(baseline_scenario)
        intervention_result = self.run_scenario(intervention_scenario)

        return {
            "baseline": {
                "mean_glucose_mgdl": round(baseline_result.mean_glucose, 1),
                "time_in_range_pct": round(baseline_result.time_in_range_pct, 1),
                "mean_systolic_bp": round(baseline_result.mean_systolic_bp, 1),
                "egfr_5year": round(baseline_result.egfr_5year, 1),
            },
            "intervention": {
                "mean_glucose_mgdl": round(intervention_result.mean_glucose, 1),
                "time_in_range_pct": round(intervention_result.time_in_range_pct, 1),
                "mean_systolic_bp": round(intervention_result.mean_systolic_bp, 1),
                "egfr_5year": round(intervention_result.egfr_5year, 1),
                "hypoglycemia_events": intervention_result.hypoglycemia_events,
                "warnings": intervention_result.warnings,
            },
            "comparison": self.compare_scenarios(baseline_result, intervention_result),
        }

    def _get_current_basal_rate(self) -> float:
        """Get current basal insulin rate from active medication requests."""
        if self.patient is None:
            return 0.0
        try:
            insulin_rx = self.patient.medication_requests.filter(
                status="active",
                medication_display__icontains="glargine",
            ).first()
            if insulin_rx and insulin_rx.dosage_instruction:
                # Parse dose from dosage instruction JSON
                dosage = insulin_rx.dosage_instruction
                if isinstance(dosage, list) and dosage:
                    dose = dosage[0].get("doseQuantity", {}).get("value", 0)
                    return float(dose) / 24.0  # Convert daily units to units/hr
        except Exception:
            pass
        return 0.0

    def get_ckd_trajectory(self, years: int = 10) -> Dict:
        """
        Get CKD progression trajectory under current and optimized treatment.

        Returns projected eGFR by year under different scenarios.
        """
        if not self._calibrated:
            self.calibrate()

        # Current trajectory
        current_trajectory = []
        for year in range(years + 1):
            egfr = ckd_progression_model(self.params.baseline_egfr, year, self.params, 0.0)
            current_trajectory.append({"year": year, "egfr": round(egfr, 1)})

        # Optimized trajectory (ACE inhibitor + SGLT2 inhibitor)
        renal_protection_effect = (
            MEDICATION_PK["lisinopril"]["egfr_effect_per_year"] +
            MEDICATION_PK["empagliflozin"]["egfr_effect_per_year"]
        )
        optimized_trajectory = []
        for year in range(years + 1):
            egfr = ckd_progression_model(
                self.params.baseline_egfr, year, self.params, renal_protection_effect
            )
            optimized_trajectory.append({"year": year, "egfr": round(egfr, 1)})

        # CKD staging
        def ckd_stage(egfr):
            if egfr >= 90:
                return "G1"
            elif egfr >= 60:
                return "G2"
            elif egfr >= 45:
                return "G3a"
            elif egfr >= 30:
                return "G3b"
            elif egfr >= 15:
                return "G4"
            else:
                return "G5 (Kidney Failure)"

        current_5yr = current_trajectory[min(5, years)]["egfr"]
        current_10yr = current_trajectory[min(10, years)]["egfr"]
        optimized_5yr = optimized_trajectory[min(5, years)]["egfr"]
        optimized_10yr = optimized_trajectory[min(10, years)]["egfr"]

        return {
            "baseline_egfr": self.params.baseline_egfr,
            "annual_decline_rate": round(self.params.egfr_decline_rate, 2),
            "current_treatment_trajectory": current_trajectory,
            "optimized_treatment_trajectory": optimized_trajectory,
            "current_5yr_stage": ckd_stage(current_5yr),
            "current_10yr_stage": ckd_stage(current_10yr),
            "optimized_5yr_stage": ckd_stage(optimized_5yr),
            "optimized_10yr_stage": ckd_stage(optimized_10yr),
            "benefit_of_optimization": {
                "egfr_preserved_at_5yr": round(optimized_5yr - current_5yr, 1),
                "egfr_preserved_at_10yr": round(optimized_10yr - current_10yr, 1),
            },
        }
