import React, { Component, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuthStore } from '@/store/authStore'
import MainLayout from '@/components/layout/MainLayout'

// Lazy-loaded pages
const LoginPage = React.lazy(() => import('@/pages/auth/LoginPage'))
const ClinicianDashboard = React.lazy(() => import('@/pages/dashboard/ClinicianDashboard'))
const PatientDashboard = React.lazy(() => import('@/pages/dashboard/PatientDashboard'))
const PatientListPage = React.lazy(() => import('@/pages/patients/PatientListPage'))
const PatientDetailPage = React.lazy(() => import('@/pages/patients/PatientDetailPage'))
const AgentControlPage = React.lazy(() => import('@/pages/agents/AgentControlPage'))
const AnalyticsPage = React.lazy(() => import('@/pages/analytics/AnalyticsPage'))
const ResearchPage = React.lazy(() => import('@/pages/research/ResearchPage'))
const AlertsPage = React.lazy(() => import('@/pages/alerts/AlertsPage'))
const TenantAdminPage = React.lazy(() => import('@/pages/admin/TenantAdminPage'))
const SettingsPage = React.lazy(() => import('@/pages/settings/SettingsPage'))

// Page transition variants
const pageVariants = {
  initial: { opacity: 0, y: 8 },
  in: { opacity: 1, y: 0 },
  out: { opacity: 0, y: -8 },
}

const pageTransition = { type: 'tween', ease: 'easeInOut', duration: 0.2 }

// Loading skeleton
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-4 border-primary-200 dark:border-primary-900" />
          <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin" />
        </div>
        <p className="text-sm text-muted-foreground animate-pulse">Loading...</p>
      </div>
    </div>
  )
}

// Error boundary
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('InHealth Error Boundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-background">
          <div className="max-w-md mx-auto text-center p-8">
            <div className="w-16 h-16 bg-danger-100 dark:bg-danger-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-danger-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-foreground mb-2">
              Something went wrong
            </h2>
            <p className="text-sm text-muted-foreground mb-6">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null })
                window.location.reload()
              }}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors text-sm font-medium"
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// Protected route component
interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRoles?: string[]
}

function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requiredRoles && user && !requiredRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

// Animated page wrapper
function AnimatedPage({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial="initial"
      animate="in"
      exit="out"
      variants={pageVariants}
      transition={pageTransition}
      className="h-full"
    >
      {children}
    </motion.div>
  )
}

export default function App() {
  const location = useLocation()
  const { isAuthenticated, user } = useAuthStore()

  return (
    <ErrorBoundary>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          {/* Public routes */}
          <Route
            path="/login"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Suspense fallback={<PageLoader />}>
                  <AnimatedPage>
                    <LoginPage />
                  </AnimatedPage>
                </Suspense>
              )
            }
          />

          {/* Protected routes under MainLayout */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            {/* Dashboard — role-based redirect */}
            <Route
              index
              element={
                <Navigate
                  to={user?.role === 'patient' ? '/dashboard/patient' : '/dashboard'}
                  replace
                />
              }
            />

            {/* Clinician dashboard */}
            <Route
              path="dashboard"
              element={
                <ProtectedRoute requiredRoles={['physician', 'nurse', 'admin', 'org_admin']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <ClinicianDashboard />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* Patient dashboard */}
            <Route
              path="dashboard/patient"
              element={
                <ProtectedRoute requiredRoles={['patient']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <PatientDashboard />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* Patient management */}
            <Route
              path="patients"
              element={
                <ProtectedRoute requiredRoles={['physician', 'nurse', 'admin', 'org_admin']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <PatientListPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            <Route
              path="patients/:patientId"
              element={
                <ProtectedRoute requiredRoles={['physician', 'nurse', 'admin', 'org_admin']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <PatientDetailPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* AI Agents */}
            <Route
              path="agents"
              element={
                <ProtectedRoute requiredRoles={['physician', 'admin', 'org_admin']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <AgentControlPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* Analytics */}
            <Route
              path="analytics"
              element={
                <ProtectedRoute requiredRoles={['physician', 'admin', 'org_admin']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <AnalyticsPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* Research */}
            <Route
              path="research"
              element={
                <ProtectedRoute requiredRoles={['physician', 'admin', 'org_admin']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <ResearchPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* Alerts */}
            <Route
              path="alerts"
              element={
                <ProtectedRoute>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <AlertsPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* Admin */}
            <Route
              path="admin"
              element={
                <ProtectedRoute requiredRoles={['org_admin', 'admin']}>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <TenantAdminPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />

            {/* Settings */}
            <Route
              path="settings"
              element={
                <ProtectedRoute>
                  <Suspense fallback={<PageLoader />}>
                    <AnimatedPage>
                      <SettingsPage />
                    </AnimatedPage>
                  </Suspense>
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Catch-all */}
          <Route
            path="*"
            element={
              <div className="flex items-center justify-center min-h-screen bg-background">
                <div className="text-center">
                  <h1 className="text-6xl font-bold text-primary-600 mb-4">404</h1>
                  <p className="text-xl text-muted-foreground mb-6">Page not found</p>
                  <a
                    href="/dashboard"
                    className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                  >
                    Return to Dashboard
                  </a>
                </div>
              </div>
            }
          />
        </Routes>
      </AnimatePresence>
    </ErrorBoundary>
  )
}
