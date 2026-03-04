// FHIR R4 TypeScript Type Definitions
// Based on HL7 FHIR R4 specification

export type FHIRResourceType =
  | 'Patient'
  | 'Observation'
  | 'Condition'
  | 'MedicationRequest'
  | 'DiagnosticReport'
  | 'Appointment'
  | 'Encounter'
  | 'Procedure'
  | 'AllergyIntolerance'
  | 'CarePlan'
  | 'Goal'
  | 'Immunization'
  | 'ServiceRequest'
  | 'DocumentReference'
  | 'Organization'
  | 'Practitioner'
  | 'PractitionerRole'
  | 'Bundle'
  | 'OperationOutcome'

// ─── Primitives ──────────────────────────────────────────────────────────────

export type FHIRDateTime = string   // ISO 8601
export type FHIRDate = string       // YYYY-MM-DD
export type FHIRTime = string       // HH:MM:SS
export type FHIRInstant = string    // ISO 8601 with timezone
export type FHIRCode = string
export type FHIRUri = string
export type FHIRUrl = string
export type FHIRId = string
export type FHIRDecimal = number
export type FHIRPositiveInt = number
export type FHIRUnsignedInt = number
export type FHIRBoolean = boolean
export type FHIRString = string
export type FHIRMarkdown = string

// ─── Data Types ───────────────────────────────────────────────────────────────

export interface FHIRCoding {
  system?: FHIRUri
  version?: FHIRString
  code?: FHIRCode
  display?: FHIRString
  userSelected?: FHIRBoolean
}

export interface FHIRCodeableConcept {
  coding?: FHIRCoding[]
  text?: FHIRString
}

export interface FHIRIdentifier {
  use?: 'usual' | 'official' | 'temp' | 'secondary' | 'old'
  type?: FHIRCodeableConcept
  system?: FHIRUri
  value?: FHIRString
  period?: FHIRPeriod
  assigner?: FHIRReference
}

export interface FHIRHumanName {
  use?: 'usual' | 'official' | 'temp' | 'nickname' | 'anonymous' | 'old' | 'maiden'
  text?: FHIRString
  family?: FHIRString
  given?: FHIRString[]
  prefix?: FHIRString[]
  suffix?: FHIRString[]
  period?: FHIRPeriod
}

export interface FHIRAddress {
  use?: 'home' | 'work' | 'temp' | 'old' | 'billing'
  type?: 'postal' | 'physical' | 'both'
  text?: FHIRString
  line?: FHIRString[]
  city?: FHIRString
  district?: FHIRString
  state?: FHIRString
  postalCode?: FHIRString
  country?: FHIRString
  period?: FHIRPeriod
}

export interface FHIRContactPoint {
  system?: 'phone' | 'fax' | 'email' | 'pager' | 'url' | 'sms' | 'other'
  value?: FHIRString
  use?: 'home' | 'work' | 'temp' | 'old' | 'mobile'
  rank?: FHIRPositiveInt
  period?: FHIRPeriod
}

export interface FHIRPeriod {
  start?: FHIRDateTime
  end?: FHIRDateTime
}

export interface FHIRRange {
  low?: FHIRQuantity
  high?: FHIRQuantity
}

export interface FHIRQuantity {
  value?: FHIRDecimal
  comparator?: '<' | '<=' | '>=' | '>'
  unit?: FHIRString
  system?: FHIRUri
  code?: FHIRCode
}

export interface FHIRRatio {
  numerator?: FHIRQuantity
  denominator?: FHIRQuantity
}

export interface FHIRReference {
  reference?: FHIRString
  type?: FHIRUri
  identifier?: FHIRIdentifier
  display?: FHIRString
}

export interface FHIRAnnotation {
  authorReference?: FHIRReference
  authorString?: FHIRString
  time?: FHIRDateTime
  text: FHIRMarkdown
}

export interface FHIRAttachment {
  contentType?: FHIRCode
  language?: FHIRCode
  data?: FHIRString  // base64
  url?: FHIRUrl
  size?: FHIRUnsignedInt
  hash?: FHIRString
  title?: FHIRString
  creation?: FHIRDateTime
}

