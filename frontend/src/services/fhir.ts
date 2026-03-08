import { fhirApi } from './api'
import type {
  FHIRPatient,
  FHIRObservation,
  FHIRCondition,
  FHIRMedicationRequest,
  FHIRDiagnosticReport,
  FHIRAppointment,
  FHIREncounter,
  FHIRAllergyIntolerance,
  FHIRBundle,
  FHIRSearchResult,
} from '@/types/fhir'

// ─── Pagination params ────────────────────────────────────────────────────────

export interface FHIRSearchParams {
  _count?: number
  _offset?: number
  _sort?: string
  _include?: string
  [key: string]: string | number | undefined
}

// ─── Patient ──────────────────────────────────────────────────────────────────

export async function getAllPatients(params?: FHIRSearchParams): Promise<FHIRSearchResult<FHIRPatient>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRPatient>>('/Patient', { params })
  return response.data
}

export async function getPatient(patientId: string): Promise<FHIRPatient> {
  const response = await fhirApi.get<FHIRPatient>(`/Patient/${patientId}`)
  return response.data
}

export async function searchPatients(query: string): Promise<FHIRSearchResult<FHIRPatient>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRPatient>>('/Patient', {
    params: { name: query, _count: 20 },
  })
  return response.data
}

export async function createPatient(patient: Partial<FHIRPatient>): Promise<FHIRPatient> {
  const response = await fhirApi.post<FHIRPatient>('/Patient', patient)
  return response.data
}

export async function updatePatient(patientId: string, patient: Partial<FHIRPatient>): Promise<FHIRPatient> {
  const response = await fhirApi.put<FHIRPatient>(`/Patient/${patientId}`, patient)
  return response.data
}

// ─── Observations / Vital Signs ───────────────────────────────────────────────

export async function getObservations(
  patientId: string,
  params?: FHIRSearchParams & {
    category?: string
    code?: string
    date?: string
    '_date-start'?: string
    '_date-end'?: string
  },
): Promise<FHIRSearchResult<FHIRObservation>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRObservation>>('/Observation', {
    params: {
      patient: patientId,
      _sort: '-date',
      _count: 100,
      ...params,
    },
  })
  return response.data
}

export async function getVitalSigns(
  patientId: string,
  dateFrom?: string,
  dateTo?: string,
): Promise<FHIRSearchResult<FHIRObservation>> {
  return getObservations(patientId, {
    category: 'vital-signs',
    date: dateFrom ? `ge${dateFrom}` : undefined,
    ...(dateTo ? { 'date-end': dateTo } : {}),
    _count: 200,
  })
}

export async function getLabResults(
  patientId: string,
  dateFrom?: string,
): Promise<FHIRSearchResult<FHIRObservation>> {
  return getObservations(patientId, {
    category: 'laboratory',
    date: dateFrom ? `ge${dateFrom}` : undefined,
    _count: 200,
  })
}

export async function getGlucoseReadings(
  patientId: string,
  hours = 24,
): Promise<FHIRSearchResult<FHIRObservation>> {
  const since = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString()
  return getObservations(patientId, {
    code: '41653-7,2339-0', // CGM + glucose LOINC codes
    date: `ge${since}`,
    _count: 500,
  })
}

export async function createObservation(obs: Partial<FHIRObservation>): Promise<FHIRObservation> {
  const response = await fhirApi.post<FHIRObservation>('/Observation', obs)
  return response.data
}

// ─── Conditions ───────────────────────────────────────────────────────────────

export async function getConditions(
  patientId: string,
  clinicalStatus?: 'active' | 'resolved' | 'inactive',
): Promise<FHIRSearchResult<FHIRCondition>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRCondition>>('/Condition', {
    params: {
      patient: patientId,
      'clinical-status': clinicalStatus ?? 'active',
      _sort: '-onset-date',
      _count: 50,
    },
  })
  return response.data
}

export async function createCondition(condition: Partial<FHIRCondition>): Promise<FHIRCondition> {
  const response = await fhirApi.post<FHIRCondition>('/Condition', condition)
  return response.data
}

// ─── Medications ──────────────────────────────────────────────────────────────

export async function getMedications(
  patientId: string,
  status?: string,
): Promise<FHIRSearchResult<FHIRMedicationRequest>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRMedicationRequest>>('/MedicationRequest', {
    params: {
      patient: patientId,
      status: status ?? 'active',
      _sort: '-authored-on',
      _count: 100,
    },
  })
  return response.data
}

export async function createMedicationRequest(
  med: Partial<FHIRMedicationRequest>,
): Promise<FHIRMedicationRequest> {
  const response = await fhirApi.post<FHIRMedicationRequest>('/MedicationRequest', med)
  return response.data
}

export async function updateMedicationRequest(
  id: string,
  med: Partial<FHIRMedicationRequest>,
): Promise<FHIRMedicationRequest> {
  const response = await fhirApi.put<FHIRMedicationRequest>(`/MedicationRequest/${id}`, med)
  return response.data
}

