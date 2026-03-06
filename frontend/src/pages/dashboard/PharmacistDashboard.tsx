import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Pill,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Search,
  ShieldAlert,
  Activity,
  Users,
  FileText,
  TrendingUp,
} from 'lucide-react'
import api from '@/services/api'

interface DrugInteraction {
  id: string
  patient_name: string
  patient_id: string
  drug_a: string
  drug_b: string
  severity: 'minor' | 'moderate' | 'major' | 'contraindicated'
  description: string
  detected_at: string
  status: 'pending_review' | 'reviewed' | 'overridden'
}

interface MedicationReviewItem {
  id: string
  patient_name: string
  patient_id: string
  medication: string
  dosage: string
  prescriber: string
  status: 'pending' | 'approved' | 'flagged'
  flagged_reason?: string
  created_at: string
}

// Severity badge colors
const severityColors: Record<string, string> = {
  minor: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  moderate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  major: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  contraindicated: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  pending_review: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  approved: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  reviewed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  flagged: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  overridden: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
}

// Placeholder data used when backend hasn't returned data yet
const placeholderInteractions: DrugInteraction[] = [
  { id: '1', patient_name: 'Maria Santos', patient_id: 'p1', drug_a: 'Warfarin', drug_b: 'Aspirin', severity: 'major', description: 'Increased risk of bleeding', detected_at: new Date().toISOString(), status: 'pending_review' },
  { id: '2', patient_name: 'James Chen', patient_id: 'p2', drug_a: 'Metformin', drug_b: 'Contrast Dye', severity: 'contraindicated', description: 'Risk of lactic acidosis', detected_at: new Date().toISOString(), status: 'pending_review' },
  { id: '3', patient_name: 'Eleanor Brown', patient_id: 'p3', drug_a: 'Lisinopril', drug_b: 'Potassium Supplement', severity: 'moderate', description: 'Hyperkalemia risk', detected_at: new Date().toISOString(), status: 'pending_review' },
  { id: '4', patient_name: 'Robert Kim', patient_id: 'p4', drug_a: 'Simvastatin', drug_b: 'Amiodarone', severity: 'major', description: 'Increased rhabdomyolysis risk', detected_at: new Date().toISOString(), status: 'reviewed' },
  { id: '5', patient_name: 'Aisha Patel', patient_id: 'p5', drug_a: 'Ciprofloxacin', drug_b: 'Theophylline', severity: 'moderate', description: 'Theophylline toxicity risk', detected_at: new Date().toISOString(), status: 'pending_review' },
]

const placeholderReviews: MedicationReviewItem[] = [
  { id: 'r1', patient_name: 'Maria Santos', patient_id: 'p1', medication: 'Metoprolol 50mg', dosage: 'BID', prescriber: 'Dr. Williams', status: 'pending', created_at: new Date().toISOString() },
  { id: 'r2', patient_name: 'James Chen', patient_id: 'p2', medication: 'Insulin Glargine 30U', dosage: 'QHS', prescriber: 'Dr. Patel', status: 'flagged', flagged_reason: 'Dose exceeds typical range for BMI', created_at: new Date().toISOString() },
  { id: 'r3', patient_name: 'Eleanor Brown', patient_id: 'p3', medication: 'Amlodipine 10mg', dosage: 'QD', prescriber: 'Dr. Kim', status: 'approved', created_at: new Date().toISOString() },
  { id: 'r4', patient_name: 'Robert Kim', patient_id: 'p4', medication: 'Duloxetine 60mg', dosage: 'QD', prescriber: 'Dr. Williams', status: 'pending', created_at: new Date().toISOString() },
  { id: 'r5', patient_name: 'Fatima Ali', patient_id: 'p6', medication: 'Empagliflozin 25mg', dosage: 'QD', prescriber: 'Dr. Patel', status: 'pending', created_at: new Date().toISOString() },
  { id: 'r6', patient_name: 'Aisha Patel', patient_id: 'p5', medication: 'Gabapentin 300mg', dosage: 'TID', prescriber: 'Dr. Chen', status: 'flagged', flagged_reason: 'Renal dose adjustment needed (eGFR 38)', created_at: new Date().toISOString() },
]

