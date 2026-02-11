# DEVELOPMENT ROADMAP - AI Office Manager
**Last Updated:** 2026-02-08 by Claude Code (Employee Portal - Backend Foundation)

---

## 🚀 BUILD STATUS

### ✅ Employee Portal - COMPLETE! 🎉

**Backend:**
- ✅ Permission System with role-based defaults
- ✅ Database tables (user_permissions, scim_group_mappings)
- ✅ RLS Policies for own/assigned access
- ✅ Audit Logging with correlation IDs
- ✅ Portal API Endpoints (Appointments, Tasks, Notes, Customers)
- ✅ Employee Login endpoint

**Frontend Pages (All Interactive):**
- ✅ **Layout** - Sidebar navigation, header, role indicator
- ✅ **Dashboard** - Interactive stats cards, quick add buttons, clickable items
- ✅ **Calendar** - Full calendar with privacy rules (Busy blocks)
- ✅ **Appointments** - Full CRUD (Create, Read, Update, Delete)
- ✅ **Tasks** - Full CRUD (Create, Read, Update, Delete)
- ✅ **Notes** - Full CRUD (Create, Read, Update, Delete)
- ✅ **Customers** - Read-only with search and detail view

---

### ✅ CUSTOMER PORTAL - COMPLETE! 🎉

**Frontend Pages:**
- ✅ **Layout** - Simplified sidebar for customers
- ✅ **Dashboard** - Stats, upcoming appointments/tasks
- ✅ **Appointments** - View own appointments
- ✅ **Tasks** - View assigned tasks
- ✅ **Notes** - View own notes

---

### 📋 NEXT PRIORITIES

1. **AI Agent & Workflow Automation (NEW!)**
   - ✅ **Database Tables** - Workflows, agent tasks, automation rules
   - ✅ **Automation API** - CRUD workflows, agent tasks, reminders
   - ✅ **Pre-built Templates** - Appointment reminders, follow-ups, daily summaries

2. **Testing & Bug Fixes**
   - Test employee login flow
   - Test customer login flow
   - Verify permissions work correctly

3. **Calendar → Appointments Sync**
   - Rebuild backend to sync meetings to appointments

4. **Cloud Hosting Prep**
   - Choose cloud DB provider
   - Deploy to production

### 📅 Calendar Features
- [ ] View full org calendar (restricted details)
- [ ] **Privacy Rules:**
  - Events NOT owned/attended → Show "Busy" block only (no title/guests/notes)
  - Full details only if: owner, attendee, or role-granted access
- [ ] Calendar API with permission-based data filtering

### 📋 Appointments
- [ ] **CRUD** for appointments where `owner_employee_id = current_user`
- [ ] Optional: Edit if listed as attendee
- [ ] Create/Edit/Delete own appointments only

### ✅ Tasks
- [ ] View tasks assigned to employee
- [ ] Edit: status changes, comments, time logs
- [ ] **No delete** permission
- [ ] Filter by: assigned_to, status, due_date

### 📝 Notes
- [ ] View/Edit notes they **created**
- [ ] View notes **shared with their department/team**
- [ ] No delete (soft delete only)

### 👥 Customers (Read-Only)
- [ ] View customers **assigned to them**
- [ ] View customers **department-scoped**
- [ ] No edit/delete

---

## 🔐 PERMISSION MODEL (Backend-Enforced)

### Explicit Permissions
| Permission | Description |
|------------|-------------|
| `calendar.read` | View calendar (details based on privacy rules) |
| `appointments.write_own` | Create/Edit/Delete own appointments |
| `appointments.read_all` | Read all appointments (managers only) |
| `tasks.write_assigned` | Edit tasks assigned to user |
| `tasks.read_all` | Read all tasks (managers only) |
| `notes.write_own` | Edit notes created by user |
| `notes.read_team` | Read notes shared with department |
| `customers.read_assigned` | Read assigned customers |
| `customers.read_all` | Read all customers (sales managers) |
| `time.create` | Log time entries |

### RLS Policy Extensions
- [ ] Extend `appointments` policy: `assigned_to_id = current_setting('app.current_user_id') OR owner_id = current_setting('app.current_user_id')`
- [ ] Extend `tasks` policy: `assigned_to_id = current_setting('app.current_user_id')`
- [ ] Extend `notes` policy: `created_by_id = current_setting('app.current_user_id') OR shared_with_department = current_setting('app.current_department_id')`
- [ ] Extend `customers` policy: `assigned_employee_id = current_setting('app.current_user_id') OR department_id = current_setting('app.current_department_id')`

---

## 📊 AUDIT LOGGING (Enterprise Trust)

