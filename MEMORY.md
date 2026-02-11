# Clawdbot + Office Manager API

## Security Mandate (P0 - Highest Priority)

**Date:** 2026-01-31  
**Classification:** Enterprise Security First

All development follows **Security-First Development** principles:

### Core Principles
1. **OWASP ASVS Level 2 Compliance** - All applications must meet enterprise security standards
2. **Tenant Isolation** - Mandatory for all multi-tenant applications
3. **Zero Trust** - Verify everything, trust nothing
4. **Defense in Depth** - Multiple security layers
5. **Fail Secure** - Errors deny access by default

### Security Requirements
- All new features require security review before merge
- Dependency scanning on every PR (Snyk/Dependabot)
- Secret detection on every push
- Critical/High CVEs block deployment
- AI/LLM security (prompt injection, data leakage)

### Key Documents
- `security/requirements/OWASP-ASVS-Compliance.md` - Full requirements
- `security/knowledge/vulnerability-kb.md` - Vulnerability reference
- `security/labs/prompt-injection-lab.md` - LLM security exercises
- `security/github-actions/security-scan-suite.yml` - CI/CD scanning

---

## Setup
- **Office Manager API**: Dockerized, running on localhost:8000
  - PostgreSQL: port 5432
  - Redis: port 6379
  - Admin: admin@example.com / password123

- **Clawdbot Gateway**: Cloned to C:\Users\antho\clawd\clawdbot
  - Telegram bot token: 8504942821:AAHkNDF5Fbs2RNPiAwYjXNONoKXHVGKsk8Y
  - Docker build in progress

## Features
- Registration supports Employee/Manager/Admin roles
- Customer testing via Employee role (tasks, calendar, notes)
- Ngrok tunnel active for remote access

## Files Modified
- `office-manager-api/app/api/v1/admin_ui.py` - Added role parameter
- `office-manager-api/app/templates/register.html` - Added role selector

---

## Strategic Direction - "God Mode" Office Manager (Added 2026-02-06)

**Vision:** Build an automated office manager that handles everything automatically without requiring technical setup from users.

### Simplified Signup Pattern (Reference)
- **Signup fields:** Full Name, Company/Business Name, Email, Password
- **Settings page:** Account info, Organization name + plan, Google Calendar integration, Sign Out
- **Behind scenes:** Auto-create organization on signup

### Key Principles
1. **No technical configuration visible to users** - no GHL, no API keys, no CRM settings
2. **Auto-everything** - organization creation, integrations, configurations handled automatically
3. **"God mode" automation** - the system does the work, users just use it

### Implementation Notes
- Simplify signup flow to match this pattern
- Implement auto-organization creation for multi-tenant support
- Hide technical configurations from regular users
- Focus on user experience, not technical complexity

---

## AI Assistant Coordination (Added 2026-02-03)

**Two AI assistants work on this project:**
- **Claude Code** - VS Code terminal, file editing, complex work
- **Minimax** - Telegram bot, mobile access, quick tasks

**Coordination System:**
1. Always read `PROJECT_STATUS.md` before starting work
2. Update `PROJECT_STATUS.md` after completing tasks
3. Check/update `memory/YYYY-MM-DD.md` for daily context
4. Run `git status` to see recent changes
5. Don't duplicate work - check who's working on what

**The workspace is:** `C:\Users\antho\clawd`

---

## User Timezone Support (Added 2026-02-08)

Following Rico's feedback, implemented per-user timezone settings:

### Implementation
- Each user has a `timezone` field in database (default: "UTC")
- Frontend auto-detects browser timezone
- Common timezones provided in dropdown (30+ options)
- Calendar events display in user's local timezone

### Key Files
- Backend: `app/models/user.py`, `app/api/v1/auth.py`
- Migration: `migrations/add_timezone.sql`
- Frontend: `src/lib/timezone.ts`, `src/lib/queries/user-settings.ts`

### Supported Timezones
US, Europe, Asia, Australia, Americas, India, Southeast Asia, Korea, New Zealand

---

## Employee Portal Debugging (2026-02-11)

### Issues Found & Fixed

1. **Missing Badge Component**
   - Created `office-manager-frontend/src/components/ui/badge.tsx`
   - Fixed calendar page import error

2. **Employee Portal Redirect Loop**
   - **Problem**: After login, clicking navigation redirects to `/portal/employee-login`
   - **Root cause**: Token persistence issue + missing refresh_token in API response
   - **Fixes applied**:
     - Added `refresh_token` to `/portal/auth/employee-login` endpoint
     - Added console.debug logging to `employee/layout.tsx` for debugging
   - **In progress**: Need to restart backend and check browser console for auth flow

### Backend Changes
- `app/api/v1/endpoints/portal/auth.py`: Added refresh_token to employee-login response

### Frontend Changes
- `src/app/(portal)/portal/employee/layout.tsx`: Added debug logging for auth flow
