import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Pill,
  AlertTriangle,
  ChevronDown,
  Clock,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import type { Medication, MedicationInteraction } from '@/types/clinical'
import { cn } from '@/lib/utils'

interface MedicationListProps {
  medications: Medication[]
  showInteractions?: boolean
  showAdherence?: boolean
}

const ADHERENCE_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  adherent: { label: 'Adherent', color: 'text-secondary-600 dark:text-secondary-400', icon: CheckCircle2 },
  partial: { label: 'Partial', color: 'text-warning-600 dark:text-warning-400', icon: AlertCircle },
  non_adherent: { label: 'Non-Adherent', color: 'text-danger-600 dark:text-danger-400', icon: XCircle },
  unknown: { label: 'Unknown', color: 'text-muted-foreground', icon: AlertCircle },
}

const INTERACTION_SEVERITY = {
  contraindicated: { label: 'Contraindicated', bg: 'bg-danger-100 dark:bg-danger-900/30', text: 'text-danger-700 dark:text-danger-400', dot: 'bg-danger-500' },
  major: { label: 'Major', bg: 'bg-danger-50 dark:bg-danger-900/20', text: 'text-danger-600 dark:text-danger-400', dot: 'bg-danger-400' },
  moderate: { label: 'Moderate', bg: 'bg-warning-50 dark:bg-warning-900/20', text: 'text-warning-700 dark:text-warning-400', dot: 'bg-warning-400' },
  minor: { label: 'Minor', bg: 'bg-clinical-50 dark:bg-clinical-800', text: 'text-clinical-600 dark:text-clinical-400', dot: 'bg-clinical-400' },
}

