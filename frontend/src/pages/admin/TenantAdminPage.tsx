import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Building2,
  Users,
  Key,
  BarChart3,
  Settings,
  Plus,
  Copy,
  Eye,
  EyeOff,
  Shield,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/services/api'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'users', label: 'User Management', icon: Users },
  { id: 'api', label: 'API Keys', icon: Key },
  { id: 'settings', label: 'Org Settings', icon: Settings },
]

export default function TenantAdminPage() {
  const [activeTab, setActiveTab] = useState('overview')
  const { user } = useAuthStore()

  const { data: orgData } = useQuery({
    queryKey: ['org-admin-data'],
    queryFn: () => api.get('/admin/organization/').then((r) => r.data),
    placeholderData: {
      organization: {
        id: 'org_1',
        name: 'General Hospital',
        domain: 'generalhospital.com',
        tier: 'enterprise',
        logo: null,
        primaryColor: '#1d6fdb',
        totalPatients: 1284,
        totalUsers: 47,
        apiCallsThisMonth: 182450,
        agentExecutionsThisMonth: 34821,
        storageUsedGb: 128,
        storageLimitGb: 500,
      },
      users: [
        { id: 'u1', name: 'Dr. Sarah Johnson', email: 'sjohnson@gh.com', role: 'physician', lastLogin: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), active: true },
        { id: 'u2', name: 'Dr. James Wilson', email: 'jwilson@gh.com', role: 'physician', lastLogin: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), active: true },
        { id: 'u3', name: 'Nurse Maria Garcia', email: 'mgarcia@gh.com', role: 'nurse', lastLogin: new Date(Date.now() - 30 * 60 * 1000).toISOString(), active: true },
        { id: 'u4', name: 'Admin User', email: 'admin@gh.com', role: 'admin', lastLogin: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), active: true },
        { id: 'u5', name: 'Dr. Kim Park', email: 'kpark@gh.com', role: 'physician', lastLogin: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), active: false },
      ],
      apiKeys: [
        { id: 'k1', name: 'Production API', key: 'sk-prod-...xxxx1234', createdAt: '2024-01-15', lastUsed: new Date(Date.now() - 60000).toISOString(), active: true },
        { id: 'k2', name: 'Development API', key: 'sk-dev-...xxxx5678', createdAt: '2024-02-01', lastUsed: new Date(Date.now() - 3600000).toISOString(), active: true },
        { id: 'k3', name: 'Webhook Integration', key: 'sk-wh-...xxxx9012', createdAt: '2024-02-20', lastUsed: null, active: false },
      ],
    },
  })

  const org = orgData?.organization
  const storagePercent = org ? (org.storageUsedGb / org.storageLimitGb) * 100 : 0

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
          <Building2 className="w-5 h-5 text-primary-500" />
          Organization Admin
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {org?.name} · {org?.tier?.charAt(0).toUpperCase() + (org?.tier?.slice(1) ?? '')} Plan
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border border-border rounded-xl overflow-hidden">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'bg-primary-600 text-white'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            <tab.icon className="w-4 h-4" />
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          {/* Usage stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Total Patients', value: org?.totalPatients?.toLocaleString(), icon: Users, color: 'text-primary-500' },
              { label: 'Total Users', value: org?.totalUsers, icon: Users, color: 'text-secondary-500' },
              { label: 'API Calls / Month', value: org?.apiCallsThisMonth?.toLocaleString(), icon: Key, color: 'text-warning-500' },
              { label: 'Agent Executions', value: org?.agentExecutionsThisMonth?.toLocaleString(), icon: BarChart3, color: 'text-purple-500' },
            ].map((stat) => (
              <div key={stat.label} className="clinical-card">
                <stat.icon className={`w-5 h-5 mb-2 ${stat.color}`} />
                <p className="text-2xl font-bold font-mono text-foreground">{stat.value ?? '—'}</p>
                <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* Storage */}
          <div className="clinical-card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-foreground">Storage Usage</h3>
              <span className="text-sm font-mono font-bold text-foreground">
                {org?.storageUsedGb}GB / {org?.storageLimitGb}GB
              </span>
            </div>
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-700', storagePercent > 80 ? 'bg-danger-500' : storagePercent > 60 ? 'bg-warning-500' : 'bg-primary-500')}
                style={{ width: `${storagePercent}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-2">{storagePercent.toFixed(1)}% used</p>
          </div>

          {/* Subscription */}
          <div className="clinical-card">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-primary-500" />
              <h3 className="text-sm font-bold text-foreground">Subscription</h3>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg font-bold text-foreground capitalize">{org?.tier} Plan</p>
                <p className="text-xs text-muted-foreground mt-1">All features included · Renews annually</p>
              </div>
              <button className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-accent transition-colors">
                Manage Plan
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{orgData?.users?.length} users</p>
            <button className="flex items-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium">
              <Plus className="w-4 h-4" />
              Invite User
            </button>
          </div>
          <div className="clinical-card p-0 overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted/50 border-b border-border">
                <tr>
                  {['User', 'Role', 'Last Login', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(orgData?.users ?? []).map((u: { id: string; name: string; email: string; role: string; lastLogin: string; active: boolean }) => (
                  <tr key={u.id} className="hover:bg-accent/30 transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-semibold text-foreground">{u.name}</p>
                        <p className="text-xs text-muted-foreground">{u.email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium capitalize bg-muted text-foreground px-2 py-0.5 rounded">
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {new Date(u.lastLogin).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      {u.active ? (
                        <span className="flex items-center gap-1 text-xs text-secondary-600"><CheckCircle2 className="w-3.5 h-3.5" />Active</span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground"><XCircle className="w-3.5 h-3.5" />Inactive</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <button className="text-xs text-primary-600 hover:underline">Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* API Keys Tab */}
      {activeTab === 'api' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">API keys for integrations</p>
            <button className="flex items-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium">
              <Plus className="w-4 h-4" />
              New API Key
            </button>
          </div>
          <div className="space-y-3">
            {(orgData?.apiKeys ?? []).map((key: { id: string; name: string; key: string; createdAt: string; lastUsed: string | null; active: boolean }) => (
              <APIKeyCard key={key.id} apiKey={key} />
            ))}
          </div>
        </motion.div>
      )}

      {/* Org Settings Tab */}
      {activeTab === 'settings' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="clinical-card space-y-6">
          <h3 className="text-sm font-bold text-foreground">Organization Settings</h3>
          <div className="space-y-4">
            {[
              { label: 'Organization Name', value: org?.name, type: 'text' },
              { label: 'Domain', value: org?.domain, type: 'text' },
              { label: 'Primary Color', value: org?.primaryColor, type: 'color' },
            ].map((field) => (
              <div key={field.label}>
                <label className="block text-xs font-medium text-foreground mb-1.5">{field.label}</label>
                <input
                  type={field.type}
                  defaultValue={field.value ?? ''}
                  className="w-full px-3 py-2.5 border border-border rounded-lg bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
              </div>
            ))}
            <button className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-semibold transition-colors">
              Save Settings
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}

// ─── API Key Card ─────────────────────────────────────────────────────────────

function APIKeyCard({ apiKey }: { apiKey: { id: string; name: string; key: string; createdAt: string; lastUsed: string | null; active: boolean } }) {
  const [showKey, setShowKey] = useState(false)

  const copyKey = async () => {
    await navigator.clipboard.writeText(apiKey.key)
    toast.success('API key copied')
  }

  return (
    <div className={cn('clinical-card', !apiKey.active && 'opacity-60')}>
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-foreground">{apiKey.name}</p>
            {apiKey.active ? (
              <span className="text-[10px] text-secondary-600 bg-secondary-50 dark:bg-secondary-900/20 px-1.5 py-0.5 rounded font-semibold">Active</span>
            ) : (
              <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-semibold">Inactive</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Created {apiKey.createdAt} · Last used {apiKey.lastUsed ? new Date(apiKey.lastUsed).toLocaleDateString() : 'Never'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <code className="text-xs font-mono bg-muted px-3 py-1.5 rounded text-foreground">
            {showKey ? apiKey.key : '••••••••••••••••'}
          </code>
          <button onClick={() => setShowKey((v) => !v)} className="p-1.5 rounded hover:bg-accent text-muted-foreground">
            {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
          <button onClick={copyKey} className="p-1.5 rounded hover:bg-accent text-muted-foreground">
            <Copy className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
