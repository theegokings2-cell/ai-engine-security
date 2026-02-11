# AI Office Manager API

A production-ready enterprise backend for an autonomous AI Office Manager SaaS platform.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repo>
cd office-manager-api

# Copy environment file
cp .env.example .env

# Start with Docker Compose
docker-compose up -d

# Or run locally (requires PostgreSQL + Redis)
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## 📁 Project Structure

```
office-manager-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py          # Login, register, token refresh
│   │       ├── calendar.py      # CRUD events, sync with M365/Google
│   │       ├── tasks.py         # Task CRUD, NL creation
│   │       ├── notes.py         # Notes + AI summarization
│   │       ├── email.py         # M365 Graph integration
│   │       ├── sms.py           # Twilio integration
│   │       └── admin.py         # Tenant management, audit logs
│   ├── core/
│   │   ├── config.py            # Settings from env
│   │   ├── security.py          # JWT handling, password hashing
│   │   ├── tenant.py            # Tenant isolation middleware
│   │   └── audit.py             # Audit logging decorators
│   ├── models/
│   │   ├── tenant.py            # Tenant model
│   │   ├── user.py              # User with role
│   │   ├── role.py              # Role + permissions
│   │   ├── task.py              # Task with assignee
│   │   ├── event.py             # Calendar event
│   │   ├── note.py              # Meeting note + summary
│   │   ├── audit_log.py         # Audit entries
│   │   └── base.py              # SQLAlchemy base
│   ├── services/
│   │   ├── calendar_service.py
│   │   ├── task_service.py
│   │   ├── notes_service.py     # AI summarization
│   │   ├── email_service.py
│   │   ├── sms_service.py
│   │   └── ai_service.py        # OpenAI abstraction + RAG
│   ├── integrations/
│   │   ├── microsoft.py         # M365 Graph API (calendar/email)
│   │   ├── google.py            # Google Calendar (future)
│   │   ├── twilio.py            # SMS
│   │   └── telegram.py          # Telegram bot webhook
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/
│   ├── main.py                  # FastAPI application
│   └── dependencies.py          # FastAPI dependencies
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 🏢 Multi-Tenant Architecture

### Tenancy Model

The platform uses **row-level multi-tenancy** with database-level isolation:

- **Shared Database**: All tenants share the same PostgreSQL database
- **Row Isolation**: Every table includes `tenant_id` column
- **Request Scoping**: Tenant ID extracted from JWT token
- **Query Filtering**: Automatic tenant filter via middleware

#### Tenant Model
```python
class Tenant(Base):
    id: UUID
    name: str
    slug: str                    # URL-friendly identifier
    settings: TenantSettings     # JSON with email_provider, sms_enabled, etc.
    subscription_tier: str       # free, pro, enterprise
    created_at: datetime
    is_active: bool
```

### RBAC Implementation

Three-tier role system with granular permissions:

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| **admin** | Tenant administrator | Full access: users, settings, all data |
| **manager** | Team lead | Manage team tasks, view all notes |
| **employee** | Regular user | Own tasks, own notes, read-only calendar |

#### Permission Model
```python
class Permission(Enum):
    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Task Management
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    
    # Calendar
    EVENT_CREATE = "event:create"
    EVENT_READ = "event:read"
    EVENT_UPDATE = "event:update"
    EVENT_DELETE = "event:delete"
    
    # Notes
    NOTE_CREATE = "note:create"
    NOTE_READ = "note:read"
    NOTE_UPDATE = "note:update"
    NOTE_DELETE = "note:delete"
    NOTE_SUMMARIZE = "note:summarize"
    
    # Admin
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SETTINGS = "admin:settings"
```

#### Role-Permission Matrix
```python
ROLE_PERMISSIONS = {
    "admin": list(Permission),  # All permissions
    "manager": [
        Permission.USER_READ,
        Permission.TASK_CREATE, Permission.TASK_READ,
        Permission.TASK_UPDATE, Permission.TASK_ASSIGN,
        Permission.EVENT_CREATE, Permission.EVENT_READ,
        Permission.EVENT_UPDATE,
        Permission.NOTE_CREATE, Permission.NOTE_READ,
        Permission.NOTE_UPDATE, Permission.NOTE_SUMMARIZE,
    ],
    "employee": [
        Permission.TASK_CREATE, Permission.TASK_READ,
        Permission.TASK_UPDATE,  # Only own tasks
        Permission.EVENT_READ,
        Permission.NOTE_CREATE, Permission.NOTE_READ,
        Permission.NOTE_UPDATE,  # Only own notes
        Permission.NOTE_SUMMARIZE,
    ],
}
```

### Audit Logging

Every write operation is automatically logged:

```python
@audit_log(action=AuditAction.TASK_CREATE)
async def create_task(db, user, tenant_id, task_data):
    # ... create task ...
    return task
