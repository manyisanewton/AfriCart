export function useAdminAuth() {
  const auth = useAuth()

  return {
    checked: auth.hasCheckedSession,
    fetchCurrentUser: auth.refreshSession,
    isAuthenticated: auth.isAdmin,
    loading: auth.isLoading,
    login: (email: string, password: string) => auth.login({ email, password }),
    logout: auth.logout,
    user: auth.user,
  }
}
