import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'

// ─── Types ────────────────────────────────────────────────────────────────────

interface LoginCredentials {
  email: string
  password: string
  totpCode?: string
}

interface LoginResponse {
  access: string
  refresh: string
  user: {
    id: string
    email: string
    firstName: string
    lastName: string
    role: string
    tenantId: string
    avatar?: string
    specialty?: string
    npi?: string
    preferences?: Record<string, unknown>
  }
  requires2FA?: boolean
  tempToken?: string
}

interface ChangePasswordPayload {
  currentPassword: string
  newPassword: string
}

interface Setup2FAResponse {
  qrCodeUrl: string
  secret: string
  backupCodes: string[]
}

// ─── useAuth hook ─────────────────────────────────────────────────────────────

export function useAuth() {
  const navigate = useNavigate()
  const {
    user,
    token,
    isLoading,
    requires2FA,
    isAuthenticated,
    isPhysician,
    isPatient,
    isAdmin,
    isOrgAdmin,
    isClinician,
    login: storeLogin,
    logout: storeLogout,
    refreshTokens,
    setToken,
    updateUser,
    updatePreferences,
    clearAuth,
  } = useAuthStore()

  // ─── Login ─────────────────────────────────────────────────────────────────

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials): Promise<LoginResponse> => {
      const { data } = await api.post<LoginResponse>('/auth/login/', credentials)
      return data
    },
    onSuccess: (data) => {
      if (data.requires2FA && data.tempToken) {
        // Partial login — waiting for TOTP code
        useAuthStore.setState({ requires2FA: true, tempToken: data.tempToken })
        return
      }

      storeLogin(
        {
          id: data.user.id,
          email: data.user.email,
          firstName: data.user.firstName,
          lastName: data.user.lastName,
          role: data.user.role as Parameters<typeof storeLogin>[0]['role'],
          tenantId: data.user.tenantId,
          avatar: data.user.avatar,
          specialty: data.user.specialty,
          npi: data.user.npi,
          preferences: data.user.preferences ?? {},
        },
        data.access,
        data.refresh,
      )

      toast.success(`Welcome back, ${data.user.firstName}!`)

      // Role-based redirect
      if (data.user.role === 'patient') {
        navigate('/dashboard/patient')
      } else {
        navigate('/dashboard')
      }
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Login failed. Please check your credentials.'
      toast.error(message)
    },
  })

  // ─── Logout ────────────────────────────────────────────────────────────────

  const logout = useCallback(async () => {
    try {
      const refreshToken = useAuthStore.getState().refreshToken
      if (refreshToken) {
        await api.post('/auth/logout/', { refresh: refreshToken }).catch(() => {
          // Ignore server errors on logout
        })
      }
    } finally {
      storeLogout()
      navigate('/login')
      toast.success('Signed out successfully')
    }
  }, [storeLogout, navigate])

  // ─── Refresh token ─────────────────────────────────────────────────────────

  const refreshMutation = useMutation({
    mutationFn: refreshTokens,
    onError: () => {
      clearAuth()
      navigate('/login')
    },
  })

  // ─── Change password ───────────────────────────────────────────────────────

  const changePasswordMutation = useMutation({
    mutationFn: async (payload: ChangePasswordPayload) => {
      await api.post('/auth/change-password/', {
        current_password: payload.currentPassword,
        new_password: payload.newPassword,
      })
    },
    onSuccess: () => {
      toast.success('Password updated successfully')
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to change password'
      toast.error(message)
    },
  })

  // ─── Setup 2FA ─────────────────────────────────────────────────────────────

  const setup2FAMutation = useMutation({
    mutationFn: async (): Promise<Setup2FAResponse> => {
      const { data } = await api.post<Setup2FAResponse>('/auth/2fa/setup/')
      return data
    },
    onError: () => toast.error('Failed to initiate 2FA setup'),
  })

  const verify2FAMutation = useMutation({
    mutationFn: async (totpCode: string) => {
      await api.post('/auth/2fa/verify/', { totp_code: totpCode })
    },
    onSuccess: () => {
      updateUser({ twoFactorEnabled: true } as Partial<Parameters<typeof updateUser>[0]>)
      toast.success('Two-factor authentication enabled')
    },
    onError: () => toast.error('Invalid verification code'),
  })

  const disable2FAMutation = useMutation({
    mutationFn: async (totpCode: string) => {
      await api.post('/auth/2fa/disable/', { totp_code: totpCode })
    },
    onSuccess: () => {
      updateUser({ twoFactorEnabled: false } as Partial<Parameters<typeof updateUser>[0]>)
      toast.success('Two-factor authentication disabled')
    },
    onError: () => toast.error('Failed to disable 2FA'),
  })

  // ─── Update profile ────────────────────────────────────────────────────────

  const updateProfileMutation = useMutation({
    mutationFn: async (profileData: Partial<{
      firstName: string
      lastName: string
      email: string
      specialty: string
      npi: string
      avatar: string
    }>) => {
      const { data } = await api.patch('/auth/profile/', {
        first_name: profileData.firstName,
        last_name: profileData.lastName,
        email: profileData.email,
        specialty: profileData.specialty,
        npi: profileData.npi,
        avatar: profileData.avatar,
      })
      return data
    },
    onSuccess: (data) => {
      updateUser({
        firstName: data.first_name,
        lastName: data.last_name,
        email: data.email,
        specialty: data.specialty,
        npi: data.npi,
        avatar: data.avatar,
      })
      toast.success('Profile updated')
    },
    onError: () => toast.error('Failed to update profile'),
  })

  // ─── Computed helpers ──────────────────────────────────────────────────────

  const fullName = user ? `${user.firstName} ${user.lastName}` : ''
  const initials = user
    ? `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase()
    : ''

  const hasRole = useCallback(
    (...roles: string[]) => {
      return roles.includes(user?.role ?? '')
    },
    [user?.role],
  )

  const canAccessPatientData = isPhysician || isAdmin || isClinician
  const canManageAgents = isPhysician || isAdmin || isClinician
  const canViewAnalytics = isPhysician || isAdmin || isClinician
  const canManageOrg = isOrgAdmin || isAdmin

  return {
    // State
    user,
    token,
    isLoading,
    requires2FA,
    isAuthenticated,

    // Role flags
    isPhysician,
    isPatient,
    isAdmin,
    isOrgAdmin,
    isClinician,

    // Permission helpers
    hasRole,
    canAccessPatientData,
    canManageAgents,
    canViewAnalytics,
    canManageOrg,

    // Display helpers
    fullName,
    initials,

    // Actions
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,

    logout,

    refreshToken: refreshMutation.mutate,
    isRefreshing: refreshMutation.isPending,

    changePassword: changePasswordMutation.mutate,
    isChangingPassword: changePasswordMutation.isPending,

    setup2FA: setup2FAMutation.mutate,
    setup2FAData: setup2FAMutation.data,
    isSettingUp2FA: setup2FAMutation.isPending,

    verify2FA: verify2FAMutation.mutate,
    isVerifying2FA: verify2FAMutation.isPending,

    disable2FA: disable2FAMutation.mutate,
    isDisabling2FA: disable2FAMutation.isPending,

    updateProfile: updateProfileMutation.mutate,
    isUpdatingProfile: updateProfileMutation.isPending,

    updatePreferences,
    setToken,
  }
}

// ─── Lightweight selector hooks ────────────────────────────────────────────────

/** Returns only authentication state — avoids re-renders for action-only consumers. */
export function useAuthState() {
  const { isAuthenticated, user, token, isLoading } = useAuthStore()
  return { isAuthenticated, user, token, isLoading }
}

/** Returns only the user's role — minimal subscription. */
export function useUserRole() {
  return useAuthStore((s) => s.user?.role)
}

/** Returns only the tenant ID — for API headers and multi-tenant logic. */
export function useTenantId() {
  return useAuthStore((s) => s.user?.tenantId)
}
