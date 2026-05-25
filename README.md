# AfriCart

AfriCart is a multi-app commerce workspace centered around **TechHive**, a marketplace platform with:

- a Flask backend API
- a customer storefront
- an internal dashboard for admin and back-office operations

The project has moved beyond a simple storefront prototype. It now includes live catalog management, order operations, promotions tooling, M-Pesa sandbox work, media handling, reporting, and a growing internal dashboard wired to the same backend and database.

## Repository Layout

The main application code lives under [techhive](/home/leopardfx/AfriCart/techhive:1).

- [techhive/backend](/home/leopardfx/AfriCart/techhive/backend:1)
  Flask API, business logic, admin endpoints, tests, media storage, and local SQLite development data.
- [techhive/frontend](/home/leopardfx/AfriCart/techhive/frontend:1)
  Customer-facing storefront built with React and Vite.
- [techhive/Dashboard](/home/leopardfx/AfriCart/techhive/Dashboard:1)
  Internal dashboard built with Nuxt for admin and future role-based back-office access.
- [techhive/docs](/home/leopardfx/AfriCart/techhive/docs:1)
  Supporting project documentation.

## Current Architecture

The platform currently follows this split:

- `frontend/` handles the customer shopping experience
- `Dashboard/` handles internal operations and administration
- `backend/` is the shared API and shared data source for both

The guiding integration rule has been:

- the dashboard adapts to the backend
- the backend is extended where real missing capability exists
- the storefront reflects changes made through the dashboard when supported by existing APIs

## What Is Working

### Backend

The backend now covers a broad set of marketplace operations, including:

- authentication and JWT session flows
- customers, vendors, admins, and delivery-agent roles
- products, brands, categories, images, and media
- carts, orders, payments, refunds, and delivery operations
- support tickets and notifications
- review moderation
- reporting and admin operations queues
- M-Pesa sandbox initiation, callbacks, reconciliation, and logging
- promotions foundations for offers, vouchers, ranges, and campaign summaries

### Dashboard

The dashboard has been substantially rewired away from its original template assumptions and now talks to the real backend for major admin workflows.

Admin areas that are already integrated include:

- overview
- users
- orders
- vendors
- support
- reports
- settings and operations
- products
- categories
- product types
- attributes
- options
- stock alerts
- reviews
- media
- offers
- vouchers
- ranges
- campaigns

Some slices are deeper than others, but the admin console is no longer just placeholder UI. Much of it is already backed by live API flows.

### Storefront

The storefront now reads real backend product data and can reflect:

- dashboard-created products
- backend-hosted product images
- category-driven listing behavior
- product detail data from the API

## Local Development

### 1. Backend

```bash
cd /home/leopardfx/AfriCart/techhive/backend
source .venv/bin/activate
python run.py
```

Default local API:

```text
http://127.0.0.1:5000/api/v1
```

### 2. Storefront

```bash
cd /home/leopardfx/AfriCart/techhive/frontend
npm run dev
```

Typical local URL:

```text
http://localhost:5173
```

### 3. Dashboard

```bash
cd /home/leopardfx/AfriCart/techhive/Dashboard
npm run dev
```

Typical local URL:

```text
http://localhost:3000
```

## Environment Notes

Local development has mainly been running with:

- Flask backend on `localhost:5000`
- Nuxt dashboard on `localhost:3000`
- Vite storefront on `localhost:5173`

The backend `.env` already supports important local integrations such as:

- SMTP aliases via `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`
- M-Pesa sandbox credentials and callback URLs
- local CORS allowances for dashboard and storefront development origins

## Important Development Notes

- The local backend currently uses SQLite for development.
- Some newer schema work has required direct local DB patching because the local Alembic history is drifted.
- Migration files are still being added to keep the repository state moving forward, but local dev databases may need normalization later before a clean deployment pipeline.
- The dashboard is currently admin-first, with vendor and other role slices planned to follow after admin is fully hardened.

## Recent Progress Highlights

Some of the most important recent milestones:

- admin dashboard auth switched to the real backend JWT flow
- live admin management for products, users, orders, vendors, support, and reports
- media and product image handling wired through the backend
- promotions tooling added for offers, vouchers, ranges, and campaigns
- review moderation introduced end to end
- product low-stock thresholds and stock alert workflows added
- temporary-password user creation flow added:
  - admin creates the user
  - backend generates a strong password
  - SMTP email sends the credentials
  - first login forces a password change
- storefront product visibility aligned with dashboard-managed catalog data

## Testing

Backend tests are located in [techhive/backend/tests](/home/leopardfx/AfriCart/techhive/backend/tests:1).

A common local test command is:

```bash
cd /home/leopardfx/AfriCart/techhive/backend
source .venv/bin/activate
pytest tests/test_admin.py -q
```

The dashboard also has a smoke test script used during integration work:

```bash
cd /home/leopardfx/AfriCart/techhive/Dashboard
node scripts/smoke-tests.mjs
```

## Next Direction

The project is now at the stage where the main priorities are less about scaffolding and more about:

- finishing the remaining admin operations slices
- improving vendor-role dashboard support
- normalizing migrations and local database setup
- hardening real-world delivery of email, payments, and operational workflows
- continuing storefront integration with backend-managed data

## License

This repository includes a [LICENSE](/home/leopardfx/AfriCart/LICENSE:1) file at the root.