### Log These Events
- [ ] **Auth:** Login, logout, failed logins, token refresh
- [ ] **Appointments:** Create, edit, cancel (with before/after values)
- [ ] **Tasks:** Status changes, comments, time logs
- [ ] **Notes:** Create, edit (track content changes)
- [ ] **Customers:** Record views, exports
- [ ] **Permissions:** Role changes, permission grants (especially SCIM-driven)
- [ ] **Risky Actions:** Delete, permission changes, data exports

### Implementation
- [ ] Create `audit_logs` table (if not exists)
- [ ] Add middleware to log every API request
- [ ] Include: correlation_id, user_id, action, resource, timestamp, IP, user_agent
- [ ] **No PII/secrets** in logs (redact tokens, passwords, sensitive content)
- [ ] Retention policy: 90 days standard, 1 year for compliance

---

## 🔒 GUARDRAILS (Agent Safety)

### Approval Layer
- [ ] Block **risky actions** unless explicitly permitted:
  - Delete records
  - Message customers (external)
  - Change permissions
  - Data exports
  - Bulk operations

### Prompt Injection Defenses
- [ ] Treat Telegram/Email/Web content as **untrusted**
- [ ] **Isolate** external content from system instructions
- [ ] **Validate** tool parameters before executing
- [ ] Sanitize all user input in agent prompts

---

## 🔄 SCIM GROUP → ROLE MAPPING

### IdP Groups Mapping
| IdP Group | System Role | Department |
|-----------|-------------|------------|
| `Admins` | Admin | - |
| `Managers` | Manager | Department-based |
| `Employees` | Employee | Department-based |
| `Sales-Team` | Employee | Sales |
| `Support-Team` | Employee | Support |

### Implementation
- [ ] Define group-to-role mapping table
- [ ] On SCIM group change → Update user role automatically
- [ ] **Audit log** every role/group change
- [ ] Source of truth: IdP (Okta/Entra/Google)

---

## 📋 BUILD ORDER

1. **Backend Foundation**
   - [ ] Extend RLS policies for "own/assigned" access
   - [ ] Add permission columns to users table
   - [ ] Create SCIM group mapping table

2. **Employee Portal Pages**
   - [ ] Calendar view with privacy rules
   - [ ] Appointments (own CRUD)
   - [ ] Tasks (assigned, with status changes)
   - [ ] Notes (own + team-shared)
   - [ ] Customers (read-only, assigned)

3. **Audit Logging Pipeline**
   - [ ] Create audit_log table
   - [ ] Add middleware for automatic logging
   - [ ] Verify all actions are traceable

4. **SCIM Integration**
   - [ ] Group → role mapping logic
   - [ ] Automatic role updates on group changes
   - [ ] Audit trail for changes

---

## 🎯 CURRENT PRIORITY: Backend Foundation

### Next Steps
- [ ] Extend RLS policies for employee "own/assigned" access
- [ ] Add permission system to user model
- [ ] Create SCIM group mapping table
- [ ] Start building Employee Calendar page

---

## 🗓️ COMPLETED FEATURES

### ✅ Core Features Working

### ✅ Security (Done)
- [x] JWT tokens (15-min expiry)
- [x] Row-Level Security (RLS) - appointments table
- [x] Password hashing (bcrypt)
- [x] Rate limiting (5/min reg, 10/min login)
- [x] Security headers (CSP, HSTS, X-Frame-Options)

### ✅ Timezone Support
- [x] User timezone field in database
- [x] Frontend auto-detect browser timezone
- [x] 30+ common timezones in dropdown
- [x] Backend API accepts timezone updates

### ✅ Integrations
- [x] Telegram bot (@TheEntrepreneurBot)
- [x] MiniMax M2.1 API (AI responses)
- [x] Google Calendar (sync in progress)

---

## 🚀 TESTING PHASE TASKS

### ✅ Bug Fixes - COMPLETE!
- ✅ Test employee creation (422 error fixed with Form data)
- ✅ Verify department creation works
- ✅ Fix Appointments frontend display
- ✅ **Missing badge component** - Created badge.tsx
- ✅ **Employee portal redirect loop** - Fixed API client, endpoints, added refresh_token
- ✅ **Make all tabs interactive** - Added CRUD to all pages, clickable dashboard cards

### Calendar → Appointments Sync
- [ ] Rebuild backend to apply Calendar→Appointment sync
- [ ] Test: Meeting in Calendar → appears in Appointments
- [ ] Test: Call in Calendar → appears in Appointments
- [ ] Test: Reminder/Blocked → stays in Calendar only

---

## ☁️ CLOUD HOSTING PREP

