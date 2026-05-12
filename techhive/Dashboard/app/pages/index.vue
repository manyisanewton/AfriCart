<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type {
  AdminDashboardAuditEvent,
  AdminDashboardOrder,
  AdminDashboardResponse,
  AdminDashboardSupportTicket,
  AdminDashboardTopProduct,
} from '~/composables/useDashboard'

const { getDashboard } = useDashboard()
const toast = useToast()

const isLoading = ref(false)
const summary = ref<AdminDashboardResponse | null>(null)

const moneyFormatter = computed(() =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'KES',
    maximumFractionDigits: 0,
  }),
)

const latestOrderColumns: TableColumn<AdminDashboardOrder>[] = [
  {
    accessorKey: 'order_number',
    header: 'Order',
  },
  {
    accessorKey: 'created_at',
    header: 'Date',
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  },
  {
    accessorKey: 'total_amount',
    header: 'Total',
    cell: ({ row }) => moneyFormatter.value.format(Number(row.original.total_amount || 0)),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => h(resolveComponent('UBadge'), {
      label: row.original.status || 'pending',
      color: statusColor(row.original.status),
      variant: 'subtle',
    }),
  },
]

const productColumns: TableColumn<AdminDashboardTopProduct>[] = [
  {
    accessorKey: 'product_name',
    header: 'Product',
  },
  {
    accessorKey: 'units_sold',
    header: 'Units Sold',
  },
  {
    accessorKey: 'revenue',
    header: 'Revenue',
    cell: ({ row }) => moneyFormatter.value.format(Number(row.original.revenue || 0)),
  },
]

const supportColumns: TableColumn<AdminDashboardSupportTicket>[] = [
  {
    accessorKey: 'subject',
    header: 'Ticket',
  },
  {
    accessorKey: 'created_at',
    header: 'Opened',
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => h(resolveComponent('UBadge'), {
      label: row.original.status || 'open',
      color: supportStatusColor(row.original.status),
      variant: 'subtle',
    }),
  },
]

const auditColumns: TableColumn<AdminDashboardAuditEvent>[] = [
  {
    accessorKey: 'action',
    header: 'Action',
  },
  {
    accessorKey: 'entity_type',
    header: 'Entity',
  },
  {
    accessorKey: 'created_at',
    header: 'Time',
    cell: ({ row }) => new Date(row.original.created_at).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  },
]

function statusColor(status: string) {
  const normalized = (status || '').toLowerCase()
  if (['paid', 'shipped', 'delivered', 'complete', 'completed'].includes(normalized))
    return 'success'
  if (['failed', 'cancelled', 'canceled'].includes(normalized))
    return 'error'
  return 'warning'
}

function supportStatusColor(status: string) {
  const normalized = (status || '').toLowerCase()
  if (['resolved', 'closed'].includes(normalized))
    return 'success'
  if (['in_progress'].includes(normalized))
    return 'warning'
  return 'neutral'
}

async function loadDashboard() {
  isLoading.value = true
  const result = await getDashboard()
  if (result.success) {
    summary.value = result.data
  }
  else {
    toast.add({
      title: 'Could not load admin dashboard',
      description: result.error || 'Please sign in and try again.',
      color: 'error',
    })
  }
  isLoading.value = false
}

onMounted(loadDashboard)
</script>