export default function MedicationList({
  medications,
  showInteractions = true,
  showAdherence = true,
}: MedicationListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const activeMeds = medications.filter((m) => m.status === 'active')
  const inactiveMeds = medications.filter((m) => m.status !== 'active')

  const allInteractions = medications.flatMap((m) => m.interactions ?? [])
  const criticalInteractions = allInteractions.filter(
    (i) => i.severity === 'contraindicated' || i.severity === 'major',
  )

  return (
    <div className="space-y-4">
      {/* Interaction banner */}
      {showInteractions && criticalInteractions.length > 0 && (
        <div className="flex items-start gap-3 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-xl">
          <AlertTriangle className="w-4 h-4 text-danger-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-danger-700 dark:text-danger-400">
              {criticalInteractions.length} Critical Drug Interaction{criticalInteractions.length !== 1 ? 's' : ''}
            </p>
            <p className="text-xs text-danger-600 dark:text-danger-400 mt-0.5">
              Review medications carefully before prescribing
            </p>
          </div>
        </div>
      )}

      {/* Active medications */}
      <div>
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
          Active ({activeMeds.length})
        </h4>
        <div className="space-y-2">
          {activeMeds.map((med) => (
            <MedicationRow
              key={med.id}
              medication={med}
              expanded={expandedId === med.id}
              onToggle={() => setExpandedId(expandedId === med.id ? null : med.id)}
              showInteractions={showInteractions}
              showAdherence={showAdherence}
            />
          ))}
        </div>
      </div>

      {/* Inactive medications */}
      {inactiveMeds.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Inactive / Discontinued ({inactiveMeds.length})
          </h4>
          <div className="space-y-2 opacity-60">
            {inactiveMeds.slice(0, 3).map((med) => (
              <MedicationRow
                key={med.id}
                medication={med}
                expanded={false}
                onToggle={() => {}}
                showInteractions={false}
                showAdherence={false}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Medication Row ───────────────────────────────────────────────────────────

function MedicationRow({
  medication: med,
  expanded,
  onToggle,
  showInteractions,
  showAdherence,
}: {
  medication: Medication
  expanded: boolean
  onToggle: () => void
  showInteractions: boolean
  showAdherence: boolean
}) {
  const adherenceConfig = ADHERENCE_CONFIG[med.adherenceStatus ?? 'unknown']
  const AdherenceIcon = adherenceConfig.icon
  const maxInteractionSeverity = med.interactions?.reduce<keyof typeof INTERACTION_SEVERITY | null>((max, i) => {
    const order = ['contraindicated', 'major', 'moderate', 'minor'] as const
    if (!max) return i.severity as keyof typeof INTERACTION_SEVERITY
    return order.indexOf(i.severity as keyof typeof INTERACTION_SEVERITY) < order.indexOf(max) ? i.severity as keyof typeof INTERACTION_SEVERITY : max
  }, null)

  const needsRefill = med.nextRefillDate && new Date(med.nextRefillDate) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-card">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent/30 transition-colors"
      >
        {/* Icon */}
        <div className="w-8 h-8 rounded-lg bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center flex-shrink-0">
          <Pill className="w-4 h-4 text-primary-600 dark:text-primary-400" />
        </div>

        {/* Drug info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-foreground">{med.name}</p>
            {med.isControlledSubstance && (
              <span className="text-[10px] font-bold text-purple-600 bg-purple-50 dark:bg-purple-900/20 px-1.5 rounded">
                CII
              </span>
            )}
            {maxInteractionSeverity && showInteractions && (
              <span className={cn(
                'text-[10px] font-semibold px-1.5 py-0.5 rounded flex items-center gap-1',
                INTERACTION_SEVERITY[maxInteractionSeverity].bg,
                INTERACTION_SEVERITY[maxInteractionSeverity].text,
              )}>
                <AlertTriangle className="w-2.5 h-2.5" />
                {INTERACTION_SEVERITY[maxInteractionSeverity].label}
              </span>
            )}
            {needsRefill && (
              <span className="text-[10px] font-semibold text-warning-600 bg-warning-50 dark:bg-warning-900/20 px-1.5 py-0.5 rounded flex items-center gap-1">
                <RefreshCw className="w-2.5 h-2.5" />
                Refill Soon
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {med.dose} {med.doseUnit} · {med.frequency} · {med.route}
            {med.indication && ` · For ${med.indication}`}
          </p>
        </div>

        {/* Adherence */}
        {showAdherence && med.adherenceStatus && (
          <div className={cn('flex items-center gap-1 text-xs font-medium flex-shrink-0', adherenceConfig.color)}>
            <AdherenceIcon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{adherenceConfig.label}</span>
          </div>
        )}

        <ChevronDown className={cn('w-4 h-4 text-muted-foreground flex-shrink-0 transition-transform', expanded && 'rotate-180')} />
      </button>

      {/* Expanded */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-border space-y-3">
              <div className="grid grid-cols-2 gap-x-6 gap-y-1 pt-3 text-xs">
                <InfoRow label="Generic Name" value={med.genericName} />
                <InfoRow label="Prescribed" value={med.prescribedDate ? format(new Date(med.prescribedDate), 'MMM d, yyyy') : undefined} />
                <InfoRow label="Prescriber" value={med.prescribedBy} />
                {med.pdc !== undefined && (
                  <InfoRow label="PDC Score" value={`${(med.pdc * 100).toFixed(0)}%`} />
                )}
                {med.lastFillDate && (
                  <InfoRow label="Last Fill" value={format(new Date(med.lastFillDate), 'MMM d, yyyy')} />
                )}
                {med.nextRefillDate && (
                  <InfoRow
                    label="Next Refill"
                    value={format(new Date(med.nextRefillDate), 'MMM d, yyyy')}
                    highlight={!!needsRefill}
                  />
                )}
                {med.refillsRemaining !== undefined && (
                  <InfoRow label="Refills Left" value={String(med.refillsRemaining)} />
                )}
                {med.tierLevel && (
                  <InfoRow label="Formulary Tier" value={`Tier ${med.tierLevel}`} />
                )}
              </div>

              {/* Interactions */}
              {showInteractions && med.interactions && med.interactions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-foreground mb-2">Interactions:</p>
                  <div className="space-y-1.5">
                    {med.interactions.map((interaction, i) => (
                      <InteractionRow key={i} interaction={interaction} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function InfoRow({ label, value, highlight }: { label: string; value?: string; highlight?: boolean }) {
  if (!value) return null
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-muted-foreground w-24 flex-shrink-0">{label}:</span>
      <span className={cn('font-medium text-foreground', highlight && 'text-warning-600 dark:text-warning-400')}>
        {value}
      </span>
    </div>
  )
}

function InteractionRow({ interaction }: { interaction: MedicationInteraction }) {
  const config = INTERACTION_SEVERITY[interaction.severity]
  return (
    <div className={cn('p-2 rounded-lg text-xs', config.bg)}>
      <div className="flex items-start gap-2">
        <span className={cn('w-2 h-2 rounded-full mt-0.5 flex-shrink-0', config.dot)} />
        <div>
          <p className={cn('font-semibold', config.text)}>
            {interaction.drug1} ↔ {interaction.drug2} ({config.label})
          </p>
          <p className={cn('mt-0.5', config.text, 'opacity-80')}>{interaction.recommendation}</p>
        </div>
      </div>
    </div>
  )
}
