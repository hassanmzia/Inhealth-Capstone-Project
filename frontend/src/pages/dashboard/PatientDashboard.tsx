import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Heart,
  Activity,
  Pill,
  Calendar,
  Trophy,
  Flame,
  Target,
  MessageSquare,
  Sparkles,
  CheckCircle2,
} from 'lucide-react'
import { format } from 'date-fns'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { ease: [0.4, 0, 0.2, 1] } } }

export default function PatientDashboard() {
  const { user } = useAuthStore()

  const { data: healthData } = useQuery({
    queryKey: ['patient-health-summary'],
    queryFn: () => api.get('/patient/health-summary/').then((r) => r.data),
  })

  const h = healthData ?? null
  const scoreColor = (h?.healthScore ?? 0) >= 80 ? '#22c55e' : (h?.healthScore ?? 0) >= 60 ? '#3b82f6' : (h?.healthScore ?? 0) >= 40 ? '#f59e0b' : '#e11d48'

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-[1400px] mx-auto">
      {/* Welcome */}
      <motion.div variants={ITEM} className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Hello, {user?.firstName}!
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {format(new Date(), 'EEEE, MMMM d')} · Let's check on your health today
          </p>
        </div>
        {h?.streakDays > 0 && (
          <div className="flex items-center gap-2.5 px-4 py-2.5 bg-gradient-to-r from-warning-500 to-orange-500 rounded-xl text-white shadow-lg shadow-warning-500/20">
            <Flame className="w-5 h-5" />
            <div>
              <p className="text-sm font-bold">{h.streakDays} Day Streak!</p>
              <p className="text-[10px] text-white/80">Keep it up!</p>
            </div>
          </div>
        )}
      </motion.div>

      {/* Health score + quick stats */}
      <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        {/* Health score — hero card */}
        <div className="col-span-2 sm:col-span-1 clinical-card flex flex-col items-center text-center relative overflow-hidden">
          <div className="absolute inset-0 opacity-[0.04]" style={{ background: `radial-gradient(circle at 50% 30%, ${scoreColor}, transparent 70%)` }} />
          <div className="relative w-24 h-24 sm:w-28 sm:h-28">
            <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
              <circle cx="18" cy="18" r="15.915" fill="none" stroke="hsl(var(--muted))" strokeWidth="2" />
              <motion.circle
                cx="18" cy="18" r="15.915" fill="none"
                stroke={scoreColor}
                strokeWidth="2.5"
                strokeDasharray={`${h?.healthScore ?? 0} 100`}
                strokeLinecap="round"
                initial={{ strokeDasharray: '0 100' }}
                animate={{ strokeDasharray: `${h?.healthScore ?? 0} 100` }}
                transition={{ duration: 1.2, ease: 'easeOut' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold text-foreground tracking-tight">{h?.healthScore ?? 0}</span>
              <span className="text-[10px] text-muted-foreground font-medium">/ 100</span>
            </div>
          </div>
          <p className="text-sm font-bold text-foreground mt-2">Health Score</p>
          <p className="text-[10px] text-muted-foreground">Based on your latest data</p>
        </div>

        {/* Quick vitals — gradient cards */}
        {[
          { label: 'Blood Pressure', value: h?.todayVitals?.bloodPressure ?? '—', unit: 'mmHg', icon: Activity, gradient: 'from-primary-500 to-primary-700' },
          { label: 'Heart Rate', value: h?.todayVitals?.heartRate ?? '—', unit: 'bpm', icon: Heart, gradient: 'from-danger-500 to-danger-700' },
          { label: 'Glucose', value: h?.todayVitals?.glucose ?? '—', unit: 'mg/dL', icon: Target, gradient: 'from-secondary-500 to-secondary-700' },
        ].map((v) => (
          <div key={v.label} className={cn('relative overflow-hidden rounded-2xl p-4 sm:p-5 text-white bg-gradient-to-br transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5', v.gradient)}>
            <div className="absolute -right-3 -top-3 w-16 h-16 rounded-full bg-white/10" />
            <v.icon className="w-4 h-4 mb-2 text-white/80" />
            <p className="text-2xl font-bold font-mono tracking-tight">{v.value}</p>
            <p className="text-[10px] text-white/70 mt-0.5">{v.unit}</p>
            <p className="text-xs text-white/80 mt-1 font-medium">{v.label}</p>
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Goals */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center gap-2 mb-5">
            <div className="p-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20">
              <Target className="w-4 h-4 text-primary-500" />
            </div>
            <h2 className="text-sm font-bold text-foreground">Health Goals</h2>
          </div>
          <div className="space-y-5">
            {(h?.goals ?? []).map((goal: { title: string; progress: number; unit: string; current: number; target: number; category: string }, i: number) => (
              <GoalProgress key={i} goal={goal} />
            ))}
          </div>
        </motion.div>

        {/* Medication adherence calendar */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-secondary-50 dark:bg-secondary-900/20">
                <Pill className="w-4 h-4 text-secondary-500" />
              </div>
              <h2 className="text-sm font-bold text-foreground">Medication Adherence</h2>
            </div>
            <span className="text-sm font-bold text-secondary-600 dark:text-secondary-400 font-mono">
              {h?.medicationAdherence ?? 0}%
            </span>
          </div>
          <AdherenceCalendar data={h?.adherenceCalendar ?? []} />
        </motion.div>

        {/* AI Health Tips */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center gap-2 mb-5">
            <div className="p-1.5 rounded-lg bg-gradient-to-br from-primary-500/20 to-purple-500/20">
              <Sparkles className="w-4 h-4 text-primary-500" />
            </div>
            <h2 className="text-sm font-bold text-foreground">AI Health Tips</h2>
          </div>
          <div className="space-y-3">
            {(h?.tips ?? []).map((tip: { icon: string; text: string }, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3.5 bg-gradient-to-r from-primary-50/60 to-purple-50/40 dark:from-primary-900/10 dark:to-purple-900/10 rounded-xl border border-primary-100/60 dark:border-primary-900/30">
                <div className="p-1 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex-shrink-0">
                  <Sparkles className="w-3.5 h-3.5 text-primary-500" />
                </div>
                <p className="text-sm text-foreground leading-relaxed">{tip.text}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Next appointment + messages */}
        <motion.div variants={ITEM} className="space-y-4">
          {h?.nextAppointment && (
            <div className="clinical-card border-l-4 border-l-primary-500 relative overflow-hidden">
              <div className="absolute -right-6 -top-6 w-24 h-24 rounded-full bg-primary-500/5" />
              <div className="relative">
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20">
                    <Calendar className="w-4 h-4 text-primary-500" />
                  </div>
                  <h3 className="text-sm font-bold text-foreground">Upcoming Appointment</h3>
                </div>
                <p className="text-base font-semibold text-foreground">
                  {format(new Date(h.nextAppointment), 'EEEE, MMMM d')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {format(new Date(h.nextAppointment), 'h:mm a')} · Dr. Johnson · Diabetes Follow-up
                </p>
                <button className="mt-3 text-xs font-semibold text-primary-600 hover:text-primary-700 dark:text-primary-400 transition-colors">
                  Add to calendar →
                </button>
              </div>
            </div>
          )}

          <div className="clinical-card">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20">
                <MessageSquare className="w-4 h-4 text-primary-500" />
              </div>
              <h3 className="text-sm font-bold text-foreground">Messages</h3>
            </div>
            <div className="space-y-2">
              {(h?.messages ?? []).map((msg: { from: string; time: string; preview: string }, i: number) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl hover:bg-accent/50 transition-colors cursor-pointer">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-sm">
                    {msg.from[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold text-foreground">{msg.from}</p>
                      <p className="text-[10px] text-muted-foreground">{msg.time}</p>
                    </div>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{msg.preview}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {h?.badges?.length > 0 && (
            <div className="clinical-card">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-1.5 rounded-lg bg-warning-50 dark:bg-warning-900/20">
                  <Trophy className="w-4 h-4 text-warning-500" />
                </div>
                <h3 className="text-sm font-bold text-foreground">Achievements</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {h.badges.map((badge: string, i: number) => (
                  <span key={i} className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-warning-50 to-orange-50 dark:from-warning-900/20 dark:to-orange-900/20 border border-warning-200/60 dark:border-warning-800/60 rounded-xl text-xs font-semibold text-warning-700 dark:text-warning-400">
                    <Trophy className="w-3.5 h-3.5" />
                    {badge}
                  </span>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  )
}

function GoalProgress({ goal }: { goal: { title: string; progress: number; current: number; target: number; unit: string } }) {
  const isComplete = goal.progress >= 100
  const barColor = isComplete ? 'from-secondary-400 to-secondary-600' : goal.progress >= 70 ? 'from-primary-400 to-primary-600' : goal.progress >= 40 ? 'from-warning-400 to-warning-600' : 'from-danger-400 to-danger-600'

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-foreground">{goal.title}</span>
        <div className="flex items-center gap-1.5">
          {isComplete && <CheckCircle2 className="w-4 h-4 text-secondary-500" />}
          <span className={cn('text-sm font-mono font-bold', isComplete ? 'text-secondary-600 dark:text-secondary-400' : 'text-foreground')}>
            {goal.progress}%
          </span>
        </div>
      </div>
      <div className="h-2.5 bg-muted/80 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(goal.progress, 100)}%` }}
          transition={{ duration: 1, ease: [0.4, 0, 0.2, 1] }}
          className={cn('h-full rounded-full bg-gradient-to-r', barColor)}
        />
      </div>
      <p className="text-[11px] text-muted-foreground mt-1.5">
        {goal.current} / {goal.target} {goal.unit}
      </p>
    </div>
  )
}

function AdherenceCalendar({ data }: { data: Array<{ date: string; taken: boolean }> }) {
  const days = data.slice(-30)

  return (
    <div>
      <div className="grid grid-cols-10 gap-1.5">
        {days.map((day, i) => (
          <div
            key={i}
            className={cn(
              'aspect-square rounded-lg flex items-center justify-center transition-all duration-200 hover:scale-110 cursor-default',
              day.taken
                ? 'bg-gradient-to-br from-secondary-400 to-secondary-600 shadow-sm shadow-secondary-500/20'
                : 'bg-danger-200/60 dark:bg-danger-900/30',
            )}
            title={`${format(new Date(day.date), 'MMM d')}: ${day.taken ? 'Taken' : 'Missed'}`}
          >
            {day.taken && <CheckCircle2 className="w-2.5 h-2.5 text-white" />}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 mt-4 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <div className="w-3.5 h-3.5 rounded bg-gradient-to-br from-secondary-400 to-secondary-600" />
          <span>Taken</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3.5 h-3.5 rounded bg-danger-200/60 dark:bg-danger-900/30" />
          <span>Missed</span>
        </div>
      </div>
    </div>
  )
}

