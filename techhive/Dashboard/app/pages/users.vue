<script setup lang="ts">
import { getUserTableColumns } from '~/config/userTableColumns'
import type { SortBy, SortDir } from '~/types/Table'
import type { UserTableRow } from '~/types/UserTableRow'

const UBadge = resolveComponent('UBadge')
const UButton = resolveComponent('UButton')

const searchQuery = ref('')
const searchInput = ref('')
const ALL_ROLES = '__all_roles__'
const ALL_STATUSES = '__all_statuses__'
const roleFilter = ref(ALL_ROLES)
const statusFilter = ref(ALL_STATUSES)
const sortBy = ref<SortBy>()
const sortDir = ref<SortDir>('asc')
const userData = ref<UserTableRow[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const isEditorOpen = ref(false)
const selectedUser = ref<UserTableRow | null>(null)
const saveError = ref('')

const userForm = reactive({
  role: 'customer',
  status: 'active',
})

const roleOptions = [
  { label: 'All roles', value: ALL_ROLES },
  { label: 'Admin', value: 'admin' },
  { label: 'Vendor', value: 'vendor' },
  { label: 'Customer', value: 'customer' },
  { label: 'Delivery Agent', value: 'delivery_agent' },
]

const editableRoleOptions = roleOptions.filter(option => option.value !== ALL_ROLES)

const statusOptions = [
  { label: 'All statuses', value: ALL_STATUSES },
  { label: 'Active', value: 'active' },
  { label: 'Suspended', value: 'suspended' },
]

const { getUsers, updateUserActive, updateUserRole } = useUser()
const toast = useToast()

const columns = getUserTableColumns({
  onEdit: user => openEditUser(user),
  sortBy,
  sortDir,
  components: [UButton, UBadge] as Component[],
})

const filteredUsers = computed(() => {
  let rows = [...userData.value]

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    rows = rows.filter(user =>
      user.name.toLowerCase().includes(query)
      || user.email.toLowerCase().includes(query)
      || (user.phone || '').toLowerCase().includes(query),
    )
  }

  if (roleFilter.value !== ALL_ROLES) {
    rows = rows.filter(user => user.roleValue === roleFilter.value)
  }

  if (statusFilter.value !== ALL_STATUSES) {
    rows = rows.filter(user => statusFilter.value === 'active' ? user.isActive : !user.isActive)
  }

  if (sortBy.value) {
    const direction = sortDir.value === 'desc' ? -1 : 1
    rows.sort((a, b) => {
      const left = String(a[sortBy.value as keyof UserTableRow] || '').toLowerCase()
      const right = String(b[sortBy.value as keyof UserTableRow] || '').toLowerCase()
      return left.localeCompare(right) * direction
    })
  }

  return rows
})

const summary = computed(() => ({
  total: userData.value.length,
  active: userData.value.filter(user => user.isActive).length,
  suspended: userData.value.filter(user => !user.isActive).length,
  admins: userData.value.filter(user => user.roleValue === 'admin').length,
}))

function applySearch() {
  searchQuery.value = searchInput.value.trim()
}

function clearFilters() {
  searchInput.value = ''
  searchQuery.value = ''
  roleFilter.value = ALL_ROLES
  statusFilter.value = ALL_STATUSES
}

