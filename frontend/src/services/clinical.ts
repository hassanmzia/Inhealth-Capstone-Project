import api from './api'

// ─── Dashboard Stats ─────────────────────────────────────────────────────────

export async function getDashboardStats() {
  const res = await api.get('/dashboard/stats/')
  return res.data
}

export async function getNurseDashboardStats() {
  const res = await api.get('/dashboard/nurse-stats/')
  return res.data
}

export async function getResearcherDashboard() {
  const res = await api.get('/dashboard/researcher/')
  return res.data
}

export async function getAppointments(params?: Record<string, unknown>) {
  const res = await api.get('/appointments/', { params })
  return res.data
}

// ─── Patient (clinician-facing) ──────────────────────────────────────────────

export async function getPatients(params?: Record<string, unknown>) {
  const res = await api.get('/patients/', { params })
  return res.data
}

export async function getPatient(id: string) {
  const res = await api.get(`/patients/${id}/`)
  return res.data
}

export async function createPatient(data: Record<string, unknown>) {
  const res = await api.post('/patients/', data)
  return res.data
}

export async function updatePatient(id: string, data: Record<string, unknown>) {
  const res = await api.put(`/patients/${id}/`, data)
  return res.data
}

export async function getPatientDemographics(patientId: string) {
  const res = await api.get(`/patients/${patientId}/demographics/`)
  return res.data
}

export async function getPatientEngagement(patientId: string) {
  const res = await api.get(`/patients/${patientId}/engagement/`)
  return res.data
}

export async function getPatientDevices(patientId: string) {
  const res = await api.get(`/patients/${patientId}/devices/`)
  return res.data
}

export async function registerDevice(patientId: string, data: Record<string, unknown>) {
  const res = await api.post(`/patients/${patientId}/devices/`, data)
  return res.data
}

// ─── Patient Self-Service ────────────────────────────────────────────────────

export async function getPatientHealthSummary() {
  const res = await api.get('/patient/health-summary/')
  return res.data
}

// ─── Clinical (Encounters, Care Gaps, Order Sets) ────────────────────────────

export async function getEncounters(params?: Record<string, unknown>) {
  const res = await api.get('/clinical/encounters/', { params })
  return res.data
}

export async function createEncounter(data: Record<string, unknown>) {
  const res = await api.post('/clinical/encounters/', data)
  return res.data
}

export async function getEncounter(id: string) {
  const res = await api.get(`/clinical/encounters/${id}/`)
  return res.data
}

export async function getCareGaps(params?: Record<string, unknown>) {
  const res = await api.get('/clinical/care-gaps/', { params })
  return res.data
}

export async function getOrderSets(params?: Record<string, unknown>) {
  const res = await api.get('/clinical/order-sets/', { params })
  return res.data
}

export async function createOrderSet(data: Record<string, unknown>) {
  const res = await api.post('/clinical/order-sets/', data)
  return res.data
}

// ─── Notifications ───────────────────────────────────────────────────────────

export async function getNotifications(params?: Record<string, unknown>) {
  const res = await api.get('/notifications/', { params })
  return res.data
}

export async function markNotificationRead(id: string) {
  const res = await api.put(`/notifications/${id}/`, { is_read: true })
  return res.data
}

// ─── Billing ─────────────────────────────────────────────────────────────────

export async function getClaims(params?: Record<string, unknown>) {
  const res = await api.get('/billing/claims/', { params })
  return res.data
}

export async function createClaim(data: Record<string, unknown>) {
  const res = await api.post('/billing/claims/', data)
  return res.data
}

export async function getRPMEpisodes(params?: Record<string, unknown>) {
  const res = await api.get('/billing/rpm/', { params })
  return res.data
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export async function getCohorts(params?: Record<string, unknown>) {
  const res = await api.get('/analytics/cohorts/', { params })
  return res.data
}

export async function createCohort(data: Record<string, unknown>) {
  const res = await api.post('/analytics/cohorts/', data)
  return res.data
}

export async function getRiskScores(params?: Record<string, unknown>) {
  const res = await api.get('/analytics/risk-scores/', { params })
  return res.data
}

export async function getKPIs(params?: Record<string, unknown>) {
  const res = await api.get('/analytics/kpis/', { params })
  return res.data
}

export async function getPopulationHealth() {
  const res = await api.get('/analytics/population/')
  return res.data
}

// ─── Research ────────────────────────────────────────────────────────────────

export async function getResearchQueries(params?: Record<string, unknown>) {
  const res = await api.get('/research/queries/', { params })
  return res.data
}

export async function createResearchQuery(data: Record<string, unknown>) {
  const res = await api.post('/research/queries/', data)
  return res.data
}

export async function getClinicalTrials(params?: Record<string, unknown>) {
  const res = await api.get('/research/trials/', { params })
  return res.data
}

export async function getMedicalEvidence(params?: Record<string, unknown>) {
  const res = await api.get('/research/evidence/', { params })
  return res.data
}

// ─── SDOH ────────────────────────────────────────────────────────────────────

export async function getSDOHAssessments(params?: Record<string, unknown>) {
  const res = await api.get('/sdoh/', { params })
  return res.data
}

export async function createSDOHAssessment(data: Record<string, unknown>) {
  const res = await api.post('/sdoh/', data)
  return res.data
}

// ─── Telemedicine ────────────────────────────────────────────────────────────

export async function getVideoSessions(params?: Record<string, unknown>) {
  const res = await api.get('/telemedicine/sessions/', { params })
  return res.data
}

export async function createVideoSession(data: Record<string, unknown>) {
  const res = await api.post('/telemedicine/sessions/', data)
  return res.data
}

// ─── Tenant / Org ────────────────────────────────────────────────────────────

export async function getCurrentOrganization() {
  const res = await api.get('/tenants/current/')
  return res.data
}

export async function getTenantConfig() {
  const res = await api.get('/tenants/current/config/')
  return res.data
}

export async function updateTenantConfig(data: Record<string, unknown>) {
  const res = await api.put('/tenants/current/config/', data)
  return res.data
}

export async function getOrganizations(params?: Record<string, unknown>) {
  const res = await api.get('/tenants/organizations/', { params })
  return res.data
}

export async function getAPIKeys() {
  const res = await api.get('/tenants/api-keys/')
  return res.data
}

export async function createAPIKey(data: Record<string, unknown>) {
  const res = await api.post('/tenants/api-keys/', data)
  return res.data
}

// ─── Auth & Profile ──────────────────────────────────────────────────────────

export async function getProfile() {
  const res = await api.get('/auth/profile/')
  return res.data
}

export async function updateProfile(data: Record<string, unknown>) {
  const res = await api.put('/auth/profile/', data)
  return res.data
}

export async function changePassword(data: { old_password: string; new_password: string }) {
  const res = await api.post('/auth/change-password/', data)
  return res.data
}

export async function setupMFA() {
  const res = await api.post('/auth/mfa/setup/')
  return res.data
}

export async function verifyMFA(code: string) {
  const res = await api.post('/auth/mfa/verify/', { code })
  return res.data
}

export async function disableMFA() {
  const res = await api.post('/auth/mfa/disable/')
  return res.data
}

export async function getAuditLogs(params?: Record<string, unknown>) {
  const res = await api.get('/auth/audit-logs/', { params })
  return res.data
}

// ─── A2A Bridge ──────────────────────────────────────────────────────────────

export async function sendA2AMessage(data: Record<string, unknown>) {
  const res = await api.post('/a2a/send/', data)
  return res.data
}

export async function broadcastA2AMessage(data: Record<string, unknown>) {
  const res = await api.post('/a2a/broadcast/', data)
  return res.data
}
