import { useState, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import Sidebar from './Sidebar'
import TopNav from './TopNav'
import { useAuthStore } from '@/store/authStore'
import { wsManager } from '@/services/websocket'
import { cn } from '@/lib/utils'

type Theme = 'light' | 'dark' | 'system'

function getSystemTheme(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  const effectiveTheme = theme === 'system' ? getSystemTheme() : theme
  root.classList.toggle('dark', effectiveTheme === 'dark')
}

export default function MainLayout() {
  const location = useLocation()
  const { user, updatePreferences } = useAuthStore()

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem('sidebar-collapsed') === 'true'
  })
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [theme, setTheme] = useState<Theme>(() => {
    return (user?.preferences?.theme ?? localStorage.getItem('theme') ?? 'system') as Theme
  })

  // Apply theme on mount and change
  useEffect(() => {
    applyTheme(theme)

    // Listen for system theme change
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      if (theme === 'system') applyTheme('system')
    }
    mq.addEventListener('change', handleChange)
    return () => mq.removeEventListener('change', handleChange)
  }, [theme])

  // Connect WebSocket
  useEffect(() => {
    const cleanupAgents = wsManager.connectAgentsSocket()
    const cleanupNotifications = wsManager.connectNotificationsSocket()

    return () => {
      cleanupAgents()
      cleanupNotifications()
    }
  }, [])

  // Close mobile menu on resize
  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 1024) {
        setMobileMenuOpen(false)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [mobileMenuOpen])

  const handleSidebarToggle = () => {
    setSidebarCollapsed((v) => {
      const next = !v
      localStorage.setItem('sidebar-collapsed', String(next))
      return next
    })
  }

  const handleThemeToggle = () => {
    const next: Theme = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'
    setTheme(next)
    localStorage.setItem('theme', next)
    updatePreferences({ theme: next })
  }

  const effectiveTheme = theme === 'system' ? getSystemTheme() : theme

  return (
    <div className={cn('flex h-[100dvh] bg-background overflow-hidden', effectiveTheme === 'dark' && 'dark')}>
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex flex-col h-full flex-shrink-0">
        <Sidebar collapsed={sidebarCollapsed} onToggle={handleSidebarToggle} />
      </div>

      {/* Mobile Sidebar Drawer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 30, stiffness: 350 }}
              className="fixed left-0 top-0 bottom-0 w-[272px] z-50 lg:hidden safe-top safe-bottom"
            >
              <div className="relative h-full shadow-2xl">
                <Sidebar collapsed={false} onToggle={() => {}} />
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="absolute top-4 right-3 p-2 rounded-xl bg-white/10 text-white/70 hover:bg-white/20 hover:text-white transition-all touch-target"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navigation */}
        <TopNav
          onMobileMenuToggle={() => setMobileMenuOpen(true)}
          onThemeToggle={handleThemeToggle}
          theme={theme}
          sidebarCollapsed={sidebarCollapsed}
        />

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden bg-background">
          <div className="h-full p-3 sm:p-4 md:p-6 lg:p-8">
            <div key={location.pathname} className="h-full animate-fade-in">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
