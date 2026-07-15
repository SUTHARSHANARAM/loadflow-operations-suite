# LoadFlow — Freight Brokerage Operations Suite

> Take-home assessment submission for the LoadFlow Hackathon Project.

A full-stack, multi-tenant freight brokerage operations platform connecting **Shippers**, **Brokers**, and **Carriers** with automated compliance enforcement, RBAC, versioned rate confirmations, and a complete shipment lifecycle state machine.

---

## 🚀 Live Demo

> **🌐 Frontend (Live)**: https://loadflow-operations-suite-eta.vercel.app
> **⚙️ Backend API (Live)**: https://loadflow-operations-suite.onrender.com
> **📖 API Docs (Swagger)**: https://loadflow-operations-suite.onrender.com/docs

---

## 📦 Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend | FastAPI (Python) | Fast async API with built-in OpenAPI docs, clean dependency injection for RBAC |
| Database | SQLite + SQLAlchemy ORM | Simple, file-based, zero-config for assessment purposes |
| Auth | JWT (PyJWT + Passlib bcrypt) | Stateless, industry-standard token auth |
| Frontend | React 19 + TypeScript + Vite | Type-safe, fast HMR dev server, clean component model |
| Styling | Vanilla CSS (custom design tokens) | Full control, no framework overhead |

---

## ✅ Feature Checklist

### Must-Haves
- [x] **Auth** — JWT-based login for all 3 account types (Broker, Carrier, Shipper)
- [x] **RBAC** — Admin-defined roles from a fixed permission catalog (`load.create`, `load.assign_carrier`, `load.override_compliance_flag`, `rate.confirm`, `load.update_status`, `staff.manage`, `pod.upload`). Enforced at the API layer — not just UI hiding.
- [x] **Org + Object-level scoping** — Broker staff never see Carrier data. Shippers see only their own loads.
- [x] **Staff management** — Broker/Carrier Admins create staff and assign custom roles via UI
- [x] **Load CRUD** — Create, assign, search/filter loads on the broker load board
- [x] **Full State Machine** — `Posted → Carrier Assigned → Rate Confirmed → Dispatched → In Transit → Delivered → POD Verified → Closed`. Every transition is timestamped and attributed.
- [x] **Audit Trail** — Immutable log of every action (logins, load changes, status updates, compliance blocks/overrides)
- [x] **Carrier Compliance Engine** — Auto-flags loads if carrier has expired insurance/authority, or mismatched equipment/commodity. Blocks progression past `Carrier Assigned` until resolved or overridden by authorized staff.
- [x] **Rate Confirmation with Versioning** — Broker proposes versioned rate proposals; both parties must sign before dispatch.
- [x] **Dashboards per account type** — Broker (load board + compliance alerts), Carrier (assigned loads + status actions), Shipper (own load tracker)
- [x] **Search/filter** on broker load board

### Stretch Goals
- [x] **POD upload/viewer** — Carrier uploads proof of delivery; Broker verifies
- [x] **Audit Log Viewer** — Broker Admin dashboard with full chronological event history
- [ ] Compliance expiry renewal alerts (not implemented — would add scheduled background task with email notification)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│            React/TypeScript Frontend        │
│  Broker | Carrier | Shipper Dashboards      │
└────────────────────┬────────────────────────┘
                     │ JWT Auth Headers
┌────────────────────▼────────────────────────┐
│              FastAPI Backend                │
│  PermissionChecker RBAC Middleware          │
│  ┌─────────────────────────────────────┐   │
│  │  Auth | RBAC | Loads | Compliance   │   │
│  │  Rates | Audit Logs Routers         │   │
│  └──────────────────┬──────────────────┘   │
│  ┌──────────────────▼──────────────────┐   │
│  │  State Machine | Compliance Engine  │   │
│  │  Rate Service  | Audit Service      │   │
│  └──────────────────┬──────────────────┘   │
└────────────────────┬────────────────────────┘
                     │ SQLAlchemy ORM
             ┌───────▼───────┐
             │   SQLite DB   │
             └───────────────┘
```

---

## 🔐 RBAC Design

- **Permission Catalog** (fixed): `load.create`, `load.assign_carrier`, `load.override_compliance_flag`, `rate.confirm`, `load.update_status`, `staff.manage`, `pod.upload`
- **Roles** = named bundles of permissions, created by Org Admins via UI
- **Code always checks permissions, never role names** (e.g., `if "load.create" in user.permissions`)
- **Bootstrap**: First Broker/Carrier account registered via `/api/auth/register` is automatically the Org Admin with full permissions. Additional staff are invited by the Admin with scoped roles.

---

## 🚦 Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Clone the Repository
```bash
git clone https://github.com/SUTHARSHANARAM/loadflow-operations-suite.git
cd loadflow-operations-suite
```

### 2. Start the Backend
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```
- API available at: `http://localhost:8000`
- Swagger docs at: `http://localhost:8000/docs`
- Database tables and permission catalog are auto-created on first startup.

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev -- --port 3000
```
- App available at: `http://localhost:3000`

### 4. Run Tests
```bash
cd backend
python -m pytest
```

---

## 🌐 Deployment

### Backend → Render.com (Free Tier)
1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repository
3. Set **Root Directory** to `backend`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Copy the deployed URL (e.g., `https://loadflow-api.onrender.com`)

### Frontend → Vercel (Free Tier)
1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repository
3. Set **Root Directory** to `frontend`
4. Add Environment Variable:
   - `VITE_API_URL` = `https://loadflow-api.onrender.com/api`
5. Deploy

---

## 📝 Assumptions & Trade-offs

- **SQLite**: Chosen for zero-config setup. On Render's free tier, the filesystem is ephemeral — the database resets on each deploy. For production, this would be replaced with PostgreSQL.
- **JWT Secret**: Currently hardcoded in `backend/app/auth/security.py`. In production, this would be set via an environment variable (`SECRET_KEY`).
- **No email invitations**: Staff accounts are created directly by Admins via the UI. In production, an email invitation flow with a token-based signup link would be implemented.
- **Compliance expiry alerts**: Not implemented. Would be added as a scheduled background task (e.g., APScheduler or Celery) sending email/webhook notifications 30 days before expiry.
- **Rate confirmation signing**: Currently single-party sign-off by the Carrier. A full implementation would require cryptographic digital signatures.

## ⏭️ What I'd Do With More Time

1. Replace SQLite with PostgreSQL for production persistence
2. Add email invitation flow for staff onboarding
3. Implement compliance expiry renewal alert system (scheduled tasks)
4. Add real file upload for POD documents (currently text/reference only)
5. Migrate Pydantic schemas to V2 `model_config` syntax
6. Add end-to-end Playwright tests for the full shipment lifecycle

---

## 🤖 AI Tool Usage

This project was built with the assistance of **Antigravity (Google DeepMind)** as the AI coding tool throughout the development process.

**How it was used:**
- Scaffolding the initial FastAPI backend architecture (models, schemas, routers, services)
- Implementing the RBAC permission checker middleware
- Designing and implementing the compliance state machine logic
- Debugging SQLAlchemy relationship mappings and type errors
- Generating the React/TypeScript frontend dashboard components
- Refactoring UI components (badge layout, vertical stepper, card styling)
- Writing integration test suites

**Review habits:** Every generated code block was reviewed for correctness, security implications (e.g., RBAC enforcement at API layer), and alignment with the business requirements before being committed.
