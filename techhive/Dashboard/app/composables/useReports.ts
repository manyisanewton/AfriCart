export interface AdminOverviewReport {
  summary: Record<string, any>
  breakdowns: {
    orders: Record<string, number>
    payments: Record<string, number>
    vendors: Record<string, number>
    support_tickets: Record<string, number>
    refunds: Record<string, number>
  }
}

export interface VendorPerformanceItem {
  vendor_id: number
  business_name: string
  slug: string
  status: string
  revenue: string
  units_sold: number
  order_count: number
  product_count: number
  active_product_count: number
  low_stock_count: number
}

export interface AdminOperationsQueues {
  summary: {
    pending_vendor_count: number
    pending_kyc_count: number
    open_support_ticket_count: number
    pending_refund_count: number
    failed_notification_delivery_count: number
    stale_pending_payment_count: number
    low_stock_product_count: number
  }
  queues: Record<string, number[]>
}

function readApiError(err: any) {
  return err?.data?.error?.detail
    || err?.data?.error?.message
    || err?.data?.detail
    || err?.message
    || 'Unknown error'
}

export function useReports() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getOverviewReport() {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: AdminOverviewReport }>('/admin/reports/overview', {
        method: 'GET',
      })
      return { success: true, data: result.item }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function getVendorPerformance(limit = 10) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: VendorPerformanceItem[] }>('/admin/reports/vendors-performance', {
        method: 'GET',
        query: { limit },
      })
      return { success: true, data: result.items || [] }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function getOperationsQueues() {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: AdminOperationsQueues }>('/admin/operations/queues', {
        method: 'GET',
      })
      return { success: true, data: result.item }
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
    getOperationsQueues,
    getOverviewReport,
    getVendorPerformance,
    loading,
  }
}
