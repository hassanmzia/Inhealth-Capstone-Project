import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  User,
  Bell,
  Globe,
  Shield,
  Sun,
  Moon,
  Monitor,
  Save,
  Camera,
  Loader2,
  Check,
  Stethoscope,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'security', label: 'Security & 2FA', icon: Shield },
  { id: 'appearance', label: 'Appearance', icon: Sun },
  { id: 'clinical', label: 'Clinical Prefs', icon: Stethoscope },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile')
  const { user, updateUser, updatePreferences } = useAuthStore()

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage your account and preferences</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar tabs */}
        <div className="lg:w-48 flex-shrink-0">
          <nav className="space-y-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
                  activeTab === tab.id
                    ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                )}
              >
                <tab.icon className="w-4 h-4 flex-shrink-0" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <motion.div key={activeTab} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.15 }}>
            {activeTab === 'profile' && <ProfileTab user={user} onUpdate={updateUser} />}
            {activeTab === 'notifications' && <NotificationsTab user={user} onUpdate={updatePreferences} />}
            {activeTab === 'security' && <SecurityTab />}
            {activeTab === 'appearance' && <AppearanceTab user={user} onUpdate={updatePreferences} />}
            {activeTab === 'clinical' && <ClinicalPrefsTab />}
          </motion.div>
        </div>
      </div>
    </div>
  )
}

// ─── Profile Tab ──────────────────────────────────────────────────────────────

