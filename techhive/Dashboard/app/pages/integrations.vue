<script setup lang="ts">
import type {
  ERPNextPreviewResource,
  ERPNextPreviewResult,
  IntegrationConnection,
  IntegrationConnectionPayload,
  IntegrationLog,
} from '~/composables/useIntegrations'

const toast = useToast()
const { createConnection, deleteConnection, getConnection, getConnections, getLogs, testConnection, syncStock, previewERPNext, importERPNextCatalog, updateConnection } = useIntegrations()
const { getPartners } = usePartners()

const connections = ref<IntegrationConnection[]>([])
const selectedConnection = ref<IntegrationConnection | null>(null)
const logs = ref<IntegrationLog[]>([])
const detailLogs = ref<IntegrationLog[]>([])
const isLoading = ref(false)
const actionId = ref<number | null>(null)
const previewActionId = ref<number | null>(null)
const importActionId = ref<number | null>(null)
const previewResource = ref<ERPNextPreviewResource>('items')
const previewLimit = ref(20)
const previewResult = ref<ERPNextPreviewResult | null>(null)
const previewConnection = ref<IntegrationConnection | null>(null)
const importIncludeStock = ref(true)
const importSummary = ref<Record<string, any> | null>(null)
const editorOpen = ref(false)
const editingConnection = ref<IntegrationConnection | null>(null)
const deleteTarget = ref<IntegrationConnection | null>(null)
const formError = ref('')
const detailTestResult = ref<Record<string, any> | null>(null)
const partnerOptions = ref<{ label: string, value: number | string }[]>([{ label: 'No partner', value: '__none__' }])
const NO_PARTNER = '__none__'
const connectionTypeOptions = [
  { label: 'ERPNext', value: 'erpnext' },
  { label: 'Zoho Inventory', value: 'zoho_inventory' },
  { label: 'Custom REST', value: 'custom_rest' },
]
const authTypeOptions = [
  { label: 'API key / secret', value: 'api_key_secret' },
  { label: 'Username / password', value: 'username_password' },
  { label: 'Token', value: 'token' },
]
const credentialSourceOptions = [
  { label: 'Environment', value: 'environment' },
  { label: 'Vault / external secret store', value: 'vault' },
]
const connectionStatusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Active', value: 'active' },
  { label: 'Error', value: 'error' },
  { label: 'Disabled', value: 'disabled' },
]
const connectionForm = reactive<IntegrationConnectionPayload>({
  name: '',
  partner_id: null,
  connection_type: 'erpnext',
  base_url: '',
  auth_type: 'api_key_secret',
  credential_source: 'environment',
  secret_env_prefix: '',
  credential_values: {},
  default_company: '',
  default_warehouse: '',
  poll_interval_minutes: 30,
  status: 'draft',
  is_active: true,
})

const previewResourceOptions = [
  { label: 'Items', value: 'items' },
  { label: 'Stock', value: 'stock' },
  { label: 'Prices', value: 'prices' },
]

const previewLimitOptions = [
  { label: '10 records', value: 10 },
  { label: '20 records', value: 20 },
  { label: '50 records', value: 50 },
  { label: '100 records', value: 100 },
]

