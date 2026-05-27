<script setup lang="ts">
import { getDashboardSubtitleForRole, getNavSectionsForRole, getSupportNavForRole } from '~/config/navigation'

const route = useRoute()
const auth = useAuth()
const runtimeConfig = useRuntimeConfig()
const dashboardName = computed(() => String(runtimeConfig.public.dashboardName || 'TechHive Dashboard'))
const dashboardSubtitle = computed(() => getDashboardSubtitleForRole(auth.user.value?.role))
const navSections = computed(() => getNavSectionsForRole(auth.user.value?.role))
const supportNav = computed(() => getSupportNavForRole(auth.user.value?.role))

const isLinkActive = (item: { to?: string }) => {
  if (!item.to)
    return false
  if (item.to === '/')
    return route.path === '/'
  return route.path.startsWith(item.to)
}
</script>

<template>
  <div
    class="fixed bottom-0 left-0 top-0 hidden min-h-screen w-64 flex-col border-r border-slate-200 bg-white p-4 lg:flex"
  >
    <NuxtLink to="/" class="mb-8 flex items-start overflow-hidden">
      <img src="/logo.png" alt="TechHive" class="h-12 w-auto max-w-full object-contain" />
    </NuxtLink>

    <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
      <nav class="min-h-0 flex-1 space-y-6 overflow-y-auto pr-1">
        <section v-for="section in navSections" :key="section.label" class="space-y-2">
          <div class="text-xs font-bold uppercase tracking-wide text-slate-400">
            {{ section.label }}
          </div>
          <div class="w-full space-y-1">
            <NuxtLink v-for="item in section.items" :key="item.label" :to="item.to" block>
              <UButton
                color="neutral"
                variant="ghost"
                :active="isLinkActive(item)"
                active-variant="soft"
                class="w-full justify-start"
                :icon="item.icon"
              >
                {{ item.label }}
              </UButton>
            </NuxtLink>
          </div>
        </section>
      </nav>

      <div class="mt-4 border-t border-slate-100 pt-4">
        <div class="mb-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs font-bold uppercase tracking-wide text-slate-400">
            Access
          </p>
          <p class="mt-2 text-sm font-semibold text-slate-900">
            {{ auth.user.value?.role || 'guest' }}
          </p>
          <p class="mt-1 text-xs text-slate-500">
            Admin is the active dashboard role in the current integration phase.
          </p>
        </div>

        <template v-if="supportNav.length">
          <h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
            Help
          </h3>
          <template v-for="item in supportNav" :key="item.label">
            <NuxtLink v-if="item.to" :to="item.to">
              <UButton
                color="neutral"
                variant="ghost"
                class="w-full justify-start"
                :icon="item.icon"
              >
                {{ item.label }}
                <span
                  v-if="item.highlight"
                  class="ml-auto h-1.5 w-1.5 rounded-full bg-[#3d7cff]"
                />
              </UButton>
            </NuxtLink>
          </template>
        </template>
      </div>
    </div>
  </div>
</template>
