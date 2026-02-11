# PROJECT_STATUS.md - Shared Between Claude Code & Minimax

**IMPORTANT:** Both AI assistants must read this file before starting work.

**Last Updated:** 2026-02-10 19:58 EST by Claude Code (Portal route fix + customer login UUID fix)

---

## 🔒 SECURITY AUDIT COMPLETED (2026-02-10)

### Vulnerabilities Fixed

**Critical:**
1. ✅ **JWT_SECRET_KEY & SECRET_KEY validation at startup** - App now fails immediately if secrets aren't set properly (prevents runtime errors)
2. ✅ **Notes storage - Removed insecure in-memory dict** - Now uses proper PostgreSQL database with RLS policies (was using `_notes_storage: dict = {}`)

**High:**
3. ✅ **Removed passlib from requirements.txt** - Was causing Python 3.14 compatibility issues, now using bcrypt directly

**Medium:**
4. ✅ **CSP documentation** - Dev mode uses 'unsafe-inline'/'unsafe-eval' (documented in code, strict in production)

---

## Current State

### ✅ COMPLETE - EMPLOYEE PORTAL (2026-02-08)
**Backend:**
- ✅ Permission System with role-based defaults
- ✅ Database tables (user_permissions, scim_group_mappings)
- ✅ RLS Policies for own/assigned access
- ✅ Audit Logging with correlation IDs
- ✅ Portal API Endpoints (Appointments, Tasks, Notes, Customers)
- ✅ Employee Login endpoint (`/api/v1/portal/auth/employee-login`)

**Frontend Pages (`/portal/employee/`):** *(moved to `(portal)` route group — no admin layout)*
- ✅ **Layout** - Sidebar navigation, header, role indicator
- ✅ **Dashboard** - Stats, quick links
- ✅ **Calendar** - Full calendar with privacy rules (Busy blocks)
- ✅ **Appointments** - Full CRUD for own appointments
- ✅ **Tasks** - View tasks, update status, overdue tracking
- ✅ **Notes** - Create, edit, delete own notes
- ✅ **Customers** - Read-only customer list

### ✅ COMPLETE - CUSTOMER PORTAL (2026-02-08)
**Frontend Pages (`/portal/customer/`):** *(moved to `(portal)` route group — no admin layout)*
- ✅ **Layout** - Simplified sidebar, role validation (redirects employees)
- ✅ **Dashboard** - Stats, upcoming appointments/tasks
- ✅ **Appointments** - View own appointments (grouped by date)
- ✅ **Tasks** - View assigned tasks with overdue tracking
- ✅ **Notes** - View own notes with search

### ✅ COMPLETE - AI AGENT & WORKFLOW AUTOMATION (2026-02-08)
**Database Tables:**
- ✅ `workflow_templates` - Workflow definitions with triggers and actions
- ✅ `workflow_executions` - Execution history and logs
- ✅ `agent_tasks` - AI processing tasks (summarize, follow-up, reminders, etc.)
- ✅ `automation_rules` - Event-based automation triggers

**Pre-built Workflow Templates:**
1. ✅ **Appointment Reminders** - Auto-send 24h and 1h before appointments
2. ✅ **Appointment Follow-up** - Generate follow-up message after completed appointments
3. ✅ **Daily Task Summary** - Morning digest of tasks at 8am

**Automation API Endpoints (`/api/v1/automation/`):**
- ✅ `POST /workflows` - Create workflow
- ✅ `GET /workflows` - List workflows
- ✅ `POST /workflows/{id}/activate` - Activate
- ✅ `POST /workflows/{id}/deactivate` - Deactivate
- ✅ `POST /agent-tasks` - Create AI task
- ✅ `GET /agent-tasks` - List tasks
- ✅ `POST /ai/summarize` - AI text summarization
- ✅ `POST /ai/follow-up` - Generate follow-up message
- ✅ `POST /ai/task-summary` - Generate task summary
- ✅ `POST /remind` - Schedule reminders

