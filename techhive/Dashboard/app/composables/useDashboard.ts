export interface AdminDashboardOrder {
  id: number
  order_number: string
  status: string
  total_amount: string
  currency: string
  created_at: string
}

export interface AdminDashboardTopProduct {
  product_id: number
  product_name: string
  product_slug: string
  units_sold: number
  revenue: string
  links?: Record<string, string>
}

export interface AdminDashboardSupportTicket {
  id: number
  subject: string
  status: string
  created_at: string
}

export interface AdminDashboardAuditEvent {
  id: number
  action: string
  entity_type: string
  entity_id: number
  created_at: string
}

export interface AdminDashboardResponse {
  persona: 'admin'
  generated_at: string
  summary: {
    user_count: number
    active_user_count: number
    vendor_count: number
    approved_vendor_count: number
    pending_vendor_count: number
    pending_kyc_count: number
    open_support_ticket_count: number
    order_count: number
    pending_order_count: number
    payment_count: number
    failed_payment_count: number
    links?: Record<string, string>
  }
  catalog: {
    product_count: number
    inactive_product_count: number
    low_stock_product_count: number
    top_products: AdminDashboardTopProduct[]
    links?: Record<string, string>
  }
  commerce: {
    total_revenue: string
    recent_orders: AdminDashboardOrder[]
    recent_payments: any[]
    recent_refunds: any[]
    links?: Record<string, string>
  }
  operations: {
    recent_support_tickets: AdminDashboardSupportTicket[]
    pending_kyc_submissions: any[]
    failed_notification_deliveries: any[]
    links?: Record<string, string>
  }
  audit: {
    latest_events: AdminDashboardAuditEvent[]
    links?: Record<string, string>
  }
}

export function useDashboard() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getDashboard() {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: AdminDashboardResponse }>('/admin/dashboard', {
        method: 'GET',
      })
      return { success: true, data: result.item }
    }
    catch (err: any) {
      error.value = err?.data?.error?.message || err?.message || 'Unknown error'
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  return {
    error,
    getDashboard,
    loading,
  }
}
