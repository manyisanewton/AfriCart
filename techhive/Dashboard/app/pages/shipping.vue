<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { DeliveryAgentItem, ShippingOrderItem, ShippingZoneItem } from '~/composables/useShipping'

const UButton = resolveComponent('UButton')
const UBadge = resolveComponent('UBadge')

const toast = useToast()
const {
  createZone,
  deleteZone,
  getDeliveryAgents,
  getShippingOrders,
  getZones,
  updateOrderShipping,
  updateZone,
} = useShipping()

const searchQuery = ref('')
const zoneFilter = ref('__all__')
const deliveryStatusFilter = ref('__all__')
const isLoading = ref(false)
const isSaving = ref(false)
const saveError = ref('')

const zones = ref<ShippingZoneItem[]>([])
const agents = ref<DeliveryAgentItem[]>([])
const orders = ref<ShippingOrderItem[]>([])

const zoneEditorOpen = ref(false)
const orderEditorOpen = ref(false)
const pendingDeleteZone = ref<ShippingZoneItem | null>(null)
const editingZone = ref<ShippingZoneItem | null>(null)
const selectedOrder = ref<ShippingOrderItem | null>(null)

const zoneForm = reactive({
  name: '',
  city: '',
  fee: '0',
  estimated_days_min: '1',
  estimated_days_max: '3',
  is_active: true,
})

const orderForm = reactive({
  delivery_agent_id: '',
  delivery_status: 'processing',
  tracking_token: '',
  notes: '',
})

const deliveryStatusOptions = [
  { label: 'All statuses', value: '__all__' },
  { label: 'Processing', value: 'processing' },
  { label: 'Assigned', value: 'assigned' },
  { label: 'In transit', value: 'in_transit' },
  { label: 'Delivered', value: 'delivered' },
  { label: 'Failed attempt', value: 'failed_attempt' },
]

const zoneOptions = computed(() => [
  { label: 'All zones', value: '__all__' },
  ...zones.value.map(zone => ({ label: `${zone.city} · ${zone.name}`, value: zone.name })),
])

const filteredOrders = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  return orders.value.filter((order) => {
    const matchesQuery = !query
      || order.order_number.toLowerCase().includes(query)
      || order.shipping_address.name.toLowerCase().includes(query)
      || order.shipping_address.city.toLowerCase().includes(query)
      || (order.delivery_agent?.display_name || '').toLowerCase().includes(query)

    const matchesZone = zoneFilter.value === '__all__' || (order.delivery_zone_name || '') === zoneFilter.value
    const matchesStatus = deliveryStatusFilter.value === '__all__' || order.delivery_status === deliveryStatusFilter.value

    return matchesQuery && matchesZone && matchesStatus
  })
})

const totalAssignedOrders = computed(() => orders.value.filter(order => !!order.delivery_agent).length)
const totalActiveZones = computed(() => zones.value.filter(zone => zone.is_active).length)
const totalActiveAgents = computed(() => agents.value.filter(agent => agent.is_active).length)

const orderColumns: TableColumn<ShippingOrderItem>[] = [
  {
    accessorKey: 'order_number',
    header: 'Order',
    cell: ({ row }) =>
      h('button', {
        class: 'space-y-1 text-left',
        onClick: () => openOrder(row.original),
      }, [
        h('p', { class: 'font-medium text-default' }, row.original.order_number),
        h('p', { class: 'text-xs text-slate-500' }, row.original.shipping_address.name),
      ]),
  },
  {
    accessorKey: 'delivery_zone_name',
    header: 'Zone',
    cell: ({ row }) => row.original.delivery_zone_name || 'Unzoned',
  },
  {
    accessorKey: 'delivery_status',
    header: 'Delivery',
    cell: ({ row }) =>
      h(UBadge as Component, {
        label: formatStatus(row.original.delivery_status),
        color: deliveryStatusColor(row.original.delivery_status),
        variant: 'soft',
      }),
  },
  {
    accessorKey: 'delivery_agent',
    header: 'Agent',
    cell: ({ row }) => row.original.delivery_agent?.display_name || 'Unassigned',
  },
  {
    accessorKey: 'total_amount',
    header: 'Total',
    cell: ({ row }) => `${row.original.currency} ${row.original.total_amount}`,
  },
  {
    id: 'actions',
    header: () => h('span', { class: 'sr-only' }, 'Actions'),
    cell: ({ row }) =>
      h(UButton as Component, {
        icon: 'i-lucide-truck',
        color: 'neutral',
        variant: 'ghost',
        size: 'xs',
        'aria-label': `Manage ${row.original.order_number}`,
        onClick: (event: Event) => {
          event.stopPropagation()
          openOrder(row.original)
        },
      }),
  },
]