### 🔒 SECURITY HARDENING COMPLETED (2026-02-08)
1. **JWT Token Security** - Reduced expiration from 24h → 15 minutes (OWASP ASVS)
2. **Cookie Security** - SameSite changed to "strict"
3. **Hardcoded Secrets Removed** - JWT_SECRET_KEY and SECRET_KEY now require environment variables
4. **Rate Limiting** - Login (10/min), Registration (5/min) to prevent brute force
5. **Error Handling** - Generic error messages in production (no stack traces exposed)
6. **Row-Level Security (RLS)** - Database-level tenant isolation applied ✅
   - Tables: users, tasks, notes, events, audit_logs
   - Migration: `migrations/rls_setup.sql` applied to database

### TIMEZONE SUPPORT ADDED (2026-02-08)
- User `timezone` field added to database (default: UTC)
- Frontend auto-detects browser timezone
- 30+ common timezones in dropdown selector
- `date-fns-tz` installed for timezone handling
- Key files: `app/models/user.py`, `app/api/v1/auth.py`, `migrations/add_timezone.sql`, `src/lib/timezone.ts`, `src/lib/queries/user-settings.ts`

### FIXED THIS SESSION (by Claude Code)
1. **Security vulnerabilities patched** - All 6 fixes applied and tested
1. **MiniMax API key** - Old key was invalidated. Updated in:
   - `office-manager-api/.env` (ANTHROPIC_API_KEY)
   - `clawdbot/.env` (added MINIMAX_API_KEY - was missing)
   - `~/.openclaw/agents/main/agent/auth-profiles.json` (minimax:default key + minimax-portal:default access token)
   - Cleared cooldown state (both providers had errorCount:3, cooldownUntil set)
2. **Dashboard fully interactive** - Rebuilt `/dashboard` page:
   - All stat cards (Office Overview + Task Statistics) now clickable, link to proper sections
   - Added Quick Links row (Calendar, Notes, Appointments, Settings)
   - "Today's Schedule" card shows real calendar events from `/calendar/today` API
   - "Recent Tasks" card shows real tasks from `/tasks` API
   - Upcoming Appointments card shows when appointments exist
   - Hover effects with arrow indicators on all cards
3. **Calendar types fixed** - Installed `@types/react-big-calendar`, fixed DnD generic types
4. **`/calendar/today` response parsing** - API returns `{ events_by_hour: { "16": [...] } }` not a flat array. Dashboard now properly flattens and sorts the nested structure.

### FIXED THIS SESSION (by Minimax)
1. **Employee creation 422 error** - Fixed params filtering to only send non-empty values
2. **Notes page API integration** - Added full CRUD API endpoints and frontend hooks
   - Added `/office/notes` endpoints (GET, POST, PUT, DELETE)
   - Added useNotes, useCreateNote, useUpdateNote, useDeleteNote hooks
   - Updated Notes page to use real API instead of mock data

### FIXED THIS SESSION (2026-02-06)
1. **Employee creation (hire_date)** - Backend expected `datetime` but received string from form. Changed to accept string and parse manually with `datetime.fromisoformat()`.
2. **Appointment creation** - Backend required `customer_id` and `assigned_to_id` but frontend didn't send them. Changed all Form params to optional with defaults.
3. **Appointment creation (frontend)** - Hook was sending query params but backend expects Form data. Updated `useCreateAppointment` to send `application/x-www-form-urlencoded` data.
4. **passlib/bcrypt incompatibility** - passlib 1.7.4 doesn't work with bcrypt 5.0. Updated portal auth to use bcrypt directly.
5. **Database missing column** - Added `appointment_id` column to `events` table for Calendar→Appointment sync.
6. **Datetime timezone issue** - Frontend sends datetime with timezone but database expects naive. Updated appointment creation to strip timezone info.

### ✅ COMPLETE - Customer Portal (2026-02-08)
All pages built and ready for testing:
- `/portal/customer` - Dashboard
- `/portal/customer/appointments` - View own appointments
- `/portal/customer/tasks` - View assigned tasks
- `/portal/customer/notes` - View own notes

