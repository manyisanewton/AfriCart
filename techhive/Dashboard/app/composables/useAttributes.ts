export interface AttributeItem {
  id: number
  product_class_id: number
  name: string
  code: string
  type: string
  required: boolean
  option_group_id: number | null
}

export interface AttributePayload {
  product_class_id: number
  name: string
  code?: string
  type: string
  required: boolean
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

function slugifyCode(value: string) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

export function useAttributes() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getAttributes(params: { page?: number, pageSize?: number } = {}) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: AttributeItem[] }>('/admin/attributes', {
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

  async function createAttribute(payload: AttributePayload) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: AttributeItem }>('/admin/attributes', {
        method: 'POST',
        body: {
          product_type_id: payload.product_class_id,
          name: payload.name,
          code: payload.code?.trim() || slugifyCode(payload.name),
          type: payload.type,
          required: payload.required,
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

  async function updateAttribute(id: number, payload: Partial<AttributePayload>) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: AttributeItem }>(`/admin/attributes/${id}`, {
        method: 'PATCH',
        body: {
          ...(payload.name !== undefined ? { name: payload.name } : {}),
          ...(payload.code !== undefined || payload.name !== undefined
            ? { code: payload.code?.trim() || slugifyCode(payload.name || '') }
            : {}),
          ...(payload.type !== undefined ? { type: payload.type } : {}),
          ...(payload.required !== undefined ? { required: payload.required } : {}),
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

  async function deleteAttribute(id: number) {
    loading.value = true
    error.value = null

    try {
      await request(`/admin/attributes/${id}`, {
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
    createAttribute,
    deleteAttribute,
    getAttributes,
    updateAttribute,
  }
}