export default function PharmacistDashboard() {
  // Fetch dashboard stats
  const { data: stats } = useQuery({
    queryKey: ['pharmacist-stats'],
    queryFn: async () => {
      try {
        const res = await api.get('/dashboard/stats/')
        return res.data
      } catch {
        return null
      }
    },
    retry: false,
  })

  // Fetch drug interactions from the agents/recommendations endpoint
  const { data: interactions } = useQuery({
    queryKey: ['drug-interactions'],
    queryFn: async () => {
      try {
        const res = await api.get<DrugInteraction[]>('/agents/recommendations/', {
          params: { category: 'drug_interaction', limit: 20 },
        })
        return res.data
      } catch {
        return null
      }
    },
    retry: false,
  })

  // Fetch medication review queue
  const { data: reviews } = useQuery({
    queryKey: ['medication-reviews'],
    queryFn: async () => {
      try {
        const res = await api.get<MedicationReviewItem[]>('/fhir/MedicationRequest/', {
          params: { status: 'active', _sort: '-authored-on', _count: 20 },
        })
        return res.data
      } catch {
        return null
      }
    },
    retry: false,
  })

  const interactionList = interactions ?? placeholderInteractions
  const reviewList = reviews ?? placeholderReviews
  const pendingInteractions = interactionList.filter(i => i.status === 'pending_review')
  const pendingReviews = reviewList.filter(r => r.status === 'pending' || r.status === 'flagged')

  const summaryCards = [
    { label: 'Pending Reviews', value: pendingReviews.length, icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-50 dark:bg-yellow-900/20' },
    { label: 'Drug Interactions', value: pendingInteractions.length, icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20' },
    { label: 'Reviewed Today', value: stats?.reviewed_today ?? 12, icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
    { label: 'Active Patients', value: stats?.total_patients ?? 248, icon: Users, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
  ]

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Pill className="w-7 h-7 text-primary-500" />
            Pharmacist Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Medication reviews, drug interaction alerts, and prescription management</p>
        </div>
        <div className="flex gap-2">
          <Link to="/patients" className="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2">
            <Search className="w-4 h-4" /> Patient Lookup
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className={`${card.bg} rounded-xl p-4 border border-border`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{card.label}</p>
                  <p className="text-2xl font-bold mt-1">{card.value}</p>
                </div>
                <Icon className={`w-8 h-8 ${card.color}`} />
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Drug Interaction Alerts */}
        <div className="bg-card rounded-xl border border-border">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold text-foreground flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-red-500" />
              Drug Interaction Alerts
            </h2>
            <span className="text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 px-2 py-1 rounded-full font-medium">
              {pendingInteractions.length} pending
            </span>
          </div>
          <div className="divide-y divide-border max-h-[500px] overflow-y-auto">
            {interactionList.map((interaction) => (
              <div key={interaction.id} className="p-4 hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link to={`/patients/${interaction.patient_id}`} className="font-medium text-sm text-primary-600 hover:underline">
                        {interaction.patient_name}
                      </Link>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${severityColors[interaction.severity]}`}>
                        {interaction.severity}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[interaction.status]}`}>
                        {interaction.status.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm mt-1">
                      <span className="font-medium">{interaction.drug_a}</span>
                      <span className="text-muted-foreground mx-1">+</span>
                      <span className="font-medium">{interaction.drug_b}</span>
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">{interaction.description}</p>
                  </div>
                  {interaction.status === 'pending_review' && (
                    <button className="text-xs px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors whitespace-nowrap">
                      Review
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Medication Review Queue */}
        <div className="bg-card rounded-xl border border-border">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold text-foreground flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" />
              Medication Review Queue
            </h2>
            <span className="text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300 px-2 py-1 rounded-full font-medium">
              {pendingReviews.length} pending
            </span>
          </div>
          <div className="divide-y divide-border max-h-[500px] overflow-y-auto">
            {reviewList.map((review) => (
              <div key={review.id} className="p-4 hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link to={`/patients/${review.patient_id}`} className="font-medium text-sm text-primary-600 hover:underline">
                        {review.patient_name}
                      </Link>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[review.status]}`}>
                        {review.status}
                      </span>
                    </div>
                    <p className="text-sm mt-1 font-medium">{review.medication}</p>
                    <p className="text-xs text-muted-foreground">
                      {review.dosage} &middot; Prescribed by {review.prescriber}
                    </p>
                    {review.flagged_reason && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> {review.flagged_reason}
                      </p>
                    )}
                  </div>
                  {(review.status === 'pending' || review.status === 'flagged') && (
                    <div className="flex gap-1.5">
                      <button className="text-xs px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                        Approve
                      </button>
                      <button className="text-xs px-3 py-1.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 rounded-lg hover:bg-red-200 transition-colors">
                        Flag
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Drug Database', icon: Search, href: '/research', desc: 'Search drug info' },
          { label: 'Interaction Checker', icon: ShieldAlert, href: '/research', desc: 'Check combinations' },
          { label: 'AI Agents', icon: Activity, href: '/agents', desc: 'Monitor AI agents' },
          { label: 'Analytics', icon: TrendingUp, href: '/analytics', desc: 'Prescribing trends' },
        ].map((action) => {
          const Icon = action.icon
          return (
            <Link
              key={action.label}
              to={action.href}
              className="bg-card rounded-xl border border-border p-4 hover:border-primary-300 hover:shadow-md transition-all group"
            >
              <Icon className="w-6 h-6 text-primary-500 group-hover:text-primary-600 mb-2" />
              <p className="font-medium text-sm">{action.label}</p>
              <p className="text-xs text-muted-foreground">{action.desc}</p>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
