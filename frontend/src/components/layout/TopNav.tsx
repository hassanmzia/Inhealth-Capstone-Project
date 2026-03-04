import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  Search,
  Sun,
  Moon,
  Monitor,
  ChevronDown,
  LogOut,
  Settings,
  User,
  Menu,
  X,
  AlertTriangle,
  Info,
  Clock,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useAlertStore } from '@/store/alertStore'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'

interface TopNavProps {
  onMobileMenuToggle: () => void
  onThemeToggle: () => void
  theme: 'light' | 'dark' | 'system'
  sidebarCollapsed: boolean
}

export default function TopNav({
  onMobileMenuToggle,
  onThemeToggle,
  theme,
}: TopNavProps) {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { unreadCount, criticalCount, alerts, markRead, markAllRead } = useAlertStore()

  const [showNotifications, setShowNotifications] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)

  const notifRef = useRef<HTMLDivElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/patients?q=${encodeURIComponent(searchQuery.trim())}`)
      setShowSearch(false)
      setSearchQuery('')
    }
  }

  const ThemeIcon = theme === 'dark' ? Moon : theme === 'light' ? Sun : Monitor

  const recentAlerts = alerts.slice(0, 8)

  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <AlertTriangle className="w-4 h-4 text-danger-500" />
      case 'urgent': return <AlertTriangle className="w-4 h-4 text-warning-500" />
      case 'soon': return <Clock className="w-4 h-4 text-primary-400" />
      default: return <Info className="w-4 h-4 text-clinical-400" />
    }
  }

  return (
    <header className="h-16 bg-white dark:bg-clinical-900 border-b border-border flex items-center px-4 gap-4 z-30">
      {/* Mobile menu button */}
      <button
        onClick={onMobileMenuToggle}
        className="lg:hidden p-2 rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Search */}
      <div className="flex-1 max-w-lg">
        {showSearch ? (
          <form onSubmit={handleSearch} className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search patients by name, MRN, or DOB..."
                autoFocus
                className="w-full pl-9 pr-4 py-2 bg-accent rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <button
              type="button"
              onClick={() => { setShowSearch(false); setSearchQuery('') }}
              className="p-2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          </form>
        ) : (
          <button
            onClick={() => setShowSearch(true)}
            className="flex items-center gap-2 px-3 py-2 bg-accent rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-accent/80 transition-colors w-full max-w-xs"
          >
            <Search className="w-4 h-4 flex-shrink-0" />
            <span className="hidden sm:block">Search patients...</span>
            <kbd className="hidden md:inline-flex ml-auto text-xs bg-background border border-border rounded px-1.5 py-0.5">
              ⌘K
            </kbd>
          </button>
        )}
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-1 ml-auto">
        {/* Theme toggle */}
        <button
          onClick={onThemeToggle}
          className="p-2 rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          title="Toggle theme"
        >
          <ThemeIcon className="w-4 h-4" />
        </button>

        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => {
              setShowNotifications((v) => !v)
              setShowUserMenu(false)
            }}
            className={cn(
              'relative p-2 rounded-lg transition-colors',
              criticalCount > 0
                ? 'text-danger-500 hover:bg-danger-50 dark:hover:bg-danger-900/20 animate-alert-pulse'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-danger-500 text-white text-[9px] font-bold flex items-center justify-center leading-none">
                {unreadCount > 99 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notification dropdown */}
          <AnimatePresence>
            {showNotifications && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-2 w-80 bg-card border border-border rounded-xl shadow-clinical-lg overflow-hidden"
              >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-sm text-foreground">Notifications</h3>
                    {unreadCount > 0 && (
                      <span className="px-1.5 py-0.5 rounded-full bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400 text-xs font-medium">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllRead}
                        className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
                      >
                        Mark all read
                      </button>
                    )}
                    <button
                      onClick={() => {
                        navigate('/alerts')
                        setShowNotifications(false)
                      }}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      View all
                    </button>
                  </div>
                </div>

                {/* Alert list */}
                <div className="max-h-80 overflow-y-auto divide-y divide-border">
                  {recentAlerts.length === 0 ? (
                    <div className="py-8 text-center text-sm text-muted-foreground">
                      No notifications
                    </div>
                  ) : (
                    recentAlerts.map((alert) => (
                      <button
                        key={alert.id}
                        onClick={() => {
                          markRead(alert.id)
                          navigate('/alerts')
                          setShowNotifications(false)
                        }}
                        className={cn(
                          'w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-accent transition-colors',
                          !alert.isRead && 'bg-primary-50/50 dark:bg-primary-900/10',
                        )}
                      >
                        <div className="mt-0.5 flex-shrink-0">
                          {getAlertIcon(alert.severity)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">
                            {alert.title}
                          </p>
                          <p className="text-xs text-muted-foreground truncate mt-0.5">
                            {alert.patientName && (
                              <span className="font-medium">{alert.patientName} · </span>
                            )}
                            {alert.description}
                          </p>
                          <p className="text-[10px] text-muted-foreground mt-1">
                            {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                          </p>
                        </div>
                        {!alert.isRead && (
                          <div className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0 mt-1.5" />
                        )}
                      </button>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* User menu */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => {
              setShowUserMenu((v) => !v)
              setShowNotifications(false)
            }}
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-accent transition-colors"
          >
            {user?.photoUrl ? (
              <img
                src={user.photoUrl}
                alt={user.firstName}
                className="w-7 h-7 rounded-full object-cover"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-gradient-clinical flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                {user?.firstName?.[0]}{user?.lastName?.[0]}
              </div>
            )}
            <div className="hidden md:block text-left">
              <p className="text-xs font-semibold text-foreground leading-tight">
                {user?.firstName} {user?.lastName}
              </p>
              <p className="text-[10px] text-muted-foreground capitalize leading-tight">
                {user?.role?.replace('_', ' ')}
              </p>
            </div>
            <ChevronDown className="w-3 h-3 text-muted-foreground hidden md:block" />
          </button>

          {/* User dropdown */}
          <AnimatePresence>
            {showUserMenu && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-2 w-52 bg-card border border-border rounded-xl shadow-clinical-lg overflow-hidden"
              >
                <div className="px-4 py-3 border-b border-border">
                  <p className="text-sm font-semibold text-foreground">
                    {user?.firstName} {user?.lastName}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                  <p className="text-xs text-muted-foreground">{user?.tenantName}</p>
                </div>

                <div className="py-1">
                  <button
                    onClick={() => { navigate('/settings'); setShowUserMenu(false) }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-accent transition-colors"
                  >
                    <User className="w-4 h-4 text-muted-foreground" />
                    Profile
                  </button>
                  <button
                    onClick={() => { navigate('/settings'); setShowUserMenu(false) }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-accent transition-colors"
                  >
                    <Settings className="w-4 h-4 text-muted-foreground" />
                    Settings
                  </button>
                </div>

                <div className="py-1 border-t border-border">
                  <button
                    onClick={() => {
                      logout()
                      navigate('/login')
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-danger-600 dark:text-danger-400 hover:bg-danger-50 dark:hover:bg-danger-900/20 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  )
}