### Infrastructure Planning
- [ ] Choose cloud DB provider (Supabase / Railway / Render / Neon)
- [ ] Choose hosting platform (Railway/Render for backend, Vercel for frontend)
- [ ] Purchase domain name
- [ ] Export local PostgreSQL data (pg_dump)

### Deployment Steps
- [ ] Deploy backend to Railway/Render
- [ ] Deploy frontend to Vercel
- [ ] Update .env with cloud URLs
- [ ] Update CORS origins for production domain
- [ ] Test multi-user login (employees + customers)

---

## 📞 VOICE & COMMUNICATION (Later)

### Phase 3A: Voice Responses
- [ ] ElevenLabs TTS integration
- [ ] Voice command processing (STT)
- [ ] Text-to-speech for notifications

### Phase 3B: Phone Reception
- [ ] VAPI/Retell AI account setup
- [ ] Phone number purchase
- [ ] AI receptionist integration

### Phase 3C: Messaging
- [ ] Twilio SMS integration
- [ ] WhatsApp Business API

---

## 🤖 AI AGENT & WORKFLOW AUTOMATION

### ✅ What's Built

**Database Tables:**
- `workflow_templates` - Workflow definitions with triggers and actions
- `workflow_executions` - Execution history and logs
- `agent_tasks` - AI processing tasks (summarize, follow-up, reminders, etc.)
- `automation_rules` - Event-based automation triggers

**Pre-built Workflow Templates:**
1. **Appointment Reminders** - Auto-send 24h and 1h before appointments
2. **Appointment Follow-up** - Generate follow-up message after completed appointments
3. **Daily Task Summary** - Morning digest of tasks at 8am

**Automation API Endpoints:**
- `POST /api/v1/automation/workflows` - Create workflow
- `GET /api/v1/automation/workflows` - List workflows
- `POST /api/v1/automation/workflows/{id}/activate` - Activate
- `POST /api/v1/automation/workflows/{id}/deactivate` - Deactivate
- `POST /api/v1/automation/agent-tasks` - Create AI task
- `GET /api/v1/automation/agent-tasks` - List tasks
- `POST /api/v1/automation/ai/summarize` - AI text summarization
- `POST /api/v1/automation/ai/follow-up` - Generate follow-up message
- `POST /api/v1/automation/ai/task-summary` - Generate task summary
- `POST /api/v1/automation/remind` - Schedule reminders

### Trigger Types
- `scheduled` - Cron-based schedules
- `event` - Event-based (appointment.created, task.completed, etc.)
- `webhook` - External webhook triggers
- `manual` - Manual triggering

### Action Types
- `send_reminder` - Send reminders via Telegram/email
- `create_agent_task` - Queue AI task
- `find_appointments` - Find appointments matching criteria
- `aggregate_tasks` - Gather tasks for summary
- `generate_summary` - AI summary generation
- `send_digest` - Send digest to user

### Coming Soon
- Visual workflow builder UI
- Pre-built templates marketplace
- Integration with Google Calendar events
- SMS/WhatsApp automation channels

---

## 🚨 ENTERPRISE LAUNCH REQUIREMENTS (DEFERRED)

**Note:** These are needed closer to production launch, not for current testing phase.

### Enterprise SSO (SAML 2.0 + OIDC)
- Evaluate WorkOS/Stytch/ScaleKit vs in-house
- SAML 2.0 support (Okta, Entra ID)
- OIDC support (Google Workspace, Auth0)
- Org domain discovery, SSO enforcement
- Fallback local login for non-SSO tenants

### SCIM 2.0 Provisioning
- `/scim/Users` and `/scim/Groups` endpoints
- HTTPS-only, bearer token auth, rate limiting
- Idempotency, stable SCIM identifiers
- Audit logs for every SCIM request

### Agent Authority Guardrails
- Centralized policy engine
- Auto-approve low-risk / require approval high-risk
- Prompt injection defenses

### Enterprise Audit Logging
- Structured logging with correlation IDs
- OpenTelemetry instrumentation
- PII redaction, log retention policy

### Admin Control Plane
- SSO configuration UI
- SCIM token rotation
- Integration health checks
- Audit log export

---

## 📁 Key Files

| Purpose | File |
|---------|------|
| Shared status | `PROJECT_STATUS.md` |
| Quick reference | `QUICK_REFERENCE.md` |
| This roadmap | `HEARTBEAT.md` |

---

## 👥 Team Notes
- **Rico** - Product owner, testing via Telegram
- **Claude Code** - VS Code terminal, complex fixes
- **Minimax** - Telegram bot, quick tasks, voice commands

**Workspace:** `C:\Users\antho\clawd`
**Backend:** localhost:8000
**Frontend:** localhost:3000