export interface FHIRDosage {
  sequence?: FHIRPositiveInt
  text?: FHIRString
  additionalInstruction?: FHIRCodeableConcept[]
  patientInstruction?: FHIRString
  timing?: FHIRTiming
  asNeededBoolean?: FHIRBoolean
  asNeededCodeableConcept?: FHIRCodeableConcept
  site?: FHIRCodeableConcept
  route?: FHIRCodeableConcept
  method?: FHIRCodeableConcept
  doseAndRate?: Array<{
    type?: FHIRCodeableConcept
    doseRange?: FHIRRange
    doseQuantity?: FHIRQuantity
    rateRatio?: FHIRRatio
    rateRange?: FHIRRange
    rateQuantity?: FHIRQuantity
  }>
  maxDosePerPeriod?: FHIRRatio
  maxDosePerAdministration?: FHIRQuantity
  maxDosePerLifetime?: FHIRQuantity
}

export interface FHIRTiming {
  event?: FHIRDateTime[]
  repeat?: {
    boundsDuration?: FHIRQuantity
    boundsRange?: FHIRRange
    boundsPeriod?: FHIRPeriod
    count?: FHIRPositiveInt
    countMax?: FHIRPositiveInt
    duration?: FHIRDecimal
    durationMax?: FHIRDecimal
    durationUnit?: 's' | 'min' | 'h' | 'd' | 'wk' | 'mo' | 'a'
    frequency?: FHIRPositiveInt
    frequencyMax?: FHIRPositiveInt
    period?: FHIRDecimal
    periodMax?: FHIRDecimal
    periodUnit?: 's' | 'min' | 'h' | 'd' | 'wk' | 'mo' | 'a'
    dayOfWeek?: FHIRCode[]
    timeOfDay?: FHIRTime[]
    when?: FHIRCode[]
    offset?: FHIRUnsignedInt
  }
  code?: FHIRCodeableConcept
}

// ─── Base Resource ────────────────────────────────────────────────────────────

export interface FHIRResource {
  resourceType: FHIRResourceType
  id?: FHIRId
  meta?: {
    versionId?: FHIRId
    lastUpdated?: FHIRInstant
    source?: FHIRUri
    profile?: FHIRUri[]
    security?: FHIRCoding[]
    tag?: FHIRCoding[]
  }
  implicitRules?: FHIRUri
  language?: FHIRCode
}

// ─── Patient ──────────────────────────────────────────────────────────────────

export interface FHIRPatient extends FHIRResource {
  resourceType: 'Patient'
  identifier?: FHIRIdentifier[]
  active?: FHIRBoolean
  name?: FHIRHumanName[]
  telecom?: FHIRContactPoint[]
  gender?: 'male' | 'female' | 'other' | 'unknown'
  birthDate?: FHIRDate
  deceasedBoolean?: FHIRBoolean
  deceasedDateTime?: FHIRDateTime
  address?: FHIRAddress[]
  maritalStatus?: FHIRCodeableConcept
  multipleBirthBoolean?: FHIRBoolean
  multipleBirthInteger?: number
  photo?: FHIRAttachment[]
  contact?: Array<{
    relationship?: FHIRCodeableConcept[]
    name?: FHIRHumanName
    telecom?: FHIRContactPoint[]
    address?: FHIRAddress
    gender?: 'male' | 'female' | 'other' | 'unknown'
    organization?: FHIRReference
    period?: FHIRPeriod
  }>
  communication?: Array<{
    language: FHIRCodeableConcept
    preferred?: FHIRBoolean
  }>
  generalPractitioner?: FHIRReference[]
  managingOrganization?: FHIRReference
  link?: Array<{
    other: FHIRReference
    type: 'replaced-by' | 'replaces' | 'refer' | 'seealso'
  }>
  // Extension: MRN for display
  mrn?: string
}

// ─── Observation ──────────────────────────────────────────────────────────────

