export interface AdminVendorItem {
  id: number
  business_name: string
  slug: string
  status: 'pending' | 'approved' | 'suspended' | 'rejected'
  is_verified: boolean
  user_id: number
}

export interface VendorDetailItem extends AdminVendorItem {
  description: string | null
  phone_number: string
  support_email: string
  created_at: string | null
  updated_at: string | null
  user: {
    id: number
    email: string
    full_name: string
    phone_number: string | null
    role: string
    created_at: string | null
  } | null
  kyc_submission: {
    id: number
    vendor_id: number
    legal_business_name: string
    registration_number: string
    tax_id: string | null
    contact_person_name: string
    contact_person_id_number: string
    document_url: string
    status: 'not_submitted' | 'pending' | 'approved' | 'rejected'
    admin_note: string | null
    submitted_at: string | null
    reviewed_at: string | null
    updated_at: string | null
  } | null
  metrics: {
    products: number
    active_products: number
    low_stock_products: number
    orders: number
    reviews: number
  }
  recent_products: Array<{
    id: number
    name: string
    slug: string
    sku: string
    stock_quantity: number
    is_active: boolean
    created_at: string | null
  }>
  recent_orders: Array<{
    id: number
    order_number: string
    status: string
    delivery_status: string
    total_amount: string
    currency: string
    created_at: string | null
  }>
}

export interface VendorTableRow {
  id: number
  businessName: string
  slug: string
  status: string
  isVerified: boolean
  userId: number
  raw?: AdminVendorItem
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

function formatStatus(value: string) {
  return value
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function mapVendorToRow(vendor: AdminVendorItem): VendorTableRow {
  return {
    id: vendor.id,
    businessName: vendor.business_name,
    slug: vendor.slug,
    status: formatStatus(vendor.status),
    isVerified: Boolean(vendor.is_verified),
    userId: vendor.user_id,
    raw: vendor,
  }
}

export function useVendor() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getVendors() {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: AdminVendorItem[] }>('/admin/vendors', {
        method: 'GET',
      })

      return {
        success: true,
        data: {
          items: (result.items || []).map(mapVendorToRow),
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

  async function getVendor(id: number | string) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: VendorDetailItem }>(`/admin/vendors/${id}`, {
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

  async function updateVendorStatus(id: number | string, status: string) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: AdminVendorItem }>(`/admin/vendors/${id}/status`, {
        method: 'PATCH',
        body: { status },
      })

      return { success: true, data: mapVendorToRow(result.item), raw: result.item }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function updateVendorKycStatus(id: number | string, status: string, admin_note: string) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: VendorDetailItem['kyc_submission'] }>(`/admin/kyc-submissions/${id}/status`, {
        method: 'PATCH',
        body: { status, admin_note },
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
    getVendor,
    getVendors,
    loading,
    updateVendorKycStatus,
    updateVendorStatus,
  }
}
