<script setup lang="ts">
import type { CmsPageItem, CmsPagePayload } from '~/composables/usePages'

const toast = useToast()
const { createPage, deletePage, getPage, getPages, updatePage } = usePages()

const pages = ref<CmsPageItem[]>([])
const selectedPage = ref<CmsPageItem | null>(null)
const editingPage = ref<CmsPageItem | null>(null)
const pendingDeletePage = ref<CmsPageItem | null>(null)
const totalItems = ref(0)
const searchQuery = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const editorOpen = ref(false)
const saveError = ref('')

const form = reactive({
  url: '',
  page_key: '',
  page_type: 'custom',
  status: 'draft',
  title: '',
  excerpt: '',
  content: '',
  meta_title: '',
  meta_description: '',
  registration_required: false,
  is_system_page: false,
  allow_indexing: true,
})

const pageTypeOptions = [
  { label: 'Custom', value: 'custom' },
  { label: 'Policy', value: 'policy' },
  { label: 'Help', value: 'help' },
  { label: 'Marketing', value: 'marketing' },
  { label: 'Legal', value: 'legal' },
]

const pageStatusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Published', value: 'published' },
  { label: 'Archived', value: 'archived' },
]

const filteredPages = computed(() => {
  const search = searchQuery.value.trim().toLowerCase()
  return pages.value.filter((page) => {
    return !search
      || page.title.toLowerCase().includes(search)
      || page.url.toLowerCase().includes(search)
      || page.content.toLowerCase().includes(search)
      || String(page.id).includes(search)
  })
})

const publicPageCount = computed(() => pages.value.filter(page => !page.registration_required).length)
const protectedPageCount = computed(() => pages.value.filter(page => page.registration_required).length)
const publishedPageCount = computed(() => pages.value.filter(page => page.status === 'published').length)
const systemPageCount = computed(() => pages.value.filter(page => page.is_system_page).length)

function statusColor(status: string) {
  if (status === 'published')
    return 'success'
  if (status === 'archived')
    return 'neutral'
  return 'warning'
}

function typeColor(type: string) {
  if (type === 'policy' || type === 'legal')
    return 'error'
  if (type === 'help')
    return 'primary'
  if (type === 'marketing')
    return 'warning'
  return 'neutral'
}

function resetForm() {
  editingPage.value = null
  saveError.value = ''
  form.url = ''
  form.page_key = ''
  form.page_type = 'custom'
  form.status = 'draft'
  form.title = ''
  form.excerpt = ''
  form.content = ''
  form.meta_title = ''
  form.meta_description = ''
  form.registration_required = false
  form.is_system_page = false
  form.allow_indexing = true
}

function fillForm(page: CmsPageItem) {
  form.url = page.url || ''
  form.page_key = page.page_key || ''
  form.page_type = page.page_type || 'custom'
  form.status = page.status || 'draft'
  form.title = page.title || ''
  form.excerpt = page.excerpt || ''
  form.content = page.content || ''
  form.meta_title = page.meta_title || ''
  form.meta_description = page.meta_description || ''
  form.registration_required = !!page.registration_required
  form.is_system_page = !!page.is_system_page
  form.allow_indexing = page.allow_indexing !== false
}

function normalizeUrl(value: string) {
  const trimmed = value.trim()
  if (!trimmed)
    return ''
  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  return withLeadingSlash.endsWith('/') ? withLeadingSlash : `${withLeadingSlash}/`
}

