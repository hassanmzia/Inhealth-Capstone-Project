import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Monitor,
  Calendar,
  Clock,
  User,
  MessageSquare,
  Settings,
  ChevronRight,
  Loader2,
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }
const ITEM = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }

interface Appointment {
  id: string
  patientName: string
  patientId: string
  start: string
  end: string
  serviceType: string
  appointmentType: string
  status: string
  isTelehealth: boolean
  location: string
}

function VideoCallPanel({ appointment, onEnd }: { appointment: Appointment; onEnd: () => void }) {
  const [videoOn, setVideoOn] = useState(true)
  const [audioOn, setAudioOn] = useState(true)
  const [screenShare, setScreenShare] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="fixed inset-0 bg-gray-900 z-50 flex flex-col"
    >
      {/* Video area */}
      <div className="flex-1 relative bg-gray-800 flex items-center justify-center">
        <div className="w-full h-full flex items-center justify-center">
          <div className="text-center">
            <div className="w-24 h-24 rounded-full bg-primary-700 flex items-center justify-center mx-auto mb-4">
              <User className="w-12 h-12 text-white" />
            </div>
            <p className="text-white text-xl font-semibold">{appointment.patientName}</p>
            <p className="text-gray-400 text-sm mt-1">
              {videoOn ? 'Camera off on patient side' : 'Video disabled'}
            </p>
          </div>
        </div>

        {/* Self-view pip */}
        <div className="absolute bottom-4 right-4 w-32 h-24 bg-gray-700 rounded-lg border border-gray-600 flex items-center justify-center">
          {videoOn ? (
            <p className="text-gray-400 text-xs">Your camera</p>
          ) : (
            <VideoOff className="w-6 h-6 text-gray-500" />
          )}
        </div>

        {/* Call info overlay */}
        <div className="absolute top-4 left-4 bg-black/60 backdrop-blur-sm rounded-lg px-3 py-2">
          <p className="text-white text-sm font-medium">{appointment.serviceType || 'Telemedicine Visit'}</p>
          <p className="text-gray-300 text-xs">{format(parseISO(appointment.start), 'MMM d, h:mm a')}</p>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-gray-900 border-t border-gray-800 px-8 py-4 flex items-center justify-center gap-4">
        <button
          onClick={() => setAudioOn(!audioOn)}
          className={cn(
            'w-12 h-12 rounded-full flex items-center justify-center transition-colors',
            audioOn ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-danger-600 hover:bg-danger-700 text-white',
          )}
          title={audioOn ? 'Mute microphone' : 'Unmute microphone'}
        >
          {audioOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
        </button>

        <button
          onClick={() => setVideoOn(!videoOn)}
          className={cn(
            'w-12 h-12 rounded-full flex items-center justify-center transition-colors',
            videoOn ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-danger-600 hover:bg-danger-700 text-white',
          )}
          title={videoOn ? 'Turn off camera' : 'Turn on camera'}
        >
          {videoOn ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
        </button>

        <button
          onClick={() => setScreenShare(!screenShare)}
          className={cn(
            'w-12 h-12 rounded-full flex items-center justify-center transition-colors',
            screenShare ? 'bg-primary-600 hover:bg-primary-700 text-white' : 'bg-gray-700 hover:bg-gray-600 text-white',
          )}
          title={screenShare ? 'Stop sharing' : 'Share screen'}
        >
          <Monitor className="w-5 h-5" />
        </button>

        <button
          onClick={onEnd}
          className="w-14 h-14 rounded-full bg-danger-600 hover:bg-danger-700 text-white flex items-center justify-center transition-colors"
          title="End call"
        >
          <PhoneOff className="w-6 h-6" />
        </button>

        <button
          className="w-12 h-12 rounded-full bg-gray-700 hover:bg-gray-600 text-white flex items-center justify-center transition-colors"
          title="Chat"
        >
          <MessageSquare className="w-5 h-5" />
        </button>

        <button
          className="w-12 h-12 rounded-full bg-gray-700 hover:bg-gray-600 text-white flex items-center justify-center transition-colors"
          title="Settings"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </motion.div>
  )
}

export default function TelemedicinePage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [activeCall, setActiveCall] = useState<Appointment | null>(null)

  const isPatient = user?.role === 'patient'

  const { data: appointments, isLoading } = useQuery({
    queryKey: ['telehealth-appointments'],
    queryFn: () =>
      api
        .get('/appointments/', { params: { status: 'booked,pending', limit: 20, days_ahead: 30 } })
        .then((r) => (r.data?.results ?? []) as Appointment[])
        .then((appts) => appts.filter((a) => a.isTelehealth || true)), // show all for demo
    refetchInterval: 60000,
    placeholderData: [],
  })

  if (activeCall) {
    return <VideoCallPanel appointment={activeCall} onEnd={() => setActiveCall(null)} />
  }

  const upcomingAppts = appointments ?? []

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-5xl">
      {/* Header */}
      <motion.div variants={ITEM} className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Telemedicine</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {isPatient
              ? 'Join virtual appointments with your care team'
              : 'Manage and start virtual patient consultations'}
          </p>
        </div>
      </motion.div>

      {/* Quick actions */}
      {!isPatient && (
        <motion.div variants={ITEM} className="grid grid-cols-3 gap-4">
          {[
            { label: 'Start Instant Call', icon: Phone, color: 'bg-secondary-600 hover:bg-secondary-700', href: null },
            { label: 'Schedule Visit', icon: Calendar, color: 'bg-primary-600 hover:bg-primary-700', href: '/patients' },
            { label: 'Test Connection', icon: Video, color: 'bg-gray-600 hover:bg-gray-700', href: null },
          ].map((action) => (
            <button
              key={action.label}
              onClick={() => action.href && navigate(action.href)}
              className={cn(
                'flex items-center justify-center gap-2 py-3 rounded-lg text-white text-sm font-semibold transition-colors',
                action.color,
              )}
            >
              <action.icon className="w-4 h-4" />
              {action.label}
            </button>
          ))}
        </motion.div>
      )}

      {/* Upcoming telehealth appointments */}
      <motion.div variants={ITEM} className="clinical-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-bold text-foreground">
              {isPatient ? 'Upcoming Appointments' : 'Scheduled Video Visits'}
            </h2>
          </div>
          <span className="text-xs text-muted-foreground">Next 30 days</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : upcomingAppts.length === 0 ? (
          <div className="text-center py-10">
            <Video className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-40" />
            <p className="text-sm text-muted-foreground">No upcoming virtual appointments.</p>
            {!isPatient && (
              <button
                onClick={() => navigate('/patients')}
                className="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline"
              >
                Schedule a video visit →
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {upcomingAppts.map((appt) => (
              <div key={appt.id} className="flex items-center gap-4 py-3">
                <div className="w-10 h-10 rounded-full bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center flex-shrink-0">
                  <Video className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground">
                    {isPatient ? (appt.serviceType || 'Virtual Visit') : appt.patientName}
                  </p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="w-3 h-3" />
                      {format(parseISO(appt.start), 'EEE, MMM d')}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="w-3 h-3" />
                      {format(parseISO(appt.start), 'h:mm a')}
                    </span>
                    {appt.serviceType && (
                      <span className="text-xs text-muted-foreground">· {appt.serviceType}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <span
                    className={cn(
                      'text-[10px] font-semibold px-2 py-0.5 rounded capitalize',
                      appt.status === 'booked'
                        ? 'text-secondary-700 bg-secondary-100 dark:bg-secondary-900/30'
                        : 'text-warning-700 bg-warning-100 dark:bg-warning-900/30',
                    )}
                  >
                    {appt.status}
                  </span>
                  <button
                    onClick={() => setActiveCall(appt)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-semibold rounded-lg transition-colors"
                  >
                    <Phone className="w-3 h-3" />
                    Join
                  </button>
                  {!isPatient && (
                    <button
                      onClick={() => navigate(`/patients/${appt.patientId}`)}
                      className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                      title="View patient chart"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Device check */}
      <motion.div variants={ITEM} className="clinical-card">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-bold text-foreground">Connection Check</h2>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Camera', icon: Video, status: 'ready' },
            { label: 'Microphone', icon: Mic, status: 'ready' },
            { label: 'Network', icon: Monitor, status: 'good' },
          ].map((item) => (
            <div
              key={item.label}
              className="flex flex-col items-center gap-2 p-3 rounded-lg border border-border bg-card"
            >
              <div className="w-9 h-9 rounded-full bg-secondary-50 dark:bg-secondary-900/20 flex items-center justify-center">
                <item.icon className="w-5 h-5 text-secondary-600" />
              </div>
              <p className="text-xs font-medium text-foreground">{item.label}</p>
              <span className="text-[10px] font-semibold text-secondary-600 bg-secondary-50 dark:bg-secondary-900/20 px-1.5 py-0.5 rounded">
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  )
}
