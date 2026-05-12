// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: false },

  app: {
    baseURL: process.env.NUXT_APP_BASE_URL || '/',
    head: {
      title: 'TechHive Dashboard',
      titleTemplate: '%s · TechHive Dashboard',
      meta: [
        { name: 'description', content: 'Internal TechHive dashboard for admin, vendor, support, and operations workflows.' },
      ],
    },
  },

  modules: ['@nuxt/ui', '@nuxt/eslint', 'nuxt-charts', '@nuxthub/core'],

  css: ['~/assets/css/main.css'],

  future: {
    compatibilityVersion: 4
  },

  compatibilityDate: '2024-11-27',

  colorMode: {
    storage: 'localStorage',
    preference: 'light',
  },

  hub: {
    // Enable NuxtHub features as needed
    // database: true,  // Enable D1 database
    // kv: true,        // Enable KV storage
    // blob: true,      // Enable R2 blob storage
    // cache: true,     // Enable cache
  },

  nitro: {
    preset: 'cloudflare-pages',
  },

  vite: {
    optimizeDeps: {
      include: ['striptags'],
    },
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:5000/api/v1',
      dashboardName: process.env.NUXT_PUBLIC_DASHBOARD_NAME || 'TechHive Dashboard',
      dashboardSubtitle: process.env.NUXT_PUBLIC_DASHBOARD_SUBTITLE || 'Admin and Vendor Console',
    },
  },
})
