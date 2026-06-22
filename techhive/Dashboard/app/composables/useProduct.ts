export interface AdminProductItem {
  id: number
  name: string
  slug: string
  sku: string
  short_description: string | null
  description: string | null
  price: string | null
  compare_at_price: string | null
  currency: string
  stock_quantity: number
  low_stock_threshold: number
  weight_grams: number | null
  dimensions_text: string | null
  in_stock: boolean
  is_active: boolean
  is_featured: boolean
  average_rating: number | null
  review_count: number
  category: {
    id: number
    name: string
    slug: string
    description?: string | null
    is_active?: boolean
  }
  brand: {
    id: number
    name: string
    slug: string
    description?: string | null
    website_url?: string | null
    logo_url?: string | null
    is_active?: boolean
  }
  vendor: {
    id: number
    business_name: string
    slug: string
    status: string
  }
  primary_image?: {
    id: number
    image_url: string
    alt_text?: string | null
    is_primary?: boolean
    sort_order?: number
  } | null
}

export interface ProductListParams {
  search?: string
  status?: 'active' | 'draft' | ''
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

function mapProductToRow(product: AdminProductItem) {
  return {
    id: product.id,
    name: product.name,
    sku: product.sku || '',
    price: Number(product.price || 0),
    currency: product.currency || 'KES',
    status: product.is_active ? 'Active' : 'Draft',
    category: product.category?.name || 'Uncategorized',
      stock: Number(product.stock_quantity || 0),
      lowStockThreshold: Number(product.low_stock_threshold ?? 5),
      weight: product.weight_grams === null || product.weight_grams === undefined ? null : Number(product.weight_grams),
      dimensions: product.dimensions_text || '',
      imageUrl: mediaUrl(product.primary_image?.image_url || ''),
    updatedAt: '',
    vendorName: product.vendor?.business_name || 'Unknown vendor',
    rating: product.average_rating,
    reviewCount: Number(product.review_count || 0),
    isActive: Boolean(product.is_active),
    raw: product,
  }
}

function slugify(value: string) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function useProduct() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const { request } = useBackendApi()

