import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import api from '@/services/api'

// ─── User Types ───────────────────────────────────────────────────────────────

export type UserRole = 'physician' | 'nurse' | 'patient' | 'admin' | 'org_admin' | 'researcher'

export interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  role: UserRole
  tenantId: string
  tenantName: string
  npi?: string              // Physician NPI
  specialty?: string
  photoUrl?: string
  is2FAEnabled: boolean
  preferences: {
    theme: 'light' | 'dark' | 'system'
    language: string
    notificationsEnabled: boolean
    emailNotifications: boolean
    smsNotifications: boolean
    pushNotifications: boolean
  }
  lastLogin?: string
  createdAt: string
}

export interface LoginCredentials {
  email: string
  password: string
  totpCode?: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: User
  requires2FA?: boolean
  tempToken?: string
}

// ─── Auth Store State ─────────────────────────────────────────────────────────

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isLoading: boolean
  requires2FA: boolean
  tempToken: string | null

  // Computed values (as functions for Zustand)
  isAuthenticated: boolean
  isPhysician: boolean
  isPatient: boolean
  isAdmin: boolean
  isOrgAdmin: boolean
  isClinician: boolean

  // Actions
  login: (credentials: LoginCredentials) => Promise<LoginResponse>
  logout: () => void
  refreshTokens: () => Promise<void>
  setToken: (token: string) => void
  updateUser: (updates: Partial<User>) => void
  updatePreferences: (prefs: Partial<User['preferences']>) => void
  clearAuth: () => void
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isLoading: false,
      requires2FA: false,
      tempToken: null,

      // Derived computed booleans
      get isAuthenticated() {
        return !!(get().token && get().user)
      },
      get isPhysician() {
        return get().user?.role === 'physician'
      },
      get isPatient() {
        return get().user?.role === 'patient'
      },
      get isAdmin() {
        return get().user?.role === 'admin'
      },
      get isOrgAdmin() {
        return get().user?.role === 'org_admin'
      },
      get isClinician() {
        const role = get().user?.role
        return role === 'physician' || role === 'nurse' || role === 'admin' || role === 'org_admin'
      },

      // ── Actions ─────────────────────────────────────────────────────────────

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true })
        try {
          const response = await api.post<LoginResponse>('/auth/login/', credentials)
          const data = response.data

          if (data.requires2FA) {
            set({
              requires2FA: true,
              tempToken: data.tempToken ?? null,
              isLoading: false,
            })
            return data
          }

          set({
            user: data.user,
            token: data.access,
            refreshToken: data.refresh,
            isLoading: false,
            requires2FA: false,
            tempToken: null,
          })

          return data
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: () => {
        // Call logout endpoint (fire and forget)
        const token = get().token
        if (token) {
          api.post('/auth/logout/', { refresh: get().refreshToken }).catch(() => {})
        }

        set({
          user: null,
          token: null,
          refreshToken: null,
          requires2FA: false,
          tempToken: null,
        })
      },

      refreshTokens: async () => {
        const refresh = get().refreshToken
        if (!refresh) throw new Error('No refresh token')

        const response = await api.post<{ access: string; refresh: string }>(
          '/auth/token/refresh/',
          { refresh },
        )

        set({
          token: response.data.access,
          refreshToken: response.data.refresh,
        })
      },

      setToken: (token: string) => {
        set({ token })
      },

      updateUser: (updates: Partial<User>) => {
        const user = get().user
        if (!user) return
        set({ user: { ...user, ...updates } })
      },

      updatePreferences: (prefs: Partial<User['preferences']>) => {
        const user = get().user
        if (!user) return
        set({
          user: {
            ...user,
            preferences: { ...user.preferences, ...prefs },
          },
        })
      },

      clearAuth: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          requires2FA: false,
          tempToken: null,
        })
      },
    }),
    {
      name: 'inhealth-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
    },
  ),
)

// ─── Selectors ────────────────────────────────────────────────────────────────

export const selectUser = (state: AuthState) => state.user
export const selectToken = (state: AuthState) => state.token
export const selectIsAuthenticated = (state: AuthState) => !!(state.token && state.user)
export const selectUserRole = (state: AuthState) => state.user?.role
export const selectTenantId = (state: AuthState) => state.user?.tenantId
