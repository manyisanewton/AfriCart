export interface AdminSupportTicketItem {
  id: number
  user_id: number | null
  name: string
  email: string
  phone_number: string | null
  subject: string
  message: string
  category: string
  status: 'open' | 'in_progress' | 'resolved' | 'closed'
  admin_note: string | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface SupportTicketRow {
  id: number
  customerName: string
  email: string
  phoneNumber: string
  subject: string
  category: string
  status: string
  createdAt: string
  updatedAt: string
  resolvedAt: string | null
  adminNote: string
  message: string
  raw?: AdminSupportTicketItem
}

export interface UpdateSupportTicketPayload {
  status: string
  admin_note: string
}

function readApiError(err: any) {
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

  return typeof detail === 'string' ? detail : 'Unknown error'
}

function mapTicketToRow(ticket: AdminSupportTicketItem): SupportTicketRow {
  return {
    id: ticket.id,
    customerName: ticket.name || 'Unknown customer',
    email: ticket.email || '',
    phoneNumber: ticket.phone_number || '',
    subject: ticket.subject,
    category: ticket.category || 'general',
    status: ticket.status,
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at,
    resolvedAt: ticket.resolved_at,
    adminNote: ticket.admin_note || '',
    message: ticket.message,
    raw: ticket,
  }
}

export function useSupport() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getSupportTickets(status?: string) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: AdminSupportTicketItem[] }>('/admin/support-tickets', {
        method: 'GET',
        query: status ? { status } : undefined,
      })

      return {
        success: true,
        data: {
          items: (result.items || []).map(mapTicketToRow),
          raw: result.items || [],
        },
      }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function updateSupportTicketStatus(id: number | string, payload: UpdateSupportTicketPayload) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: AdminSupportTicketItem }>(`/admin/support-tickets/${id}/status`, {
        method: 'PATCH',
        body: payload,
      })

      return { success: true, data: mapTicketToRow(result.item), raw: result.item }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  return {
    error,
    getSupportTickets,
    loading,
    updateSupportTicketStatus,
  }
}