<template>
  <div class="min-h-screen bg-default">
    <div class="flex flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between md:px-8">
      <div>
        <h1 class="text-xl font-semibold">Admin Overview</h1>
        <p class="text-sm text-toned">
          Live TechHive platform snapshot from the shared backend database.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <UBadge color="neutral" variant="soft">
          {{ summary?.generated_at ? new Date(summary.generated_at).toLocaleString() : 'Loading…' }}
        </UBadge>
        <UButton variant="outline" :loading="isLoading" @click="loadDashboard">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 px-4 md:grid-cols-2 md:px-8 xl:grid-cols-4">
      <CardsKpiCard2
        name="Revenue"
        :value="Number(summary?.commerce?.total_revenue || 0)"
        :budget="Number(summary?.commerce?.total_revenue || 0)"
        format="currency"
        currency="KES"
        color="var(--color-success)"
        icon="i-lucide-banknote"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Orders"
        :value="summary?.summary?.order_count || 0"
        :budget="summary?.summary?.pending_order_count || 0"
        color="var(--color-info)"
        icon="i-lucide-shopping-cart"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Products"
        :value="summary?.catalog?.product_count || 0"
        :budget="summary?.catalog?.low_stock_product_count || 0"
        color="var(--color-warning)"
        icon="i-lucide-box"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Users"
        :value="summary?.summary?.user_count || 0"
        :budget="summary?.summary?.active_user_count || 0"
        color="var(--color-primary)"
        icon="i-lucide-users"
        :loading="isLoading"
      />
    </div>

    <div class="mt-6 grid grid-cols-1 gap-6 px-4 md:px-8 xl:grid-cols-3">
      <UCard>
        <template #header>
          <div>
            <h3 class="text-base font-semibold">Marketplace Health</h3>
            <p class="text-sm text-toned">Core platform counts that need daily attention.</p>
          </div>
        </template>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Pending vendors</span>
            <UBadge color="warning" variant="soft">{{ summary?.summary?.pending_vendor_count || 0 }}</UBadge>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Pending KYC</span>
            <UBadge color="warning" variant="soft">{{ summary?.summary?.pending_kyc_count || 0 }}</UBadge>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Open support tickets</span>
            <UBadge color="error" variant="soft">{{ summary?.summary?.open_support_ticket_count || 0 }}</UBadge>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Failed payments</span>
            <UBadge color="error" variant="soft">{{ summary?.summary?.failed_payment_count || 0 }}</UBadge>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div>
            <h3 class="text-base font-semibold">Catalog Signals</h3>
            <p class="text-sm text-toned">Inventory and product-state visibility.</p>
          </div>
        </template>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Inactive products</span>
            <UBadge color="neutral" variant="soft">{{ summary?.catalog?.inactive_product_count || 0 }}</UBadge>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Low stock products</span>
            <UBadge color="warning" variant="soft">{{ summary?.catalog?.low_stock_product_count || 0 }}</UBadge>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Approved vendors</span>
            <UBadge color="success" variant="soft">{{ summary?.summary?.approved_vendor_count || 0 }}</UBadge>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-toned">Payment records</span>
            <UBadge color="neutral" variant="soft">{{ summary?.summary?.payment_count || 0 }}</UBadge>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div>
            <h3 class="text-base font-semibold">Quick Links</h3>
            <p class="text-sm text-toned">Jump into the most important admin surfaces.</p>
          </div>
        </template>
        <div class="grid grid-cols-1 gap-3">
          <NuxtLink to="/orders"><UButton block variant="outline" color="neutral" icon="i-lucide-receipt">Orders</UButton></NuxtLink>
          <NuxtLink to="/products"><UButton block variant="outline" color="neutral" icon="i-lucide-box">Products</UButton></NuxtLink>
          <NuxtLink to="/users"><UButton block variant="outline" color="neutral" icon="i-lucide-user">Users</UButton></NuxtLink>
          <NuxtLink to="/support"><UButton block variant="outline" color="neutral" icon="i-lucide-message-circle">Support</UButton></NuxtLink>
        </div>
      </UCard>
    </div>

    <div class="mt-6 grid grid-cols-1 gap-6 px-4 md:px-8 xl:grid-cols-2">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold">Recent Orders</h3>
            <NuxtLink to="/orders">
              <UButton color="neutral" variant="ghost" size="sm">View all</UButton>
            </NuxtLink>
          </div>
        </template>
        <UTable
          :columns="latestOrderColumns"
          :data="summary?.commerce?.recent_orders || []"
          :loading="isLoading"
        />
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold">Top Products</h3>
            <NuxtLink to="/products">
              <UButton color="neutral" variant="ghost" size="sm">Manage products</UButton>
            </NuxtLink>
          </div>
        </template>
        <UTable
          :columns="productColumns"
          :data="summary?.catalog?.top_products || []"
          :loading="isLoading"
        />
      </UCard>
    </div>

    <div class="mt-6 grid grid-cols-1 gap-6 px-4 pb-8 md:px-8 xl:grid-cols-2">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold">Support Queue</h3>
            <NuxtLink to="/support">
              <UButton color="neutral" variant="ghost" size="sm">Open support</UButton>
            </NuxtLink>
          </div>
        </template>
        <UTable
          :columns="supportColumns"
          :data="summary?.operations?.recent_support_tickets || []"
          :loading="isLoading"
        />
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold">Latest Audit Events</h3>
            <NuxtLink to="/audit-logs">
              <UButton color="neutral" variant="ghost" size="sm">Audit logs</UButton>
            </NuxtLink>
          </div>
        </template>
        <UTable
          :columns="auditColumns"
          :data="summary?.audit?.latest_events || []"
          :loading="isLoading"
        />
      </UCard>
    </div>
  </div>
</template>
