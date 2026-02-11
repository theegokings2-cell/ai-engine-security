# Customer Portal - Development Plan

## Overview
Build a self-service customer portal where clients can:
- View their appointments
- See tasks assigned to them
- Access their notes
- Update their profile

## Architecture

### Multi-Tenant Design
- **Organizations** - Companies using the system (e.g., "Acme Corp")
- **Users** - People within organizations (employees and customers)
- **Customers** - External clients linked to organizations

### Customer Portal Pages
1. `/portal/login` - Customer login page
2. `/portal/register` - Customer self-registration
3. `/portal/dashboard` - Customer's main view
4. `/portal/appointments` - Customer's appointments
5. `/portal/tasks` - Tasks assigned to customer
6. `/portal/notes` - Notes about the customer
7. `/portal/profile` - Customer profile settings

## Implementation Steps

### Phase 1: Authentication & Organization
- [ ] Create customer registration endpoint (`/portal/register`)
- [ ] Auto-create organization on registration (if not provided)
- [ ] Customer login endpoint
- [ ] Customer logout endpoint
- [ ] Customer role (`CUSTOMER`) in User model

### Phase 2: Customer Dashboard
- [ ] Customer dashboard page
- [ ] Show upcoming appointments
- [ ] Show assigned tasks
- [ ] Show recent notes

### Phase 3: Customer Features
- [ ] Appointments list for customer
- [ ] Tasks list for customer
- [ ] Notes list for customer
- [ ] Profile management

### Phase 4: Customer Invitations
- [ ] Employees can invite customers via email
- [ ] Customer receives invitation link
- [ ] Customer creates account linked to organization

## API Endpoints Needed

### Authentication
- `POST /portal/auth/register` - Customer registration
- `POST /portal/auth/login` - Customer login
- `POST /portal/auth/refresh` - Refresh token

### Customer Data
- `GET /portal/me` - Get current customer profile
- `PUT /portal/me` - Update profile
- `GET /portal/appointments` - Customer's appointments
- `GET /portal/tasks` - Customer's tasks
- `GET /portal/notes` - Customer's notes

## Frontend Routes

```
/portal/
├── login
├── register
├── dashboard
├── appointments
├── tasks
├── notes
└── profile
```

## Key Design Decisions

1. **Separate Portal URL** - `/portal/*` for customers, keeping admin at `/dashboard/*`
2. **Same Backend** - Reuse existing models and database
3. **Limited Access** - Customers can only see their own data
4. **Simplified UI** - Clean, self-service focused design
