import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Users,
  Stethoscope,
  BrainCircuit,
  BarChart3,
  FlaskConical,
  Video,
  Receipt,
  Bell,
  Settings,
  Building2,
  ChevronLeft,
  ChevronRight,
  Activity,
  Heart,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useAgentStore, selectTotalActiveAgents } from '@/store/agentStore'
import { useAlertStore } from '@/store/alertStore'
import { cn } from '@/lib/utils'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

interface NavItem {
  label: string
  href: string
  icon: React.ElementType
  roles?: string[]
  badge?: () => number | null
  badgeColor?: string
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { user } = useAuthStore()
  const activeAgents = useAgentStore(selectTotalActiveAgents)
  const { unreadCount, criticalCount } = useAlertStore()
  const location = useLocation()

  const dashboardHref =
    user?.role === 'patient'
      ? '/dashboard/patient'
      : user?.role === 'researcher'
      ? '/dashboard/researcher'
      : '/dashboard'

  const navItems: NavItem[] = [
    {
      label: 'Dashboard',
      href: dashboardHref,
      icon: LayoutDashboard,
    },
    {
      label: 'Patients',
      href: '/patients',
      icon: Users,
      roles: ['physician', 'nurse', 'admin', 'org_admin'],
    },
    {
      label: 'Clinical Workspace',
      href: '/patients',
      icon: Stethoscope,
      roles: ['physician', 'nurse', 'admin', 'org_admin'],
    },
    {
      label: 'AI Agents',
      href: '/agents',
      icon: BrainCircuit,
      roles: ['physician', 'nurse', 'admin', 'org_admin'],
      badge: () => (activeAgents > 0 ? activeAgents : null),
      badgeColor: 'bg-secondary-500',
    },
    {
      label: 'Analytics',
      href: '/analytics',
      icon: BarChart3,
      roles: ['physician', 'admin', 'org_admin', 'researcher'],
    },
    {
      label: 'Research (AI)',
      href: '/research',
      icon: FlaskConical,
      roles: ['physician', 'admin', 'org_admin', 'researcher'],
    },
    {
      label: 'Telemedicine',
      href: '/telemedicine',
      icon: Video,
      roles: ['physician', 'nurse', 'patient'],
    },
    {
      label: 'Billing',
      href: '/billing',
      icon: Receipt,
      roles: ['admin', 'org_admin'],
    },
    {
      label: 'Alerts',
      href: '/alerts',
      icon: Bell,
      badge: () => (unreadCount > 0 ? unreadCount : null),
      badgeColor: criticalCount > 0 ? 'bg-danger-500' : 'bg-warning-500',
    },
  ]

  const bottomItems: NavItem[] = [
    {
      label: 'Admin',
      href: '/admin',
      icon: Building2,
      roles: ['admin', 'org_admin'],
    },
    {
      label: 'Settings',
      href: '/settings',
      icon: Settings,
    },
  ]

  const filteredNavItems = navItems.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role)),
  )

  const filteredBottomItems = bottomItems.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role)),
  )

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="relative flex flex-col h-full bg-clinical-900 dark:bg-clinical-950 border-r border-clinical-800 dark:border-clinical-900 overflow-hidden"
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-clinical-800 dark:border-clinical-900 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-clinical flex items-center justify-center flex-shrink-0">
            <Heart className="w-4 h-4 text-white" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.15 }}
                className="min-w-0"
              >
                <p className="text-white font-bold text-sm leading-none">InHealth</p>
                <p className="text-clinical-400 text-xs leading-none mt-0.5">Chronic Care</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto overflow-x-hidden">
        <ul className="space-y-1 px-2">
          {filteredNavItems.map((item) => (
            <NavItem
              key={item.href + item.label}
              item={item}
              collapsed={collapsed}
              currentPath={location.pathname}
            />
          ))}
        </ul>

        {/* Divider */}
        <div className="mx-2 my-4 border-t border-clinical-800 dark:border-clinical-900" />

        {/* Bottom items */}
        <ul className="space-y-1 px-2">
          {filteredBottomItems.map((item) => (
            <NavItem
              key={item.href}
              item={item}
              collapsed={collapsed}
              currentPath={location.pathname}
            />
          ))}
        </ul>
      </nav>

      {/* Agent activity indicator */}
      {!collapsed && activeAgents > 0 && (
        <div className="mx-3 mb-3 p-2.5 rounded-lg bg-primary-900/40 border border-primary-700/30">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-primary-400 animate-pulse flex-shrink-0" />
            <p className="text-xs text-primary-300 font-medium">
              {activeAgents} agent{activeAgents !== 1 ? 's' : ''} running
            </p>
          </div>
        </div>
      )}

      {/* Collapse toggle button */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-clinical-700 border border-clinical-600 text-clinical-300 hover:bg-clinical-600 hover:text-white transition-colors flex items-center justify-center shadow-lg z-10"
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3" />
        ) : (
          <ChevronLeft className="w-3 h-3" />
        )}
      </button>
    </motion.aside>
  )
}

// ─── NavItem Component ────────────────────────────────────────────────────────

interface NavItemProps {
  item: {
    label: string
    href: string
    icon: React.ElementType
    badge?: () => number | null
    badgeColor?: string
  }
  collapsed: boolean
  currentPath: string
}

function NavItem({ item, collapsed, currentPath }: NavItemProps) {
  const Icon = item.icon
  const badgeCount = item.badge?.()
  const isActive =
    item.href === '/dashboard' || item.href === '/dashboard/patient' || item.href === '/dashboard/researcher'
      ? currentPath === item.href
      : currentPath.startsWith(item.href)

  return (
    <li>
      <NavLink
        to={item.href}
        className={cn(
          'flex items-center gap-3 px-2 py-2 rounded-lg transition-all duration-150 group relative',
          isActive
            ? 'bg-primary-600/20 text-primary-300 border border-primary-600/20'
            : 'text-clinical-400 hover:text-clinical-200 hover:bg-clinical-800',
        )}
        title={collapsed ? item.label : undefined}
      >
        {/* Active indicator */}
        {isActive && (
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary-400 rounded-r-full" />
        )}

        {/* Icon */}
        <div className="relative flex-shrink-0">
          <Icon
            className={cn(
              'w-5 h-5 transition-colors',
              isActive ? 'text-primary-400' : 'text-clinical-500 group-hover:text-clinical-300',
            )}
          />
          {/* Badge on icon when collapsed */}
          {collapsed && badgeCount !== null && badgeCount !== undefined && badgeCount > 0 && (
            <span
              className={cn(
                'absolute -top-1 -right-1 w-4 h-4 rounded-full text-[9px] font-bold text-white flex items-center justify-center',
                item.badgeColor ?? 'bg-danger-500',
              )}
            >
              {badgeCount > 99 ? '99+' : badgeCount}
            </span>
          )}
        </div>

        {/* Label + badge */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.1 }}
              className="flex-1 flex items-center justify-between min-w-0"
            >
              <span className="text-sm font-medium truncate">{item.label}</span>
              {badgeCount !== null && badgeCount !== undefined && badgeCount > 0 && (
                <span
                  className={cn(
                    'ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-bold text-white leading-none',
                    item.badgeColor ?? 'bg-danger-500',
                  )}
                >
                  {badgeCount > 99 ? '99+' : badgeCount}
                </span>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </NavLink>
    </li>
  )
}