export type ObservationStatus = 'registered' | 'preliminary' | 'final' | 'amended' | 'corrected' | 'cancelled' | 'entered-in-error' | 'unknown'

export interface FHIRObservation extends FHIRResource {
  resourceType: 'Observation'
  identifier?: FHIRIdentifier[]
  basedOn?: FHIRReference[]
  partOf?: FHIRReference[]
  status: ObservationStatus
  category?: FHIRCodeableConcept[]
  code: FHIRCodeableConcept
  subject?: FHIRReference
  focus?: FHIRReference[]
  encounter?: FHIRReference
  effectiveDateTime?: FHIRDateTime
  effectivePeriod?: FHIRPeriod
  effectiveTiming?: FHIRTiming
  effectiveInstant?: FHIRInstant
  issued?: FHIRInstant
  performer?: FHIRReference[]
  valueQuantity?: FHIRQuantity
  valueCodeableConcept?: FHIRCodeableConcept
  valueString?: FHIRString
  valueBoolean?: FHIRBoolean
  valueInteger?: number
  valueRange?: FHIRRange
  valueRatio?: FHIRRatio
  valueSampledData?: Record<string, unknown>
  valueTime?: FHIRTime
  valueDateTime?: FHIRDateTime
  valuePeriod?: FHIRPeriod
  dataAbsentReason?: FHIRCodeableConcept
  interpretation?: FHIRCodeableConcept[]
  note?: FHIRAnnotation[]
  bodySite?: FHIRCodeableConcept
  method?: FHIRCodeableConcept
  specimen?: FHIRReference
  device?: FHIRReference
  referenceRange?: Array<{
    low?: FHIRQuantity
    high?: FHIRQuantity
    type?: FHIRCodeableConcept
    appliesTo?: FHIRCodeableConcept[]
    age?: FHIRRange
    text?: FHIRString
  }>
  hasMember?: FHIRReference[]
  derivedFrom?: FHIRReference[]
  component?: Array<{
    code: FHIRCodeableConcept
    valueQuantity?: FHIRQuantity
    valueCodeableConcept?: FHIRCodeableConcept
    valueString?: FHIRString
    valueBoolean?: FHIRBoolean
    valueInteger?: number
    valueRange?: FHIRRange
    valueRatio?: FHIRRatio
    valueSampledData?: Record<string, unknown>
    valueTime?: FHIRTime
    valueDateTime?: FHIRDateTime
    valuePeriod?: FHIRPeriod
    dataAbsentReason?: FHIRCodeableConcept
    interpretation?: FHIRCodeableConcept[]
    referenceRange?: Array<{
      low?: FHIRQuantity
      high?: FHIRQuantity
      type?: FHIRCodeableConcept
    }>
  }>
}

// ─── Condition ────────────────────────────────────────────────────────────────

export interface FHIRCondition extends FHIRResource {
  resourceType: 'Condition'
  identifier?: FHIRIdentifier[]
  clinicalStatus?: FHIRCodeableConcept
  verificationStatus?: FHIRCodeableConcept
  category?: FHIRCodeableConcept[]
  severity?: FHIRCodeableConcept
  code?: FHIRCodeableConcept
  bodySite?: FHIRCodeableConcept[]
  subject: FHIRReference
  encounter?: FHIRReference
  onsetDateTime?: FHIRDateTime
  onsetAge?: FHIRQuantity
  onsetPeriod?: FHIRPeriod
  onsetRange?: FHIRRange
  onsetString?: FHIRString
  abatementDateTime?: FHIRDateTime
  abatementAge?: FHIRQuantity
  abatementPeriod?: FHIRPeriod
  abatementRange?: FHIRRange
  abatementString?: FHIRString
  recordedDate?: FHIRDateTime
  recorder?: FHIRReference
  asserter?: FHIRReference
  stage?: Array<{
    summary?: FHIRCodeableConcept
    assessment?: FHIRReference[]
    type?: FHIRCodeableConcept
  }>
  evidence?: Array<{
    code?: FHIRCodeableConcept[]
    detail?: FHIRReference[]
  }>
  note?: FHIRAnnotation[]
}

