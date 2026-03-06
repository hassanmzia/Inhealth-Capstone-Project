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
  MessageSquare,
  Zap,
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
      : user?.role === 'nurse'
      ? '/dashboard/nurse'
      : user?.role === 'pharmacist'
      ? '/dashboard/pharmacist'
      : user?.role === 'billing'
      ? '/billing'
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
      roles: ['physician', 'nurse', 'admin', 'org_admin', 'pharmacist'],
    },
    {
      label: 'Clinical Workspace',
      href: '/clinical-workspace',
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
      label: 'Vitals Simulator',
      href: '/vitals-simulator',
      icon: Zap,
      roles: ['physician', 'admin', 'org_admin'],
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
      roles: ['admin', 'org_admin', 'billing'],
    },
    {
      label: 'Messages',
      href: '/messages',
      icon: MessageSquare,
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
      animate={{ width: collapsed ? 68 : 256 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className="relative flex flex-col h-full overflow-hidden"
      style={{
        background: 'linear-gradient(180deg, #0c1222 0%, #111827 50%, #0f172a 100%)',
      }}
    >
      {/* Ambient gradient overlay */}
      <div
        className="absolute inset-0 opacity-30 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 20% 0%, rgba(59, 130, 246, 0.15) 0%, transparent 60%), radial-gradient(ellipse at 80% 100%, rgba(139, 92, 246, 0.1) 0%, transparent 60%)',
        }}
      />

      {/* Logo */}
      <div className="relative flex items-center h-16 px-4 border-b border-white/[0.06] flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0 shadow-lg shadow-primary-500/20">
            <Heart className="w-4.5 h-4.5 text-white" />
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
                <p className="text-white font-bold text-sm tracking-tight leading-none">InHealth</p>
                <p className="text-clinical-500 text-[11px] leading-none mt-1">Chronic Care</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation */}
      <nav className="relative flex-1 py-3 overflow-y-auto overflow-x-hidden scrollbar-hide">
        <ul className="space-y-0.5 px-2">
          {filteredNavItems.map((item) => (
            <SidebarNavItem
              key={item.href + item.label}
              item={item}
              collapsed={collapsed}
              currentPath={location.pathname}
            />
          ))}
        </ul>

        {/* Divider */}
        <div className="mx-4 my-3 border-t border-white/[0.06]" />

        {/* Bottom items */}
        <ul className="space-y-0.5 px-2">
          {filteredBottomItems.map((item) => (
            <SidebarNavItem
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
        <div className="relative mx-3 mb-3 p-3 rounded-xl overflow-hidden">
          <div className="absolute inset-0 bg-primary-500/10 border border-primary-500/20 rounded-xl" />
          <div className="relative flex items-center gap-2.5">
            <div className="relative">
              <Activity className="w-4 h-4 text-primary-400" />
              <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-secondary-400 animate-pulse" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-primary-300 font-semibold">
                {activeAgents} agent{activeAgents !== 1 ? 's' : ''} active
              </p>
              <p className="text-[10px] text-clinical-500">Processing tasks</p>
            </div>
          </div>
        </div>
      )}

      {/* Collapse toggle button */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-clinical-800 border border-clinical-700 text-clinical-400 hover:bg-clinical-700 hover:text-white transition-all duration-200 flex items-center justify-center shadow-lg z-10 hover:scale-110"
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

function SidebarNavItem({ item, collapsed, currentPath }: NavItemProps) {
  const Icon = item.icon
  const badgeCount = item.badge?.()
  const isActive =
    item.href === '/dashboard' || item.href.startsWith('/dashboard/')
      ? currentPath === item.href
      : item.href === '/billing'
      ? currentPath === '/billing'
      : currentPath.startsWith(item.href)

  return (
    <li>
      <NavLink
        to={item.href}
        className={cn(
          'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative',
          isActive
            ? 'text-white'
            : 'text-clinical-400 hover:text-clinical-200 hover:bg-white/[0.04]',
        )}
        title={collapsed ? item.label : undefined}
      >
        {/* Active background with glow */}
        {isActive && (
          <motion.div
            layoutId="sidebar-active"
            className="absolute inset-0 rounded-xl"
            style={{
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.08) 100%)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
            }}
            transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }}
          />
        )}

        {/* Active left accent */}
        {isActive && (
          <motion.div
            layoutId="sidebar-accent"
            className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary-400"
            transition={{ type: 'spring', bounce: 0.15, duration: 0.5 }}
          />
        )}

        {/* Icon */}
        <div className="relative flex-shrink-0 z-10">
          <Icon
            className={cn(
              'w-[18px] h-[18px] transition-all duration-200',
              isActive ? 'text-primary-400' : 'text-clinical-500 group-hover:text-clinical-300',
            )}
          />
          {/* Badge on icon when collapsed */}
          {collapsed && badgeCount !== null && badgeCount !== undefined && badgeCount > 0 && (
            <span
              className={cn(
                'absolute -top-1.5 -right-1.5 min-w-[16px] h-4 rounded-full text-[9px] font-bold text-white flex items-center justify-center px-1',
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
              className="flex-1 flex items-center justify-between min-w-0 z-10"
            >
              <span className="text-[13px] font-medium truncate">{item.label}</span>
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
