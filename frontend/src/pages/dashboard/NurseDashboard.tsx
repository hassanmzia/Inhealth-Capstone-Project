import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Stethoscope,
  Heart,
  AlertTriangle,
  Users,
  Clock,
  Activity,
  Thermometer,
  Droplets,
  Wind,
  ClipboardList,
  Phone,
  CalendarCheck,
} from 'lucide-react'
import api from '@/services/api'
import { useAlertStore } from '@/store/alertStore'

interface NurseStats {
  assigned_patients: number
  critical_alerts: number
  vitals_due: number
  tasks_pending: number
  patients_seen_today: number
  care_gaps_open: number
}

interface VitalTask {
  id: string
  patient_name: string
  patient_id: string
  vital_type: string
  last_reading: string
  last_value: string
  status: 'due' | 'overdue' | 'critical'
  room?: string
}

interface PatientRound {
  id: string
  patient_name: string
  patient_id: string
  room: string
  conditions: string[]
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  last_vitals: string
  next_medication: string
  notes: string
}

const riskColors: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

const vitalStatusColors: Record<string, string> = {
  due: 'text-yellow-600',
  overdue: 'text-orange-600',
  critical: 'text-red-600',
}

const vitalIcons: Record<string, React.ElementType> = {
  'Blood Pressure': Heart,
  'Heart Rate': Activity,
  'Temperature': Thermometer,
  'SpO2': Wind,
  'Blood Glucose': Droplets,
}

// Placeholder data
const placeholderVitalTasks: VitalTask[] = [
  { id: 'v1', patient_name: 'Maria Santos', patient_id: 'p1', vital_type: 'Blood Pressure', last_reading: '2h ago', last_value: '148/92 mmHg', status: 'overdue', room: '302A' },
  { id: 'v2', patient_name: 'James Chen', patient_id: 'p2', vital_type: 'Blood Glucose', last_reading: '4h ago', last_value: '285 mg/dL', status: 'critical', room: '304B' },
  { id: 'v3', patient_name: 'Eleanor Brown', patient_id: 'p3', vital_type: 'Temperature', last_reading: '1h ago', last_value: '101.2°F', status: 'critical', room: '301A' },
  { id: 'v4', patient_name: 'Robert Kim', patient_id: 'p4', vital_type: 'SpO2', last_reading: '30m ago', last_value: '94%', status: 'due', room: '305A' },
  { id: 'v5', patient_name: 'Aisha Patel', patient_id: 'p5', vital_type: 'Heart Rate', last_reading: '3h ago', last_value: '110 bpm', status: 'overdue', room: '303B' },
  { id: 'v6', patient_name: 'Fatima Ali', patient_id: 'p6', vital_type: 'Blood Pressure', last_reading: '45m ago', last_value: '120/78 mmHg', status: 'due', room: '306A' },
]

const placeholderRounds: PatientRound[] = [
  { id: 'r1', patient_name: 'James Chen', patient_id: 'p2', room: '304B', conditions: ['T2 Diabetes', 'CKD'], risk_level: 'critical', last_vitals: '4h ago', next_medication: 'Insulin 30U in 1h', notes: 'Blood glucose trending high, needs sliding scale check' },
  { id: 'r2', patient_name: 'Eleanor Brown', patient_id: 'p3', room: '301A', conditions: ['Heart Failure', 'Afib'], risk_level: 'high', last_vitals: '1h ago', next_medication: 'Metoprolol 50mg in 2h', notes: 'Low-grade fever, monitor closely' },
  { id: 'r3', patient_name: 'Maria Santos', patient_id: 'p1', room: '302A', conditions: ['Hypertension', 'T2 Diabetes'], risk_level: 'high', last_vitals: '2h ago', next_medication: 'Amlodipine 10mg in 30m', notes: 'BP still elevated, check after medication' },
  { id: 'r4', patient_name: 'Robert Kim', patient_id: 'p4', room: '305A', conditions: ['COPD', 'Anxiety'], risk_level: 'medium', last_vitals: '30m ago', next_medication: 'Albuterol PRN', notes: 'SpO2 borderline, encourage deep breathing' },
  { id: 'r5', patient_name: 'Aisha Patel', patient_id: 'p5', room: '303B', conditions: ['T1 Diabetes', 'Neuropathy'], risk_level: 'medium', last_vitals: '3h ago', next_medication: 'Gabapentin 300mg in 3h', notes: 'Elevated HR, likely anxiety' },
  { id: 'r6', patient_name: 'Fatima Ali', patient_id: 'p6', room: '306A', conditions: ['CKD Stage 3'], risk_level: 'low', last_vitals: '45m ago', next_medication: 'None due', notes: 'Stable, ready for discharge discussion' },
]