const credentialFieldOptions = computed(() => {
  switch (connectionForm.connection_type) {
    case 'erpnext':
      return [
        { key: 'api_key', label: 'API Key' },
        { key: 'api_secret', label: 'API Secret' },
      ]
    case 'zoho_inventory':
      return [
        { key: 'organization_id', label: 'Organization ID' },
        { key: 'client_id', label: 'Client ID' },
        { key: 'client_secret', label: 'Client Secret' },
        { key: 'refresh_token', label: 'Refresh Token' },
      ]
    case 'custom_rest':
      if (connectionForm.auth_type === 'username_password') {
        return [
          { key: 'username', label: 'Username' },
          { key: 'password', label: 'Password' },
        ]
      }
      if (connectionForm.auth_type === 'token') {
        return [
          { key: 'access_token', label: 'Access Token' },
        ]
      }
      return [
        { key: 'api_key', label: 'API Key' },
        { key: 'api_secret', label: 'API Secret' },
      ]
    case 'mpesa':
      return [
        { key: 'consumer_key', label: 'Consumer Key' },
        { key: 'consumer_secret', label: 'Consumer Secret' },
        { key: 'shortcode', label: 'Shortcode' },
        { key: 'passkey', label: 'Passkey' },
        { key: 'transaction_type', label: 'Transaction Type' },
      ]
    case 'smtp':
      return [
        { key: 'host', label: 'SMTP Host' },
        { key: 'port', label: 'Port' },
        { key: 'username', label: 'Username' },
        { key: 'password', label: 'Password' },
        { key: 'from_email', label: 'From Email' },
        { key: 'from_name', label: 'From Name' },
      ]
    case 'twilio':
      return [
        { key: 'account_sid', label: 'Account SID' },
        { key: 'auth_token', label: 'Auth Token' },
        { key: 'from_number', label: 'From Number' },
        { key: 'messaging_service_sid', label: 'Messaging Service SID' },
      ]
    case 'sentry':
      return [
        { key: 'dsn', label: 'DSN' },
        { key: 'environment', label: 'Environment' },
      ]
    default:
      return []
  }
})

const activeConnections = computed(() => connections.value.filter(connection => connection.is_active).length)
const healthyConnections = computed(() => connections.value.filter(connection => connection.status === 'active').length)
const errorConnections = computed(() => connections.value.filter(connection => connection.status === 'error').length)
const credentialsReadOnly = computed(() => Boolean(editingConnection.value?.credentials?.read_only))
const previewColumns = computed(() => {
  const firstRecord = previewResult.value?.records?.[0]
  if (!firstRecord)
    return []

  return Object.keys(firstRecord).slice(0, 7)
})

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '')
    return '-'

  if (typeof value === 'object')
    return JSON.stringify(value)

  return String(value)
}

function openCreateConnection() {
  editingConnection.value = null
  formError.value = ''
  detailLogs.value = []
  detailTestResult.value = null
  connectionForm.name = ''
  connectionForm.partner_id = null
  connectionForm.connection_type = 'erpnext'
  connectionForm.base_url = ''
  connectionForm.auth_type = 'api_key_secret'
  connectionForm.credential_source = 'environment'
  connectionForm.secret_env_prefix = ''
  connectionForm.credential_values = {}
  connectionForm.default_company = ''
  connectionForm.default_warehouse = ''
  connectionForm.poll_interval_minutes = 30
  connectionForm.status = 'draft'
  connectionForm.is_active = true
  editorOpen.value = true
}

async function openEditConnection(connection: IntegrationConnection) {
  actionId.value = connection.id
  const detailResult = await getConnection(connection.id)
  const logsResult = await getLogs(connection.id)
  if (!detailResult.success || !detailResult.data) {
    toast.add({
      title: 'Could not load integration',
      description: detailResult.error || 'Please try again.',
      color: 'error',
    })
    actionId.value = null
    return
  }

  editingConnection.value = detailResult.data
  detailLogs.value = logsResult.data || []
  formError.value = ''
  detailTestResult.value = null
  connectionForm.name = detailResult.data.name
  connectionForm.partner_id = detailResult.data.partner ?? null
  connectionForm.connection_type = detailResult.data.connection_type
  connectionForm.base_url = detailResult.data.base_url
  connectionForm.auth_type = detailResult.data.auth_type
  connectionForm.credential_source = detailResult.data.credential_source
  connectionForm.secret_env_prefix = detailResult.data.secret_env_prefix || ''
  connectionForm.credential_values = { ...(detailResult.data.credentials?.values || {}) }
  connectionForm.default_company = detailResult.data.default_company || ''
  connectionForm.default_warehouse = detailResult.data.default_warehouse || ''
  connectionForm.poll_interval_minutes = detailResult.data.poll_interval_minutes || 30
  connectionForm.status = detailResult.data.status
  connectionForm.is_active = detailResult.data.is_active
  editorOpen.value = true
  actionId.value = null
}

