let refreshPromise: Promise<string | null> | null = null

export function useBackendApi() {
  const config = useRuntimeConfig()
  const apiBase = String(config.public.apiBase || 'http://localhost:5000/api/v1').replace(/\/$/, '')
  const accessToken = useCookie<string | null>('techhive_dashboard_access_token', {
    sameSite: 'lax',
    secure: false,
    default: () => null,
  })
  const refreshToken = useCookie<string | null>('techhive_dashboard_refresh_token', {
    sameSite: 'lax',
    secure: false,
    default: () => null,
  })

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
  }

  async function refreshAccessToken() {
    if (!refreshToken.value)
      return null

    if (refreshPromise)
      return await refreshPromise

    refreshPromise = (async () => {
      try {
        const response = await $fetch<{ access_token: string, token_type: string }>(`${apiBase}/auth/refresh`, {
          method: 'POST',
          body: {
            refresh_token: refreshToken.value,
          },
        })
        accessToken.value = response.access_token
        return response.access_token
      }
      catch {
        clearTokens()
        return null
      }
      finally {
        refreshPromise = null
      }
    })()

    return await refreshPromise
  }

  async function request<T>(path: string, options: Record<string, any> = {}) {
    const {
      redirectOnAuthError = true,
      retryOnAuthError = true,
      _retried = false,
      ...fetchOptions
    } = options

    const method = String(fetchOptions.method || 'GET').toUpperCase()
    const headers: Record<string, string> = { ...(fetchOptions.headers || {}) }

    if (accessToken.value)
      headers.Authorization = `Bearer ${accessToken.value}`

    try {
      return await $fetch<T>(`${apiBase}${path}`, {
        ...fetchOptions,
        method,
        headers,
      })
    }
    catch (err: any) {
      const statusCode = Number(err?.status || err?.statusCode || 0)
      const shouldTryRefresh = statusCode === 401 && retryOnAuthError && !_retried && Boolean(refreshToken.value)

      if (shouldTryRefresh) {
        const newAccessToken = await refreshAccessToken()
        if (newAccessToken) {
          return await request<T>(path, {
            ...options,
            _retried: true,
          })
        }
      }

      if (redirectOnAuthError && import.meta.client && [401, 403].includes(statusCode)) {
        const auth = useAuth()
        auth.clearSession()
        if (window.location.pathname !== '/login')
          await navigateTo('/login')
      }

      throw err
    }
  }

  return {
    accessToken,
    apiBase,
    clearTokens,
    refreshAccessToken,
    refreshToken,
    request,
  }
}