export default function NurseDashboard() {
  const { criticalCount } = useAlertStore()

  const { data: nurseStats } = useQuery({
    queryKey: ['nurse-stats'],
    queryFn: async () => {
      try {
        const res = await api.get<NurseStats>('/dashboard/nurse-stats/')
        return res.data
      } catch {
        return null
      }
    },
    retry: false,
  })

  const stats = nurseStats ?? {
    assigned_patients: placeholderRounds.length,
    critical_alerts: criticalCount || 3,
    vitals_due: placeholderVitalTasks.filter(v => v.status !== 'due').length,
    tasks_pending: 8,
    patients_seen_today: 4,
    care_gaps_open: 6,
  }

  const summaryCards = [
    { label: 'My Patients', value: stats.assigned_patients, icon: Users, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { label: 'Critical Alerts', value: stats.critical_alerts, icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20' },
    { label: 'Vitals Overdue', value: stats.vitals_due, icon: Clock, color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/20' },
    { label: 'Tasks Pending', value: stats.tasks_pending, icon: ClipboardList, color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/20' },
  ]

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Stethoscope className="w-7 h-7 text-primary-500" />
            Nurse Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Patient rounds, vital sign monitoring, and care coordination
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/vitals" className="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2">
            <Activity className="w-4 h-4" /> Live Vitals
          </Link>
          <Link to="/alerts" className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2 relative">
            <AlertTriangle className="w-4 h-4" /> Alerts
            {stats.critical_alerts > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-white text-red-600 text-[10px] font-bold rounded-full flex items-center justify-center">
                {stats.critical_alerts}
              </span>
            )}
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

      {/* Vital Sign Tasks */}
      <div className="bg-card rounded-xl border border-border">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="font-semibold text-foreground flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-500" />
            Vital Sign Collection Queue
          </h2>
          <span className="text-xs text-muted-foreground">
            {placeholderVitalTasks.filter(v => v.status === 'critical').length} critical &middot; {placeholderVitalTasks.filter(v => v.status === 'overdue').length} overdue
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-border">
          {placeholderVitalTasks.map((task) => {
            const VitalIcon = vitalIcons[task.vital_type] || Activity
            return (
              <div key={task.id} className="bg-card p-4 hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      task.status === 'critical' ? 'bg-red-100 dark:bg-red-900/30' :
                      task.status === 'overdue' ? 'bg-orange-100 dark:bg-orange-900/30' :
                      'bg-blue-100 dark:bg-blue-900/30'
                    }`}>
                      <VitalIcon className={`w-5 h-5 ${vitalStatusColors[task.status]}`} />
                    </div>
                    <div>
                      <Link to={`/patients/${task.patient_id}`} className="font-medium text-sm text-primary-600 hover:underline">
                        {task.patient_name}
                      </Link>
                      <p className="text-xs text-muted-foreground">Room {task.room}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    task.status === 'critical' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' :
                    task.status === 'overdue' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' :
                    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                  }`}>
                    {task.status}
                  </span>
                </div>
                <div className="mt-2 ml-13">
                  <p className="text-sm"><span className="text-muted-foreground">{task.vital_type}:</span> {task.last_value}</p>
                  <p className="text-xs text-muted-foreground">Last reading: {task.last_reading}</p>
                </div>
                <button className="mt-2 w-full text-xs px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                  Record Vitals
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* Patient Rounds */}
      <div className="bg-card rounded-xl border border-border">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="font-semibold text-foreground flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-purple-500" />
            Patient Rounds
          </h2>
          <p className="text-xs text-muted-foreground">{stats.patients_seen_today} of {stats.assigned_patients} seen today</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left p-3 font-medium text-muted-foreground">Patient</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Room</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Conditions</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Risk</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Last Vitals</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Next Medication</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Notes</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {placeholderRounds.map((pt) => (
                <tr key={pt.id} className="hover:bg-muted/50 transition-colors">
                  <td className="p-3">
                    <Link to={`/patients/${pt.patient_id}`} className="font-medium text-primary-600 hover:underline">
                      {pt.patient_name}
                    </Link>
                  </td>
                  <td className="p-3 text-muted-foreground">{pt.room}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-1">
                      {pt.conditions.map(c => (
                        <span key={c} className="text-xs bg-muted px-1.5 py-0.5 rounded">{c}</span>
                      ))}
                    </div>
                  </td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${riskColors[pt.risk_level]}`}>
                      {pt.risk_level}
                    </span>
                  </td>
                  <td className="p-3 text-muted-foreground text-xs">{pt.last_vitals}</td>
                  <td className="p-3 text-xs">{pt.next_medication}</td>
                  <td className="p-3 text-xs text-muted-foreground max-w-[200px] truncate" title={pt.notes}>{pt.notes}</td>
                  <td className="p-3">
                    <div className="flex gap-1">
                      <Link to={`/patients/${pt.patient_id}`} className="text-xs px-2 py-1 bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 rounded hover:bg-primary-200 transition-colors">
                        View
                      </Link>
                      <Link to="/vitals" className="text-xs px-2 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 rounded hover:bg-green-200 transition-colors">
                        Vitals
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Record Vitals', icon: Activity, href: '/vitals', desc: 'Enter vital signs' },
          { label: 'Care Gaps', icon: ClipboardList, href: '/clinical-workspace', desc: `${stats.care_gaps_open} open gaps` },
          { label: 'Call Provider', icon: Phone, href: '/telemedicine', desc: 'Contact physician' },
          { label: 'Appointments', icon: CalendarCheck, href: '/clinical-workspace', desc: "Today's schedule" },
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
