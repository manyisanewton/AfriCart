<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { VendorTableRow } from '~/composables/useVendor'

const UBadge = resolveComponent('UBadge')
const UButton = resolveComponent('UButton')

const searchInput = ref('')
const searchQuery = ref('')
const ALL_STATUSES = '__all__'
const statusFilter = ref(ALL_STATUSES)

const { getVendors, updateVendorStatus } = useVendor()
const toast = useToast()

const vendorData = ref<VendorTableRow[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const isEditorOpen = ref(false)
const selectedVendor = ref<VendorTableRow | null>(null)
const saveError = ref('')
const vendorForm = reactive({
  status: 'pending',
})

const statusOptions = [
  { label: 'All statuses', value: ALL_STATUSES },
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Suspended', value: 'suspended' },
  { label: 'Rejected', value: 'rejected' },
]

const editableStatusOptions = statusOptions.filter(option => option.value !== ALL_STATUSES)

const columns: TableColumn<VendorTableRow>[] = [
  {
    accessorKey: 'businessName',
    header: 'Vendor',
    cell: ({ row }) =>
      h('button', {
        class: 'space-y-1 text-left',
        onClick: () => openVendor(row.original),
      }, [
        h('p', { class: 'font-medium text-default' }, row.original.businessName),
        h('p', { class: 'text-xs text-slate-500' }, `@${row.original.slug}`),
      ]),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) =>
      h(UBadge as Component, {
        label: row.original.status,
        color: statusColor(row.original.status),
        variant: 'soft',
      }),
  },
  {
    accessorKey: 'isVerified',
    header: 'Verification',
    cell: ({ row }) =>
      h(UBadge as Component, {
        label: row.original.isVerified ? 'Verified' : 'Unverified',
        color: row.original.isVerified ? 'success' : 'warning',
        variant: 'soft',
      }),
  },
  {
    accessorKey: 'userId',
    header: 'User ID',
    cell: ({ row }) => `#${row.original.userId}`,
  },
  {
    id: 'actions',
    header: () => h('span', { class: 'sr-only' }, 'Actions'),
    cell: ({ row }) =>
      h('div', { class: 'flex items-center justify-end gap-2' }, [
        h(UButton as Component, {
          icon: 'i-lucide-pencil',
          color: 'neutral',
          variant: 'ghost',
          size: 'xs',
          'aria-label': `Manage ${row.original.businessName}`,
          onClick: (event: Event) => {
            event.stopPropagation()
            openVendor(row.original)
          },
        }),
      ]),
  },
]

const filteredVendors = computed(() => {
  let rows = [...vendorData.value]

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    rows = rows.filter(vendor =>
      vendor.businessName.toLowerCase().includes(query)
      || vendor.slug.toLowerCase().includes(query)
      || String(vendor.userId).includes(query),
    )
  }

  if (statusFilter.value !== ALL_STATUSES) {
    const label = formatStatus(statusFilter.value)
    rows = rows.filter(vendor => vendor.status === label)
  }

  return rows
})

const summary = computed(() => ({
  total: vendorData.value.length,
  pending: vendorData.value.filter(vendor => vendor.status === 'Pending').length,
  approved: vendorData.value.filter(vendor => vendor.status === 'Approved').length,
  suspended: vendorData.value.filter(vendor => vendor.status === 'Suspended').length,
}))