### FIXED THIS SESSION (by Claude Code - 2026-02-08 evening)
1. **Employee creation VERIFIED WORKING** - Tested end-to-end, creates User + Employee in one call
2. **Employee creation error handling** - Added IntegrityError catch with proper rollback:
   - Duplicate employee_id → clean 409 error ("Employee ID 'X' already exists")
   - Duplicate email → clean 400 error ("User with this email already exists")
   - Transaction rollback prevents orphaned user accounts on failure
   - File modified: `app/api/v1/endpoints/office/__init__.py` (added `IntegrityError` import + try/except block)
3. **All services started and verified:**
   - Backend API: localhost:8000 ✅
   - Frontend: localhost:3000 ✅
   - OpenClaw Gateway: ws://127.0.0.1:18789 ✅
   - Telegram bot: @TheEntrepreneurBot ✅
   - Model: MiniMax M2.1 ✅

### BUGS FIXED BY CLAUDE CODE (2026-02-10)
Minimax wrote portal + automation code with 8 bugs. All fixed:
1. **`JSONB` not imported** in `app/models/automation/__init__.py` — added to postgresql imports
2. **Syntax error** in `app/api/v1/endpoints/portal/auth.py` lines 7-9 — corrupted import statement fixed
3. **passlib import** in portal auth — replaced with `bcrypt` directly (same fix as main auth)
4. **Missing `__init__.py`** in `app/api/v1/endpoints/portal/` — package wasn't loadable
5. **Wrong model imports** — `Task` imported from `office_models` instead of `app.models.task`
6. **Double route prefix** — main.py added `/api/v1/portal` on top of router's own `/portal` prefix
7. **Dependency injection bug** — `db: AsyncSession = Depends(get_current_portal_user)` in ALL 12 endpoints (should be `get_db`)
8. **Wrong field/enum references** — `Appointment.notes` (doesn't exist), `TaskStatus.DONE` (should be COMPLETED), `AppointmentStatus.CONFIRMED` (should be IN_PROGRESS), `settings.ALGORITHM` (should be `JWT_ALGORITHM`), `settings.SECRET_KEY` (should be `JWT_SECRET_KEY`)

### VERIFIED WORKING (2026-02-10)
All endpoints tested and returning correct data:
- ✅ `POST /api/v1/portal/auth/employee-login` — 200, returns JWT
- ✅ `GET /api/v1/portal/appointments` — 200, returns 8 appointments
- ✅ `GET /api/v1/portal/tasks` — 200
- ✅ `GET /api/v1/portal/notes` — 200
- ✅ `GET /api/v1/portal/customers` — 200
- ✅ `GET /api/v1/portal/dashboard/stats` — 200
- ✅ `GET /api/v1/automation/workflows` — 200, 3 pre-built templates
- ✅ `GET /api/v1/automation/agent-tasks` — 200
- ✅ `POST /api/v1/automation/ai/summarize` — 200 (placeholder response)

### FIXED (2026-02-10 evening by Claude Code)
- ✅ **Portal pages wrapped in admin layout** - Portal pages (login, employee, customer) were nested inside `(dashboard)` route group, causing AuthGuard redirect and admin Sidebar to appear. Moved all portal pages to new `(portal)` route group with minimal passthrough layout. `/portal/login` now renders independently.
- ✅ **Customer login UUID serialization** - `create_access_token`/`create_refresh_token` in `app/api/v1/portal/auth.py` received `customer_id` as UUID object, causing `TypeError: Object of type UUID is not JSON serializable`. Fixed by wrapping with `str()`.
- ✅ **CustomerUserResponse schema mismatch** - Pydantic schema declared `id` and `customer_id` as `str` but SQLAlchemy model returns `UUID`. Changed schema fields to `UUID` type.
- ✅ **Docker image rebuilt** with all fixes baked in.
- ✅ **JWT_SECRET_KEY in .env** - Was set to placeholder value, causing startup failure on rebuilt container. Set to proper generated secret.

### FIXED (2026-02-10 by Claude Code)
- ✅ **Appointments frontend display** - Was filtering out past appointments in current month (`aptDate >= now`). Removed that filter, now shows all appointments for selected month. Also removed debug console.logs.
- ✅ **RLS on customers table** - Added `customers_tenant_isolation` policy: `tenant_id = current_setting('app.current_tenant_id')::uuid`. All tables now have proper tenant isolation.

### REMAINING ITEMS
- **AI endpoints are placeholders** - summarize/follow-up/task-summary return hardcoded strings, need MiniMax integration

---

## Architecture Notes

### Two Separate Event Systems
**This is important!** There are TWO separate data stores for time-based events:

1. **Calendar Events** (`/api/v1/calendar`) - This is where user's actual events live
   - Supports: meeting, call, reminder, blocked types
   - Has drag-and-drop, recurring, export to Google/Outlook
   - `/calendar/today` returns nested format: `{ date, events_by_hour: { "16": [...] }, total_count }`

2. **Appointments** (`/api/v1/office/appointments`) - Office appointment system
   - Supports: scheduled, confirmed, completed, cancelled statuses
   - Links to customers
   - Currently EMPTY - user hasn't used this system yet

**Decision needed:** Should these be unified? Or keep separate (calendar = internal events, appointments = customer-facing)?

---

## Key Files Modified This Session

### Frontend (`office-manager-frontend/`)
- `src/app/(dashboard)/dashboard/page.tsx` - **Complete rewrite** - fully interactive dashboard with real data
- `src/app/(dashboard)/calendar/page.tsx` - Fixed TypeScript generics for react-big-calendar DnD
- `src/app/(dashboard)/notes/page.tsx` - **Complete rewrite** - now uses real Notes API
- `src/lib/queries/office.ts` - Added Notes CRUD hooks (useNotes, useCreateNote, useUpdateNote, useDeleteNote)
- `package.json` - Added `@types/react-big-calendar` devDependency

### Backend (`office-manager-api/`)
- `app/api/v1/endpoints/office/__init__.py` - Added Notes CRUD endpoints (`/notes`)

### Config Files
- `office-manager-api/.env` line 35 - New ANTHROPIC_API_KEY
- `clawdbot/.env` - Added MINIMAX_API_KEY
- `~/.openclaw/agents/main/agent/auth-profiles.json` - New keys + cleared cooldown

---

## Frontend Files Overview

### Pages (`src/app/(dashboard)/`)
| Route | File | Status |
|-------|------|--------|
| `/` | `page.tsx` | Basic dashboard with Link-wrapped cards |
| `/dashboard` | `dashboard/page.tsx` | **Main dashboard** - fully interactive, real data |
| `/tasks` | `tasks/page.tsx` | Working - CRUD, search, filters |
| `/customers` | `customers/page.tsx` | Working - CRUD, search, type filter |
| `/employees` | `employees/page.tsx` | **Working** - CRUD with proper error handling |
| `/appointments` | `appointments/page.tsx` | **Working** - shows all month's appointments |
| `/calendar` | `calendar/page.tsx` | Working - react-big-calendar with DnD |
| `/notes` | `notes/page.tsx` | **Working now!** - Full CRUD with real API |
| `/settings` | `settings/page.tsx` | Tabs: Departments, Locations, Rooms |

### Query Hooks (`src/lib/queries/`)
- `office.ts` - Customers, Employees, Departments, Locations, Rooms, Appointments, **Notes**, Dashboard stats, useUpcomingAppointments
- `tasks.ts` - Tasks CRUD, useTaskStatistics
- `calendar.ts` - Calendar events CRUD, useTodayEvents, useEvents
- `auth.ts` - Login, register, logout

### Key UI Components
- `components/layouts/sidebar.tsx` - Navigation (links to /dashboard)
- `components/layouts/header.tsx` - Page header with search
- `components/layouts/auth-guard.tsx` - Protected routes
- `components/ui/` - Radix-based: card, button, dialog, input, select, tabs, etc.

---

## API Endpoints

### Employee Portal (`/api/v1/portal/`)
- `POST /auth/employee-login` - Employee login
- `GET /auth/me` - Get current user info
- `GET /appointments` - List appointments (own)
- `GET /tasks` - List tasks (assigned)
- `GET /notes` - List notes (own)
- `GET /customers` - List customers (assigned)

### Customer Portal (`/api/v1/portal/`)
- `POST /auth/customer-login` - Customer login
- `GET /auth/me` - Get current user info
- `GET /appointments` - List appointments (own)
- `GET /tasks` - List tasks (own)
- `GET /notes` - List notes (own)

### AI Automation (`/api/v1/automation/`)
- `POST /workflows` - Create workflow template
- `GET /workflows` - List workflows
- `POST /workflows/{id}/activate` - Activate workflow
- `POST /workflows/{id}/deactivate` - Deactivate workflow
- `POST /agent-tasks` - Create AI task
- `GET /agent-tasks` - List tasks
- `POST /ai/summarize` - AI text summarization
- `POST /ai/follow-up` - Generate follow-up message
- `POST /ai/task-summary` - Generate task summary
- `POST /remind` - Schedule reminders

### Verified Working
- `POST /office/employees/with-user` - ✅ Create user+employee (tested, IntegrityError handling added)
- `POST /api/v1/portal/auth/employee-login` - ✅ Employee portal login
- `POST /api/v1/portal/auth/customer-login` - ✅ Customer portal login
- `DELETE /office/employees/{id}` - Needs testing

---

## What To Work On Next

### Priority 1 - Testing & Verification (2026-02-08)
1. ~~Employee Portal~~ - ✅ COMPLETE
2. ~~Customer Portal~~ - ✅ COMPLETE
3. ~~AI Agent & Workflow Automation~~ - ✅ COMPLETE
4. **Test Employee Portal** - Login at `/portal/login`, navigate to `/portal/employee`
5. **Test Customer Portal** - Login at `/portal/login`, navigate to `/portal/customer`
6. **Debug Appointments frontend** - Check browser console (F12) for errors

### Priority 2 - Enhancements
1. **Calendar → Appointments Sync** - Rebuild backend to sync meetings to appointments
2. **Cloud Hosting Prep** - Choose provider, deploy to production
3. **Visual Workflow Builder** - Frontend UI for creating automation workflows
4. **Real-time updates** - WebSocket or polling for live dashboard data

### Priority 3 - Polish
8. **Mobile responsive** - Test and fix layout on small screens
9. **Dark mode** - Theme toggle
10. **Search** - Global search across tasks, customers, events

---

## Tech Stack

**Frontend:** Next.js 16.1.6 + React 19 + TypeScript + Tailwind CSS 4 + Radix UI + React Query + Zustand
**Backend:** FastAPI (Python) + PostgreSQL + Redis + Celery
**AI Gateway:** OpenClaw + MiniMax M2.1 via Anthropic-compatible API
**Telegram:** Grammy (Node.js bot) + OpenClaw gateway on port 18789

## How to Start

**Backend (Docker):**
```powershell
cd C:\Users\antho\clawd\office-manager-api
docker compose up -d
```

**Frontend:**
```powershell
cd C:\Users\antho\clawd\office-manager-frontend
npm run dev
```

**OpenClaw Gateway:**
```powershell
cd C:\Users\antho\clawd\clawdbot
openclaw gateway
```

**Access:** http://localhost:3000
**Login:** admin@test.com / password123
**Telegram:** @TheEntrepreneurBot

---

## 🔒 Security Status (OWASP ASVS Level 2)

| Feature | Status | Notes |
|---------|--------|-------|
| Password hashing (bcrypt) | ✅ | Implemented |
| Security headers (CSP, HSTS) | ✅ | Implemented |
| JWT token security (15min expiry) | ✅ | Implemented |
| Cookie security (SameSite=strict) | ✅ | Implemented |
| Rate limiting (login/register) | ✅ | Implemented |
| Row-Level Security (RLS) | ✅ | Applied to database |
| MFA for admins | 📅 Planned | Deferred to launch |
| Session invalidation on password change | TODO | Pending |

---

**Last Update:** 2026-02-10 19:58 EST by Claude Code (Portal route group fix, customer login UUID fix, Docker rebuilt)
