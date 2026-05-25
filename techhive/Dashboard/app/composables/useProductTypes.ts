export interface ProductTypeItem {
  id: number
  name: string
  slug: string
  requires_shipping: boolean
  track_stock: boolean
}

export interface ProductTypePayload {
  name: string
  slug?: string
  requires_shipping: boolean
  track_stock: boolean
}

function readApiError(err: any) {
  const details = err?.data?.error?.details
  if (details && typeof details === 'object') {
    return Object.entries(details)
      .map(([field, message]) => `${field}: ${Array.isArray(message) ? message.join(' ') : String(message)}`)
      .join(' ')
  }

  return err?.data?.error?.detail
    || err?.data?.error?.message
    || err?.data?.detail
    || err?.message
    || 'Unknown error'
}

function slugify(value: string) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function useProductTypes() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getProductTypes(params: { page?: number, pageSize?: number } = {}) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: ProductTypeItem[] }>('/admin/product-types', {
        method: 'GET',
      })
      return {
        success: true,
        data: {
          results: result.items || [],
          pagination: {
            page: params.page || 1,
            page_size: params.pageSize || 100,
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

  async function createProductType(payload: ProductTypePayload) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: ProductTypeItem }>('/admin/product-types', {
        method: 'POST',
        body: {
          ...payload,
          slug: payload.slug?.trim() || slugify(payload.name),
        },
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

  async function updateProductType(id: number, payload: Partial<ProductTypePayload>) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: ProductTypeItem }>(`/admin/product-types/${id}`, {
        method: 'PATCH',
        body: {
          ...payload,
          ...(payload.slug !== undefined || payload.name !== undefined
            ? { slug: payload.slug?.trim() || slugify(payload.name || '') }
            : {}),
        },
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

  async function deleteProductType(id: number) {
    loading.value = true
    error.value = null

    try {
      await request(`/admin/product-types/${id}`, {
        method: 'DELETE',
      })
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

  return {
    loading,
    error,
    createProductType,
    deleteProductType,
    getProductTypes,
    updateProductType,
  }
}