function ProfileTab({ user, onUpdate }: { user: ReturnType<typeof useAuthStore>['user']; onUpdate: ReturnType<typeof useAuthStore>['updateUser'] }) {
  const { register, handleSubmit, formState: { isDirty } } = useForm({
    defaultValues: {
      firstName: user?.firstName ?? '',
      lastName: user?.lastName ?? '',
      email: user?.email ?? '',
      specialty: user?.specialty ?? '',
      npi: user?.npi ?? '',
      preferredLanguage: user?.preferences?.language ?? 'en',
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, string>) => api.patch('/auth/profile/', data),
    onSuccess: (_, data) => {
      onUpdate(data as Parameters<typeof onUpdate>[0])
      toast.success('Profile updated')
    },
    onError: () => toast.error('Failed to update profile'),
  })

  return (
    <div className="clinical-card space-y-6">
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="w-16 h-16 rounded-full bg-gradient-clinical flex items-center justify-center text-white text-xl font-bold">
            {user?.firstName?.[0]}{user?.lastName?.[0]}
          </div>
          <button className="absolute bottom-0 right-0 w-6 h-6 rounded-full bg-primary-600 flex items-center justify-center text-white shadow-lg">
            <Camera className="w-3 h-3" />
          </button>
        </div>
        <div>
          <p className="font-semibold text-foreground">{user?.firstName} {user?.lastName}</p>
          <p className="text-sm text-muted-foreground capitalize">{user?.role?.replace('_', ' ')}</p>
          <p className="text-xs text-muted-foreground">{user?.tenantName}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit((data) => updateMutation.mutate(data as Record<string, string>))} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">First Name</label>
            <input {...register('firstName')} className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label className="block text-xs font-medium text-foreground mb-1.5">Last Name</label>
            <input {...register('lastName')} className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Email Address</label>
          <input {...register('email')} type="email" className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" />
        </div>

        {(user?.role === 'physician' || user?.role === 'nurse') && (
          <>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">Specialty</label>
              <input {...register('specialty')} className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" />
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">NPI Number</label>
              <input {...register('npi')} className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-400" />
            </div>
          </>
        )}

        <button
          type="submit"
          disabled={!isDirty || updateMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
        >
          {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Changes
        </button>
      </form>
    </div>
  )
}

// ─── Notifications Tab ────────────────────────────────────────────────────────

function NotificationsTab({ user, onUpdate }: { user: ReturnType<typeof useAuthStore>['user']; onUpdate: ReturnType<typeof useAuthStore>['updatePreferences'] }) {
  const prefs = user?.preferences

  const handleToggle = (key: keyof NonNullable<typeof prefs>) => {
    if (!prefs) return
    const current = prefs[key] as boolean
    onUpdate({ [key]: !current } as Parameters<typeof onUpdate>[0])
    toast.success('Preference updated')
  }

  const notifPrefs = [
    { key: 'notificationsEnabled' as const, label: 'Enable All Notifications', desc: 'Master toggle for all notifications' },
    { key: 'emailNotifications' as const, label: 'Email Notifications', desc: 'Receive alerts via email' },
    { key: 'smsNotifications' as const, label: 'SMS Notifications', desc: 'Receive critical alerts via SMS' },
    { key: 'pushNotifications' as const, label: 'Push Notifications', desc: 'Browser push notifications' },
  ]

  return (
    <div className="clinical-card space-y-4">
      <h3 className="text-sm font-bold text-foreground">Notification Preferences</h3>
      <div className="space-y-3">
        {notifPrefs.map((pref) => (
          <div key={pref.key} className="flex items-center justify-between py-2 border-b border-border last:border-0">
            <div>
              <p className="text-sm font-medium text-foreground">{pref.label}</p>
              <p className="text-xs text-muted-foreground">{pref.desc}</p>
            </div>
            <button
              onClick={() => handleToggle(pref.key)}
              className={cn(
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                prefs?.[pref.key] ? 'bg-primary-600' : 'bg-clinical-300 dark:bg-clinical-600',
              )}
            >
              <span
                className={cn(
                  'inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform',
                  prefs?.[pref.key] ? 'translate-x-6' : 'translate-x-1',
                )}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Security Tab ─────────────────────────────────────────────────────────────

function SecurityTab() {
  const [show2FASetup, setShow2FASetup] = useState(false)

  return (
    <div className="space-y-4">
      <div className="clinical-card space-y-4">
        <h3 className="text-sm font-bold text-foreground">Change Password</h3>
        <div className="space-y-3">
          {['Current Password', 'New Password', 'Confirm New Password'].map((label) => (
            <div key={label}>
              <label className="block text-xs font-medium text-foreground mb-1.5">{label}</label>
              <input type="password" className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" />
            </div>
          ))}
          <button className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-semibold transition-colors">
            <Save className="w-4 h-4" />
            Update Password
          </button>
        </div>
      </div>

      <div className="clinical-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-foreground">Two-Factor Authentication</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Add an extra layer of security</p>
          </div>
          <button
            onClick={() => setShow2FASetup((v) => !v)}
            className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-sm font-medium hover:bg-accent transition-colors"
          >
            <Shield className="w-4 h-4" />
            {show2FASetup ? 'Cancel' : 'Enable 2FA'}
          </button>
        </div>

        {show2FASetup && (
          <div className="p-4 bg-muted rounded-xl space-y-3">
            <p className="text-sm text-foreground">
              1. Install an authenticator app (Google Authenticator, Authy, etc.)
            </p>
            <div className="w-32 h-32 bg-white rounded-lg flex items-center justify-center mx-auto border border-border">
              <p className="text-xs text-muted-foreground text-center p-2">QR Code<br />(Generated by backend)</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-foreground mb-1.5">Verification Code</label>
              <input type="text" maxLength={6} placeholder="000000" className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary-400" />
            </div>
            <button className="w-full flex items-center justify-center gap-2 py-2 bg-secondary-600 hover:bg-secondary-700 text-white rounded-lg text-sm font-semibold transition-colors">
              <Check className="w-4 h-4" />
              Verify & Enable 2FA
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Appearance Tab ───────────────────────────────────────────────────────────

function AppearanceTab({ user, onUpdate }: { user: ReturnType<typeof useAuthStore>['user']; onUpdate: ReturnType<typeof useAuthStore>['updatePreferences'] }) {
  const currentTheme = user?.preferences?.theme ?? 'system'

  const themes = [
    { id: 'light', label: 'Light', icon: Sun },
    { id: 'dark', label: 'Dark', icon: Moon },
    { id: 'system', label: 'System', icon: Monitor },
  ]

  const handleTheme = (theme: 'light' | 'dark' | 'system') => {
    onUpdate({ theme })
    document.documentElement.classList.toggle('dark', theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches))
    toast.success(`Theme set to ${theme}`)
  }

  return (
    <div className="clinical-card space-y-6">
      <div>
        <h3 className="text-sm font-bold text-foreground mb-3">Theme</h3>
        <div className="grid grid-cols-3 gap-3">
          {themes.map((t) => (
            <button
              key={t.id}
              onClick={() => handleTheme(t.id as 'light' | 'dark' | 'system')}
              className={cn(
                'flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all',
                currentTheme === t.id
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-border hover:border-primary-300',
              )}
            >
              <t.icon className={cn('w-6 h-6', currentTheme === t.id ? 'text-primary-600 dark:text-primary-400' : 'text-muted-foreground')} />
              <span className={cn('text-sm font-medium', currentTheme === t.id ? 'text-primary-700 dark:text-primary-400' : 'text-muted-foreground')}>
                {t.label}
              </span>
              {currentTheme === t.id && (
                <Check className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              )}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-sm font-bold text-foreground mb-3">Language</h3>
        <select className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400">
          <option value="en">English (US)</option>
          <option value="es">Español</option>
          <option value="fr">Français</option>
          <option value="de">Deutsch</option>
          <option value="pt">Português</option>
          <option value="zh">中文</option>
        </select>
      </div>
    </div>
  )
}

// ─── Clinical Prefs Tab ───────────────────────────────────────────────────────

function ClinicalPrefsTab() {
  return (
    <div className="clinical-card space-y-4">
      <h3 className="text-sm font-bold text-foreground">Clinical Preferences</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Default Unit System</label>
          <select className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400">
            <option value="metric">Metric (kg, cm, °C)</option>
            <option value="imperial">Imperial (lbs, in, °F)</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Glucose Unit</label>
          <select className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400">
            <option value="mgdl">mg/dL</option>
            <option value="mmol">mmol/L</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1.5">Default Patient View</label>
          <select className="w-full px-3 py-2 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400">
            <option value="overview">Overview</option>
            <option value="vitals">Vitals</option>
            <option value="agents">AI Agents</option>
          </select>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-semibold transition-colors">
          <Save className="w-4 h-4" />
          Save Preferences
        </button>
      </div>
    </div>
  )
}
