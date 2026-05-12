import type { OrderTableRow } from '~/types/OrderTableRow'

export interface AdminOrderItem {
  id: number
  order_number: string
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled'
  delivery_status: string
  tracking_token: string
  delivery_zone_name: string | null
  currency: string
  subtotal: string
  discount_amount: string
  promo_code: string | null
  shipping_amount: string
  total_amount: string
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
  notes: string | null
  created_at: string
  items?: Array<{
    id: number
    product_id: number
    product_name: string
    product_slug: string
    sku: string
    quantity: number
    unit_price: string
    line_total: string
  }>
}

export interface UpdateOrderStatusPayload {
  status: string
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

function formatDate(value?: string) {
  if (!value)
    return 'Unknown'

  return new Intl.DateTimeFormat('en-KE', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function mapOrderToRow(order: AdminOrderItem): OrderTableRow {
  const itemCount = (order.items || []).reduce((sum, item) => sum + Number(item.quantity || 0), 0)

  return {
    id: order.id,
    orderNumber: order.order_number,
    customerName: order.shipping_address?.name || 'Unknown customer',
    phoneNumber: order.shipping_address?.phone_number || '',
    city: order.shipping_address?.city || '',
    status: order.status,
    deliveryStatus: order.delivery_status,
    itemCount,
    totalAmount: Number(order.total_amount || 0),
    currency: order.currency || 'KES',
    createdAt: order.created_at,
    raw: order,
  }
}

export function useOrder() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getOrders() {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ items: AdminOrderItem[] }>('/admin/orders', {
        method: 'GET',
      })
      return {
        success: true,
        data: {
          items: (result.items || []).map(mapOrderToRow),
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

  async function updateOrderStatus(id: number | string, payload: UpdateOrderStatusPayload) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: AdminOrderItem }>(`/admin/orders/${id}/status`, {
        method: 'PATCH',
        body: payload,
      })
      return { success: true, data: mapOrderToRow(result.item), raw: result.item }
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
    getOrders,
    loading,
    updateOrderStatus,
  }
}
