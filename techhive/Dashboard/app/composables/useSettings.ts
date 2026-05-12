export interface PlatformSettingItem {
  id: number
  key: string
  value: string
  description: string | null
  is_public: boolean
  updated_by_user_id: number | null
  updated_at: string
}

export interface RecommendationSettingItem {
  key: string
  db_key: string
  value: number
  default: number
  min: number
  max: number
}

export interface NotificationDeliveryItem {
  id: number
  notification_id: number
  channel: string
  status: string
  recipient: string
  subject: string | null
  template: string | null
  category: string | null
  reason: string | null
  retry_count: number
  last_attempted_at: string | null
  created_at: string
  updated_at: string
}

export interface MpesaLogSnapshot {
  path: string
  exists: boolean
  lines: string[]
  line_count: number
}

export interface StalePaymentReconciliationResult {
  count: number
  awaiting_confirmation_count: number
  provider_failed_count: number
  manual_review_count: number
  timed_out_count: number
  items: Array<Record<string, any>>
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

export function useSettings() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getPlatformSettings() {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ items: PlatformSettingItem[] }>('/admin/settings', { method: 'GET' })
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

  async function createPlatformSetting(payload: {
    key: string
    value: string
    description?: string | null
    is_public?: boolean
  }) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: PlatformSettingItem }>('/admin/settings', {
        method: 'POST',
        body: payload,
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

  async function updatePlatformSetting(key: string, payload: {
    value?: string
    description?: string | null
    is_public?: boolean
  }) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: PlatformSettingItem }>(`/admin/settings/${key}`, {
        method: 'PATCH',
        body: payload,
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

  async function getRecommendationSettings() {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ items: RecommendationSettingItem[] }>('/admin/recommendations/settings', {
        method: 'GET',
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

  async function updateRecommendationSettings(payload: Record<string, number>) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ items: RecommendationSettingItem[] }>('/admin/recommendations/settings', {
        method: 'PATCH',
        body: payload,
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

  async function getNotificationDeliveries(params: { status?: string, channel?: string } = {}) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ items: NotificationDeliveryItem[] }>('/admin/notification-deliveries', {
        method: 'GET',
        query: params,
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

  async function retryNotificationDelivery(deliveryId: number) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: NotificationDeliveryItem } & Record<string, any>>('/admin/notification-deliveries/retry', {
        method: 'POST',
        body: { delivery_id: deliveryId },
      })
      return { success: true, data: result }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function reconcileStalePayments(limit: number) {
    loading.value = true
    error.value = null
    try {
      const result = await request<StalePaymentReconciliationResult>('/admin/payments/reconcile-stale', {
        method: 'POST',
        body: { limit },
      })
      return { success: true, data: result }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function getMpesaLogs(limit = 100) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: MpesaLogSnapshot }>('/admin/logs/mpesa', {
        method: 'GET',
        query: { limit },
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
    createPlatformSetting,
    error,
    getMpesaLogs,
    getNotificationDeliveries,
    getPlatformSettings,
    getRecommendationSettings,
    loading,
    reconcileStalePayments,
    retryNotificationDelivery,
    updatePlatformSetting,
    updateRecommendationSettings,
  }
}