function formatCurrency(value: string | number) {
  return `KES ${Number(value || 0).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatStatus(value?: string | null) {
  const raw = String(value || '').trim()
  if (!raw)
    return 'Unknown'
  return raw.split('_').map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
}

function deliveryStatusColor(status: string) {
  if (status === 'delivered')
    return 'success'
  if (status === 'in_transit' || status === 'assigned')
    return 'info'
  if (status === 'failed_attempt')
    return 'error'
  return 'warning'
}

function resetZoneForm() {
  editingZone.value = null
  saveError.value = ''
  zoneForm.name = ''
  zoneForm.city = ''
  zoneForm.fee = '0'
  zoneForm.estimated_days_min = '1'
  zoneForm.estimated_days_max = '3'
  zoneForm.is_active = true
}

function resetOrderForm() {
  saveError.value = ''
  orderForm.delivery_agent_id = ''
  orderForm.delivery_status = 'processing'
  orderForm.tracking_token = ''
  orderForm.notes = ''
}

async function loadShippingData() {
  isLoading.value = true

  const [zonesResult, agentsResult, ordersResult] = await Promise.all([
    getZones(),
    getDeliveryAgents(),
    getShippingOrders(),
  ])

  if (zonesResult.success)
    zones.value = zonesResult.data || []
  else
    toast.add({ title: 'Could not load zones', description: zonesResult.error || 'Please try again.', color: 'error' })

  if (agentsResult.success)
    agents.value = agentsResult.data || []
  else
    toast.add({ title: 'Could not load delivery agents', description: agentsResult.error || 'Please try again.', color: 'error' })

  if (ordersResult.success)
    orders.value = ordersResult.data || []
  else
    toast.add({ title: 'Could not load shipping orders', description: ordersResult.error || 'Please try again.', color: 'error' })

  isLoading.value = false
}

function openCreateZone() {
  resetZoneForm()
  zoneEditorOpen.value = true
}

function openEditZone(zone: ShippingZoneItem) {
  editingZone.value = zone
  saveError.value = ''
  zoneForm.name = zone.name
  zoneForm.city = zone.city
  zoneForm.fee = String(zone.fee)
  zoneForm.estimated_days_min = String(zone.estimated_days_min)
  zoneForm.estimated_days_max = String(zone.estimated_days_max)
  zoneForm.is_active = zone.is_active
  zoneEditorOpen.value = true
}

async function submitZone() {
  saveError.value = ''
  if (!zoneForm.name.trim() || !zoneForm.city.trim()) {
    saveError.value = 'Zone name and city are required.'
    return
  }

  isSaving.value = true
  const payload = {
    name: zoneForm.name.trim(),
    city: zoneForm.city.trim(),
    fee: zoneForm.fee,
    estimated_days_min: zoneForm.estimated_days_min,
    estimated_days_max: zoneForm.estimated_days_max,
    is_active: zoneForm.is_active,
  }

  const result = editingZone.value
    ? await updateZone(editingZone.value.id, payload)
    : await createZone(payload)

  if (result.success) {
    toast.add({
      title: editingZone.value ? 'Zone updated' : 'Zone created',
      color: 'success',
    })
    zoneEditorOpen.value = false
    resetZoneForm()
    await loadShippingData()
  }
  else {
    saveError.value = result.error || 'Could not save delivery zone.'
  }

  isSaving.value = false
}

async function confirmDeleteZone() {
  if (!pendingDeleteZone.value)
    return

  isSaving.value = true
  const result = await deleteZone(pendingDeleteZone.value.id)

  if (result.success) {
    toast.add({ title: 'Zone deleted', color: 'success' })
    pendingDeleteZone.value = null
    await loadShippingData()
  }
  else {
    toast.add({ title: 'Delete failed', description: result.error || 'Could not delete zone.', color: 'error' })
  }

  isSaving.value = false
}

function openOrder(order: ShippingOrderItem) {
  selectedOrder.value = order
  saveError.value = ''
  orderForm.delivery_agent_id = order.delivery_agent ? String(order.delivery_agent.id) : ''
  orderForm.delivery_status = order.delivery_status || 'processing'
  orderForm.tracking_token = order.tracking_token || ''
  orderForm.notes = order.notes || ''
  orderEditorOpen.value = true
}

async function submitOrder() {
  if (!selectedOrder.value)
    return

  isSaving.value = true
  saveError.value = ''

  const payload = {
    delivery_agent_id: orderForm.delivery_agent_id ? Number(orderForm.delivery_agent_id) : null,
    delivery_status: orderForm.delivery_status,
    tracking_token: orderForm.tracking_token,
    notes: orderForm.notes,
  }

  const result = await updateOrderShipping(selectedOrder.value.id, payload)

  if (result.success) {
    toast.add({ title: 'Shipping order updated', color: 'success' })
    orderEditorOpen.value = false
    selectedOrder.value = null
    resetOrderForm()
    await loadShippingData()
  }
  else {
    saveError.value = result.error || 'Could not update shipping order.'
  }

  isSaving.value = false
}

onMounted(loadShippingData)
</script>

<template>
  <div class="px-4 py-8 sm:px-6 lg:px-10">
    <div class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 class="text-3xl font-black tracking-tight text-slate-950">
          Shipping
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-slate-600">
          Manage delivery zones, review active delivery agents, and keep shipping orders moving through the shared TechHive backend.
        </p>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <UInput
          v-model="searchQuery"
          class="w-full sm:w-72"
          size="lg"
          variant="outline"
          icon="i-lucide-search"
          placeholder="Search order, customer, city..."
        />
        <USelect
          v-model="zoneFilter"
          :items="zoneOptions"
          value-attribute="value"
          option-attribute="label"
          class="w-full sm:w-48"
          size="lg"
          variant="outline"
        />
        <USelect
          v-model="deliveryStatusFilter"
          :items="deliveryStatusOptions"
          value-attribute="value"
          option-attribute="label"
          class="w-full sm:w-48"
          size="lg"
          variant="outline"
        />
        <UButton variant="outline" size="lg" :loading="isLoading" @click="loadShippingData">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
        <UButton size="lg" @click="openCreateZone">
          <UIcon name="i-lucide-plus" />
          New Zone
        </UButton>
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <CardsKpiCard2 name="Zones" :value="zones.length" :budget="zones.length" color="var(--color-info)" icon="i-lucide-map-pinned" :loading="isLoading" />
      <CardsKpiCard2 name="Active zones" :value="totalActiveZones" :budget="zones.length" color="var(--color-success)" icon="i-lucide-map" :loading="isLoading" />
      <CardsKpiCard2 name="Agents" :value="agents.length" :budget="agents.length" color="var(--color-warning)" icon="i-lucide-bike" :loading="isLoading" />
      <CardsKpiCard2 name="Assigned orders" :value="totalAssignedOrders" :budget="orders.length" color="var(--color-error)" icon="i-lucide-package-check" :loading="isLoading" />
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <div class="space-y-6">
        <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-6 py-4">
            <h2 class="text-lg font-black text-slate-950">Delivery zones</h2>
            <p class="mt-1 text-sm text-slate-500">These zones power storefront delivery estimates and order shipping charges.</p>
          </div>
          <div v-if="zones.length" class="divide-y divide-slate-200">
            <div v-for="zone in zones" :key="zone.id" class="flex flex-col gap-4 px-6 py-4 md:flex-row md:items-start md:justify-between">
              <div>
                <div class="flex flex-wrap items-center gap-3">
                  <h3 class="font-semibold text-slate-950">{{ zone.city }}</h3>
                  <UBadge :label="zone.is_active ? 'Active' : 'Inactive'" :color="zone.is_active ? 'success' : 'neutral'" variant="soft" />
                </div>
                <p class="mt-1 text-sm text-slate-600">{{ zone.name }}</p>
                <p class="mt-2 text-sm text-slate-500">
                  {{ formatCurrency(zone.fee) }} · {{ zone.estimated_days_min }}-{{ zone.estimated_days_max }} days
                </p>
              </div>
              <div class="flex items-center gap-2">
                <UButton color="neutral" variant="ghost" size="sm" icon="i-lucide-pencil" @click="openEditZone(zone)" />
                <UButton color="error" variant="ghost" size="sm" icon="i-lucide-trash-2" @click="pendingDeleteZone = zone" />
              </div>
            </div>
          </div>
          <div v-else class="px-6 py-16 text-center text-sm text-slate-500">
            No delivery zones yet.
          </div>
        </div>

        <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-6 py-4">
            <h2 class="text-lg font-black text-slate-950">Shipping orders</h2>
            <p class="mt-1 text-sm text-slate-500">Assign agents, update delivery state, and monitor order flow.</p>
          </div>

          <UTable
            class="cursor-pointer"
            :data="filteredOrders"
            :columns="orderColumns"
            :loading="isLoading"
            @select="(row) => openOrder(row.original || row)"
          />
        </div>
      </div>

      <div class="space-y-6">
        <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-6 py-4">
            <h2 class="text-lg font-black text-slate-950">Delivery agents</h2>
            <p class="mt-1 text-sm text-slate-500">Active delivery capacity currently visible to shipping operations.</p>
          </div>
          <div v-if="agents.length" class="divide-y divide-slate-200">
            <div v-for="agent in agents" :key="agent.id" class="px-6 py-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-semibold text-slate-950">{{ agent.display_name }}</p>
                  <p class="text-sm text-slate-500">{{ agent.phone_number }}</p>
                </div>
                <UBadge :label="agent.is_active ? 'Active' : 'Inactive'" :color="agent.is_active ? 'success' : 'neutral'" variant="soft" />
              </div>
              <p class="mt-2 text-sm text-slate-600">{{ agent.active_assignments }} active assignments</p>
            </div>
          </div>
          <div v-else class="px-6 py-16 text-center text-sm text-slate-500">
            No delivery agents yet.
          </div>
        </div>
      </div>
    </div>

    <div v-if="zoneEditorOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <UCard class="w-full max-w-2xl">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">{{ editingZone ? 'Edit delivery zone' : 'New delivery zone' }}</h3>
              <p class="text-sm text-dimmed">Configure storefront shipping fees and delivery estimate windows by city.</p>
            </div>
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" square @click="zoneEditorOpen = false" />
          </div>
        </template>

        <div v-if="saveError" class="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
          {{ saveError }}
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Zone name">
            <UInput v-model="zoneForm.name" placeholder="Nairobi Urban" />
          </UFormField>
          <UFormField label="City">
            <UInput v-model="zoneForm.city" placeholder="Nairobi" />
          </UFormField>
          <UFormField label="Shipping fee">
            <UInput v-model="zoneForm.fee" type="number" min="0" step="0.01" />
          </UFormField>
          <UFormField label="Status">
            <USelect
              v-model="zoneForm.is_active"
              :items="[{ label: 'Active', value: true }, { label: 'Inactive', value: false }]"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Estimated minimum days">
            <UInput v-model="zoneForm.estimated_days_min" type="number" min="1" step="1" />
          </UFormField>
          <UFormField label="Estimated maximum days">
            <UInput v-model="zoneForm.estimated_days_max" type="number" min="1" step="1" />
          </UFormField>
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" :disabled="isSaving" @click="zoneEditorOpen = false">Cancel</UButton>
            <UButton :loading="isSaving" @click="submitZone">Save zone</UButton>
          </div>
        </template>
      </UCard>
    </div>

    <div v-if="orderEditorOpen && selectedOrder" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <UCard class="max-h-[92vh] w-full max-w-3xl overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">Shipping order</h3>
              <p class="text-sm text-dimmed">{{ selectedOrder.order_number }} · {{ selectedOrder.shipping_address.name }}</p>
            </div>
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" square @click="orderEditorOpen = false" />
          </div>
        </template>

        <div v-if="saveError" class="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
          {{ saveError }}
        </div>

        <div class="mb-5 grid grid-cols-1 gap-3 md:grid-cols-4">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Zone</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.delivery_zone_name || 'Unzoned' }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Shipping fee</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.currency }} {{ selectedOrder.shipping_amount }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Order total</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.currency }} {{ selectedOrder.total_amount }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Tracking</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedOrder.tracking_token }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Delivery agent">
            <USelect
              v-model="orderForm.delivery_agent_id"
              :items="[{ label: 'Unassigned', value: '' }, ...agents.filter(agent => agent.is_active).map(agent => ({ label: `${agent.display_name} · ${agent.phone_number}`, value: String(agent.id) }))]"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Delivery status">
            <USelect
              v-model="orderForm.delivery_status"
              :items="deliveryStatusOptions.filter(option => option.value !== '__all__')"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Tracking token" class="md:col-span-2">
            <UInput v-model="orderForm.tracking_token" />
          </UFormField>
          <UFormField label="Notes" class="md:col-span-2">
            <UTextarea v-model="orderForm.notes" :rows="4" autoresize placeholder="Add shipping or delivery notes..." />
          </UFormField>
        </div>

        <div class="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Shipping address</p>
          <p class="mt-2 text-sm font-medium text-slate-950">{{ selectedOrder.shipping_address.address_line_1 }}</p>
          <p class="text-sm text-slate-600">
            {{ selectedOrder.shipping_address.city }}<span v-if="selectedOrder.shipping_address.state_or_county">, {{ selectedOrder.shipping_address.state_or_county }}</span><span v-if="selectedOrder.shipping_address.postal_code">, {{ selectedOrder.shipping_address.postal_code }}</span>
          </p>
          <p class="text-sm text-slate-600">{{ selectedOrder.shipping_address.country }} · {{ selectedOrder.shipping_address.phone_number }}</p>
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" :disabled="isSaving" @click="orderEditorOpen = false">Cancel</UButton>
            <UButton :loading="isSaving" @click="submitOrder">Save shipping changes</UButton>
          </div>
        </template>
      </UCard>
    </div>

    <div v-if="pendingDeleteZone" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <UCard class="w-full max-w-lg">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">Delete delivery zone</h3>
              <p class="text-sm text-dimmed">Remove this delivery zone if it is no longer needed.</p>
            </div>
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" square @click="pendingDeleteZone = null" />
          </div>
        </template>
        <p class="text-sm text-slate-600">
          Delete <span class="font-semibold text-slate-950">{{ pendingDeleteZone.name }}</span> for <span class="font-semibold text-slate-950">{{ pendingDeleteZone.city }}</span>?
        </p>
        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" :disabled="isSaving" @click="pendingDeleteZone = null">Cancel</UButton>
            <UButton color="error" :loading="isSaving" @click="confirmDeleteZone">Delete zone</UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
