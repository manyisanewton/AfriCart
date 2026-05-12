import type { TableColumn } from '@nuxt/ui'
import type { OrderTableRow } from '~/types/OrderTableRow'
import { useSortableHeader } from '~/composables/useSortableHeader'
import type { SortBy, SortDir } from '~/types/Table'
import { formatMoney } from '~/utils/media'

function orderStatusColor(status: string) {
  const normalized = String(status || '').toLowerCase()

  if (['delivered', 'confirmed'].includes(normalized))
    return 'success'
  if (['processing', 'shipped'].includes(normalized))
    return 'primary'
  if (['cancelled', 'canceled'].includes(normalized))
    return 'error'
  return 'warning'
}

export function getOrderTableColumns({
  onManage,
  sortBy,
  sortDir,
  components,
}: {
  onManage: (order: OrderTableRow, event?: Event) => void
  sortBy: Ref<SortBy>
  sortDir: Ref<SortDir>
  components: Component[]
}): TableColumn<OrderTableRow>[] {
  const [UButton, UBadge] = components
  const { renderSortableHeader } = useSortableHeader(UButton!, sortBy, sortDir)

  return [
    {
      accessorKey: 'orderNumber',
      header: ({ column }) => renderSortableHeader('Order #', column),
      cell: ({ row }) =>
        h('span', { class: 'font-mono text-sm font-semibold text-slate-950' }, row.original.orderNumber),
    },
    {
      accessorKey: 'customerName',
      header: ({ column }) => renderSortableHeader('Customer', column),
      cell: ({ row }) =>
        h('div', { class: 'space-y-1' }, [
          h('div', { class: 'font-medium text-slate-950' }, row.original.customerName),
          h('div', { class: 'text-xs text-slate-500' }, row.original.phoneNumber || 'No phone number'),
        ]),
    },
    {
      accessorKey: 'status',
      header: ({ column }) => renderSortableHeader('Status', column),
      cell: ({ row }) =>
        h(UBadge as Component, {
          label: row.original.status,
          color: orderStatusColor(row.original.status),
          variant: 'soft',
          class: 'capitalize',
        }),
    },
    {
      accessorKey: 'deliveryStatus',
      header: ({ column }) => renderSortableHeader('Delivery', column),
      cell: ({ row }) =>
        h(UBadge as Component, {
          label: row.original.deliveryStatus || 'processing',
          color: 'neutral',
          variant: 'soft',
        }),
    },
    {
      accessorKey: 'itemCount',
      header: ({ column }) => renderSortableHeader('Items', column),
      cell: ({ row }) => `${row.original.itemCount}`,
    },
    {
      accessorKey: 'totalAmount',
      header: ({ column }) => renderSortableHeader('Total', column),
      cell: ({ row }) =>
        h('span', { class: 'font-semibold text-slate-950' }, formatMoney(row.original.totalAmount, row.original.currency)),
    },
    {
      accessorKey: 'createdAt',
      header: ({ column }) => renderSortableHeader('Created', column),
      cell: ({ row }) =>
        h('span', { class: 'text-sm text-slate-600' }, new Date(row.original.createdAt).toLocaleDateString()),
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
            'aria-label': `Manage ${row.original.orderNumber}`,
            onClick: (event: Event) => {
              event.stopPropagation()
              onManage(row.original, event)
            },
          }),
        ]),
    },
  ]
}
