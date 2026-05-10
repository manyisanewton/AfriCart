import type { TableColumn } from '@nuxt/ui'
import type { UserTableRow } from '~/types/UserTableRow'
import { useSortableHeader } from '~/composables/useSortableHeader'
import type { SortBy, SortDir } from '~/types/Table'

export function getUserTableColumns({
  onEdit,
  sortBy,
  sortDir,
  components,
}: {
  onEdit: (user: UserTableRow, event?: Event) => void
  sortBy: Ref<SortBy>
  sortDir: Ref<SortDir>
  components: Component[]
}): TableColumn<UserTableRow>[] {
  const [UButton, UBadge] = components
  const { renderSortableHeader } = useSortableHeader(UButton!, sortBy, sortDir)

  return [
    {
      accessorKey: 'name',
      header: ({ column }) => renderSortableHeader('User', column),
      cell: ({ row }) => h('div', { class: 'space-y-1' }, [
        h('div', { class: 'font-medium text-default' }, row.original.name),
        h('div', { class: 'text-xs text-slate-500' }, row.original.phone || 'No phone number'),
      ]),
    },
    {
      accessorKey: 'email',
      header: ({ column }) => renderSortableHeader('Email', column),
      cell: ({ row }) => h('div', { class: 'space-y-1' }, [
        h('div', row.original.email),
        h(UBadge as Component, {
          label: row.original.emailVerified ? 'Verified' : 'Unverified',
          color: row.original.emailVerified ? 'success' : 'warning',
          variant: 'soft',
        }),
      ]),
    },
    {
      accessorKey: 'role',
      header: ({ column }) => renderSortableHeader('Role', column),
      cell: ({ row }) => row.original.role,
    },
    {
      accessorKey: 'status',
      header: ({ column }) => renderSortableHeader('Status', column),
      cell: ({ row }) => {
        const color = row.original.status === 'Active' ? 'success' : 'error'
        return h(UBadge as Component, {
          label: row.original.status,
          color,
          variant: 'soft',
        })
      },
    },
    {
      accessorKey: 'joined',
      header: ({ column }) => renderSortableHeader('Joined', column),
      cell: ({ row }) => row.original.joined,
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
            'aria-label': `Manage ${row.original.name}`,
            onClick: (event: Event) => {
              event.stopPropagation()
              onEdit(row.original, event)
            },
          }),
        ]),
    },
  ]
}
