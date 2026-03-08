import { create } from 'zustand'
import * as fhirService from '@/services/fhir'

/**
 * Global simulator store – keeps the simulation interval alive even when
 * the user navigates away from the VitalsSimulatorPage.
 *
 * When `backgroundEnabled` is true and the user starts a simulation,
 * the interval is owned by this store (not the component). Navigating
 * away from the page won't stop it.
 */

// LOINC codes matching the simulator page
const VITAL_KEY_TO_LOINC: Record<string, { code: string; display: string }> = {
  heartRate: { code: '8867-4', display: 'Heart rate' },
  systolicBP: { code: '8480-6', display: 'Systolic blood pressure' },
  diastolicBP: { code: '8462-4', display: 'Diastolic blood pressure' },
  spo2: { code: '59408-5', display: 'Oxygen saturation' },
  temperature: { code: '8310-5', display: 'Body temperature' },
  respRate: { code: '9279-1', display: 'Respiratory rate' },
  glucose: { code: '2339-0', display: 'Blood glucose' },
  ecgRate: { code: '8601-7', display: 'ECG heart rate' },
}

// Minimal vital config for background generation
interface VitalConfig {
  key: string
  unit: string
  normalLow: number
  normalHigh: number
  defaultBaseline: number
}

const VITAL_CONFIGS: VitalConfig[] = [
  { key: 'heartRate', unit: 'bpm', normalLow: 60, normalHigh: 100, defaultBaseline: 75 },
  { key: 'systolicBP', unit: 'mmHg', normalLow: 90, normalHigh: 140, defaultBaseline: 120 },
  { key: 'diastolicBP', unit: 'mmHg', normalLow: 60, normalHigh: 90, defaultBaseline: 78 },
  { key: 'spo2', unit: '%', normalLow: 95, normalHigh: 100, defaultBaseline: 97 },
  { key: 'temperature', unit: '°F', normalLow: 97.8, normalHigh: 99.1, defaultBaseline: 98.6 },
  { key: 'respRate', unit: 'br/min', normalLow: 12, normalHigh: 20, defaultBaseline: 16 },
  { key: 'glucose', unit: 'mg/dL', normalLow: 70, normalHigh: 140, defaultBaseline: 100 },
]

function gaussRandom(mean: number, std: number): number {
  const u1 = Math.random()
  const u2 = Math.random()
  return mean + std * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
}

interface SimulatorState {
  isRunning: boolean
  backgroundEnabled: boolean
  patientId: string | null
  intervalMs: number
  tickCount: number

  // Actions
  startBackground: (patientId: string, intervalMs?: number) => void
  stop: () => void
  setBackgroundEnabled: (enabled: boolean) => void
}

let bgTimer: ReturnType<typeof setInterval> | null = null

export const useSimulatorStore = create<SimulatorState>((set, get) => ({
  isRunning: false,
  backgroundEnabled: false,
  patientId: null,
  intervalMs: 2000,
  tickCount: 0,

  setBackgroundEnabled: (enabled) => set({ backgroundEnabled: enabled }),

  startBackground: (patientId, intervalMs = 2000) => {
    // Clear any existing timer
    if (bgTimer) {
      clearInterval(bgTimer)
      bgTimer = null
    }

    set({ isRunning: true, patientId, intervalMs, tickCount: 0 })

    const tick = () => {
      const state = get()
      if (!state.patientId) return

      const now = new Date().toISOString()
      set({ tickCount: state.tickCount + 1 })

      // Generate and persist one reading for each vital
      for (const cfg of VITAL_CONFIGS) {
        const loinc = VITAL_KEY_TO_LOINC[cfg.key]
        if (!loinc) continue

        const variability = (cfg.normalHigh - cfg.normalLow) * 0.15
        const value = gaussRandom(cfg.defaultBaseline, variability)
        const clamped = Math.max(cfg.normalLow * 0.7, Math.min(cfg.normalHigh * 1.3, value))
        const rounded = cfg.key === 'temperature' ? Math.round(clamped * 10) / 10 : Math.round(clamped)

        let interpretation = 'N'
        if (rounded > cfg.normalHigh) interpretation = rounded > cfg.normalHigh * 1.2 ? 'HH' : 'H'
        else if (rounded < cfg.normalLow) interpretation = rounded < cfg.normalLow * 0.8 ? 'LL' : 'L'

        fhirService.createObservation({
          status: 'final',
          code: loinc.code,
          display: loinc.display,
          value_quantity: rounded,
          value_unit: cfg.unit,
          effective_datetime: now,
          reference_range_low: cfg.normalLow,
          reference_range_high: cfg.normalHigh,
          interpretation,
          device_type: 'simulator',
          patient_fhir_id: state.patientId,
        } as Record<string, unknown>).catch(() => {})
      }

      // ECG observation
      const ecgLoinc = VITAL_KEY_TO_LOINC.ecgRate
      const hr = gaussRandom(75, 6)
      fhirService.createObservation({
        status: 'final',
        code: ecgLoinc.code,
        display: ecgLoinc.display,
        value_quantity: Math.round(hr),
        value_unit: 'bpm',
        effective_datetime: now,
        reference_range_low: 60,
        reference_range_high: 100,
        interpretation: 'NSR',
        device_type: 'simulator',
        patient_fhir_id: state.patientId,
      } as Record<string, unknown>).catch(() => {})
    }

    // First tick immediately
    tick()
    bgTimer = setInterval(tick, intervalMs)
  },

  stop: () => {
    if (bgTimer) {
      clearInterval(bgTimer)
      bgTimer = null
    }
    set({ isRunning: false, tickCount: 0 })
  },
}))