// ─── Diagnostic Reports ───────────────────────────────────────────────────────

export async function getDiagnosticReports(
  patientId: string,
  dateFrom?: string,
): Promise<FHIRSearchResult<FHIRDiagnosticReport>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRDiagnosticReport>>('/DiagnosticReport', {
    params: {
      patient: patientId,
      date: dateFrom ? `ge${dateFrom}` : undefined,
      _sort: '-date',
      _count: 50,
    },
  })
  return response.data
}

// ─── Appointments ─────────────────────────────────────────────────────────────

export async function getAppointments(
  patientId: string,
  status?: string,
): Promise<FHIRSearchResult<FHIRAppointment>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRAppointment>>('/Appointment', {
    params: {
      patient: patientId,
      status: status ?? 'booked',
      _sort: 'date',
      _count: 20,
    },
  })
  return response.data
}

export async function createAppointment(appt: Partial<FHIRAppointment>): Promise<FHIRAppointment> {
  const response = await fhirApi.post<FHIRAppointment>('/Appointment', appt)
  return response.data
}

// ─── Encounters ───────────────────────────────────────────────────────────────

export async function getEncounters(
  patientId: string,
  dateFrom?: string,
): Promise<FHIRSearchResult<FHIREncounter>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIREncounter>>('/Encounter', {
    params: {
      patient: patientId,
      date: dateFrom ? `ge${dateFrom}` : undefined,
      _sort: '-date',
      _count: 50,
    },
  })
  return response.data
}

// ─── Allergies ────────────────────────────────────────────────────────────────

export async function getAllergies(
  patientId: string,
): Promise<FHIRSearchResult<FHIRAllergyIntolerance>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRAllergyIntolerance>>(
    '/AllergyIntolerance',
    { params: { patient: patientId, _count: 50 } },
  )
  return response.data
}

// ─── Care Plans ──────────────────────────────────────────────────────────────

export interface FHIRCarePlan {
  resourceType: 'CarePlan'
  id: string
  fhir_id: string
  patient_fhir_id?: string
  status: 'draft' | 'active' | 'on-hold' | 'revoked' | 'completed'
  intent: 'proposal' | 'plan' | 'order' | 'option'
  title: string
  description: string
  category: string
  goals: Array<{
    description: string
    priority: string
    status: string
    start_date?: string
  }>
  activities: Array<{
    detail: string
    status: string
    source?: string
    evidence_level?: string
    created_from_recommendation?: string
  }>
  period_start?: string
  period_end?: string
  created: string
  ai_generated: boolean
  ai_model_used?: string
  author_id?: string
  note?: string
}

export async function getCarePlans(
  patientId: string,
  status?: string,
): Promise<FHIRSearchResult<FHIRCarePlan>> {
  const response = await fhirApi.get<FHIRSearchResult<FHIRCarePlan>>('/CarePlan', {
    params: {
      patient: patientId,
      ...(status ? { status } : {}),
      _count: 50,
    },
  })
  return response.data
}

// ─── Patient Summary (everything bundle) ──────────────────────────────────────

export async function getPatientEverything(
  patientId: string,
): Promise<FHIRBundle> {
  const response = await fhirApi.get<FHIRBundle>(`/Patient/${patientId}/$everything`, {
    params: { _count: 200 },
  })
  return response.data
}

// ─── FHIR Utilities ───────────────────────────────────────────────────────────

export function getPatientDisplayName(patient: FHIRPatient): string {
  const name = patient.name?.[0]
  if (!name) return 'Unknown Patient'
  if (name.text) return name.text
  const given = name.given?.join(' ') ?? ''
  const family = name.family ?? ''
  return [given, family].filter(Boolean).join(' ') || 'Unknown Patient'
}

export function getPatientAge(patient: FHIRPatient): number {
  if (!patient.birthDate) return 0
  const birth = new Date(patient.birthDate)
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const m = today.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
  return age
}

export function getObservationValue(obs: FHIRObservation): string {
  if (obs.valueQuantity) {
    return `${obs.valueQuantity.value} ${obs.valueQuantity.unit ?? ''}`
  }
  if (obs.valueCodeableConcept?.text) return obs.valueCodeableConcept.text
  if (obs.valueString) return obs.valueString
  if (obs.valueBoolean !== undefined) return obs.valueBoolean ? 'Yes' : 'No'
  // BP panel — look at components
  if (obs.component) {
    return obs.component
      .map((c) => `${c.valueQuantity?.value ?? '?'} ${c.valueQuantity?.unit ?? ''}`)
      .join(' / ')
  }
  return '—'
}

export function getMRN(patient: FHIRPatient): string {
  const mrnIdentifier = patient.identifier?.find(
    (id) =>
      id.type?.coding?.some((c) => c.code === 'MR') ||
      id.system?.includes('mrn') ||
      id.use === 'usual',
  )
  return mrnIdentifier?.value ?? patient.id ?? '—'
}