async function loadUsers() {
  isLoading.value = true
  const result = await getUsers()

  if (result.success) {
    userData.value = result.data?.items || []
  }
  else {
    userData.value = []
    toast.add({
      title: 'Could not load users',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }

  isLoading.value = false
}

function openEditUser(user: UserTableRow) {
  selectedUser.value = user
  userForm.role = user.roleValue || 'customer'
  userForm.status = user.isActive ? 'active' : 'suspended'
  saveError.value = ''
  isEditorOpen.value = true
}

async function submitUserForm() {
  if (!selectedUser.value)
    return

  saveError.value = ''
  isSaving.value = true

  const userId = selectedUser.value.id
  const currentRole = selectedUser.value.roleValue
  const currentIsActive = selectedUser.value.isActive

  if (currentRole !== userForm.role) {
    const roleResult = await updateUserRole(userId, userForm.role)
    if (!roleResult.success) {
      saveError.value = roleResult.error || 'Could not update user role.'
      isSaving.value = false
      return
    }
  }

  const nextIsActive = userForm.status === 'active'
  if (currentIsActive !== nextIsActive) {
    const activeResult = await updateUserActive(userId, nextIsActive)
    if (!activeResult.success) {
      saveError.value = activeResult.error || 'Could not update user status.'
      isSaving.value = false
      return
    }
  }

  toast.add({
    title: 'User updated',
    description: `${selectedUser.value.email} was updated successfully.`,
    color: 'success',
  })

  isEditorOpen.value = false
  selectedUser.value = null
  await loadUsers()
  isSaving.value = false
}

onMounted(loadUsers)
</script>

<template>
  <div>
    <div class="mb-4 flex flex-col gap-4 p-4 pb-2 sm:p-8 sm:pb-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h1 class="text-2xl font-black text-slate-950">Users</h1>
        <p class="mt-1 text-sm text-slate-500">Manage live TechHive users, roles, and account status.</p>
      </div>

      <div class="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
        <form class="flex min-w-56 flex-1 gap-2 lg:max-w-sm" @submit.prevent="applySearch">
          <UInput
            v-model="searchInput"
            class="flex-1"
            color="neutral"
            variant="outline"
            size="lg"
            icon="i-lucide-search"
            placeholder="Search users..."
            :ui="{ leadingIcon: 'size-4' }"
          />
          <UButton color="neutral" variant="outline" type="submit" size="lg">
            Search
          </UButton>
        </form>

        <USelect
          v-model="roleFilter"
          :items="roleOptions"
          class="min-w-56 flex-1 lg:max-w-sm"
          color="neutral"
          variant="outline"
          size="lg"
          value-attribute="value"
          option-attribute="label"
        />

        <USelect
          v-model="statusFilter"
          :items="statusOptions"
          value-attribute="value"
          option-attribute="label"
          class="min-w-40"
          color="neutral"
          variant="outline"
          size="lg"
        />

        <UButton variant="outline" :loading="isLoading" @click="loadUsers">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
        <UButton variant="ghost" color="neutral" @click="clearFilters">
          Clear
        </UButton>
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-4 px-4 sm:grid-cols-2 sm:px-8 lg:grid-cols-4">
      <CardsKpiCard2
        name="Total Users"
        :value="summary.total"
        :budget="summary.total"
        color="var(--color-info)"
        icon="i-lucide-users"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Active"
        :value="summary.active"
        :budget="summary.total"
        color="var(--color-success)"
        icon="i-lucide-user-check"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Suspended"
        :value="summary.suspended"
        :budget="summary.total"
        color="var(--color-error)"
        icon="i-lucide-user-x"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Admins"
        :value="summary.admins"
        :budget="summary.total"
        color="var(--color-warning)"
        icon="i-lucide-shield"
        :loading="isLoading"
      />
    </div>

    <div class="px-4 sm:px-8">
      <UTable
        class="cursor-pointer"
        :data="filteredUsers"
        :columns="columns"
        :loading="isLoading"
        @select="(user) => openEditUser(user.original || user)"
      />
    </div>

    <div
      v-if="isEditorOpen && selectedUser"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
    >
      <UCard class="max-h-[92vh] w-full max-w-3xl overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">Manage user</h3>
              <p class="text-sm text-dimmed">Change role or suspend/activate the selected account.</p>
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
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Name</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedUser.name }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Email</p>
            <p class="mt-1 font-semibold text-slate-950 break-all">{{ selectedUser.email }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold uppercase tracking-wide text-slate-500">Phone</p>
            <p class="mt-1 font-semibold text-slate-950">{{ selectedUser.phone || 'No phone number' }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Role">
            <USelect
              v-model="userForm.role"
              :items="editableRoleOptions"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormField>
          <UFormField label="Status">
            <USelect
              v-model="userForm.status"
              :items="statusOptions.filter(option => option.value !== ALL_STATUSES)"
              value-attribute="value"
              option-attribute="label"
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
              @click="submitUserForm"
            >
              Save changes
            </UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
