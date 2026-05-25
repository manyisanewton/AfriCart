<script setup lang="ts">
import { getOrderTableColumns } from '~/config/orderTableColumns'
import type { SortBy, SortDir } from '~/types/Table'
import type { OrderTableRow } from '~/types/OrderTableRow'
import type { DeliveryAgentChoice } from '~/composables/useOrder'

const UBadge = resolveComponent('UBadge')
const UButton = resolveComponent('UButton')

const sortBy = ref<SortBy>()
const sortDir = ref<SortDir>('asc')
const searchQuery = ref('')
const searchInput = ref('')
const ALL_STATUSES = '__all__'
const statusFilter = ref(ALL_STATUSES)

const { getDeliveryAgents, getOrder, getOrders, updateOrder } = useOrder()
const toast = useToast()

const orderData = ref<OrderTableRow[]>([])
const deliveryAgents = ref<DeliveryAgentChoice[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const isEditorOpen = ref(false)
const selectedOrder = ref<OrderTableRow | null>(null)
const saveError = ref('')
const orderForm = reactive({
  status: 'pending',
  delivery_status: 'processing',
  tracking_token: '',
  notes: '',
  delivery_agent_id: null as number | null,
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
const deliveryStatusOptions = [
  { label: 'Processing', value: 'processing' },
  { label: 'Assigned', value: 'assigned' },
  { label: 'In transit', value: 'in_transit' },
  { label: 'Delivered', value: 'delivered' },
  { label: 'Failed attempt', value: 'failed_attempt' },
]
const deliveryAgentOptions = computed(() => [
  { label: 'Unassigned', value: null },
  ...deliveryAgents.value.map(agent => ({
    label: `${agent.display_name} / ${agent.phone_number}`,
    value: agent.id,
  })),
])

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
  const [ordersResult, agentsResult] = await Promise.all([
    getOrders(),
    getDeliveryAgents(),
  ])

  if (ordersResult.success)
    orderData.value = ordersResult.data?.items || []
  else {
    orderData.value = []
    toast.add({
      title: 'Could not load orders',
      description: ordersResult.error || 'Please try again.',
      color: 'error',
    })
  }

  if (agentsResult.success)
    deliveryAgents.value = agentsResult.data || []
  else
    deliveryAgents.value = []

  isLoading.value = false
}

async function openOrder(order: OrderTableRow) {
  isLoading.value = true
  const result = await getOrder(order.id)
  isLoading.value = false

  if (!result.success || !result.data) {
    toast.add({
      title: 'Could not load order details',
      description: result.error || 'Please try again.',
      color: 'error',
    })
    return
  }

  selectedOrder.value = result.data
  orderForm.status = result.data.status
  orderForm.delivery_status = result.data.deliveryStatus || 'processing'
  orderForm.tracking_token = result.data.trackingToken || ''
  orderForm.notes = result.data.notes || ''
  orderForm.delivery_agent_id = result.data.deliveryAgent?.id || null
  saveError.value = ''
  isEditorOpen.value = true
}

async function submitOrderForm() {
  if (!selectedOrder.value)
    return

  isSaving.value = true
  saveError.value = ''

  const result = await updateOrder(selectedOrder.value.id, {
    status: orderForm.status,
    delivery_status: orderForm.delivery_status,
    tracking_token: orderForm.tracking_token.trim(),
    notes: orderForm.notes.trim() || null,
    delivery_agent_id: orderForm.delivery_agent_id,
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

        <div class="mb-5 grid grid-cols-1 gap-3 md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Shipping</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.shippingAddress?.name }}</p>
            <p class="text-sm text-slate-600">{{ selectedOrder.shippingAddress?.phone_number }}</p>
            <p class="text-sm text-slate-600">
              {{ selectedOrder.shippingAddress?.address_line_1 }},
              {{ selectedOrder.shippingAddress?.city }},
              {{ selectedOrder.shippingAddress?.country }}
            </p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Tracking</p>
            <p class="mt-1 font-mono text-sm font-semibold text-slate-950">{{ selectedOrder.trackingToken }}</p>
            <p class="mt-2 text-xs font-bold uppercase tracking-wide text-slate-500">Delivery agent</p>
            <p class="mt-1 text-sm text-slate-700">
              {{ selectedOrder.deliveryAgent?.display_name || 'Unassigned' }}
            </p>
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
            <USelect
              v-model="orderForm.delivery_status"
              :items="deliveryStatusOptions"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Tracking token">
            <UInput v-model="orderForm.tracking_token" />
          </UFormField>
          <UFormField label="Delivery agent">
            <USelect
              v-model="orderForm.delivery_agent_id"
              :items="deliveryAgentOptions"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Notes" class="md:col-span-2">
            <UTextarea v-model="orderForm.notes" :rows="4" />
          </UFormField>
        </div>

        <div class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-white p-4">
            <h4 class="font-semibold text-slate-950">Items</h4>
            <div v-if="selectedOrder.items?.length" class="mt-3 space-y-3">
              <div v-for="item in selectedOrder.items" :key="item.id" class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="font-semibold text-slate-950">{{ item.product_name }}</p>
                <p class="text-xs text-slate-500">{{ item.sku }} / Qty {{ item.quantity }}</p>
                <p class="text-sm text-slate-700">{{ selectedOrder.currency }} {{ item.line_total }}</p>
              </div>
            </div>
            <p v-else class="mt-3 text-sm text-slate-500">No items found.</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-white p-4">
            <h4 class="font-semibold text-slate-950">Refunds</h4>
            <div v-if="selectedOrder.refunds?.length" class="mt-3 space-y-3">
              <div v-for="refund in selectedOrder.refunds" :key="refund.id" class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="font-semibold text-slate-950">{{ selectedOrder.currency }} {{ refund.amount }}</p>
                <p class="text-xs text-slate-500">{{ refund.status }} / {{ refund.reason }}</p>
              </div>
            </div>
            <p v-else class="mt-3 text-sm text-slate-500">No refunds recorded.</p>
          </div>
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
