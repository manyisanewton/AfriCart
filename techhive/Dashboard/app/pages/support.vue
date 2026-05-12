<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { SupportTicketRow } from '~/composables/useSupport'

const UBadge = resolveComponent('UBadge')
const UButton = resolveComponent('UButton')

const ALL_STATUSES = '__all__'
const searchInput = ref('')
const searchQuery = ref('')
const statusFilter = ref(ALL_STATUSES)

const { getSupportTickets, updateSupportTicketStatus } = useSupport()
const toast = useToast()

const ticketData = ref<SupportTicketRow[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const isEditorOpen = ref(false)
const selectedTicket = ref<SupportTicketRow | null>(null)
const saveError = ref('')
const ticketForm = reactive({
  status: 'open',
  admin_note: '',
})

const statusOptions = [
  { label: 'All statuses', value: ALL_STATUSES },
  { label: 'Open', value: 'open' },
  { label: 'In progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Closed', value: 'closed' },
]

const editableStatusOptions = statusOptions.filter(option => option.value !== ALL_STATUSES)

const ticketColumns: TableColumn<SupportTicketRow>[] = [
  {
    accessorKey: 'subject',
    header: 'Ticket',
    cell: ({ row }) =>
      h('button', {
        class: 'space-y-1 text-left',
        onClick: () => openTicket(row.original),
      }, [
        h('p', { class: 'font-medium text-default' }, row.original.subject),
        h('p', { class: 'text-xs text-slate-500' }, `${row.original.customerName} · ${row.original.email}`),
      ]),
  },
  {
    accessorKey: 'category',
    header: 'Category',
    cell: ({ row }) =>
      h(UBadge as Component, {
        label: formatCategory(row.original.category),
        color: 'info',
        variant: 'soft',
      }),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) =>
      h(UBadge as Component, {
        label: formatStatus(row.original.status),
        color: statusColor(row.original.status),
        variant: 'soft',
      }),
  },
  {
    accessorKey: 'createdAt',
    header: 'Created',
    cell: ({ row }) => formatDate(row.original.createdAt),
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
          'aria-label': `Manage support ticket ${row.original.id}`,
          onClick: (event: Event) => {
            event.stopPropagation()
            openTicket(row.original)
          },
        }),
      ]),
  },
]

const filteredTickets = computed(() => {
  let rows = [...ticketData.value]

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    rows = rows.filter(ticket =>
      ticket.subject.toLowerCase().includes(query)
      || ticket.customerName.toLowerCase().includes(query)
      || ticket.email.toLowerCase().includes(query)
      || ticket.phoneNumber.toLowerCase().includes(query),
    )
  }

  if (statusFilter.value !== ALL_STATUSES)
    rows = rows.filter(ticket => ticket.status === statusFilter.value)

  return rows
})

const summary = computed(() => ({
  total: ticketData.value.length,
  active: ticketData.value.filter(ticket => ['open', 'in_progress'].includes(ticket.status)).length,
  resolved: ticketData.value.filter(ticket => ticket.status === 'resolved').length,
  closed: ticketData.value.filter(ticket => ticket.status === 'closed').length,
}))

