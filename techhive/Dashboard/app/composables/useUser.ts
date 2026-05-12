import type { UserTableRow } from '~/types/UserTableRow'

export interface AdminUserItem {
  id: number
  email: string
  full_name: string
  phone_number: string | null
  role: 'admin' | 'vendor' | 'customer' | 'delivery_agent'
  is_active: boolean
  email_verified: boolean
}

function extractApiError(err: any) {
  const detail = err?.data?.error?.message || err?.data?.detail || err?.message
  const errors = err?.data?.error?.errors || err?.data

  if (errors && typeof errors === 'object' && !Array.isArray(errors)) {
    return Object.entries(errors)
      .map(([field, messages]) => {
        const text = Array.isArray(messages) ? messages.join(' ') : String(messages)
        return `${field}: ${text}`
      })
      .join(' ')
  }

  if (typeof detail === 'string')
    return detail

  return 'Unknown error'
}

function formatJoined(value?: string) {
  if (!value)
    return 'Unknown'

  return new Intl.DateTimeFormat('en-KE', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function normalizeRole(role?: string) {
  if (role === 'delivery_agent')
    return 'Delivery Agent'
  return role ? role.charAt(0).toUpperCase() + role.slice(1) : 'Unknown'
}

function mapUserToRow(user: AdminUserItem): UserTableRow {
  return {
    id: String(user.id),
    name: user.full_name || user.email,
    email: user.email,
    status: user.is_active ? 'Active' : 'Suspended',
    role: normalizeRole(user.role),
    joined: formatJoined((user as any).created_at),
    phone: user.phone_number || '',
    emailVerified: user.email_verified,
    roleValue: user.role,
    isActive: user.is_active,
    raw: user,
  }
}

export function useUser() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getUsers() {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ items: AdminUserItem[] }>('/admin/users', {
        method: 'GET',
      })
      return {
        success: true,
        data: {
          items: (result.items || []).map(mapUserToRow),
          raw: result.items || [],
        },
      }
    }
    catch (err: any) {
      error.value = extractApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function updateUserRole(userId: number | string, role: string) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: { id: number, email: string, role: string } }>(`/admin/users/${userId}/role`, {
        method: 'PATCH',
        body: { role },
      })
      return { success: true, data: result.item }
    }
    catch (err: any) {
      error.value = extractApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function updateUserActive(userId: number | string, isActive: boolean) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: { id: number, email: string, is_active: boolean } }>(`/admin/users/${userId}/active`, {
        method: 'PATCH',
        body: { is_active: isActive },
      })
      return { success: true, data: result.item }
    }
    catch (err: any) {
      error.value = extractApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  return {
    error,
    getUsers,
    loading,
    updateUserActive,
    updateUserRole,
  }
}