// ─── MedicationRequest ────────────────────────────────────────────────────────

export type MedicationRequestStatus = 'active' | 'on-hold' | 'cancelled' | 'completed' | 'entered-in-error' | 'stopped' | 'draft' | 'unknown'
export type MedicationRequestIntent = 'proposal' | 'plan' | 'order' | 'original-order' | 'reflex-order' | 'filler-order' | 'instance-order' | 'option'

export interface FHIRMedicationRequest extends FHIRResource {
  resourceType: 'MedicationRequest'
  identifier?: FHIRIdentifier[]
  status: MedicationRequestStatus
  statusReason?: FHIRCodeableConcept
  intent: MedicationRequestIntent
  category?: FHIRCodeableConcept[]
  priority?: 'routine' | 'urgent' | 'asap' | 'stat'
  doNotPerform?: FHIRBoolean
  reportedBoolean?: FHIRBoolean
  reportedReference?: FHIRReference
  medicationCodeableConcept?: FHIRCodeableConcept
  medicationReference?: FHIRReference
  subject: FHIRReference
  encounter?: FHIRReference
  supportingInformation?: FHIRReference[]
  authoredOn?: FHIRDateTime
  requester?: FHIRReference
  performer?: FHIRReference
  performerType?: FHIRCodeableConcept
  recorder?: FHIRReference
  reasonCode?: FHIRCodeableConcept[]
  reasonReference?: FHIRReference[]
  instantiatesCanonical?: string[]
  instantiatesUri?: FHIRUri[]
  basedOn?: FHIRReference[]
  groupIdentifier?: FHIRIdentifier
  courseOfTherapyType?: FHIRCodeableConcept
  insurance?: FHIRReference[]
  note?: FHIRAnnotation[]
  dosageInstruction?: FHIRDosage[]
  dispenseRequest?: {
    initialFill?: {
      quantity?: FHIRQuantity
      duration?: FHIRQuantity
    }
    dispenseInterval?: FHIRQuantity
    validityPeriod?: FHIRPeriod
    numberOfRepeatsAllowed?: FHIRUnsignedInt
    quantity?: FHIRQuantity
    expectedSupplyDuration?: FHIRQuantity
    performer?: FHIRReference
  }
  substitution?: {
    allowedBoolean?: FHIRBoolean
    allowedCodeableConcept?: FHIRCodeableConcept
    reason?: FHIRCodeableConcept
  }
  priorPrescription?: FHIRReference
  detectedIssue?: FHIRReference[]
  eventHistory?: FHIRReference[]
}

// ─── DiagnosticReport ─────────────────────────────────────────────────────────

export type DiagnosticReportStatus = 'registered' | 'partial' | 'preliminary' | 'final' | 'amended' | 'corrected' | 'appended' | 'cancelled' | 'entered-in-error' | 'unknown'

export interface FHIRDiagnosticReport extends FHIRResource {
  resourceType: 'DiagnosticReport'
  identifier?: FHIRIdentifier[]
  basedOn?: FHIRReference[]
  status: DiagnosticReportStatus
  category?: FHIRCodeableConcept[]
  code: FHIRCodeableConcept
  subject?: FHIRReference
  encounter?: FHIRReference
  effectiveDateTime?: FHIRDateTime
  effectivePeriod?: FHIRPeriod
  issued?: FHIRInstant
  performer?: FHIRReference[]
  resultsInterpreter?: FHIRReference[]
  specimen?: FHIRReference[]
  result?: FHIRReference[]
  imagingStudy?: FHIRReference[]
  media?: Array<{
    comment?: FHIRString
    link: FHIRReference
  }>
  conclusion?: FHIRString
  conclusionCode?: FHIRCodeableConcept[]
  presentedForm?: FHIRAttachment[]
}

// ─── Appointment ──────────────────────────────────────────────────────────────

