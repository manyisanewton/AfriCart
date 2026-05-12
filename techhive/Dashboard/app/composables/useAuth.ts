import { getDashboardHomeRouteForRole } from '~/config/navigation'

export type TechHiveDashboardRole = 'admin' | 'vendor' | 'delivery_agent' | 'customer'

export interface DashboardSessionUser {
  id: number
  email: string
  first_name?: string
  last_name?: string
  full_name?: string
  phone_number?: string | null
  role: TechHiveDashboardRole
  is_active: boolean
  email_verified: boolean
  created_at: string
}

export interface LoginPayload {
  email: string
  password: string
}

const ENABLED_DASHBOARD_ROLES: TechHiveDashboardRole[] = ['admin']

function readApiError(err: any) {
  return err?.data?.error?.message
    || err?.data?.message
    || err?.data?.detail
    || err?.data?.non_field_errors?.[0]
    || err?.message
    || 'Something went wrong.'
}

function canUseDashboard(user: DashboardSessionUser | null) {
  return Boolean(user && ENABLED_DASHBOARD_ROLES.includes(user.role))
}

export function useAuth() {
  const user = useState<DashboardSessionUser | null>('dashboard-session-user', () => null)
  const hasCheckedSession = useState('dashboard-session-checked', () => false)
  const isLoading = useState('dashboard-session-loading', () => false)
  const error = useState<string | null>('dashboard-session-error', () => null)
  const {
    accessToken,
    clearTokens,
    refreshAccessToken,
    refreshToken,
    request,
  } = useBackendApi()

  const isAuthenticated = computed(() => Boolean(user.value))
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isVendor = computed(() => user.value?.role === 'vendor')
  const hasDashboardAccess = computed(() => canUseDashboard(user.value))
  const homeRoute = computed(() => getDashboardHomeRouteForRole(user.value?.role))

  async function refreshSession() {
    isLoading.value = true
    error.value = null

    try {
      if (!accessToken.value && refreshToken.value)
        await refreshAccessToken()

      if (!accessToken.value) {
        user.value = null
        return null
      }

      const response = await request<{ user: DashboardSessionUser }>('/auth/me', {
        redirectOnAuthError: false,
      })

      if (!canUseDashboard(response.user)) {
        clearSession()
        error.value = 'This account does not have dashboard access yet.'
        return null
      }

      user.value = response.user
      return user.value
    }
    catch (err: any) {
      user.value = null
      error.value = Number(err?.status || err?.statusCode) === 401 ? null : readApiError(err)
      return null
    }
    finally {
      hasCheckedSession.value = true
      isLoading.value = false
    }
  }

  async function login(payload: LoginPayload) {
    isLoading.value = true
    error.value = null

    try {
      const response = await request<{
        user: DashboardSessionUser
        tokens: { access_token: string, refresh_token: string, token_type: string }
      }>('/auth/login', {
        method: 'POST',
        body: payload,
        redirectOnAuthError: false,
        retryOnAuthError: false,
      })

      accessToken.value = response.tokens.access_token
      refreshToken.value = response.tokens.refresh_token

      if (!canUseDashboard(response.user)) {
        clearSession()
        throw new Error('This dashboard is currently enabled for admin accounts only.')
      }

      user.value = response.user
      hasCheckedSession.value = true
      return { success: true, user: response.user }
    }
    catch (err: any) {
      clearSession()
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      isLoading.value = false
    }
  }

  async function logout(options: { redirect?: boolean } = {}) {
    const shouldRedirect = options.redirect !== false
    const submittedRefreshToken = refreshToken.value

    isLoading.value = true
    error.value = null

    try {
      if (submittedRefreshToken) {
        await request('/auth/logout', {
          method: 'POST',
          body: {
            refresh_token: submittedRefreshToken,
          },
          redirectOnAuthError: false,
          retryOnAuthError: false,
        })
      }
    }
    catch {
      // The local dashboard should still clear its state even if the server
      // rejects or no longer recognizes the refresh token.
    }
    finally {
      clearSession()
      isLoading.value = false
      if (shouldRedirect)
        await navigateTo('/login')
    }
  }

  function clearSession() {
    user.value = null
    hasCheckedSession.value = true
    clearTokens()
  }

  return {
    clearSession,
    error,
    hasCheckedSession,
    hasDashboardAccess,
    homeRoute,
    isAdmin,
    isAuthenticated,
    isLoading,
    isVendor,
    login,
    logout,
    refreshSession,
    user,
  }
}
