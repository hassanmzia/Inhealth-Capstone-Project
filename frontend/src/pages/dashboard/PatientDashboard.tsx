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
import { format, startOfMonth, eachDayOfInterval, isSameDay, subDays } from 'date-fns'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }

export default function PatientDashboard() {
  const { user } = useAuthStore()

  const { data: healthData } = useQuery({
    queryKey: ['patient-health-summary'],
    queryFn: () => api.get('/patient/health-summary/').then((r) => r.data),
    placeholderData: {
      healthScore: 78,
      streakDays: 12,
      medicationAdherence: 92,
      nextAppointment: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      goals: [
        { title: 'Walk 7,000 steps/day', progress: 68, unit: 'steps', current: 4760, target: 7000, category: 'activity' },
        { title: 'Blood sugar in range', progress: 82, unit: '%', current: 82, target: 100, category: 'glucose' },
        { title: 'Take medications on time', progress: 92, unit: '%', current: 92, target: 100, category: 'medication' },
        { title: 'Weight goal', progress: 45, unit: 'kg', current: 88, target: 82, category: 'weight' },
      ],
      badges: ['7-Day Streak', 'Medication Star', 'Step Champion'],
      todayVitals: {
        bloodPressure: '128/82',
        heartRate: 74,
        glucose: 118,
        weight: 88.2,
      },
      tips: [
        { icon: 'heart', text: 'Your blood pressure is slightly elevated today. Try deep breathing exercises for 5 minutes.' },
        { icon: 'activity', text: 'You\'re 40% to your step goal! A 15-minute walk will make a big difference.' },
        { icon: 'pill', text: 'Metformin due in 2 hours. Take it with your meal for best results.' },
      ],
      adherenceCalendar: Array.from({ length: 30 }, (_, i) => ({
        date: subDays(new Date(), 29 - i).toISOString(),
        taken: Math.random() > 0.15,
      })),
      messages: [
        { from: 'Dr. Johnson', time: '2 hours ago', preview: 'Your lab results look great! HbA1c improved to 7.1%.' },
        { from: 'Nurse Sarah', time: 'Yesterday', preview: 'Reminder: Please log your morning glucose reading.' },
      ],
    },
  })

  const h = healthData

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-4xl">
      {/* Welcome */}
      <motion.div variants={ITEM} className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Hello, {user?.firstName}! 👋
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {format(new Date(), 'EEEE, MMMM d')} · Let's check on your health today
          </p>
        </div>
        {h?.streakDays > 0 && (
          <div className="flex items-center gap-2 px-4 py-2 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-xl">
            <Flame className="w-5 h-5 text-warning-500" />
            <div>
              <p className="text-sm font-bold text-warning-700 dark:text-warning-400">{h.streakDays} Day Streak!</p>
              <p className="text-[10px] text-warning-600 dark:text-warning-500">Keep it up!</p>
            </div>
          </div>
        )}
      </motion.div>

      {/* Health score + quick stats */}
      <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Health score */}
        <div className="col-span-2 sm:col-span-1 clinical-card flex flex-col items-center text-center">
          <div className="relative w-20 h-20">
            <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
              <circle cx="18" cy="18" r="15.915" fill="none" stroke="hsl(var(--muted))" strokeWidth="2.5" />
              <circle
                cx="18" cy="18" r="15.915" fill="none"
                stroke="#1d6fdb"
                strokeWidth="2.5"
                strokeDasharray={`${h?.healthScore ?? 0} 100`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-xl font-bold text-foreground">{h?.healthScore ?? 0}</span>
            </div>
          </div>
          <p className="text-xs font-semibold text-foreground mt-2">Health Score</p>
          <p className="text-[10px] text-muted-foreground">out of 100</p>
        </div>

        {/* Quick vitals */}
        {[
          { label: 'Blood Pressure', value: h?.todayVitals?.bloodPressure ?? '—', unit: 'mmHg', icon: Activity, color: 'text-primary-500' },
          { label: 'Heart Rate', value: h?.todayVitals?.heartRate ?? '—', unit: 'bpm', icon: Heart, color: 'text-danger-500' },
          { label: 'Glucose', value: h?.todayVitals?.glucose ?? '—', unit: 'mg/dL', icon: Target, color: 'text-secondary-500' },
        ].map((v) => (
          <div key={v.label} className="clinical-card">
            <v.icon className={cn('w-4 h-4 mb-2', v.color)} />
            <p className="text-xl font-bold font-mono text-foreground">{v.value}</p>
            <p className="text-[10px] text-muted-foreground">{v.unit}</p>
            <p className="text-xs text-muted-foreground mt-1">{v.label}</p>
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Goals */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-4 h-4 text-primary-500" />
            <h2 className="text-sm font-bold text-foreground">Health Goals</h2>
          </div>
          <div className="space-y-4">
            {(h?.goals ?? []).map((goal: { title: string; progress: number; unit: string; current: number; target: number; category: string }, i: number) => (
              <GoalProgress key={i} goal={goal} />
            ))}
          </div>
        </motion.div>

        {/* Medication adherence calendar */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Pill className="w-4 h-4 text-primary-500" />
              <h2 className="text-sm font-bold text-foreground">Medication Adherence</h2>
            </div>
            <span className="text-sm font-bold text-secondary-600 dark:text-secondary-400">
              {h?.medicationAdherence ?? 0}%
            </span>
          </div>
          <AdherenceCalendar data={h?.adherenceCalendar ?? []} />
        </motion.div>

        {/* AI Health Tips */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-primary-500" />
            <h2 className="text-sm font-bold text-foreground">AI Health Tips</h2>
          </div>
          <div className="space-y-3">
            {(h?.tips ?? []).map((tip: { icon: string; text: string }, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-primary-50/60 dark:bg-primary-900/10 rounded-xl border border-primary-100 dark:border-primary-900/30">
                <Sparkles className="w-4 h-4 text-primary-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-foreground leading-relaxed">{tip.text}</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Next appointment + messages */}
        <motion.div variants={ITEM} className="space-y-4">
          {/* Next appointment */}
          {h?.nextAppointment && (
            <div className="clinical-card border-l-4 border-l-primary-500">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-4 h-4 text-primary-500" />
                <h3 className="text-sm font-bold text-foreground">Upcoming Appointment</h3>
              </div>
              <p className="text-sm text-foreground font-semibold">
                {format(new Date(h.nextAppointment), 'EEEE, MMMM d')}
              </p>
              <p className="text-xs text-muted-foreground">
                {format(new Date(h.nextAppointment), 'h:mm a')} · Dr. Johnson · Diabetes Follow-up
              </p>
              <button className="mt-3 text-xs font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400">
                Add to calendar →
              </button>
            </div>
          )}

          {/* Messages */}
          <div className="clinical-card">
            <div className="flex items-center gap-2 mb-3">
              <MessageSquare className="w-4 h-4 text-primary-500" />
              <h3 className="text-sm font-bold text-foreground">Messages</h3>
            </div>
            <div className="space-y-3">
              {(h?.messages ?? []).map((msg: { from: string; time: string; preview: string }, i: number) => (
                <div key={i} className="flex items-start gap-3 pb-3 border-b border-border last:border-0 last:pb-0">
                  <div className="w-8 h-8 rounded-full bg-gradient-clinical flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                    {msg.from[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-foreground">{msg.from}</p>
                    <p className="text-xs text-muted-foreground truncate">{msg.preview}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{msg.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Badges */}
          {h?.badges?.length > 0 && (
            <div className="clinical-card">
              <div className="flex items-center gap-2 mb-3">
                <Trophy className="w-4 h-4 text-warning-500" />
                <h3 className="text-sm font-bold text-foreground">Achievements</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {h.badges.map((badge: string, i: number) => (
                  <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-full text-xs font-semibold text-warning-700 dark:text-warning-400">
                    <Trophy className="w-3 h-3" />
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

// ─── Goal Progress ────────────────────────────────────────────────────────────

function GoalProgress({ goal }: { goal: { title: string; progress: number; current: number; target: number; unit: string } }) {
  const isComplete = goal.progress >= 100

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-foreground">{goal.title}</span>
        <div className="flex items-center gap-1.5">
          {isComplete && <CheckCircle2 className="w-3.5 h-3.5 text-secondary-500" />}
          <span className={cn('text-xs font-mono font-bold', isComplete ? 'text-secondary-600' : 'text-foreground')}>
            {goal.progress}%
          </span>
        </div>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(goal.progress, 100)}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={cn('h-full rounded-full', isComplete ? 'bg-secondary-500' : goal.progress >= 70 ? 'bg-primary-500' : goal.progress >= 40 ? 'bg-warning-500' : 'bg-danger-400')}
        />
      </div>
      <p className="text-[10px] text-muted-foreground mt-1">
        {goal.current} / {goal.target} {goal.unit}
      </p>
    </div>
  )
}

// ─── Adherence Calendar ───────────────────────────────────────────────────────

function AdherenceCalendar({ data }: { data: Array<{ date: string; taken: boolean }> }) {
  const days = data.slice(-30)

  return (
    <div>
      <div className="grid grid-cols-10 gap-1">
        {days.map((day, i) => (
          <div
            key={i}
            className={cn(
              'w-5 h-5 rounded-sm flex items-center justify-center',
              day.taken ? 'bg-secondary-500' : 'bg-danger-200 dark:bg-danger-900/40',
            )}
            title={`${format(new Date(day.date), 'MMM d')}: ${day.taken ? 'Taken' : 'Missed'}`}
          />
        ))}
      </div>
      <div className="flex items-center gap-4 mt-3 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-secondary-500" />
          <span>Taken</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-danger-200 dark:bg-danger-900/40" />
          <span>Missed</span>
        </div>
      </div>
    </div>
  )
}