export type AppointmentStatus = 'proposed' | 'pending' | 'booked' | 'arrived' | 'fulfilled' | 'cancelled' | 'noshow' | 'entered-in-error' | 'checked-in' | 'waitlist'

export interface FHIRAppointment extends FHIRResource {
  resourceType: 'Appointment'
  identifier?: FHIRIdentifier[]
  status: AppointmentStatus
  cancelationReason?: FHIRCodeableConcept
  serviceCategory?: FHIRCodeableConcept[]
  serviceType?: FHIRCodeableConcept[]
  specialty?: FHIRCodeableConcept[]
  appointmentType?: FHIRCodeableConcept
  reasonCode?: FHIRCodeableConcept[]
  reasonReference?: FHIRReference[]
  priority?: FHIRUnsignedInt
  description?: FHIRString
  supportingInformation?: FHIRReference[]
  start?: FHIRInstant
  end?: FHIRInstant
  minutesDuration?: FHIRPositiveInt
  slot?: FHIRReference[]
  created?: FHIRDateTime
  comment?: FHIRString
  patientInstruction?: FHIRString
  basedOn?: FHIRReference[]
  participant: Array<{
    type?: FHIRCodeableConcept[]
    actor?: FHIRReference
    required?: 'required' | 'optional' | 'information-only'
    status: 'accepted' | 'declined' | 'tentative' | 'needs-action'
    period?: FHIRPeriod
  }>
  requestedPeriod?: FHIRPeriod[]
}

// ─── Encounter ────────────────────────────────────────────────────────────────

export type EncounterStatus = 'planned' | 'arrived' | 'triaged' | 'in-progress' | 'onleave' | 'finished' | 'cancelled' | 'entered-in-error' | 'unknown'

export interface FHIREncounter extends FHIRResource {
  resourceType: 'Encounter'
  identifier?: FHIRIdentifier[]
  status: EncounterStatus
  statusHistory?: Array<{
    status: EncounterStatus
    period: FHIRPeriod
  }>
  class: FHIRCoding
  classHistory?: Array<{
    class: FHIRCoding
    period: FHIRPeriod
  }>
  type?: FHIRCodeableConcept[]
  serviceType?: FHIRCodeableConcept
  priority?: FHIRCodeableConcept
  subject?: FHIRReference
  episodeOfCare?: FHIRReference[]
  basedOn?: FHIRReference[]
  participant?: Array<{
    type?: FHIRCodeableConcept[]
    period?: FHIRPeriod
    individual?: FHIRReference
  }>
  appointment?: FHIRReference[]
  period?: FHIRPeriod
  length?: FHIRQuantity
  reasonCode?: FHIRCodeableConcept[]
  reasonReference?: FHIRReference[]
  diagnosis?: Array<{
    condition: FHIRReference
    use?: FHIRCodeableConcept
    rank?: FHIRPositiveInt
  }>
  account?: FHIRReference[]
  hospitalization?: {
    preAdmissionIdentifier?: FHIRIdentifier
    origin?: FHIRReference
    admitSource?: FHIRCodeableConcept
    reAdmission?: FHIRCodeableConcept
    dietPreference?: FHIRCodeableConcept[]
    specialCourtesy?: FHIRCodeableConcept[]
    specialArrangement?: FHIRCodeableConcept[]
    destination?: FHIRReference
    dischargeDisposition?: FHIRCodeableConcept
  }
  location?: Array<{
    location: FHIRReference
    status?: 'planned' | 'active' | 'reserved' | 'completed'
    physicalType?: FHIRCodeableConcept
    period?: FHIRPeriod
  }>
  serviceProvider?: FHIRReference
  partOf?: FHIRReference
}

// ─── AllergyIntolerance ───────────────────────────────────────────────────────

