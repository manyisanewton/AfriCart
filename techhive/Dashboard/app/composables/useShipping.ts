export interface ShippingZoneItem {
  id: number
  name: string
  city: string
  fee: string
  estimated_days_min: number
  estimated_days_max: number
  is_active: boolean
  created_at: string | null
}

export interface ShippingZonePayload {
  name: string
  city: string
  fee: number | string
  estimated_days_min: number | string
  estimated_days_max: number | string
  is_active?: boolean
}

export interface DeliveryAgentItem {
  id: number
  display_name: string
  phone_number: string
  is_active: boolean
  active_assignments: number
}

export interface ShippingOrderItem {
  id: number
  order_number: string
  status: string
  delivery_status: string
  tracking_token: string
  delivery_zone_name: string | null
  currency: string
  total_amount: string
  shipping_amount: string
  shipping_address: {
    name: string
    phone_number: string
    country: string
    city: string
    state_or_county: string | null
    postal_code: string | null
    address_line_1: string
    address_line_2: string | null
  }
  delivery_agent?: {
    id: number
    display_name: string
    phone_number: string
  }
  notes: string | null
  created_at: string
}

function readApiError(err: any) {
  const detail = err?.data?.error?.message || err?.data?.detail || err?.message
  const errors = err?.data?.error?.details || err?.data?.error?.errors || err?.data

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

export function useShipping() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getZones() {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: ShippingZoneItem[] }>('/admin/shipping/zones', { method: 'GET' })
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

  async function createZone(payload: ShippingZonePayload) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: ShippingZoneItem }>('/admin/shipping/zones', {
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

  async function updateZone(id: number | string, payload: Partial<ShippingZonePayload>) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: ShippingZoneItem }>(`/admin/shipping/zones/${id}`, {
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

  async function deleteZone(id: number | string) {
    loading.value = true
    error.value = null

    try {
      await request(`/admin/shipping/zones/${id}`, { method: 'DELETE' })
      return { success: true }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function getDeliveryAgents() {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: DeliveryAgentItem[] }>('/admin/delivery-agents', { method: 'GET' })
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

  async function getShippingOrders() {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: ShippingOrderItem[] }>('/admin/shipping/orders', { method: 'GET' })
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

  async function updateOrderShipping(id: number | string, payload: {
    delivery_agent_id?: number | null
    delivery_status?: string
    tracking_token?: string
    notes?: string
  }) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: ShippingOrderItem }>(`/admin/orders/${id}`, {
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

  return {
    loading,
    error,
    getZones,
    createZone,
    updateZone,
    deleteZone,
    getDeliveryAgents,
    getShippingOrders,
    updateOrderShipping,
  }
}
