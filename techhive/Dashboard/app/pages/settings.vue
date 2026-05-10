<script setup lang="ts">
import type {
  MpesaLogSnapshot,
  NotificationDeliveryItem,
  PlatformSettingItem,
  RecommendationSettingItem,
  StalePaymentReconciliationResult,
} from '~/composables/useSettings'

const colorMode = useColorMode()
const toast = useToast()
const {
  createPlatformSetting,
  getMpesaLogs,
  getNotificationDeliveries,
  getPlatformSettings,
  getRecommendationSettings,
  reconcileStalePayments,
  retryNotificationDelivery,
  updatePlatformSetting,
  updateRecommendationSettings,
} = useSettings()

const theme = ref(colorMode.preference)
const isLoading = ref(false)
const isSavingSetting = ref(false)
const isSavingRecommendations = ref(false)
const isReconciling = ref(false)
const isRetryingDeliveryId = ref<number | null>(null)

const platformSettings = ref<PlatformSettingItem[]>([])
const selectedSetting = ref<PlatformSettingItem | null>(null)
const recommendationSettings = ref<RecommendationSettingItem[]>([])
const notificationDeliveries = ref<NotificationDeliveryItem[]>([])
const mpesaLogs = ref<MpesaLogSnapshot | null>(null)
const reconciliationResult = ref<StalePaymentReconciliationResult | null>(null)

const ALL_DELIVERY_STATUSES = '__all_statuses__'
const ALL_CHANNELS = '__all_channels__'
const deliveryStatusFilter = ref(ALL_DELIVERY_STATUSES)
const deliveryChannelFilter = ref(ALL_CHANNELS)
const reconcileLimit = ref(20)

const settingForm = reactive({
  key: '',
  value: '',
  description: '',
  is_public: false,
})

const recommendationForm = reactive<Record<string, number>>({
  popularity_blend_weight: 0.35,
  trending_window_days: 14,
  trending_reason_threshold: 3,
  max_brand_recommendations: 2,
  max_vendor_recommendations: 4,
  max_category_recommendations: 3,
})

const deliveryStatusOptions = [
  { label: 'All statuses', value: ALL_DELIVERY_STATUSES },
  { label: 'Prepared', value: 'prepared' },
  { label: 'Pending', value: 'pending' },
  { label: 'Sent', value: 'sent' },
  { label: 'Delivered', value: 'delivered' },
  { label: 'Failed', value: 'failed' },
]

const deliveryChannelOptions = [
  { label: 'All channels', value: ALL_CHANNELS },
  { label: 'In-app', value: 'in_app' },
  { label: 'Email', value: 'email' },
  { label: 'SMS', value: 'sms' },
]

const deliverySummary = computed(() => ({
  total: notificationDeliveries.value.length,
  failed: notificationDeliveries.value.filter(item => item.status === 'failed').length,
  delivered: notificationDeliveries.value.filter(item => item.status === 'delivered').length,
  email: notificationDeliveries.value.filter(item => item.channel === 'email').length,
}))

function changeTheme(value: string) {
  if (!['light', 'dark', 'system'].includes(value))
    return
  theme.value = value
  colorMode.preference = value
}

function applySettingToForm(setting: PlatformSettingItem | null) {
  if (!setting) {
    settingForm.key = ''
    settingForm.value = ''
    settingForm.description = ''
    settingForm.is_public = false
    return
  }

  settingForm.key = setting.key
  settingForm.value = setting.value
  settingForm.description = setting.description || ''
  settingForm.is_public = Boolean(setting.is_public)
}

function selectSetting(setting: PlatformSettingItem) {
  selectedSetting.value = setting
  applySettingToForm(setting)
}

function prepareNewSetting() {
  selectedSetting.value = null
  applySettingToForm(null)
}

