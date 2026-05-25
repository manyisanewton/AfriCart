export interface CategoryItem {
  id: number
  name: string
  slug: string
  description: string
  is_public: boolean
  parent_id: number | null
  depth: number
  numchild: number
  is_active?: boolean
}

export interface CategoryPayload {
  name: string
  slug?: string
  description?: string
  is_public: boolean
  parent_id?: number | null
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

function mapCategory(category: any): CategoryItem {
  return {
    id: category.id,
    name: category.name,
    slug: category.slug || '',
    description: category.description || '',
    is_public: Boolean(category.is_active),
    is_active: Boolean(category.is_active),
    parent_id: category.parent_id ?? null,
    depth: Number(category.depth || 1),
    numchild: Number(category.numchild || 0),
  }
}

export function useCategories() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getCategories(params: { page?: number, pageSize?: number } = {}) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ items: any[] }>('/admin/categories', {
        method: 'GET',
      })
      const items = (result.items || []).map(mapCategory)
      return {
        success: true,
        data: {
          results: items,
          pagination: {
            page: params.page || 1,
            page_size: params.pageSize || 200,
            total: items.length,
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

  async function createCategory(payload: CategoryPayload) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: any }>('/admin/categories', {
        method: 'POST',
        body: {
          name: payload.name,
          slug: payload.slug?.trim() || slugify(payload.name),
          description: payload.description?.trim() || null,
          parent_id: payload.parent_id ?? null,
        },
      })
      return { success: true, data: mapCategory(result.item) }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value, errors: err?.data?.error?.errors || null }
    }
    finally {
      loading.value = false
    }
  }

  async function updateCategory(id: number, payload: Partial<CategoryPayload>) {
    loading.value = true
    error.value = null

    try {
      const result = await request<{ item: any }>(`/admin/categories/${id}`, {
        method: 'PATCH',
        body: {
          ...(payload.name !== undefined ? { name: payload.name } : {}),
          ...(payload.slug !== undefined ? { slug: payload.slug?.trim() || slugify(payload.name || '') } : {}),
          ...(payload.description !== undefined ? { description: payload.description?.trim() || null } : {}),
          ...(payload.is_public !== undefined ? { is_active: payload.is_public } : {}),
          ...(payload.parent_id !== undefined ? { parent_id: payload.parent_id } : {}),
        },
      })
      return { success: true, data: mapCategory(result.item) }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value, errors: err?.data?.error?.errors || null }
    }
    finally {
      loading.value = false
    }
  }

  async function deleteCategory(id: number) {
    loading.value = true
    error.value = null

    try {
      await request(`/admin/categories/${id}`, {
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
    createCategory,
    deleteCategory,
    getCategories,
    updateCategory,
  }
}