function formatDate(value?: string | null) {
  if (!value)
    return 'Unknown'

  return new Intl.DateTimeFormat('en-KE', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatCategory(value?: string) {
  if (!value)
    return 'General'

  return value
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatStatus(value?: string) {
  if (!value)
    return 'Open'

  return value
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function statusColor(status: string) {
  if (status === 'resolved')
    return 'success'
  if (status === 'closed')
    return 'neutral'
  if (status === 'in_progress')
    return 'info'
  return 'warning'
}

function applySearch() {
  searchQuery.value = searchInput.value.trim()
}

function clearFilters() {
  searchInput.value = ''
  searchQuery.value = ''
  statusFilter.value = ALL_STATUSES
}

async function loadSupport() {
  isLoading.value = true

  const result = await getSupportTickets(statusFilter.value !== ALL_STATUSES ? statusFilter.value : undefined)

  if (result.success)
    ticketData.value = result.data?.items || []
  else {
    ticketData.value = []
    toast.add({
      title: 'Could not load support tickets',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }

  isLoading.value = false
}

function openTicket(ticket: SupportTicketRow) {
  selectedTicket.value = ticket
  ticketForm.status = ticket.status || 'open'
  ticketForm.admin_note = ticket.adminNote || ''
  saveError.value = ''
  isEditorOpen.value = true
}

async function submitTicketForm() {
  if (!selectedTicket.value)
    return

  isSaving.value = true
  saveError.value = ''

  const result = await updateSupportTicketStatus(selectedTicket.value.id, {
    status: ticketForm.status,
    admin_note: ticketForm.admin_note,
  })

  if (result.success) {
    toast.add({
      title: 'Support ticket updated',
      description: `Ticket #${selectedTicket.value.id} was updated successfully.`,
      color: 'success',
    })
    isEditorOpen.value = false
    selectedTicket.value = null
    await loadSupport()
  }
  else {
    saveError.value = result.error || 'Could not update support ticket.'
  }

  isSaving.value = false
}

watch(statusFilter, async () => {
  await loadSupport()
})

onMounted(loadSupport)
</script>

<template>
  <div class="px-4 py-8 sm:px-6 lg:px-10">
    <div class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 class="text-3xl font-black tracking-tight text-slate-950">
          Support
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-slate-600">
          Review live customer support tickets from the shared TechHive backend and move them through resolution.
        </p>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <UInput
          v-model="searchInput"
          class="w-full sm:w-72"
          size="lg"
          variant="outline"
          icon="i-lucide-search"
          placeholder="Search subject, customer, email..."
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
        <UButton variant="outline" size="lg" :loading="isLoading" @click="loadSupport">
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
        name="Total tickets"
        :value="summary.total"
        :budget="summary.total"
        color="var(--color-info)"
        icon="i-lucide-life-buoy"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Active"
        :value="summary.active"
        :budget="summary.total"
        color="var(--color-warning)"
        icon="i-lucide-clock-3"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Resolved"
        :value="summary.resolved"
        :budget="summary.total"
        color="var(--color-success)"
        icon="i-lucide-badge-check"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Closed"
        :value="summary.closed"
        :budget="summary.total"
        color="var(--color-neutral)"
        icon="i-lucide-archive"
        :loading="isLoading"
      />
    </div>

    <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <UTable
        class="cursor-pointer"
        :data="filteredTickets"
        :columns="ticketColumns"
        :loading="isLoading"
        @select="(row) => openTicket(row.original || row)"
      />

      <div
        v-if="!isLoading && !filteredTickets.length"
        class="border-t border-slate-200 px-6 py-16 text-center"
      >
        <div class="mx-auto flex size-14 items-center justify-center rounded-2xl bg-amber-50 text-amber-600">
          <UIcon name="i-lucide-life-buoy" class="size-7" />
        </div>
        <h2 class="mt-5 text-xl font-black text-slate-950">
          No support tickets found
        </h2>
        <p class="mx-auto mt-2 max-w-md text-sm text-slate-600">
          Try another search term, change the status filter, or wait for new storefront support activity.
        </p>
      </div>
    </div>

    <div
      v-if="isEditorOpen && selectedTicket"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
    >
      <UCard class="max-h-[92vh] w-full max-w-3xl overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">Manage support ticket</h3>
              <p class="text-sm text-dimmed">Review customer context, update workflow state, and save an internal admin note.</p>
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
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Customer</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedTicket.customerName }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Contact</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedTicket.email }}</p>
            <p class="text-sm text-slate-600">{{ selectedTicket.phoneNumber || 'No phone number' }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Category</p>
            <p class="mt-1 font-semibold text-slate-950">{{ formatCategory(selectedTicket.category) }}</p>
          </div>
        </div>

        <div class="mb-5 grid grid-cols-1 gap-3 md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-white p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Subject</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedTicket.subject }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-white p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Timeline</p>
            <p class="mt-1 text-sm text-slate-700">Created: {{ formatDate(selectedTicket.createdAt) }}</p>
            <p class="text-sm text-slate-700">Updated: {{ formatDate(selectedTicket.updatedAt) }}</p>
            <p class="text-sm text-slate-700">Resolved: {{ formatDate(selectedTicket.resolvedAt) }}</p>
          </div>
        </div>

        <div class="mb-5 rounded-xl border border-slate-200 bg-white p-4">
          <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Customer message</p>
          <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{{ selectedTicket.message }}</p>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Ticket status">
            <USelect
              v-model="ticketForm.status"
              :items="editableStatusOptions"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Current status">
            <UInput :model-value="formatStatus(selectedTicket.status)" readonly />
          </UFormField>
          <UFormField label="Admin note" class="md:col-span-2">
            <UTextarea
              v-model="ticketForm.admin_note"
              :rows="6"
              placeholder="Add an internal support note for this ticket..."
            />
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
              @click="submitTicketForm"
            >
              Save changes
            </UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
