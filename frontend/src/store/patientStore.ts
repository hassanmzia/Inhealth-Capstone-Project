import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type { PatientSummary, VitalSign, ClinicalAlert } from '@/types/clinical'

// ─── Patient Store State ──────────────────────────────────────────────────────

interface PatientState {
  // Patient list
  patients: PatientSummary[]
  totalPatients: number
  isLoadingPatients: boolean
  patientListPage: number
  patientListSearch: string
  patientListFilters: PatientFilters

  // Selected patient
  selectedPatient: PatientSummary | null
  isLoadingPatient: boolean

  // Live vitals (per patient)
  liveVitals: Map<string, VitalSign[]>

  // Patient alerts
  patientAlerts: Map<string, ClinicalAlert[]>

  // Actions
  setPatients: (patients: PatientSummary[], total: number) => void
  setSelectedPatient: (patient: PatientSummary | null) => void
  updatePatient: (patientId: string, updates: Partial<PatientSummary>) => void
  setIsLoadingPatients: (loading: boolean) => void
  setIsLoadingPatient: (loading: boolean) => void
  setPage: (page: number) => void
  setSearch: (search: string) => void
  setFilters: (filters: Partial<PatientFilters>) => void
  resetFilters: () => void

  // Live vital actions
  addVitalReading: (patientId: string, vital: VitalSign) => void
  setPatientVitals: (patientId: string, vitals: VitalSign[]) => void
  getLatestVitals: (patientId: string) => VitalSign[]
}

// ─── Filter Types ─────────────────────────────────────────────────────────────

export interface PatientFilters {
  riskLevel: string[]
  conditions: string[]
  hasCareGaps: boolean | null
  alertStatus: string[]
  provider: string | null
  ageMin: number | null
  ageMax: number | null
  gender: string | null
  sortBy: 'name' | 'risk_score' | 'last_contact' | 'alert_status'
  sortOrder: 'asc' | 'desc'
}

const DEFAULT_FILTERS: PatientFilters = {
  riskLevel: [],
  conditions: [],
  hasCareGaps: null,
  alertStatus: [],
  provider: null,
  ageMin: null,
  ageMax: null,
  gender: null,
  sortBy: 'risk_score',
  sortOrder: 'desc',
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const usePatientStore = create<PatientState>()(
  subscribeWithSelector((set, get) => ({
    patients: [],
    totalPatients: 0,
    isLoadingPatients: false,
    patientListPage: 1,
    patientListSearch: '',
    patientListFilters: DEFAULT_FILTERS,
    selectedPatient: null,
    isLoadingPatient: false,
    liveVitals: new Map(),
    patientAlerts: new Map(),

    setPatients: (patients, total) => {
      set({ patients, totalPatients: total })
    },

    setSelectedPatient: (patient) => {
      set({ selectedPatient: patient })
    },

    updatePatient: (patientId, updates) => {
      set((state) => ({
        patients: state.patients.map((p) =>
          p.id === patientId ? { ...p, ...updates } : p,
        ),
        selectedPatient:
          state.selectedPatient?.id === patientId
            ? { ...state.selectedPatient, ...updates }
            : state.selectedPatient,
      }))
    },

    setIsLoadingPatients: (loading) => set({ isLoadingPatients: loading }),
    setIsLoadingPatient: (loading) => set({ isLoadingPatient: loading }),
    setPage: (page) => set({ patientListPage: page }),
    setSearch: (search) => set({ patientListSearch: search, patientListPage: 1 }),

    setFilters: (filters) => {
      set((state) => ({
        patientListFilters: { ...state.patientListFilters, ...filters },
        patientListPage: 1,
      }))
    },

    resetFilters: () => {
      set({ patientListFilters: DEFAULT_FILTERS, patientListPage: 1, patientListSearch: '' })
    },

    addVitalReading: (patientId, vital) => {
      set((state) => {
        const current = state.liveVitals.get(patientId) ?? []
        // Keep last 200 readings per patient
        const updated = [vital, ...current].slice(0, 200)
        const newMap = new Map(state.liveVitals)
        newMap.set(patientId, updated)

        // Update alert status on patient summary
        const patients = state.patients.map((p) => {
          if (p.id !== patientId) return p
          const newStatus = vital.status === 'critical' ? 'critical'
            : vital.status === 'warning' ? 'warning'
            : p.alertStatus
          return { ...p, alertStatus: newStatus }
        })

        return { liveVitals: newMap, patients }
      })
    },

    setPatientVitals: (patientId, vitals) => {
      set((state) => {
        const newMap = new Map(state.liveVitals)
        newMap.set(patientId, vitals)
        return { liveVitals: newMap }
      })
    },

    getLatestVitals: (patientId) => {
      return get().liveVitals.get(patientId) ?? []
    },
  })),
)

// ─── Selectors ────────────────────────────────────────────────────────────────

export const selectCriticalPatients = (state: PatientState) =>
  state.patients.filter((p) => p.alertStatus === 'critical')

export const selectHighRiskPatients = (state: PatientState) =>
  state.patients.filter((p) => p.riskScore?.category === 'high' || p.riskScore?.category === 'critical')

export const selectPatientsWithOpenGaps = (state: PatientState) =>
  state.patients.filter((p) => p.openCareGaps > 0)
