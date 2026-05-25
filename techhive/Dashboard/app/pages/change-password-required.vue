<script setup lang="ts">
definePageMeta({
  layout: false,
})

const auth = useAuth()
const toast = useToast()
const { request } = useBackendApi()

const form = reactive({
  current_password: '',
  new_password: '',
  confirm_password: '',
})
const isSubmitting = ref(false)
const error = ref('')

const canSubmit = computed(() =>
  form.current_password.length > 0
  && form.new_password.length >= 8
  && form.confirm_password.length > 0
  && !isSubmitting.value,
)

async function submit() {
  error.value = ''
  if (!canSubmit.value)
    return

  if (form.new_password !== form.confirm_password) {
    error.value = 'New password and confirmation must match.'
    return
  }

  isSubmitting.value = true
  try {
    await request('/auth/change-password', {
      method: 'POST',
      body: {
        current_password: form.current_password,
        new_password: form.new_password,
      },
    })
    await auth.refreshSession()
    toast.add({
      title: 'Password updated',
      description: 'You can now continue into the dashboard.',
      color: 'success',
    })
    await navigateTo(auth.homeRoute.value)
  }
  catch (err: any) {
    error.value = err?.data?.error?.message || err?.data?.detail || err?.message || 'Could not change password.'
  }
  finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-[#f4f7fb] px-4 py-10">
    <section class="w-full max-w-2xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-xl sm:p-10">
      <p class="text-sm font-semibold uppercase tracking-wide text-[#3d7cff]">
        Security step
      </p>
      <h1 class="mt-3 text-3xl font-black tracking-tight text-slate-950">
        Change your password
      </h1>
      <p class="mt-3 text-sm leading-6 text-slate-500">
        Your account was created with a temporary password. Change it now before using the dashboard.
      </p>

      <div class="mt-8 space-y-5">
        <UFormField label="Temporary password">
          <UInput
            v-model="form.current_password"
            size="xl"
            icon="i-lucide-lock"
            type="password"
            autocomplete="current-password"
            placeholder="Enter temporary password"
          />
        </UFormField>

        <UFormField label="New password">
          <UInput
            v-model="form.new_password"
            size="xl"
            icon="i-lucide-key-round"
            type="password"
            autocomplete="new-password"
            placeholder="Create a new password"
          />
        </UFormField>

        <UFormField label="Confirm new password">
          <UInput
            v-model="form.confirm_password"
            size="xl"
            icon="i-lucide-key-round"
            type="password"
            autocomplete="new-password"
            placeholder="Repeat the new password"
          />
        </UFormField>

        <UAlert
          v-if="error"
          color="error"
          variant="soft"
          icon="i-lucide-triangle-alert"
          :description="error"
        />

        <UButton
          size="xl"
          block
          color="primary"
          icon="i-lucide-shield-check"
          :loading="isSubmitting"
          :disabled="!canSubmit"
          @click="submit"
        >
          Update password
        </UButton>
      </div>
    </section>
  </main>
</template>
