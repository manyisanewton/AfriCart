export default defineNuxtRouteMiddleware(async (to) => {
  // Dashboard auth is client-driven because tokens are persisted in browser cookies.
  // Let the client hydrate first, then validate or refresh the session.
  if (import.meta.server)
    return

  const publicRoutes = new Set(['/login'])
  const auth = useAuth()

  if (!auth.hasCheckedSession.value)
    await auth.refreshSession()

  if (publicRoutes.has(to.path)) {
    if (auth.hasDashboardAccess.value)
      return navigateTo(auth.homeRoute.value)
    return
  }

  if (!auth.hasDashboardAccess.value)
    return navigateTo('/login')
})
