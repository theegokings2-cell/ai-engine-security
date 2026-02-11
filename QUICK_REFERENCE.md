# AI Office Manager - Quick Reference

## Start Everything

**1. Start Docker Desktop** (must be running first!)

**2. Start Backend** (PowerShell):
```powershell
cd C:\Users\antho\clawd\office-manager-api
docker compose up -d
```

**3. Start Frontend** (new PowerShell window):
```powershell
cd C:\Users\antho\clawd\office-manager-frontend
npm run dev
```

**4. Open App:** http://localhost:3000

---

## After Code Changes

**Frontend changes** - Just refresh browser (Ctrl+F5)

**Backend changes** - Rebuild and restart:
```powershell
cd C:\Users\antho\clawd\office-manager-api
docker compose build
docker compose up -d
```

---

## Check What's Running

```powershell
docker ps
```

Expected:
- office-manager-api (port 8000)
- office-manager-db (port 5432)
- office-manager-redis (port 6379)

---

## Stop Everything

```powershell
docker compose down
```

---

## Login

- **Email:** newtest@example.com
- **Password:** TestPassword123

---

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | http://localhost:3000 | Overview stats |
| Tasks | http://localhost:3000/tasks | Task management |
| Calendar | http://localhost:3000/calendar | Events (Google-style) |
| Appointments | http://localhost:3000/appointments | Customer appointments |
| Customers | http://localhost:3000/customers | Customer database |
| Employees | http://localhost:3000/employees | Team management |

---

## Troubleshooting

**Frontend won't start?**
```powershell
cd C:\Users\antho\clawd\office-manager-frontend
npm install
npm run dev
```

**Backend errors?**
```powershell
cd C:\Users\antho\clawd\office-manager-api
docker compose logs
```

**Clear browser cache:** Ctrl+Shift+R

---

## Quick Tips

- Dashboard cards are clickable → navigate to sections
- Calendar supports drag-and-drop
- Create employees with name, email, password
- 50+ enterprise departments available
- Appointments show 12 months ahead