function statusColor(status: string) {
  if (status === 'active')
    return 'success'
  if (status === 'error')
    return 'error'
  if (status === 'disabled')
    return 'neutral'
  return 'warning'
}

function formatDate(value?: string | null) {
  if (!value)
    return 'Never'

  return new Date(value).toLocaleString('en-KE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

async function loadLogs(connection: IntegrationConnection) {
  selectedConnection.value = connection
  const result = await getLogs(connection.id)
  logs.value = result.data || []

  if (!result.success) {
    toast.add({
      title: 'Could not load logs',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }
}

async function loadConnections() {
  isLoading.value = true
  const partnersResult = await getPartners({ pageSize: 200 })
  if (partnersResult.success) {
    partnerOptions.value = [
      { label: 'No partner', value: NO_PARTNER },
      ...(partnersResult.data?.results ?? []).map(partner => ({
        label: `${partner.name}${partner.code ? ` (${partner.code})` : ''}`,
        value: partner.id,
      })),
    ]
  }
  const result = await getConnections()

  if (result.success) {
    connections.value = result.data || []
    if (!selectedConnection.value && connections.value.length)
      await loadLogs(connections.value[0])
  }
  else {
    connections.value = []
    toast.add({
      title: 'Could not load integrations',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }

  isLoading.value = false
}

async function submitConnection() {
  formError.value = ''
  if (!connectionForm.name.trim()) {
    formError.value = 'Connection name is required.'
    return
  }
  if (!connectionForm.base_url.trim()) {
    formError.value = 'Base URL is required.'
    return
  }

  actionId.value = editingConnection.value?.id ?? -999
  const payload: IntegrationConnectionPayload = {
    ...connectionForm,
    name: connectionForm.name.trim(),
    base_url: connectionForm.base_url.trim(),
    secret_env_prefix: String(connectionForm.secret_env_prefix || '').trim() || null,
    credential_values: Object.fromEntries(
      Object.entries(connectionForm.credential_values || {})
        .map(([key, value]) => [key, String(value || '').trim()])
        .filter(([, value]) => value),
    ),
    default_company: String(connectionForm.default_company || '').trim() || null,
    default_warehouse: String(connectionForm.default_warehouse || '').trim() || null,
    partner_id: connectionForm.partner_id === NO_PARTNER ? null : (connectionForm.partner_id as number | null),
  }
  const result = editingConnection.value?.id && editingConnection.value.id > 0
    ? await updateConnection(editingConnection.value.id, payload)
    : await createConnection(payload)

  if (result.success) {
    toast.add({
      title: editingConnection.value?.id && editingConnection.value.id > 0 ? 'Connection updated' : 'Connection created',
      description: `${payload.name} is ready for use.`,
      color: 'success',
    })
    editorOpen.value = false
    await loadConnections()
  }
  else {
    formError.value = result.error || 'Could not save the connection.'
    toast.add({ title: 'Save failed', description: formError.value, color: 'error' })
  }
  actionId.value = null
}

async function runDetailTest() {
  if (!editingConnection.value)
    return

  actionId.value = editingConnection.value.id
  const result = await testConnection(editingConnection.value.id)
  if (result.success) {
    detailTestResult.value = result.data || {}
    toast.add({
      title: 'Connection is reachable',
      description: 'The backend confirmed this connection.',
      color: 'success',
    })
    const refreshedLogs = await getLogs(editingConnection.value.id)
    detailLogs.value = refreshedLogs.data || []
  }
  else {
    detailTestResult.value = null
    toast.add({
      title: 'Connection test failed',
      description: result.error || 'Please check the connection.',
      color: 'error',
    })
  }
  await loadConnections()
  actionId.value = null
}

async function confirmDeleteConnection() {
  if (!deleteTarget.value)
    return

  actionId.value = deleteTarget.value.id
  const result = await deleteConnection(deleteTarget.value.id)
  if (result.success) {
    toast.add({ title: 'Connection deleted', description: `${deleteTarget.value.name} was removed.`, color: 'success' })
    if (selectedConnection.value?.id === deleteTarget.value.id) {
      selectedConnection.value = null
      logs.value = []
    }
    deleteTarget.value = null
    await loadConnections()
  }
  else {
    toast.add({ title: 'Delete failed', description: result.error || 'Could not delete connection.', color: 'error' })
  }
  actionId.value = null
}

async function runTest(connection: IntegrationConnection) {
  actionId.value = connection.id
  const result = await testConnection(connection.id)

  toast.add({
    title: result.success ? 'Connection is reachable' : 'Connection test failed',
    description: result.success ? 'The backend confirmed this connection.' : result.error || 'Please check the connection.',
    color: result.success ? 'success' : 'error',
  })

  await loadConnections()
  actionId.value = null
}

async function runPreview(connection: IntegrationConnection) {
  previewActionId.value = connection.id
  previewConnection.value = connection
  selectedConnection.value = connection

  const result = await previewERPNext(connection.id, {
    resource: previewResource.value,
    limit: previewLimit.value,
  })

  if (result.success && result.data) {
    previewResult.value = result.data
    toast.add({
      title: 'Preview loaded',
      description: `${result.data.count} ${result.data.resource} records returned from ERPNext.`,
      color: 'success',
    })
  }
  else {
    previewResult.value = null
    toast.add({
      title: 'Preview failed',
      description: result.error || 'Please check the ERPNext connection.',
      color: 'error',
    })
  }

  previewActionId.value = null
}

async function runCatalogImport(connection: IntegrationConnection) {
  importActionId.value = connection.id
  selectedConnection.value = connection
  importSummary.value = null

  const result = await importERPNextCatalog(connection.id, {
    include_stock: importIncludeStock.value,
  })

  if (result.success) {
    importSummary.value = result.data || {}
    toast.add({
      title: 'Catalog import finished',
      description: importIncludeStock.value ? 'Catalog and stock data were imported from ERPNext.' : 'Catalog data was imported from ERPNext.',
      color: 'success',
    })
    await loadConnections()
    await loadLogs(connection)
  }
  else {
    toast.add({
      title: 'Catalog import failed',
      description: result.error || 'Please check the ERPNext connection.',
      color: 'error',
    })
  }

  importActionId.value = null
}

async function runStockSync(connection: IntegrationConnection) {
  actionId.value = connection.id
  const result = await syncStock(connection.id)

  toast.add({
    title: result.success ? 'Stock sync finished' : 'Stock sync failed',
    description: result.success ? 'Inventory values were refreshed from the connection.' : result.error || 'Please try again.',
    color: result.success ? 'success' : 'error',
  })

  await loadConnections()
  actionId.value = null
}

onMounted(loadConnections)
</script>

<template>
  <div class="px-4 py-8 sm:px-6 lg:px-10">
    <div class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 class="text-3xl font-black tracking-tight text-slate-950">
          Integrations
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-slate-600">
          Monitor connected business systems, test connectivity, and sync stock where supported by the backend.
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <UButton color="primary" size="lg" @click="openCreateConnection">
          <UIcon name="i-lucide-plus" />
          New Connection
        </UButton>
        <UButton variant="outline" size="lg" :loading="isLoading" @click="loadConnections">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <CardsKpiCard2 name="Connections" :value="connections.length" :budget="connections.length" color="#3d7cff" />
      <CardsKpiCard2 name="Active" :value="activeConnections" :budget="connections.length" color="#16a34a" />
      <CardsKpiCard2 name="Needs attention" :value="errorConnections" :budget="connections.length" color="#ef4444" />
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_420px]">
      <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-200 px-5 py-4">
          <h2 class="text-lg font-black text-slate-950">
            Connections
          </h2>
          <p class="mt-1 text-sm text-slate-500">
            {{ healthyConnections }} healthy connections
          </p>
        </div>

        <div v-if="isLoading" class="space-y-3 p-5">
          <USkeleton v-for="item in 4" :key="item" class="h-24 rounded-xl" />
        </div>

        <div v-else-if="!connections.length" class="px-6 py-16 text-center">
          <div class="mx-auto flex size-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
            <UIcon name="i-lucide-unplug" class="size-7" />
          </div>
          <h2 class="mt-5 text-xl font-black text-slate-950">
            No integrations configured
          </h2>
          <p class="mx-auto mt-2 max-w-md text-sm text-slate-600">
            The backend supports integration connections, but none are currently configured.
          </p>
        </div>

        <div v-else class="divide-y divide-slate-200">
          <div
            v-for="connection in connections"
            :key="connection.id"
            class="flex flex-col gap-4 px-5 py-5 lg:flex-row lg:items-center lg:justify-between"
          >
            <button class="min-w-0 text-left" @click="openEditConnection(connection)">
              <div class="flex items-center gap-3">
                <div class="flex size-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                  <UIcon name="i-lucide-plug" class="size-5" />
                </div>
                <div class="min-w-0">
                  <p class="truncate text-base font-black text-slate-950">
                    {{ connection.name }}
                  </p>
                  <p class="truncate text-sm text-slate-500">
                    {{ connection.base_url }}
                  </p>
                </div>
              </div>
            </button>

            <div class="flex flex-wrap items-center gap-2">
              <UBadge :color="statusColor(connection.status)" variant="soft" class="capitalize">
                {{ connection.status }}
              </UBadge>
              <UBadge color="neutral" variant="soft" class="uppercase">
                {{ connection.connection_type }}
              </UBadge>
              <UButton size="sm" variant="ghost" @click="openEditConnection(connection)">
                {{ connection.id > 0 ? 'Edit' : 'Open' }}
              </UButton>
              <UButton
                v-if="connection.id > 0"
                size="sm"
                color="error"
                variant="ghost"
                @click="deleteTarget = connection"
              >
                Delete
              </UButton>
              <UButton
                v-if="connection.supports_test"
                size="sm"
                variant="outline"
                :loading="actionId === connection.id"
                @click="runTest(connection)"
              >
                Test
              </UButton>
              <UButton
                v-if="connection.supports_preview"
                size="sm"
                variant="outline"
                :loading="previewActionId === connection.id"
                @click="runPreview(connection)"
              >
                Preview
              </UButton>
              <UButton
                v-if="connection.supports_import"
                size="sm"
                color="primary"
                variant="outline"
                :loading="importActionId === connection.id"
                @click="runCatalogImport(connection)"
              >
                Import
              </UButton>
              <UButton
                v-if="connection.supports_stock_sync"
                size="sm"
                color="primary"
                variant="soft"
                :loading="actionId === connection.id"
                @click="runStockSync(connection)"
              >
                Sync stock
              </UButton>
            </div>
          </div>
        </div>
      </div>

      <aside class="space-y-6">
        <div class="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-5 py-4">
            <h2 class="text-lg font-black text-slate-950">
              ERPNext tools
            </h2>
            <p class="mt-1 text-sm text-slate-500">
              Preview remote data and choose whether imports also refresh stock.
            </p>
          </div>

          <div class="space-y-4 p-5">
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <UFormField label="Preview resource">
                <USelect v-model="previewResource" :items="previewResourceOptions" class="w-full" />
              </UFormField>
              <UFormField label="Preview limit">
                <USelect v-model="previewLimit" :items="previewLimitOptions" class="w-full" />
              </UFormField>
            </div>

            <UCheckbox v-model="importIncludeStock" label="Include stock during catalog import" />

            <div v-if="previewResult" class="rounded-xl border border-slate-200">
              <div class="border-b border-slate-200 px-4 py-3">
                <p class="font-black text-slate-950">
                  {{ previewConnection?.name || 'ERPNext' }} preview
                </p>
                <p class="mt-1 text-xs uppercase tracking-wide text-slate-500">
                  {{ previewResult.count }} {{ previewResult.resource }} records
                </p>
              </div>

              <div v-if="previewColumns.length" class="max-h-80 overflow-auto">
                <table class="min-w-full divide-y divide-slate-200 text-sm">
                  <thead class="bg-slate-50">
                    <tr>
                      <th v-for="column in previewColumns" :key="column" class="px-3 py-2 text-left text-xs font-black uppercase text-slate-500">
                        {{ column }}
                      </th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100">
                    <tr v-for="(record, index) in previewResult.records" :key="index">
                      <td v-for="column in previewColumns" :key="column" class="max-w-44 truncate px-3 py-2 text-slate-700">
                        {{ formatValue(record[column]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-else class="px-4 py-6 text-center text-sm text-slate-500">
                ERPNext returned no records for this preview.
              </div>
            </div>

            <div v-if="importSummary" class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
              <p class="font-black text-emerald-950">
                Latest import summary
              </p>
              <dl class="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div v-for="(value, key) in importSummary" :key="key">
                  <dt class="text-xs uppercase tracking-wide text-emerald-700">
                    {{ key }}
                  </dt>
                  <dd class="mt-1 font-semibold text-emerald-950">
                    {{ formatValue(value) }}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>

        <div class="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div class="border-b border-slate-200 px-5 py-4">
            <h2 class="text-lg font-black text-slate-950">
              Recent logs
            </h2>
            <p class="mt-1 truncate text-sm text-slate-500">
              {{ selectedConnection?.name || 'Select a connection' }}
            </p>
          </div>

          <div v-if="!selectedConnection" class="px-5 py-12 text-center text-sm text-slate-500">
            Select a connection to view recent logs.
          </div>

          <div v-else-if="!logs.length" class="px-5 py-12 text-center text-sm text-slate-500">
            No logs recorded for this connection yet.
          </div>

          <div v-else class="max-h-[520px] divide-y divide-slate-200 overflow-y-auto">
            <div v-for="log in logs" :key="log.id" class="px-5 py-4">
              <div class="flex items-center justify-between gap-3">
                <p class="font-semibold text-slate-950">
                  {{ log.entity_type }}
                </p>
                <UBadge :color="statusColor(log.status)" variant="soft" class="capitalize">
                  {{ log.status }}
                </UBadge>
              </div>
              <p class="mt-1 text-xs text-slate-500">
                {{ formatDate(log.created_at) }}
              </p>
              <p v-if="log.error_message" class="mt-2 text-sm text-red-600">
                {{ log.error_message }}
              </p>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="editorOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-4">
      <UCard class="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden">
        <template #header>
          <div class="flex items-center justify-between gap-4">
            <div>
              <h3 class="font-semibold text-default">{{ editingConnection ? `${editingConnection.id > 0 ? 'Edit' : 'View'} connection` : 'New connection' }}</h3>
              <p class="text-sm text-dimmed">Inspect credentials, run live tests, and manage external system settings from one place.</p>
            </div>
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" square @click="editorOpen = false" />
          </div>
        </template>

        <div v-if="formError" class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">{{ formError }}</div>

        <div class="max-h-[calc(92vh-11rem)] space-y-6 overflow-y-auto pr-2">
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <UFormField label="Name" required><UInput v-model="connectionForm.name" autocomplete="off" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Connection type" required><USelect v-model="connectionForm.connection_type" :items="connectionTypeOptions" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Partner"><USelect v-model="connectionForm.partner_id" :items="partnerOptions" value-attribute="value" option-attribute="label" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Base URL" required><UInput v-model="connectionForm.base_url" autocomplete="off" placeholder="https://erp.example.com" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Auth type" required><USelect v-model="connectionForm.auth_type" :items="authTypeOptions" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Credential source" required><USelect v-model="connectionForm.credential_source" :items="credentialSourceOptions" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Secret env prefix"><UInput v-model="connectionForm.secret_env_prefix" autocomplete="off" placeholder="ERPNEXT_MAIN" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Status"><USelect v-model="connectionForm.status" :items="connectionStatusOptions" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Default company"><UInput v-model="connectionForm.default_company" autocomplete="off" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Default warehouse"><UInput v-model="connectionForm.default_warehouse" autocomplete="off" :disabled="credentialsReadOnly" /></UFormField>
            <UFormField label="Poll interval (minutes)"><UInput v-model="connectionForm.poll_interval_minutes" type="number" min="1" :disabled="credentialsReadOnly" /></UFormField>
            <div class="flex items-end pb-1">
              <UCheckbox v-model="connectionForm.is_active" label="Connection is active" :disabled="credentialsReadOnly" />
            </div>
          </div>

          <div class="rounded-xl border border-slate-200 p-4">
            <div class="mb-3 flex items-center justify-between gap-3">
              <div>
                <h4 class="font-semibold text-slate-950">Credentials</h4>
                <p class="text-sm text-slate-500">
                  {{ credentialsReadOnly ? 'Read-only values resolved from the current environment.' : 'Stored credential values for this integration connection.' }}
                </p>
              </div>
              <UBadge v-if="editingConnection?.credentials?.source" color="neutral" variant="soft" class="uppercase">
                {{ editingConnection.credentials.source }}
              </UBadge>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <UFormField v-for="field in credentialFieldOptions" :key="field.key" :label="field.label">
                <UInput
                  v-model="connectionForm.credential_values[field.key]"
                  autocomplete="off"
                  :type="field.key.includes('secret') || field.key.includes('password') || field.key.includes('token') || field.key.includes('passkey') ? 'password' : 'text'"
                  :disabled="credentialsReadOnly"
                />
              </UFormField>
            </div>
          </div>

          <div v-if="editingConnection" class="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_320px]">
            <div class="rounded-xl border border-slate-200 p-4">
              <div class="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h4 class="font-semibold text-slate-950">Recent logs</h4>
                  <p class="text-sm text-slate-500">Latest activity for this integration.</p>
                </div>
                <UButton size="sm" variant="outline" :loading="actionId === editingConnection.id" @click="runDetailTest">
                  Test live
                </UButton>
              </div>
              <div v-if="!detailLogs.length" class="text-sm text-slate-500">No logs recorded yet.</div>
              <div v-else class="max-h-64 space-y-3 overflow-y-auto">
                <div v-for="log in detailLogs.slice(0, 8)" :key="log.id" class="rounded-lg border border-slate-200 p-3">
                  <div class="flex items-center justify-between gap-3">
                    <p class="font-semibold text-slate-950">{{ log.entity_type }}</p>
                    <UBadge :color="statusColor(log.status)" variant="soft" class="capitalize">{{ log.status }}</UBadge>
                  </div>
                  <p class="mt-1 text-xs text-slate-500">{{ formatDate(log.created_at) }}</p>
                  <p v-if="log.error_message" class="mt-2 text-sm text-red-600">{{ log.error_message }}</p>
                </div>
              </div>
            </div>

            <div class="rounded-xl border border-slate-200 p-4">
              <h4 class="font-semibold text-slate-950">Latest test</h4>
              <p class="mb-3 text-sm text-slate-500">Run a live validation from this modal.</p>
              <div v-if="detailTestResult" class="space-y-2 text-sm">
                <div v-for="(value, key) in detailTestResult" :key="key">
                  <div class="text-xs uppercase tracking-wide text-slate-500">{{ key }}</div>
                  <div class="font-medium text-slate-900 break-all">{{ formatValue(value) }}</div>
                </div>
              </div>
              <div v-else class="text-sm text-slate-500">No test result yet.</div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" :disabled="actionId !== null" @click="editorOpen = false">Cancel</UButton>
            <UButton v-if="editingConnection" color="neutral" variant="outline" :loading="actionId === editingConnection.id" @click="runDetailTest">Test live</UButton>
            <UButton v-if="!credentialsReadOnly" color="primary" variant="solid" :loading="actionId !== null" @click="submitConnection">Save connection</UButton>
          </div>
        </template>
      </UCard>
    </div>

    <div v-if="deleteTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <UCard class="w-full max-w-md">
        <template #header><h3 class="font-semibold text-default">Delete connection</h3></template>
        <p class="text-sm text-default">Delete <span class="font-semibold">{{ deleteTarget.name }}</span>? This also removes its stored integration logs.</p>
        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" :disabled="actionId !== null" @click="deleteTarget = null">Cancel</UButton>
            <UButton color="error" variant="solid" :loading="actionId === deleteTarget.id" @click="confirmDeleteConnection">Delete connection</UButton>
          </div>
        </template>
      </UCard>
    </div>
  </div>
</template>
