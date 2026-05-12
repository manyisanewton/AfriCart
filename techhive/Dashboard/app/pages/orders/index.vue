<script setup lang="ts">
import { getOrderTableColumns } from '~/config/orderTableColumns'
import type { SortBy, SortDir } from '~/types/Table'
import type { OrderTableRow } from '~/types/OrderTableRow'

const UBadge = resolveComponent('UBadge')
const UButton = resolveComponent('UButton')

const sortBy = ref<SortBy>()
const sortDir = ref<SortDir>('asc')
const searchQuery = ref('')
const searchInput = ref('')
const ALL_STATUSES = '__all__'
const statusFilter = ref(ALL_STATUSES)

const { getOrders, updateOrderStatus } = useOrder()
const toast = useToast()

const orderData = ref<OrderTableRow[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const isEditorOpen = ref(false)
const selectedOrder = ref<OrderTableRow | null>(null)
const saveError = ref('')
const orderForm = reactive({
  status: 'pending',
})

const statusOptions = [
  { label: 'All statuses', value: ALL_STATUSES },
  { label: 'Pending', value: 'pending' },
  { label: 'Confirmed', value: 'confirmed' },
  { label: 'Processing', value: 'processing' },
  { label: 'Shipped', value: 'shipped' },
  { label: 'Delivered', value: 'delivered' },
  { label: 'Cancelled', value: 'cancelled' },
]

const editableStatusOptions = statusOptions.filter(option => option.value !== ALL_STATUSES)

const columns = getOrderTableColumns({
  onManage: order => openOrder(order),
  sortBy,
  sortDir,
  components: [UButton, UBadge] as Component[],
})

const filteredOrders = computed(() => {
  let rows = [...orderData.value]

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    rows = rows.filter(order =>
      order.orderNumber.toLowerCase().includes(query)
      || order.customerName.toLowerCase().includes(query)
      || (order.phoneNumber || '').toLowerCase().includes(query),
    )
  }

  if (statusFilter.value !== ALL_STATUSES)
    rows = rows.filter(order => order.status === statusFilter.value)

  if (sortBy.value) {
    const direction = sortDir.value === 'desc' ? -1 : 1
    rows.sort((a, b) => {
      const left = String(a[sortBy.value as keyof OrderTableRow] || '').toLowerCase()
      const right = String(b[sortBy.value as keyof OrderTableRow] || '').toLowerCase()
      return left.localeCompare(right) * direction
    })
  }

  return rows
})

const summary = computed(() => ({
  total: orderData.value.length,
  pending: orderData.value.filter(order => order.status === 'pending').length,
  completed: orderData.value.filter(order => ['delivered', 'confirmed'].includes(order.status)).length,
  cancelled: orderData.value.filter(order => order.status === 'cancelled').length,
}))

function applySearch() {
  searchQuery.value = searchInput.value.trim()
}

function clearFilters() {
  searchInput.value = ''
  searchQuery.value = ''
  statusFilter.value = ALL_STATUSES
}

async function loadOrders() {
  isLoading.value = true
  const result = await getOrders()

  if (result.success)
    orderData.value = result.data?.items || []
  else {
    orderData.value = []
    toast.add({
      title: 'Could not load orders',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }

  isLoading.value = false
}

function openOrder(order: OrderTableRow) {
  selectedOrder.value = order
  orderForm.status = order.status
  saveError.value = ''
  isEditorOpen.value = true
}

async function submitOrderForm() {
  if (!selectedOrder.value)
    return

  isSaving.value = true
  saveError.value = ''

  const result = await updateOrderStatus(selectedOrder.value.id, {
    status: orderForm.status,
  })

  if (result.success) {
    toast.add({
      title: 'Order updated',
      description: `${selectedOrder.value.orderNumber} was updated successfully.`,
      color: 'success',
    })
    isEditorOpen.value = false
    selectedOrder.value = null
    await loadOrders()
  }
  else {
    saveError.value = result.error || 'Could not update order.'
  }

  isSaving.value = false
}

onMounted(loadOrders)
</script>

<template>
  <div class="px-4 py-8 sm:px-6 lg:px-10">
    <div class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 class="text-3xl font-black tracking-tight text-slate-950">
          Orders
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-slate-600">
          View live marketplace orders and update order workflow status from the shared TechHive backend.
        </p>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <UInput
          v-model="searchInput"
          class="w-full sm:w-72"
          size="lg"
          variant="outline"
          icon="i-lucide-search"
          placeholder="Search order, customer, phone..."
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
        <UButton variant="outline" size="lg" :loading="isLoading" @click="loadOrders">
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
        name="Total orders"
        :value="summary.total"
        :budget="summary.total"
        color="var(--color-info)"
        icon="i-lucide-shopping-cart"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Pending"
        :value="summary.pending"
        :budget="summary.total"
        color="var(--color-warning)"
        icon="i-lucide-clock"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Completed"
        :value="summary.completed"
        :budget="summary.total"
        color="var(--color-success)"
        icon="i-lucide-check-circle"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Cancelled"
        :value="summary.cancelled"
        :budget="summary.total"
        color="var(--color-error)"
        icon="i-lucide-x-circle"
        :loading="isLoading"
      />
    </div>

    <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <UTable
        class="cursor-pointer"
        :data="filteredOrders"
        :columns="columns"
        :loading="isLoading"
        @select="(row) => openOrder(row.original || row)"
      />

      <div
        v-if="!isLoading && !filteredOrders.length"
        class="border-t border-slate-200 px-6 py-16 text-center"
      >
        <div class="mx-auto flex size-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
          <UIcon name="i-lucide-receipt-text" class="size-7" />
        </div>
        <h2 class="mt-5 text-xl font-black text-slate-950">
          No orders found
        </h2>
        <p class="mx-auto mt-2 max-w-md text-sm text-slate-600">
          Try another search term, clear the status filter, or wait for new storefront orders.
        </p>
      </div>
    </div>

    <div
      v-if="isEditorOpen && selectedOrder"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
    >
      <UCard class="max-h-[92vh] w-full max-w-3xl overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">Manage order</h3>
              <p class="text-sm text-dimmed">Update workflow state for the selected marketplace order.</p>
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
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Order</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.orderNumber }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Customer</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.customerName }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Total</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.currency }} {{ selectedOrder.totalAmount.toFixed(2) }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Order status">
            <USelect
              v-model="orderForm.status"
              :items="editableStatusOptions"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Delivery status">
            <UInput :model-value="selectedOrder.deliveryStatus" readonly />
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
              @click="submitOrderForm"
            >
              Save changes
            </UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
