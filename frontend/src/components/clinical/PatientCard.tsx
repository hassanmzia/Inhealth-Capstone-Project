import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { User, AlertTriangle, Clock, Activity } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { PatientSummary } from '@/types/clinical'
import RiskScoreGauge, { RiskScoreBadge } from '@/components/charts/RiskScoreGauge'
import { cn } from '@/lib/utils'

interface PatientCardProps {
  patient: PatientSummary
  compact?: boolean
}

const ALERT_STATUS_STYLES: Record<string, string> = {
  critical: 'border-l-4 border-l-danger-500',
  warning: 'border-l-4 border-l-warning-500',
  normal: '',
  none: '',
}

export default function PatientCard({ patient, compact = false }: PatientCardProps) {
  const navigate = useNavigate()

  const alertStyle = ALERT_STATUS_STYLES[patient.alertStatus] ?? ''

  return (
    <motion.div
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.99 }}
      onClick={() => navigate(`/patients/${patient.id}`)}
      className={cn(
        'clinical-card cursor-pointer hover:shadow-card-hover transition-all duration-200 relative overflow-hidden',
        alertStyle,
        patient.alertStatus === 'critical' && 'animate-alert-pulse',
      )}
    >
      {/* Alert badge */}
      {patient.alertCount > 0 && (
        <div className="absolute top-3 right-3">
          <span
            className={cn(
              'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold',
              patient.alertStatus === 'critical'
                ? 'bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400'
                : 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400',
            )}
          >
            <AlertTriangle className="w-3 h-3" />
            {patient.alertCount}
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-gradient-clinical flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
          {patient.photoUrl ? (
            <img src={patient.photoUrl} alt={patient.firstName} className="w-full h-full rounded-full object-cover" />
          ) : (
            `${patient.firstName[0]}${patient.lastName[0]}`
          )}
        </div>

        {/* Name + info */}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-foreground truncate">
            {patient.firstName} {patient.lastName}
          </h3>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
            <span>{patient.age}y</span>
            <span>·</span>
            <span className="capitalize">{patient.gender}</span>
            <span>·</span>
            <span className="font-mono">{patient.mrn}</span>
          </div>
        </div>
      </div>

      {/* Conditions */}
      {!compact && patient.activeConditions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {patient.activeConditions.slice(0, 3).map((c, i) => (
            <span
              key={i}
              className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-clinical-100 dark:bg-clinical-800 text-clinical-700 dark:text-clinical-300"
              title={c.display}
            >
              {c.code} · {c.display.length > 18 ? c.display.slice(0, 16) + '...' : c.display}
            </span>
          ))}
        </div>
      )}

      {/* Risk score + stats */}
      <div className="mt-3 flex items-center gap-3">
        {patient.riskScore && (
          <div className="flex-shrink-0">
            <RiskScoreGauge score={patient.riskScore.score} size="sm" showLabel />
          </div>
        )}

        <div className="flex-1 space-y-1.5">
          {patient.openCareGaps > 0 && (
            <div className="flex items-center gap-1.5">
              <Activity className="w-3 h-3 text-warning-500 flex-shrink-0" />
              <span className="text-xs text-muted-foreground">
                <span className="font-semibold text-warning-600 dark:text-warning-400">
                  {patient.openCareGaps}
                </span>
                {' '}open care gap{patient.openCareGaps !== 1 ? 's' : ''}
              </span>
            </div>
          )}

          {patient.lastContactDate && (
            <div className="flex items-center gap-1.5">
              <Clock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
              <span className="text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(patient.lastContactDate), { addSuffix: true })}
              </span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
