<script setup lang="ts">
import type { AdminOperationsQueues, AdminOverviewReport, VendorPerformanceItem } from '~/composables/useReports'

const { getOverviewReport, getOperationsQueues, getVendorPerformance } = useReports()
const toast = useToast()

const isLoading = ref(false)
const vendorLimit = ref(10)
const overview = ref<AdminOverviewReport | null>(null)
const vendorPerformance = ref<VendorPerformanceItem[]>([])
const operationsQueues = ref<AdminOperationsQueues | null>(null)

const vendorLimitOptions = [
  { label: 'Top 5', value: 5 },
  { label: 'Top 10', value: 10 },
  { label: 'Top 20', value: 20 },
]

const summaryCards = computed(() => {
  const summary = overview.value?.summary || {}

  return [
    {
      key: 'gross_revenue',
      label: 'Gross revenue',
      value: summary.gross_revenue || '0.00',
      icon: 'i-lucide-banknote',
      color: 'var(--color-success)',
    },
    {
      key: 'order_count',
      label: 'Orders',
      value: Number(summary.order_count || 0),
      icon: 'i-lucide-receipt',
      color: 'var(--color-info)',
    },
    {
      key: 'user_count',
      label: 'Users',
      value: Number(summary.user_count || 0),
      icon: 'i-lucide-users',
      color: 'var(--color-primary)',
    },
    {
      key: 'vendor_count',
      label: 'Vendors',
      value: Number(summary.vendor_count || 0),
      icon: 'i-lucide-store',
      color: 'var(--color-warning)',
    },
  ]
})

const queueCards = computed(() => {
  const summary = operationsQueues.value?.summary
  if (!summary)
    return []

  return [
    { key: 'pending_vendor_count', label: 'Pending vendors', value: summary.pending_vendor_count, icon: 'i-lucide-store' },
    { key: 'pending_kyc_count', label: 'Pending KYC', value: summary.pending_kyc_count, icon: 'i-lucide-file-badge' },
    { key: 'open_support_ticket_count', label: 'Open support', value: summary.open_support_ticket_count, icon: 'i-lucide-life-buoy' },
    { key: 'pending_refund_count', label: 'Pending refunds', value: summary.pending_refund_count, icon: 'i-lucide-rotate-ccw' },
    { key: 'failed_notification_delivery_count', label: 'Failed deliveries', value: summary.failed_notification_delivery_count, icon: 'i-lucide-mail-warning' },
    { key: 'stale_pending_payment_count', label: 'Stale payments', value: summary.stale_pending_payment_count, icon: 'i-lucide-credit-card' },
    { key: 'low_stock_product_count', label: 'Low stock', value: summary.low_stock_product_count, icon: 'i-lucide-package-minus' },
  ]
})

const breakdownGroups = computed(() => {
  const breakdowns = overview.value?.breakdowns || {}
  return [
    { key: 'orders', label: 'Orders', values: breakdowns.orders || {} },
    { key: 'payments', label: 'Payments', values: breakdowns.payments || {} },
    { key: 'vendors', label: 'Vendors', values: breakdowns.vendors || {} },
    { key: 'support_tickets', label: 'Support tickets', values: breakdowns.support_tickets || {} },
    { key: 'refunds', label: 'Refunds', values: breakdowns.refunds || {} },
  ]
})

