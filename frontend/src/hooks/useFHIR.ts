import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as fhirService from '@/services/fhir'
import type {
  FHIRPatient,
  FHIRObservation,
  FHIRCondition,
  FHIRMedicationRequest,
  FHIRDiagnosticReport,
  FHIRAppointment,
  FHIRSearchParams,
} from '@/types/fhir'
import toast from 'react-hot-toast'

// ─── Patients ─────────────────────────────────────────────────────────────────

export function usePatients(params?: FHIRSearchParams) {
  return useQuery({
    queryKey: ['fhir', 'patients', params],
    queryFn: () => fhirService.getAllPatients(params),
    staleTime: 1000 * 60 * 2,
  })
}

export function usePatient(patientId: string | undefined) {
  return useQuery({
    queryKey: ['fhir', 'patient', patientId],
    queryFn: () => fhirService.getPatient(patientId!),
    enabled: !!patientId,
    staleTime: 1000 * 60 * 5,
  })
}

export function useSearchPatients(query: string) {
  return useQuery({
    queryKey: ['fhir', 'patients', 'search', query],
    queryFn: () => fhirService.searchPatients(query),
    enabled: query.length >= 2,
    staleTime: 1000 * 30,
  })
}

// ─── Observations / Vitals ────────────────────────────────────────────────────

export function useVitalSigns(
  patientId: string | undefined,
  dateFrom?: string,
  options?: { refetchInterval?: number },
) {
  return useQuery({
    queryKey: ['fhir', 'vitals', patientId, dateFrom],
    queryFn: () => fhirService.getVitalSigns(patientId!, dateFrom),
    enabled: !!patientId,
    staleTime: 1000 * 30,
    refetchInterval: options?.refetchInterval,
  })
}

export function useLabResults(patientId: string | undefined, dateFrom?: string) {
  return useQuery({
    queryKey: ['fhir', 'labs', patientId, dateFrom],
    queryFn: () => fhirService.getLabResults(patientId!, dateFrom),
    enabled: !!patientId,
    staleTime: 1000 * 60 * 5,
  })
}

export function useGlucoseReadings(patientId: string | undefined, hours = 24) {
  return useQuery({
    queryKey: ['fhir', 'glucose', patientId, hours],
    queryFn: () => fhirService.getGlucoseReadings(patientId!, hours),
    enabled: !!patientId,
    staleTime: 1000 * 30,
    refetchInterval: 1000 * 60 * 5,
  })
}

export function useCreateObservation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (obs: Partial<FHIRObservation>) => fhirService.createObservation(obs),
    onSuccess: (data) => {
      const patientRef = data.subject?.reference
      const patientId = patientRef?.split('/').pop()
      if (patientId) {
        queryClient.invalidateQueries({ queryKey: ['fhir', 'vitals', patientId] })
        queryClient.invalidateQueries({ queryKey: ['fhir', 'labs', patientId] })
      }
      toast.success('Observation recorded')
    },
    onError: () => toast.error('Failed to record observation'),
  })
}

// ─── Conditions ───────────────────────────────────────────────────────────────

export function useConditions(
  patientId: string | undefined,
  clinicalStatus?: 'active' | 'resolved' | 'inactive',
) {
  return useQuery({
    queryKey: ['fhir', 'conditions', patientId, clinicalStatus],
    queryFn: () => fhirService.getConditions(patientId!, clinicalStatus),
    enabled: !!patientId,
    staleTime: 1000 * 60 * 5,
  })
}

export function useCreateCondition() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (condition: Partial<FHIRCondition>) => fhirService.createCondition(condition),
    onSuccess: (data) => {
      const patientId = data.subject?.reference?.split('/').pop()
      if (patientId) {
        queryClient.invalidateQueries({ queryKey: ['fhir', 'conditions', patientId] })
      }
      toast.success('Condition added')
    },
    onError: () => toast.error('Failed to add condition'),
  })
}

// ─── Medications ──────────────────────────────────────────────────────────────

export function useMedications(patientId: string | undefined, status?: string) {
  return useQuery({
    queryKey: ['fhir', 'medications', patientId, status],
    queryFn: () => fhirService.getMedications(patientId!, status),
    enabled: !!patientId,
    staleTime: 1000 * 60 * 5,
  })
}

export function useCreateMedication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (med: Partial<FHIRMedicationRequest>) =>
      fhirService.createMedicationRequest(med),
    onSuccess: (data) => {
      const patientId = data.subject?.reference?.split('/').pop()
      if (patientId) {
        queryClient.invalidateQueries({ queryKey: ['fhir', 'medications', patientId] })
      }
      toast.success('Medication added')
    },
    onError: () => toast.error('Failed to add medication'),
  })
}

// ─── Diagnostic Reports ───────────────────────────────────────────────────────

export function useDiagnosticReports(patientId: string | undefined, dateFrom?: string) {
  return useQuery({
    queryKey: ['fhir', 'reports', patientId, dateFrom],
    queryFn: () => fhirService.getDiagnosticReports(patientId!, dateFrom),
    enabled: !!patientId,
    staleTime: 1000 * 60 * 5,
  })
}

// ─── Appointments ─────────────────────────────────────────────────────────────

export function useAppointments(patientId: string | undefined, status?: string) {
  return useQuery({
    queryKey: ['fhir', 'appointments', patientId, status],
    queryFn: () => fhirService.getAppointments(patientId!, status),
    enabled: !!patientId,
    staleTime: 1000 * 60,
  })
}

export function useCreateAppointment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (appt: Partial<FHIRAppointment>) => fhirService.createAppointment(appt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fhir', 'appointments'] })
      toast.success('Appointment scheduled')
    },
    onError: () => toast.error('Failed to schedule appointment'),
  })
}

// ─── Care Plans ──────────────────────────────────────────────────────────────

export function useCarePlans(patientId: string | undefined, status?: string) {
  return useQuery({
    queryKey: ['fhir', 'care-plans', patientId, status],
    queryFn: () => fhirService.getCarePlans(patientId!, status),
    enabled: !!patientId,
    staleTime: 1000 * 60 * 2,
  })
}

// ─── Patient Everything ───────────────────────────────────────────────────────

export function usePatientEverything(patientId: string | undefined) {
  return useQuery({
    queryKey: ['fhir', 'patient-everything', patientId],
    queryFn: () => fhirService.getPatientEverything(patientId!),
    enabled: !!patientId,
    staleTime: 1000 * 60 * 10,
  })
}

// ─── FHIR utility helpers ──────────────────────────────────────────────────────

export const fhirUtils = {
  getPatientDisplayName: fhirService.getPatientDisplayName,
  getPatientAge: fhirService.getPatientAge,
  getObservationValue: fhirService.getObservationValue,
  getMRN: fhirService.getMRN,
}
