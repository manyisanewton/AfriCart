# TechHive Dashboard

This app is the internal TechHive dashboard for admin, vendor, support, and later operations workflows.

It is intentionally separate from the storefront in `techhive/frontend`, but it uses the same backend and database in `techhive/backend`.

## Current Direction

- `techhive/frontend`: customer storefront
- `techhive/Dashboard`: internal back-office dashboard
- `techhive/backend`: shared API and shared database for both apps

The dashboard should adapt to the existing TechHive backend API. We are not reshaping the backend to fit this template's original assumptions.

## Phase 1 Goal

Phase one keeps the dashboard as a standalone Nuxt app and prepares it for:

- shared backend API integration
- role-aware access for admin, vendor, and support
- deployment under its own host or under a `/dashboard` base path

## Runtime Configuration

Copy `.env.example` to `.env` and adjust values as needed.

Important variables:

- `NUXT_PUBLIC_API_BASE`
  - TechHive backend API base URL
  - default local value: `http://localhost:5000/api/v1`
- `NUXT_APP_BASE_URL`
  - base path for the dashboard app
  - use `/` for a standalone host
  - use `/dashboard` when mounted under the main domain
- `NUXT_PUBLIC_DASHBOARD_NAME`
- `NUXT_PUBLIC_DASHBOARD_SUBTITLE`

## Development

```bash
npm install
npm run dev
```

By default Nuxt runs on `http://localhost:3000`.

## Build

```bash
npm run build
npm run preview
```

## Smoke Tests

```bash
npm run test:smoke
```

## Next Integration Steps

The next implementation phases will focus on:

1. replacing the current session/CSRF auth assumptions with TechHive auth
2. introducing role-aware navigation and route guards
3. remapping dashboard composables to existing TechHive backend endpoints
4. wiring admin and vendor dashboard screens first
