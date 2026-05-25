export interface StockAlertItem {
  id: number
  status: string
  threshold: number
  date_created: string
  date_closed: string | null
  stockrecord: {
    id: number
    partner_sku: string
    num_in_stock: number
    product_id: number
    product_title: string
  }
}

function readApiError(err: any) {
  return err?.data?.error?.detail
    || err?.data?.error?.message
    || err?.data?.detail
    || err?.message
    || 'Unknown error'
}

export function useStockAlerts() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getStockAlerts(params: { page?: number, pageSize?: number } = {}) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: StockAlertItem[] }>('/admin/stock-alerts', {
        method: 'GET',
      })
      return {
        success: true,
        data: {
          results: result.items || [],
          pagination: {
            page: params.page || 1,
            page_size: params.pageSize || 200,
            total: (result.items || []).length,
            num_pages: 1,
          },
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

  async function updateStockAlert(id: number, payload: { status: string }) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: StockAlertItem }>(`/admin/stock-alerts/${id}`, {
        method: 'PATCH',
        body: payload,
      })
      return { success: true, data: result.item }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value, errors: err?.data?.error?.errors || null }
    }
    finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    getStockAlerts,
    updateStockAlert,
  }
}