function formatLabel(value: string) {
  return value
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatCurrency(value: string | number) {
  return new Intl.NumberFormat('en-KE', {
    style: 'currency',
    currency: 'KES',
  }).format(Number(value || 0))
}

async function loadReports() {
  isLoading.value = true

  const [overviewResult, vendorResult, queueResult] = await Promise.all([
    getOverviewReport(),
    getVendorPerformance(vendorLimit.value),
    getOperationsQueues(),
  ])

  if (overviewResult.success)
    overview.value = overviewResult.data || null
  else {
    overview.value = null
    toast.add({
      title: 'Could not load overview report',
      description: overviewResult.error || 'Please try again.',
      color: 'error',
    })
  }

  if (vendorResult.success)
    vendorPerformance.value = vendorResult.data || []
  else {
    vendorPerformance.value = []
    toast.add({
      title: 'Could not load vendor performance',
      description: vendorResult.error || 'Please try again.',
      color: 'error',
    })
  }

  if (queueResult.success)
    operationsQueues.value = queueResult.data || null
  else {
    operationsQueues.value = null
    toast.add({
      title: 'Could not load operations queues',
      description: queueResult.error || 'Please try again.',
      color: 'error',
    })
  }

  isLoading.value = false
}

watch(vendorLimit, async () => {
  await loadReports()
})

onMounted(loadReports)
</script>

<template>
  <div class="px-4 py-8 sm:px-6 lg:px-10">
    <div class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 class="text-3xl font-black tracking-tight text-slate-950">
          Reports
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-slate-600">
          Platform-level reporting for revenue, commerce health, vendor performance, and operational queues from the shared TechHive backend.
        </p>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <USelect
          v-model="vendorLimit"
          :items="vendorLimitOptions"
          value-attribute="value"
          option-attribute="label"
          class="w-full sm:w-36"
          size="lg"
          variant="outline"
        />
        <UButton variant="outline" size="lg" :loading="isLoading" @click="loadReports">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <CardsKpiCard2
        v-for="card in summaryCards"
        :key="card.key"
        :name="card.label"
        :value="card.key === 'gross_revenue' ? card.value : Number(card.value)"
        :budget="card.key === 'gross_revenue' ? card.value : Number(card.value)"
        :color="card.color"
        :icon="card.icon"
        :loading="isLoading"
      />
    </div>

    <div class="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="mb-5">
        <h2 class="text-xl font-black text-slate-950">Operations queues</h2>
        <p class="mt-1 text-sm text-slate-600">Current operational backlog across vendors, KYC, support, refunds, notifications, payments, and stock alerts.</p>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <CardsKpiCard2
          v-for="card in queueCards"
          :key="card.key"
          :name="card.label"
          :value="card.value"
          :budget="card.value"
          color="var(--color-info)"
          :icon="card.icon"
          :loading="isLoading"
        />
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-5">
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-3">
        <div class="mb-5">
          <h2 class="text-xl font-black text-slate-950">Status breakdowns</h2>
          <p class="mt-1 text-sm text-slate-600">How the platform is currently distributed across major operational states.</p>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div
            v-for="group in breakdownGroups"
            :key="group.key"
            class="rounded-xl border border-slate-200 bg-slate-50 p-4"
          >
            <h3 class="font-semibold text-slate-950">{{ group.label }}</h3>
            <div v-if="Object.keys(group.values).length" class="mt-3 space-y-2">
              <div
                v-for="(count, label) in group.values"
                :key="label"
                class="flex items-center justify-between gap-3 text-sm"
              >
                <span class="text-slate-600">{{ formatLabel(String(label)) }}</span>
                <UBadge color="neutral" variant="soft">{{ count }}</UBadge>
              </div>
            </div>
            <p v-else class="mt-3 text-sm text-slate-500">No data available.</p>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
        <div class="mb-5">
          <h2 class="text-xl font-black text-slate-950">Queue references</h2>
          <p class="mt-1 text-sm text-slate-600">The first live IDs in each admin queue so operations can jump into the right page quickly.</p>
        </div>

        <div class="space-y-4">
          <div
            v-for="(ids, key) in operationsQueues?.queues || {}"
            :key="key"
            class="rounded-xl border border-slate-200 bg-slate-50 p-4"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="font-semibold text-slate-950">{{ formatLabel(key) }}</p>
              <UBadge color="neutral" variant="soft">{{ ids.length }}</UBadge>
            </div>
            <p class="mt-2 text-sm text-slate-600">
              {{ ids.length ? ids.map(id => `#${id}`).join(', ') : 'No queued records.' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div class="flex flex-col gap-2 border-b border-slate-200 bg-slate-50 px-6 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="text-xl font-black text-slate-950">Vendor performance</h2>
          <p class="mt-1 text-sm text-slate-600">Top vendors ranked by revenue and marketplace output.</p>
        </div>
        <UBadge color="neutral" variant="soft">Top {{ vendorLimit }}</UBadge>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-sm">
          <thead class="bg-white">
            <tr>
              <th class="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Vendor</th>
              <th class="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Status</th>
              <th class="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Revenue</th>
              <th class="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Orders</th>
              <th class="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Units sold</th>
              <th class="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Products</th>
              <th class="whitespace-nowrap px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Low stock</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="isLoading">
              <td colspan="7" class="px-4 py-12 text-center text-sm font-semibold text-slate-500">
                <UIcon name="i-lucide-loader-circle" class="mr-2 animate-spin" />
                Loading report
              </td>
            </tr>
            <tr v-else-if="vendorPerformance.length === 0">
              <td colspan="7" class="px-4 py-12 text-center text-sm text-slate-500">
                No vendor performance data available.
              </td>
            </tr>
            <tr v-for="vendor in vendorPerformance" v-else :key="vendor.vendor_id" class="hover:bg-slate-50">
              <td class="px-4 py-3 text-slate-700">
                <div class="space-y-1">
                  <p class="font-semibold text-slate-950">{{ vendor.business_name }}</p>
                  <p class="text-xs text-slate-500">@{{ vendor.slug }}</p>
                </div>
              </td>
              <td class="px-4 py-3 text-slate-700">
                <UBadge :label="formatLabel(vendor.status)" :color="vendor.status === 'approved' ? 'success' : vendor.status === 'pending' ? 'warning' : vendor.status === 'suspended' ? 'info' : 'error'" variant="soft" />
              </td>
              <td class="px-4 py-3 text-slate-700">{{ formatCurrency(vendor.revenue) }}</td>
              <td class="px-4 py-3 text-slate-700">{{ Number(vendor.order_count).toLocaleString('en-KE') }}</td>
              <td class="px-4 py-3 text-slate-700">{{ Number(vendor.units_sold).toLocaleString('en-KE') }}</td>
              <td class="px-4 py-3 text-slate-700">{{ Number(vendor.product_count).toLocaleString('en-KE') }} / {{ Number(vendor.active_product_count).toLocaleString('en-KE') }} active</td>
              <td class="px-4 py-3 text-slate-700">{{ Number(vendor.low_stock_count).toLocaleString('en-KE') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