function formatLabel(value: string) {
  return value
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatDate(value?: string | null) {
  if (!value)
    return 'Not recorded'

  return new Intl.DateTimeFormat('en-KE', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function statusColor(status: string) {
  if (status === 'delivered' || status === 'sent')
    return 'success'
  if (status === 'failed')
    return 'error'
  if (status === 'pending')
    return 'warning'
  return 'neutral'
}

async function loadPlatformSettings() {
  const result = await getPlatformSettings()
  if (result.success) {
    platformSettings.value = result.data || []
    if (selectedSetting.value) {
      const refreshed = platformSettings.value.find(item => item.key === selectedSetting.value?.key) || null
      selectedSetting.value = refreshed
      applySettingToForm(refreshed)
    }
  }
  else {
    toast.add({
      title: 'Could not load platform settings',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }
}

async function loadRecommendationSettings() {
  const result = await getRecommendationSettings()
  if (result.success) {
    recommendationSettings.value = result.data || []
    for (const item of recommendationSettings.value)
      recommendationForm[item.key] = Number(item.value)
  }
  else {
    toast.add({
      title: 'Could not load recommendation settings',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }
}

async function loadNotificationDeliveries() {
  const result = await getNotificationDeliveries({
    status: deliveryStatusFilter.value !== ALL_DELIVERY_STATUSES ? deliveryStatusFilter.value : undefined,
    channel: deliveryChannelFilter.value !== ALL_CHANNELS ? deliveryChannelFilter.value : undefined,
  })

  if (result.success) {
    notificationDeliveries.value = result.data || []
  }
  else {
    toast.add({
      title: 'Could not load notification deliveries',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }
}

async function loadMpesaLogs() {
  const result = await getMpesaLogs(120)
  if (result.success)
    mpesaLogs.value = result.data || null
  else {
    toast.add({
      title: 'Could not load M-Pesa logs',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }
}

async function loadSettingsPage() {
  isLoading.value = true
  await Promise.all([
    loadPlatformSettings(),
    loadRecommendationSettings(),
    loadNotificationDeliveries(),
    loadMpesaLogs(),
  ])
  isLoading.value = false
}

async function savePlatformSetting() {
  isSavingSetting.value = true

  const payload = {
    value: settingForm.value,
    description: settingForm.description || null,
    is_public: settingForm.is_public,
  }

  const result = selectedSetting.value
    ? await updatePlatformSetting(selectedSetting.value.key, payload)
    : await createPlatformSetting({
        key: settingForm.key,
        value: settingForm.value,
        description: settingForm.description || null,
        is_public: settingForm.is_public,
      })

  if (result.success) {
    toast.add({
      title: selectedSetting.value ? 'Setting updated' : 'Setting created',
      description: `Platform setting ${selectedSetting.value?.key || settingForm.key} was saved successfully.`,
      color: 'success',
    })
    await loadPlatformSettings()
    if (!selectedSetting.value)
      prepareNewSetting()
  }
  else {
    toast.add({
      title: 'Could not save setting',
      description: result.error || 'Please check the form and try again.',
      color: 'error',
    })
  }

  isSavingSetting.value = false
}

async function saveRecommendationSettings() {
  isSavingRecommendations.value = true

  const payload = Object.fromEntries(
    Object.entries(recommendationForm).map(([key, value]) => [key, Number(value)]),
  )

  const result = await updateRecommendationSettings(payload)
  if (result.success) {
    recommendationSettings.value = result.data || []
    for (const item of recommendationSettings.value)
      recommendationForm[item.key] = Number(item.value)

    toast.add({
      title: 'Recommendation settings updated',
      description: 'Recommendation scoring controls were saved successfully.',
      color: 'success',
    })
  }
  else {
    toast.add({
      title: 'Could not save recommendation settings',
      description: result.error || 'Please check the form and try again.',
      color: 'error',
    })
  }

  isSavingRecommendations.value = false
}

async function retryDelivery(deliveryId: number) {
  isRetryingDeliveryId.value = deliveryId
  const result = await retryNotificationDelivery(deliveryId)

  if (result.success) {
    toast.add({
      title: 'Delivery retried',
      description: `Notification delivery #${deliveryId} was queued for retry.`,
      color: 'success',
    })
    await loadNotificationDeliveries()
  }
  else {
    toast.add({
      title: 'Could not retry delivery',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }

  isRetryingDeliveryId.value = null
}

async function runReconciliation() {
  isReconciling.value = true
  const result = await reconcileStalePayments(Number(reconcileLimit.value || 20))

  if (result.success) {
    reconciliationResult.value = result.data || null
    toast.add({
      title: 'Payment reconciliation completed',
      description: `${result.data?.count || 0} stale payments were reviewed.`,
      color: 'success',
    })
  }
  else {
    toast.add({
      title: 'Could not reconcile payments',
      description: result.error || 'Please try again.',
      color: 'error',
    })
  }

  isReconciling.value = false
}

watch([deliveryStatusFilter, deliveryChannelFilter], async () => {
  await loadNotificationDeliveries()
})

onMounted(() => {
  void loadSettingsPage()
})
</script>

<template>
  <div class="px-4 py-8 sm:px-6 lg:px-10">
    <div class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 class="text-3xl font-black tracking-tight text-slate-950">
          Settings & Operations
        </h1>
        <p class="mt-2 max-w-2xl text-sm text-slate-600">
          Manage platform settings, recommendation tuning, notification operations, payment recovery, and M-Pesa observability from the shared TechHive backend.
        </p>
      </div>

      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <UButton variant="outline" size="lg" :loading="isLoading" @click="loadSettingsPage">
          <UIcon name="i-lucide-refresh-cw" />
          Refresh
        </UButton>
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <CardsKpiCard2
        name="Platform settings"
        :value="platformSettings.length"
        :budget="platformSettings.length"
        color="var(--color-info)"
        icon="i-lucide-sliders-horizontal"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Recommendation controls"
        :value="recommendationSettings.length"
        :budget="recommendationSettings.length"
        color="var(--color-primary)"
        icon="i-lucide-sparkles"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="Failed deliveries"
        :value="deliverySummary.failed"
        :budget="deliverySummary.total"
        color="var(--color-error)"
        icon="i-lucide-mail-warning"
        :loading="isLoading"
      />
      <CardsKpiCard2
        name="M-Pesa log lines"
        :value="mpesaLogs?.line_count || 0"
        :budget="mpesaLogs?.line_count || 0"
        color="var(--color-warning)"
        icon="i-lucide-scroll-text"
        :loading="isLoading"
      />
    </div>

    <div class="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-5">
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
        <div class="mb-5 flex items-center justify-between gap-4">
          <div>
            <h2 class="text-xl font-black text-slate-950">Platform settings</h2>
            <p class="mt-1 text-sm text-slate-600">Edit the shared runtime settings stored in the backend database.</p>
          </div>
          <UButton color="neutral" variant="outline" @click="prepareNewSetting">
            New setting
          </UButton>
        </div>

        <div class="space-y-3">
          <button
            v-for="setting in platformSettings"
            :key="setting.key"
            type="button"
            class="w-full rounded-xl border p-4 text-left transition hover:border-blue-300 hover:bg-blue-50/40"
            :class="selectedSetting?.key === setting.key ? 'border-blue-500 ring-2 ring-blue-100' : 'border-slate-200'"
            @click="selectSetting(setting)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate font-semibold text-slate-950">{{ setting.key }}</p>
                <p class="mt-1 line-clamp-2 text-sm text-slate-600">{{ setting.description || 'No description provided.' }}</p>
              </div>
              <UBadge :color="setting.is_public ? 'success' : 'neutral'" variant="soft">
                {{ setting.is_public ? "Public" : "Private" }}
              </UBadge>
            </div>
            <p class="mt-2 truncate text-xs text-slate-500">{{ setting.value }}</p>
          </button>

          <div v-if="!platformSettings.length" class="rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
            No platform settings found yet.
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-3">
        <div class="mb-5">
          <h2 class="text-xl font-black text-slate-950">{{ selectedSetting ? 'Edit setting' : 'Create setting' }}</h2>
          <p class="mt-1 text-sm text-slate-600">Create a new runtime setting or update the selected one.</p>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <UFormField label="Key" required>
            <UInput v-model="settingForm.key" :readonly="Boolean(selectedSetting)" placeholder="recommendation.popularity_blend_weight" />
          </UFormField>
          <UFormField label="Public visibility">
            <div class="flex h-full items-center">
              <UCheckbox v-model="settingForm.is_public" label="Expose this setting publicly" />
            </div>
          </UFormField>
          <UFormField label="Value" required class="md:col-span-2">
            <UTextarea v-model="settingForm.value" :rows="4" placeholder="Setting value" />
          </UFormField>
          <UFormField label="Description" class="md:col-span-2">
            <UTextarea v-model="settingForm.description" :rows="3" placeholder="Explain what this setting controls" />
          </UFormField>
        </div>

        <div class="mt-5 flex justify-end gap-3">
          <UButton color="neutral" variant="outline" @click="prepareNewSetting">
            Clear
          </UButton>
          <UButton color="primary" :loading="isSavingSetting" @click="savePlatformSetting">
            Save setting
          </UButton>
        </div>
      </div>
    </div>

    <div class="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 class="text-xl font-black text-slate-950">Recommendation controls</h2>
          <p class="mt-1 text-sm text-slate-600">Tune how the recommendation engine balances popularity, trend windows, and diversity caps.</p>
        </div>
        <UButton color="primary" :loading="isSavingRecommendations" @click="saveRecommendationSettings">
          Save recommendation settings
        </UButton>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <UFormField
          v-for="setting in recommendationSettings"
          :key="setting.key"
          :label="formatLabel(setting.key)"
          :help="`Default ${setting.default} · Min ${setting.min} · Max ${setting.max}`"
        >
          <UInput
            v-model.number="recommendationForm[setting.key]"
            type="number"
            :min="setting.min"
            :max="setting.max"
            :step="String(setting.key).includes('weight') || String(setting.key).includes('threshold') ? 0.1 : 1"
          />
        </UFormField>
      </div>
    </div>

    <div class="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-5">
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-3">
        <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 class="text-xl font-black text-slate-950">Notification deliveries</h2>
            <p class="mt-1 text-sm text-slate-600">Inspect delivery failures and retry failed notification sends from the backend queue.</p>
          </div>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <USelect
              v-model="deliveryChannelFilter"
              :items="deliveryChannelOptions"
              value-attribute="value"
              option-attribute="label"
              class="w-full sm:w-36"
            />
            <USelect
              v-model="deliveryStatusFilter"
              :items="deliveryStatusOptions"
              value-attribute="value"
              option-attribute="label"
              class="w-full sm:w-36"
            />
          </div>
        </div>

        <div class="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <CardsKpiCard2
            name="Total"
            :value="deliverySummary.total"
            :budget="deliverySummary.total"
            color="var(--color-info)"
            icon="i-lucide-bell-ring"
            :loading="isLoading"
          />
          <CardsKpiCard2
            name="Failed"
            :value="deliverySummary.failed"
            :budget="deliverySummary.total"
            color="var(--color-error)"
            icon="i-lucide-x-circle"
            :loading="isLoading"
          />
          <CardsKpiCard2
            name="Delivered"
            :value="deliverySummary.delivered"
            :budget="deliverySummary.total"
            color="var(--color-success)"
            icon="i-lucide-check-circle"
            :loading="isLoading"
          />
          <CardsKpiCard2
            name="Email"
            :value="deliverySummary.email"
            :budget="deliverySummary.total"
            color="var(--color-warning)"
            icon="i-lucide-mail"
            :loading="isLoading"
          />
        </div>

        <div class="space-y-3">
          <div
            v-for="delivery in notificationDeliveries.slice(0, 20)"
            :key="delivery.id"
            class="rounded-xl border border-slate-200 p-4"
          >
            <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <p class="font-semibold text-slate-950">#{{ delivery.id }} · {{ delivery.recipient }}</p>
                  <UBadge :label="delivery.channel" color="neutral" variant="soft" />
                  <UBadge :label="delivery.status" :color="statusColor(delivery.status)" variant="soft" />
                </div>
                <p class="mt-1 text-sm text-slate-600">{{ delivery.subject || delivery.template || 'No subject recorded' }}</p>
                <p class="mt-2 text-xs text-slate-500">
                  {{ delivery.reason || 'No failure reason recorded' }} · Retries {{ delivery.retry_count }} · Last attempt {{ formatDate(delivery.last_attempted_at) }}
                </p>
              </div>
              <UButton
                v-if="delivery.status === 'failed'"
                color="primary"
                variant="outline"
                :loading="isRetryingDeliveryId === delivery.id"
                @click="retryDelivery(delivery.id)"
              >
                Retry
              </UButton>
            </div>
          </div>

          <div v-if="!notificationDeliveries.length" class="rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
            No notification deliveries matched the current filters.
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
        <div class="mb-5">
          <h2 class="text-xl font-black text-slate-950">Payment recovery</h2>
          <p class="mt-1 text-sm text-slate-600">Run stale M-Pesa reconciliation and inspect how many pending payments were classified.</p>
        </div>

        <div class="space-y-4">
          <UFormField label="Batch limit">
            <UInput v-model.number="reconcileLimit" type="number" min="1" max="500" />
          </UFormField>

          <UButton color="primary" class="w-full justify-center" :loading="isReconciling" @click="runReconciliation">
            Reconcile stale payments
          </UButton>

          <div v-if="reconciliationResult" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-xs uppercase text-slate-500">Reviewed</p>
                <p class="font-semibold text-slate-950">{{ reconciliationResult.count }}</p>
              </div>
              <div>
                <p class="text-xs uppercase text-slate-500">Awaiting confirmation</p>
                <p class="font-semibold text-slate-950">{{ reconciliationResult.awaiting_confirmation_count }}</p>
              </div>
              <div>
                <p class="text-xs uppercase text-slate-500">Provider failed</p>
                <p class="font-semibold text-slate-950">{{ reconciliationResult.provider_failed_count }}</p>
              </div>
              <div>
                <p class="text-xs uppercase text-slate-500">Manual review</p>
                <p class="font-semibold text-slate-950">{{ reconciliationResult.manual_review_count }}</p>
              </div>
              <div>
                <p class="text-xs uppercase text-slate-500">Timed out</p>
                <p class="font-semibold text-slate-950">{{ reconciliationResult.timed_out_count }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 class="text-xl font-black text-slate-950">M-Pesa logs</h2>
          <p class="mt-1 text-sm text-slate-600">Read the latest M-Pesa integration logs directly from the backend runtime.</p>
        </div>
        <div class="flex items-center gap-2">
          <UButton color="neutral" variant="outline" @click="changeTheme('light')">Light</UButton>
          <UButton color="neutral" variant="outline" @click="changeTheme('dark')">Dark</UButton>
          <UButton color="neutral" variant="outline" @click="changeTheme('system')">System</UButton>
          <UButton color="primary" variant="outline" @click="loadMpesaLogs">
            Refresh logs
          </UButton>
        </div>
      </div>

      <div class="rounded-xl border border-slate-200 bg-slate-950 p-4">
        <p class="mb-3 text-xs text-slate-400">{{ mpesaLogs?.path || 'No log path available' }}</p>
        <pre class="max-h-[28rem] overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-100">{{ (mpesaLogs?.lines || []).join('\n') || 'No M-Pesa log lines available.' }}</pre>
      </div>
    </div>
  </div>
</template>