  async function getProducts(params: ProductListParams = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await request<{ items: AdminProductItem[] }>('/admin/products', {
        method: 'GET',
      })

      let items = (response.items || []).map(mapProductToRow)

      const query = String(params.search || '').trim().toLowerCase()
      if (query) {
        items = items.filter(product =>
          product.name.toLowerCase().includes(query)
          || product.sku.toLowerCase().includes(query)
          || product.category.toLowerCase().includes(query)
          || product.vendorName.toLowerCase().includes(query),
        )
      }

      if (params.status === 'active')
        items = items.filter(product => product.isActive)
      else if (params.status === 'draft')
        items = items.filter(product => !product.isActive)

      return {
        success: true,
        data: {
          results: items,
          pagination: {
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

  async function getCategoryOptions() {
    try {
      const result = await request<{ items: Array<{ id: number, name: string }> }>('/categories', { method: 'GET' })
      return {
        success: true,
        data: (result.items || []).map(category => ({
          label: category.name,
          value: String(category.id),
        })),
      }
    }
    catch (err: any) {
      return { success: false, error: readApiError(err), data: [] }
    }
  }

  async function getBrandOptions() {
    try {
      const result = await request<{ items: Array<{ id: number, name: string }> }>('/brands', { method: 'GET' })
      return {
        success: true,
        data: (result.items || []).map(brand => ({
          label: brand.name,
          value: String(brand.id),
        })),
      }
    }
    catch (err: any) {
      return { success: false, error: readApiError(err), data: [] }
    }
  }

  async function getVendorOptions() {
    try {
      const result = await request<{ items: Array<{ id: number, business_name: string, status: string }> }>('/admin/vendors', {
        method: 'GET',
      })
      return {
        success: true,
        data: (result.items || []).map(vendor => ({
          label: `${vendor.business_name} (${vendor.status})`,
          value: String(vendor.id),
        })),
      }
    }
    catch (err: any) {
      return { success: false, error: readApiError(err), data: [] }
    }
  }

  function mapFormToPayload(data: Record<string, any>) {
    const name = String(data.name || '').trim()
    const slug = slugify(name)
    const sku = String(data.sku || '').trim() || slug.toUpperCase().replace(/-/g, '-')

    return {
      vendor_id: Number(data.vendor),
      category_id: Number(data.category),
      brand_id: Number(data.brand),
      name,
      slug,
      sku,
      short_description: String(data.description || '').trim().slice(0, 255) || null,
      description: String(data.description || '').trim() || null,
      price: Number(data.price || 0),
      compare_at_price: data.originalPrice === undefined ? null : Number(data.originalPrice || 0),
      currency: data.currency || 'KES',
      stock_quantity: Number(data.stock || 0),
      low_stock_threshold: Number(data.lowStockThreshold ?? 5),
      weight_grams: data.weight === null || data.weight === undefined || data.weight === '' ? null : Number(data.weight),
      dimensions_text: String(data.dimensions || '').trim() || null,
      is_active: data.status === 'active',
      is_featured: false,
    }
  }

  function mapProductDetailToForm(product: AdminProductItem) {
    return {
      id: product.id,
      name: product.name,
      description: product.description || '',
      price: Number(product.price || 0),
      currency: product.currency || 'KES',
      originalPrice: product.compare_at_price ? Number(product.compare_at_price) : undefined,
      chargeTax: true,
      sku: product.sku || '',
      stock: Number(product.stock_quantity || 0),
      lowStockThreshold: Number(product.low_stock_threshold ?? 5),
      weight: product.weight_grams === null || product.weight_grams === undefined ? null : Number(product.weight_grams),
      dimensions: product.dimensions_text || '',
      status: product.is_active ? 'active' : 'draft',
      vendor: String(product.vendor?.id || ''),
      category: String(product.category?.id || ''),
      brand: String(product.brand?.id || ''),
      tags: '',
      images: (product.images || []).map((image: any) => ({
        id: image.id,
        src: mediaUrl(image.image_url),
        alt: image.alt_text || '',
      })),
    }
  }

  async function createProduct(data: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: AdminProductItem }>('/admin/products', {
        method: 'POST',
        body: mapFormToPayload(data as Record<string, any>),
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

  async function getProduct(id: number | string) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: AdminProductItem }>(`/admin/products/${id}`, {
        method: 'GET',
      })
      return { success: true, data: mapProductDetailToForm(result.item), raw: result.item }
    }
    catch (err: any) {
      error.value = readApiError(err)
      return { success: false, error: error.value }
    }
    finally {
      loading.value = false
    }
  }

  async function updateProduct(id: number | string, data: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: AdminProductItem }>(`/admin/products/${id}`, {
        method: 'PATCH',
        body: mapFormToPayload(data as Record<string, any>),
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

  async function deleteProduct(id: number | string) {
    loading.value = true
    error.value = null
    try {
      await request(`/admin/products/${id}`, {
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

  async function uploadProductImage(productId: number | string, image: ProductImageItem) {
    if (!image.file)
      return { success: true, data: image }

    const formData = new FormData()
    formData.append('file', image.file)
    formData.append('alt', image.alt || '')

    try {
      const result = await request<{ item: { id: number, image_url: string, alt_text: string | null } }>(`/admin/products/${productId}/images`, {
        method: 'POST',
        body: formData,
      })
      return {
        success: true,
        data: {
          id: result.item.id,
          src: mediaUrl(result.item.image_url),
          alt: result.item.alt_text || '',
        },
      }
    }
    catch (err: any) {
      return { success: false, error: readApiError(err) }
    }
  }

  async function deleteProductImage(productId: number | string, imageId: number) {
    try {
      await request(`/admin/products/${productId}/images/${imageId}`, {
        method: 'DELETE',
      })
      return { success: true }
    }
    catch (err: any) {
      return { success: false, error: readApiError(err) }
    }
  }

  async function syncProductImages(productId: number | string, nextImages: ProductImageItem[], previousImages: ProductImageItem[] = []) {
    const previousIds = new Set(previousImages.map(image => image.id).filter((id): id is number => typeof id === 'number'))
    const nextIds = new Set(nextImages.map(image => image.id).filter((id): id is number => typeof id === 'number'))

    const removedIds = [...previousIds].filter(id => !nextIds.has(id))
    for (const imageId of removedIds) {
      const deleteResult = await deleteProductImage(productId, imageId)
      if (!deleteResult.success)
        return deleteResult
    }

    const unsavedImages = nextImages.filter(image => image.file)
    const uploadedImages: ProductImageItem[] = []
    for (const image of unsavedImages) {
      const uploadResult = await uploadProductImage(productId, image)
      if (!uploadResult.success)
        return uploadResult
      uploadedImages.push(uploadResult.data as ProductImageItem)
    }

    const persistedImages = nextImages
      .filter(image => typeof image.id === 'number' && !image.file)
      .concat(uploadedImages)

    return { success: true, data: persistedImages }
  }

  async function updateProductActive(id: number | string, isActive: boolean) {
    loading.value = true
    error.value = null
    try {
      const result = await request<{ item: AdminProductItem }>(`/admin/products/${id}/active`, {
        method: 'PATCH',
        body: { is_active: isActive },
      })
      return { success: true, data: mapProductToRow(result.item), raw: result.item }
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
    createProduct,
    deleteProduct,
    error,
    getBrandOptions,
    getCategoryOptions,
    getProduct,
    getProducts,
    getVendorOptions,
    loading,
    syncProductImages,
    updateProduct,
    updateProductActive,
  }
}