function formatStatus(value: string) {
  return value
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function statusColor(status: string) {
  if (status === 'Approved')
    return 'success'
  if (status === 'Suspended')
    return 'warning'
  if (status === 'Rejected')
    return 'error'
  return 'info'
}

function applySearch() {
  searchQuery.value = searchInput.value.trim()
}

function clearFilters() {
  searchInput.value = ''
  searchQuery.value = ''
  statusFilter.value = ALL_STATUSES
}

async function loadVendors() {
  isLoading.value = true
  const result = await getVendors()

  if (result.success)
    vendorData.value = result.data?.items || []
  else {
    vendorData.value = []
    toast.add({
      title: 'Could not load vendors',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }

  isLoading.value = false
}

function openVendor(vendor: VendorTableRow) {
  selectedVendor.value = vendor
  vendorForm.status = String(vendor.raw?.status || 'pending')
  saveError.value = ''
  isEditorOpen.value = true
}

async function submitVendorForm() {
  if (!selectedVendor.value)
    return

  isSaving.value = true
  saveError.value = ''

  const result = await updateVendorStatus(selectedVendor.value.id, vendorForm.status)

  if (result.success) {
    toast.add({
      title: 'Vendor updated',
      description: `${selectedVendor.value.businessName} was updated successfully.`,
      color: 'success',
    })
    isEditorOpen.value = false
    selectedVendor.value = null
    await loadVendors()
  }
  else {
    saveError.value = result.error || 'Could not update vendor.'
  }

  isSaving.value = false
}

onMounted(loadVendors)
</script>

<template>
  <div class="px-4 py-8 sm:px-6 lg:px-10">
    <div class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 class="text-3xl font-black tracking-tight text-slate-950">
          Vendors
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-slate-600">
          Review marketplace vendors, approve trusted businesses, and manage vendor access from the shared TechHive backend.
        </p>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <UInput
          v-model="searchInput"
          class="w-full sm:w-72"
          size="lg"
          variant="outline"
          icon="i-lucide-search"
          placeholder="Search vendor, slug, user ID..."
          :ui="{ leadingIcon: 'size-4' }"
        />
        <UButton color="neutral" variant="outline" size="lg" @click="applySearch">
          Search
        </UButton>
        <USelect
          v-model="statusFilter"
          :items="statusOptions"
          value-attribute="value"
          option-attribute="label"
          class="w-full sm:w-44"
          size="lg"
          variant="outline"
        />
        <UButton variant="outline" size="lg" :loading="isLoading" @click="loadVendors">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
        <UButton variant="ghost" color="neutral" size="lg" @click="clearFilters">
          Clear
        </UButton>
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <CardsKpiCard2
        name="Total vendors"
        :value="summary.total"
        :budget="summary.total"
        color="var(--color-info)"
        icon="i-lucide-store"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Pending"
        :value="summary.pending"
        :budget="summary.total"
        color="var(--color-warning)"
        icon="i-lucide-hourglass"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Approved"
        :value="summary.approved"
        :budget="summary.total"
        color="var(--color-success)"
        icon="i-lucide-badge-check"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Suspended"
        :value="summary.suspended"
        :budget="summary.total"
        color="var(--color-error)"
        icon="i-lucide-ban"
        :loading="isLoading"
      />
    </div>

    <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <UTable
        class="cursor-pointer"
        :data="filteredVendors"
        :columns="columns"
        :loading="isLoading"
        @select="(row) => openVendor(row.original || row)"
      />

      <div
        v-if="!isLoading && !filteredVendors.length"
        class="border-t border-slate-200 px-6 py-16 text-center"
      >
        <div class="mx-auto flex size-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
          <UIcon name="i-lucide-store" class="size-7" />
        </div>
        <h2 class="mt-5 text-xl font-black text-slate-950">
          No vendors found
        </h2>
        <p class="mx-auto mt-2 max-w-md text-sm text-slate-600">
          Try another search term, clear the status filter, or wait for new vendor registrations.
        </p>
      </div>
    </div>

    <div
      v-if="isEditorOpen && selectedVendor"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
    >
      <UCard class="max-h-[92vh] w-full max-w-2xl overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">Manage vendor</h3>
              <p class="text-sm text-dimmed">Approve, suspend, or reject a vendor account using the live marketplace workflow.</p>
            </div>
            <UButton
              icon="i-lucide-x"
              color="neutral"
              variant="ghost"
              square
              @click="isEditorOpen = false"
            />
          </div>
        </template>

        <div v-if="saveError" class="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
          {{ saveError }}
        </div>

        <div class="mb-5 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Business</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedVendor.businessName }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Slug</p>
            <p class="mt-1 font-semibold text-slate-950">@{{ selectedVendor.slug }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Linked user</p>
            <p class="mt-1 font-semibold text-slate-950">#{{ selectedVendor.userId }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Vendor status">
            <USelect
              v-model="vendorForm.status"
              :items="editableStatusOptions"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Verification">
            <UInput :model-value="selectedVendor.isVerified ? 'Verified' : 'Unverified'" readonly />
          </UFormField>
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton
              color="neutral"
              variant="outline"
              :disabled="isSaving"
              @click="isEditorOpen = false"
            >
              Cancel
            </UButton>
            <UButton
              color="primary"
              variant="solid"
              :loading="isSaving"
              @click="submitVendorForm"
            >
              Save changes
            </UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