function excerpt(content: string) {
  const text = (content || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
  return text || 'No content'
}

async function loadPages() {
  isLoading.value = true
  const result = await getPages({ pageSize: 200 })

  if (result.success) {
    pages.value = result.data?.results ?? []
    totalItems.value = result.data?.pagination?.total ?? pages.value.length
    if (selectedPage.value) {
      selectedPage.value = pages.value.find(page => page.id === selectedPage.value?.id) || null
    }
  }
  else {
    pages.value = []
    totalItems.value = 0
    toast.add({ title: 'Could not load pages', description: result.error || 'Please try again.', color: 'error' })
  }

  isLoading.value = false
}

async function openDetail(page: CmsPageItem) {
  selectedPage.value = page
  const result = await getPage(page.id)
  if (result.success && result.data)
    selectedPage.value = result.data
  else if (!result.success)
    toast.add({ title: 'Could not load page detail', description: result.error || 'Please try again.', color: 'error' })
}

function openCreatePage() {
  resetForm()
  editorOpen.value = true
}

function openEditPage(page: CmsPageItem) {
  editingPage.value = page
  fillForm(page)
  saveError.value = ''
  editorOpen.value = true
}

async function submitPage() {
  saveError.value = ''
  const normalizedUrl = normalizeUrl(form.url)
  if (!normalizedUrl) {
    saveError.value = 'URL is required.'
    return
  }
  if (!form.title.trim()) {
    saveError.value = 'Title is required.'
    return
  }

  isSaving.value = true
  const payload: CmsPagePayload = {
    url: normalizedUrl,
    page_key: form.page_key.trim() || null,
    page_type: form.page_type,
    status: form.status,
    title: form.title.trim(),
    excerpt: form.excerpt.trim() || null,
    content: form.content,
    meta_title: form.meta_title.trim() || null,
    meta_description: form.meta_description.trim() || null,
    registration_required: form.registration_required,
    is_system_page: form.is_system_page,
    allow_indexing: form.allow_indexing,
  }
  const result = editingPage.value
    ? await updatePage(editingPage.value.id, payload)
    : await createPage(payload)

  if (result.success && result.data) {
    toast.add({ title: editingPage.value ? 'Page updated' : 'Page created', description: `${result.data.title} was saved.`, color: 'success' })
    editorOpen.value = false
    resetForm()
    await loadPages()
    await openDetail(result.data)
  }
  else {
    saveError.value = result.error || 'Could not save page.'
    toast.add({ title: 'Save failed', description: saveError.value, color: 'error' })
  }

  isSaving.value = false
}

async function confirmDeletePage() {
  if (!pendingDeletePage.value)
    return

  isSaving.value = true
  const page = pendingDeletePage.value
  const result = await deletePage(page.id)

  if (result.success) {
    toast.add({ title: 'Page deleted', description: `${page.title} was removed.`, color: 'success' })
    pendingDeletePage.value = null
    if (selectedPage.value?.id === page.id)
      selectedPage.value = null
    await loadPages()
  }
  else {
    toast.add({ title: 'Delete failed', description: result.error || 'Could not delete page.', color: 'error' })
  }

  isSaving.value = false
}

onMounted(loadPages)
</script>

<template>
  <div>
    <div class="mb-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h1 class="text-2xl font-black text-slate-950">Pages</h1>
        <p class="mt-1 text-sm text-slate-500">Manage CMS pages, policies, system pages, publish status, and SEO metadata.</p>
      </div>
      <div class="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
        <UInput
          v-model="searchQuery"
          class="min-w-56 flex-1 lg:max-w-sm"
          color="neutral"
          variant="outline"
          size="lg"
          icon="i-lucide-search"
          placeholder="Search pages..."
        />
        <UButton color="neutral" variant="outline" :loading="isLoading" @click="loadPages">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
        <UButton color="primary" variant="solid" @click="openCreatePage">
          <UIcon name="i-lucide-plus" />
          New Page
        </UButton>
      </div>
    </div>

    <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <CardsKpiCard2 name="Total pages" :value="totalItems" :budget="totalItems" color="#3d7cff" icon="i-lucide-files" :loading="isLoading" />
      <CardsKpiCard2 name="Public" :value="publicPageCount" :budget="pages.length || 1" color="#059669" icon="i-lucide-globe" :loading="isLoading" />
      <CardsKpiCard2 name="Protected" :value="protectedPageCount" :budget="pages.length || 1" color="#f59e0b" icon="i-lucide-lock" :loading="isLoading" />
      <CardsKpiCard2 name="Published" :value="publishedPageCount" :budget="pages.length || 1" color="#7c3aed" icon="i-lucide-badge-check" :loading="isLoading" />
      <CardsKpiCard2 name="System pages" :value="systemPageCount" :budget="pages.length || 1" color="#0f766e" icon="i-lucide-shield-check" :loading="isLoading" />
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-5">
      <div class="overflow-hidden rounded-lg border border-slate-200 bg-white xl:col-span-3">
        <div class="grid grid-cols-12 gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">
          <div class="col-span-4">Page</div>
          <div class="col-span-3">URL</div>
          <div class="col-span-2">Type / Status</div>
          <div class="col-span-1 text-right">Access</div>
          <div class="col-span-2 text-right">Actions</div>
        </div>

        <div v-if="isLoading" class="flex items-center justify-center p-12 text-sm font-semibold text-slate-500">
          <UIcon name="i-lucide-loader-circle" class="mr-2 animate-spin" />
          Loading pages
        </div>

        <div v-else-if="filteredPages.length === 0" class="p-12 text-center">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-[#255be8]">
            <UIcon name="i-lucide-files" />
          </div>
          <h2 class="mt-4 text-lg font-black text-slate-950">No pages found</h2>
          <p class="mt-1 text-sm text-slate-500">Try another search or create a page.</p>
        </div>

        <div
          v-for="page in filteredPages"
          v-else
          :key="page.id"
          class="grid grid-cols-12 items-center gap-3 border-b border-slate-100 px-4 py-3 last:border-b-0 hover:bg-slate-50"
          :class="{ 'bg-blue-50/60': selectedPage?.id === page.id }"
        >
          <div class="col-span-4 min-w-0">
            <p class="truncate font-semibold text-slate-950">{{ page.title || 'Untitled page' }}</p>
            <p class="truncate text-xs text-slate-500">Page #{{ page.id }}</p>
          </div>
          <div class="col-span-3 truncate text-sm font-semibold text-slate-700">{{ page.url }}</div>
          <div class="col-span-2 flex flex-wrap gap-1">
            <UBadge :color="typeColor(page.page_type)" variant="soft">
              {{ page.page_type }}
            </UBadge>
            <UBadge :color="statusColor(page.status)" variant="soft">
              {{ page.status }}
            </UBadge>
            <UBadge v-if="page.is_system_page" color="primary" variant="soft">
              System
            </UBadge>
          </div>
          <div class="col-span-1 text-right">
            <UBadge :color="page.registration_required ? 'warning' : 'success'" variant="soft">
              {{ page.registration_required ? 'Login' : 'Public' }}
            </UBadge>
          </div>
          <div class="col-span-2 flex justify-end gap-1">
            <UTooltip text="View detail">
              <UButton icon="i-lucide-panel-right-open" color="neutral" variant="ghost" square @click="openDetail(page)" />
            </UTooltip>
            <UTooltip text="Edit page">
              <UButton icon="i-lucide-pencil" color="neutral" variant="ghost" square @click="openEditPage(page)" />
            </UTooltip>
            <UTooltip text="Delete page">
              <UButton icon="i-lucide-trash-2" color="error" variant="ghost" square :disabled="page.is_system_page" @click="pendingDeletePage = page" />
            </UTooltip>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white xl:col-span-2">
        <div class="border-b border-slate-200 px-4 py-3">
          <h2 class="font-black text-slate-950">Page Detail</h2>
          <p class="mt-1 text-sm text-slate-500">{{ selectedPage ? selectedPage.title : 'Select a page to preview details.' }}</p>
        </div>

        <div v-if="!selectedPage" class="p-8 text-center text-sm text-slate-500">
          Choose a page from the table to inspect its URL, access rules, and content.
        </div>

        <div v-else class="p-4">
          <div class="mb-4 flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="truncate text-lg font-black text-slate-950">{{ selectedPage.title }}</p>
              <p class="truncate text-sm text-slate-500">{{ selectedPage.url }}</p>
              <p v-if="selectedPage.page_key" class="mt-1 truncate text-xs uppercase tracking-wide text-slate-400">{{ selectedPage.page_key }}</p>
            </div>
            <div class="flex flex-wrap gap-1">
              <UBadge :color="statusColor(selectedPage.status)" variant="soft">{{ selectedPage.status }}</UBadge>
              <UBadge :color="typeColor(selectedPage.page_type)" variant="soft">{{ selectedPage.page_type }}</UBadge>
              <UBadge v-if="selectedPage.is_system_page" color="primary" variant="soft">System</UBadge>
              <UBadge :color="selectedPage.registration_required ? 'warning' : 'success'" variant="soft">
                {{ selectedPage.registration_required ? 'Login required' : 'Public' }}
              </UBadge>
            </div>
          </div>

          <div class="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="line-clamp-6 text-sm leading-6 text-slate-700">{{ selectedPage.excerpt || excerpt(selectedPage.content) }}</p>
          </div>

          <dl class="space-y-3 text-sm">
            <div>
              <dt class="font-semibold text-slate-500">SEO title</dt>
              <dd class="mt-1 text-slate-950">{{ selectedPage.meta_title || '-' }}</dd>
            </div>
            <div>
              <dt class="font-semibold text-slate-500">SEO description</dt>
              <dd class="mt-1 text-slate-950">{{ selectedPage.meta_description || '-' }}</dd>
            </div>
            <div>
              <dt class="font-semibold text-slate-500">Published at</dt>
              <dd class="mt-1 text-slate-950">{{ selectedPage.published_at || '-' }}</dd>
            </div>
            <div>
              <dt class="font-semibold text-slate-500">Updated by</dt>
              <dd class="mt-1 text-slate-950">{{ selectedPage.updated_by_name || '-' }}</dd>
            </div>
          </dl>

          <div class="mt-5 flex flex-wrap gap-2">
            <UButton color="primary" variant="solid" @click="openEditPage(selectedPage)">
              <UIcon name="i-lucide-pencil" />
              Edit Page
            </UButton>
            <UButton color="error" variant="outline" :disabled="selectedPage.is_system_page" @click="pendingDeletePage = selectedPage">
              <UIcon name="i-lucide-trash-2" />
              Delete
            </UButton>
          </div>
        </div>
      </div>
    </div>

    <p class="mt-4 text-sm text-slate-500">Showing {{ filteredPages.length }} of {{ totalItems }} pages.</p>

    <div v-if="editorOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <UCard class="max-h-[90vh] w-full max-w-4xl overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">{{ editingPage ? 'Edit page' : 'New page' }}</h3>
              <p class="text-sm text-dimmed">Configure page identity, publishing, access, and SEO metadata.</p>
            </div>
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" square @click="editorOpen = false" />
          </div>
        </template>

        <div v-if="saveError" class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">{{ saveError }}</div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Title" required><UInput v-model="form.title" autocomplete="off" /></UFormField>
          <UFormField label="URL" required><UInput v-model="form.url" autocomplete="off" placeholder="/about/" /></UFormField>
          <UFormField label="Page key"><UInput v-model="form.page_key" autocomplete="off" placeholder="privacy_policy" /></UFormField>
          <UFormField label="Page type"><USelect v-model="form.page_type" :items="pageTypeOptions" /></UFormField>
          <UFormField label="Status"><USelect v-model="form.status" :items="pageStatusOptions" /></UFormField>
          <UFormField label="Excerpt"><UTextarea v-model="form.excerpt" :rows="3" /></UFormField>
          <UFormField label="Content" class="md:col-span-2"><UTextarea v-model="form.content" :rows="12" /></UFormField>
          <UFormField label="Meta title" class="md:col-span-2"><UInput v-model="form.meta_title" autocomplete="off" /></UFormField>
          <UFormField label="Meta description" class="md:col-span-2"><UTextarea v-model="form.meta_description" :rows="3" /></UFormField>
          <div class="md:col-span-2 flex items-center gap-3 rounded-lg border border-slate-200 p-3">
            <UCheckbox v-model="form.registration_required" />
            <div>
              <p class="text-sm font-semibold text-slate-950">Require login</p>
              <p class="text-xs text-slate-500">Only authenticated users can view this page.</p>
            </div>
          </div>
          <div class="md:col-span-2 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 p-3 md:grid-cols-2">
            <div class="flex items-center gap-3">
              <UCheckbox v-model="form.is_system_page" />
              <div>
                <p class="text-sm font-semibold text-slate-950">System page</p>
                <p class="text-xs text-slate-500">Protects canonical business pages from accidental deletion.</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <UCheckbox v-model="form.allow_indexing" />
              <div>
                <p class="text-sm font-semibold text-slate-950">Allow indexing</p>
                <p class="text-xs text-slate-500">Search engines may index this page when public.</p>
              </div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" :disabled="isSaving" @click="editorOpen = false">Cancel</UButton>
            <UButton color="primary" variant="solid" :loading="isSaving" @click="submitPage">Save page</UButton>
          </div>
        </template>
      </UCard>
    </div>

    <div v-if="pendingDeletePage" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <UCard class="w-full max-w-md">
        <template #header><h3 class="font-semibold text-default">Delete page</h3></template>
        <p class="text-sm text-default">Delete <span class="font-semibold">{{ pendingDeletePage.title }}</span>?</p>
        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" :disabled="isSaving" @click="pendingDeletePage = null">Cancel</UButton>
            <UButton color="error" variant="solid" :loading="isSaving" @click="confirmDeletePage">Delete page</UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
