export interface AdminVendorItem {
  id: number
  business_name: string
  slug: string
  status: 'pending' | 'approved' | 'suspended' | 'rejected'
  is_verified: boolean
  user_id: number
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

  return {
    error,
    getVendors,
    loading,
    updateVendorStatus,
  }
}