```

#### Audit Log Model
```python
class AuditLog(Base):
    id: UUID
    tenant_id: UUID          # Always indexed
    user_id: UUID            # Who performed the action
    action: str              # What action (CREATE, UPDATE, DELETE)
    resource_type: str       # What resource (task, event, note, user)
    resource_id: UUID        # Which resource
    old_values: dict         # Previous state (for updates)
    new_values: dict         # New state
    metadata: dict           # IP, user agent, etc.
    created_at: datetime
```

## 🔐 Authentication Flow

### JWT Token Structure
```
{
  "sub": "user_id",
  "tenant_id": "tenant_uuid",
  "role": "admin",
  "permissions": ["task:create", "task:read", ...],
  "exp": 1715000000,
  "iat": 1714996400
}
```

### Auth Endpoints

#### Register
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "securepassword123",
  "tenant_name": "Acme Corp",
  "full_name": "John Admin"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "securepassword123"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}

Response:
{
  "id": "uuid",
  "email": "admin@company.com",
  "full_name": "John Admin",
  "role": "admin",
  "tenant_id": "uuid",
  "permissions": [...]
}
```

## 📋 Example API Flows

### 1. Natural Language Task Creation

Create a task from free-form text:

```http
POST /api/v1/tasks/from-text
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "text": "remind finance to approve Acme invoice tomorrow at 3pm"
}
```

**AI Processing Pipeline:**
1. Extract: "approve Acme invoice"
2. Assignee: Find "finance" user(s) → first finance team member
3. Due date: "tomorrow at 3pm" → Calculate datetime
4. Priority: Default medium, or detect urgency keywords
5. Create task with parsed fields
6. Schedule reminder

**Response:**
```json
{
  "id": "uuid",
  "title": "Approve Acme invoice",
  "description": "remind finance to approve Acme invoice tomorrow at 3pm",
  "assignee_id": "finance-user-uuid",
  "assignee_name": "Sarah Finance",
  "due_date": "2024-05-15T15:00:00Z",
  "priority": "medium",
  "status": "pending",
  "reminder_set": true
}
```

### 2. Meeting Note Summarization

Upload meeting notes and get AI summary:

```http
POST /api/v1/notes/{note_id}/summarize
Authorization: Bearer {access_token}

Response:
{
  "id": "uuid",
  "summary": "The team discussed Q2 goals and decided to focus on customer retention. Key metrics: NPS up 5%, churn down 2%. Action items assigned.",
  "action_items": [
    {
      "task": "Create customer retention campaign",
      "assignee": "marketing@company.com",
      "due_date": "2024-05-20"
    },
    {
      "task": "Review NPS report with product team",
      "assignee": "product@company.com",
      "due_date": "2024-05-17"
    }
  ],
  "key_topics": ["Q2 goals", "customer retention", "NPS metrics"],
  "sentiment": "positive"
}
```

### 3. Policy Q&A (RAG)

Ask questions against uploaded policy documents:

