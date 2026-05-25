export interface OptionItem {
  id: number
  name: string
  code: string
  type: string
  required: boolean
  help_text: string
  order: number
}

export interface OptionPayload {
  name: string
  code?: string
  type: string
  required: boolean
  help_text?: string
  order: number
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

export function useOptions() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getOptions(params: { page?: number, pageSize?: number } = {}) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: OptionItem[] }>('/admin/options', {
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

  async function createOption(payload: OptionPayload) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: OptionItem }>('/admin/options', {
        method: 'POST',
        body: {
          ...payload,
          code: payload.code?.trim() || slugifyCode(payload.name),
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

  async function updateOption(id: number, payload: Partial<OptionPayload>) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: OptionItem }>(`/admin/options/${id}`, {
        method: 'PATCH',
        body: {
          ...payload,
          ...(payload.code !== undefined || payload.name !== undefined
            ? { code: payload.code?.trim() || slugifyCode(payload.name || '') }
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

  async function deleteOption(id: number) {
    loading.value = true
    error.value = null

    try {
      await request(`/admin/options/${id}`, {
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
    createOption,
    deleteOption,
    getOptions,
    updateOption,
  }
}