export interface FHIRAllergyIntolerance extends FHIRResource {
  resourceType: 'AllergyIntolerance'
  identifier?: FHIRIdentifier[]
  clinicalStatus?: FHIRCodeableConcept
  verificationStatus?: FHIRCodeableConcept
  type?: 'allergy' | 'intolerance'
  category?: Array<'food' | 'medication' | 'environment' | 'biologic'>
  criticality?: 'low' | 'high' | 'unable-to-assess'
  code?: FHIRCodeableConcept
  patient: FHIRReference
  encounter?: FHIRReference
  onsetDateTime?: FHIRDateTime
  onsetAge?: FHIRQuantity
  onsetPeriod?: FHIRPeriod
  onsetRange?: FHIRRange
  onsetString?: FHIRString
  recordedDate?: FHIRDateTime
  recorder?: FHIRReference
  asserter?: FHIRReference
  lastOccurrence?: FHIRDateTime
  note?: FHIRAnnotation[]
  reaction?: Array<{
    substance?: FHIRCodeableConcept
    manifestation: FHIRCodeableConcept[]
    description?: FHIRString
    onset?: FHIRDateTime
    severity?: 'mild' | 'moderate' | 'severe'
    exposureRoute?: FHIRCodeableConcept
    note?: FHIRAnnotation[]
  }>
}

// ─── FHIR Bundle ─────────────────────────────────────────────────────────────

export interface FHIRBundle<T extends FHIRResource = FHIRResource> extends FHIRResource {
  resourceType: 'Bundle'
  identifier?: FHIRIdentifier
  type: 'document' | 'message' | 'transaction' | 'transaction-response' | 'batch' | 'batch-response' | 'history' | 'searchset' | 'collection'
  timestamp?: FHIRInstant
  total?: FHIRUnsignedInt
  link?: Array<{
    relation: FHIRString
    url: FHIRUri
  }>
  entry?: Array<{
    link?: Array<{ relation: FHIRString; url: FHIRUri }>
    fullUrl?: FHIRUri
    resource?: T
    search?: {
      mode?: 'match' | 'include' | 'outcome'
      score?: FHIRDecimal
    }
    request?: {
      method: 'GET' | 'HEAD' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
      url: FHIRUri
      ifNoneMatch?: FHIRString
      ifModifiedSince?: FHIRInstant
      ifMatch?: FHIRString
      ifNoneExist?: FHIRString
    }
    response?: {
      status: FHIRString
      location?: FHIRUri
      etag?: FHIRString
      lastModified?: FHIRInstant
      outcome?: FHIRResource
    }
  }>
  signature?: Record<string, unknown>
}

// ─── Helper type for FHIR API responses ──────────────────────────────────────

export interface FHIRSearchResult<T extends FHIRResource> {
  resourceType: 'Bundle'
  type: 'searchset'
  total: number
  entry: Array<{
    resource: T
    fullUrl: string
  }>
}

// ─── LOINC Codes (common vitals) ─────────────────────────────────────────────

export const LOINC = {
  HEART_RATE: '8867-4',
  BLOOD_PRESSURE_SYSTOLIC: '8480-6',
  BLOOD_PRESSURE_DIASTOLIC: '8462-4',
  BLOOD_PRESSURE_PANEL: '85354-9',
  SPO2: '2708-6',
  BODY_TEMPERATURE: '8310-5',
  BODY_WEIGHT: '29463-7',
  BODY_HEIGHT: '8302-2',
  BMI: '39156-5',
  RESPIRATORY_RATE: '9279-1',
  GLUCOSE: '2339-0',
  CGM_GLUCOSE: '41653-7',
  HBA1C: '4548-4',
  CREATININE: '2160-0',
  EGFR: '33914-3',
  CHOLESTEROL_TOTAL: '2093-3',
  CHOLESTEROL_LDL: '2089-1',
  CHOLESTEROL_HDL: '2085-9',
  TRIGLYCERIDES: '2571-8',
} as const

// ─── SNOMED CT common codes ───────────────────────────────────────────────────

export const SNOMED = {
  DIABETES_TYPE2: '44054006',
  HYPERTENSION: '38341003',
  HEART_FAILURE: '84114007',
  COPD: '13645005',
  CKD: '709044004',
  ATRIAL_FIBRILLATION: '49436004',
  DEPRESSION: '35489007',
  OBESITY: '414916001',
} as const