```http
POST /api/v1/notes/{note_id}/qa
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "question": "What is the vacation policy for new employees?"
}

Response:
{
  "answer": "New employees accrue 1.5 days of vacation per month (18 days/year). Vacation can be taken after 90 days of employment. Request must be submitted 2 weeks in advance.",
  "sources": [
    {
      "document": "HR-Policies-2024.pdf",
      "page": 3,
      "relevance_score": 0.95
    }
  ]
}
```

### 4. Reminder Trigger Flow

```mermaid
graph TD
    A[Background Job: check_reminders] --> B{Due reminders?}
    B -->|Yes| C[For each reminder]
    C --> D[Get user notification prefs]
    D --> E{Email enabled?}
    E -->|Yes| F[Send Email via M365]
    E -->|No| G{SMS enabled?}
    G -->|Yes| H[Send SMS via Twilio]
    G -->|No| I{Telegram linked?}
    I -->|Yes| J[Send Telegram message]
    I -->|No| K[Log: No notification channel]
    F --> L[Update: reminder_sent]
    H --> L
    J --> L
```

**Celery Task:**
```python
@celery.task
def check_and_send_reminders():
    """Check for due reminders and send via user-preferred channel."""
    due_reminders = reminder_service.get_due_reminders()
    for reminder in due_reminders:
        user = reminder.assignee
        channel = user.notification_preference
        if channel == "email":
            email_service.send(reminder)
        elif channel == "sms":
            sms_service.send(reminder)
        elif channel == "telegram":
            telegram_service.send(reminder)
        reminder_service.mark_sent(reminder)
```

## 🔄 Integrations

### Microsoft 365 (Graph API)

```python
# Calendar sync
await microsoft_calendar.sync_events(
    tenant_id=tenant_id,
    user_email=user_email,
    calendar_id=calendar_id
)

# Send email
await microsoft_email.send(
    to=["recipient@company.com"],
    subject="Meeting Reminder",
    body="Don't forget about the 3pm meeting"
)
```

### Twilio SMS

```python
await twilio_sms.send(
    to="+1234567890",
    message="Task reminder: Approve Acme invoice due today at 3pm"
)
```

### Telegram Webhook

```python
@app.post("/integrations/telegram/webhook")
async def telegram_webhook(update: Update):
    # Parse message
    # Extract intent
    # Route to appropriate handler
    # Create task / note / event
    return {"status": "ok"}
```

## 🛠 Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests
pytest tests/ -v --cov=app
```

### Database Migrations

```bash
# Create migration
alembic revision -m "add_user_table"

# Apply migrations
alembic upgrade head

# Check current revision
alembic current
```

### Code Style

```bash
# Format code
black app/
isort app/

# Type checking
mypy app/

# Linting
flake8 app/
```

## 📦 Environment Variables

```env
# Application
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-change-in-prod

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/office_manager

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Microsoft Graph
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT_ID=your-tenant-id

# Twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhooks/telegram
```

## 🚢 Deployment

### Docker Compose (Production)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL 15
- Redis 7
- FastAPI application
- Celery worker
- Flower (Celery monitoring)

### Kubernetes

Helm charts available in `/k8s` directory:
- `values.yaml` for configuration
- Separate deployments for API, worker, scheduler

## 📊 Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Structured Logging**: JSON logs with correlation IDs
- **Error Tracking**: Sentry integration ready

## 🔒 Security

- JWT tokens with RS256 signing
- Password hashing with Argon2
- Rate limiting per tenant/user
- CORS configured for allowed origins
- Input validation with Pydantic
- SQL injection prevention via SQLAlchemy

## 📈 Roadmap

- [ ] Google Calendar integration
- [ ] Slack integration
- [ ] Advanced RAG with vector database (Pinecone/Weaviate)
- [ ] Multi-region support
- [ ] SSO (Okta, Azure AD)
- [ ] WebSocket support for real-time updates

## 📄 License

MIT License - see LICENSE file for details.
