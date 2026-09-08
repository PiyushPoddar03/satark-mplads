---
title: SATARK MPLADS
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# SATARK-MPLADS

**Evidence-driven MPLADS monitoring and fraud/anomaly detection platform**

Built for **Smart India Hackathon (SIH) 2026 — Problem Statement 102**

## Deploy on Hugging Face Spaces

This repository is ready for a single-container **Docker Space**. It serves
the dashboard, FastAPI API, evidence files, and Swagger documentation from the
same Space URL. Create a new Space with **SDK: Docker**, then push this
repository's `main` branch to the Space repository:

```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/satark-mplads
git push hf main
```

In the Space's **Settings → Variables and secrets**, set `SECRET_KEY` as a
secret to a newly generated random value. Enable **Persistent Storage** and
set these variables so database records and evidence uploads survive rebuilds:

| Variable | Value |
| :--- | :--- |
| `DATABASE_URL` | `sqlite+aiosqlite:////data/satark.db` |
| `DATABASE_URL_SYNC` | `sqlite:////data/satark.db` |
| `EVIDENCE_STORAGE_PATH` | `/data/evidence` |
| `AI_MOCK_MODE` | `True` |

After the Space reaches **Running**, open its URL and sign in with
`admin@satark.gov.in` / `admin123`. API documentation is available at
`/docs`. The Hugging Face build uses the root `Dockerfile`; do not deploy the
older `satark-hf-space` folder, which contains only an API wrapper.

---

## Overview

SATARK-MPLADS is a comprehensive government-grade platform designed to detect anomalies, fraud, and inefficiencies in MPLADS (Member of Parliament Local Area Development Scheme) project implementation using:

- **Live field evidence** with GPS validation and geofence verification
- **AI-powered image forensics** and duplicate detection
- **Financial anomaly detection** with explainable risk scoring
- **Satellite verification** for physical progress validation
- **Role-based access control** with strict inspector authorization
- **Complete audit trail** for transparency and accountability

---

## Key Features

### 🔐 Security & Authorization
- JWT-based authentication with role-based access control (RBAC)
- **Server-side authorization** — inspectors can ONLY access their assigned projects
- Password hashing with bcrypt
- Complete audit logging of all system actions

### 📸 Live Field Evidence System
- **Authorized live-camera workflow** for field inspections
- GPS coordinate capture with accuracy validation
- **Project geofence verification** using Haversine distance calculation
- Evidence integrity via SHA-256 hashing
- Timestamp and device metadata capture

### 🤖 AI & Risk Analysis
- **Image Forensics**: Metadata analysis, ELA, C2PA verification, manipulation detection
- **Duplicate Detection**: Cross-project visual similarity using perceptual hashing
- **Financial Anomaly Engine**: Progress-expenditure decoupling detection
- **Satellite Verification**: Pre/during/post change detection (mock interface for demo)
- **Explainable Risk Score**: 0-100 composite risk with SHAP-like explainability

### 👥 User Roles
1. **Admin** — Create projects, assign inspectors, manage system
2. **Field Inspector** — View assigned projects, conduct inspections, submit evidence
3. **District Officer** — Review high-risk projects, investigate alerts
4. **Auditor** — Read-only audit log access

### 🚨 Alert System
- Multi-level alerts: LOW, MEDIUM, HIGH, CRITICAL
- Alert types: Evidence manipulation, duplicate evidence, geofence violation, financial anomaly, progress mismatch
- Escalation and resolution workflow

### 📊 Dashboard & Analytics
- District command center with risk heatmap
- Real-time project status monitoring
- Financial vs physical progress tracking
- Project timeline and event history

---

## Technology Stack

### Backend
- **Python 3.14+** with FastAPI
- **PostgreSQL** with PostGIS for spatial queries
- **SQLAlchemy 2.0** (async) with Alembic migrations
- **Pydantic** for validation and serialization
- **Uvicorn** ASGI server

### Frontend
- **Next.js 15** with App Router
- **React 19** with TypeScript
- **Tailwind CSS** for styling
- **Lucide Icons**
- **Leaflet** for maps

### AI/ML Stack (Modular Interfaces)
- **Mock providers** for demo/development
- Production-ready interfaces for:
  - OpenCV, Pillow (image processing)
  - PyTorch (forensics models)
  - FAISS (similarity search)
  - Scikit-learn (anomaly detection)

---

## Project Structure

```
satark-mplads/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # Auth dependencies & RBAC
│   │   │   └── routes/          # API endpoints
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── projects.py
│   │   │       ├── assignments.py
│   │   │       ├── inspections.py
│   │   │       ├── ai.py
│   │   │       └── alerts_audit.py
│   │   ├── core/
│   │   │   ├── config.py        # Settings
│   │   │   ├── database.py      # Async SQLAlchemy
│   │   │   └── security.py      # JWT, password hashing
│   │   ├── models/
│   │   │   ├── enums.py
│   │   │   └── models.py        # All database models
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── services/
│   │   │   ├── ai.py            # AI orchestration
│   │   │   └── audit.py         # Audit logging
│   │   ├── providers/           # AI provider interfaces
│   │   │   ├── base.py          # Abstract base classes
│   │   │   ├── mock.py          # Mock providers for demo
│   │   │   └── authorized.py    # Production providers (stub)
│   │   ├── utils/
│   │   │   └── geo.py           # Geofence/distance calculations
│   │   ├── main.py              # FastAPI app
│   │   └── seed.py              # Demo data with suspicious projects
│   ├── tests/                   # Pytest test suite
│   ├── storage/                 # Evidence file storage
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   └── app/                 # Next.js App Router
│   ├── package.json
│   └── tsconfig.json
└── README.md
```

---

## Setup Instructions

### Prerequisites
- **Python 3.14+**
- **Node.js 18+** and npm
- **PostgreSQL 16+** with PostGIS extension

### Backend Setup

1. **Create PostgreSQL database**
   ```bash
   createdb satark_mplads
   psql satark_mplads -c "CREATE EXTENSION postgis;"
   ```

2. **Create and activate virtual environment**
   ```bash
   cd backend
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run database migrations (optional, auto-created on startup)**
   ```bash
   alembic upgrade head
   ```

6. **Seed demo data**
   ```bash
   python -m app.seed
   ```

7. **Start backend server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   API docs: http://localhost:8000/docs

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**
   ```bash
   npm run dev
   ```

   App: http://localhost:3000

---

## Demo Accounts

After running the seed script:

| Role | Email | Password | Inspector ID |
|------|-------|----------|--------------|
| **Admin** | admin@satark.gov.in | admin123 | — |
| **Inspector 1** | inspector1@satark.gov.in | inspector123 | INS-0042 |
| **Inspector 2** | inspector2@satark.gov.in | inspector123 | INS-0078 |
| **Inspector 3** | inspector3@satark.gov.in | inspector123 | INS-0105 |
| **District Officer** | officer@satark.gov.in | officer123 | — |
| **Auditor** | auditor@satark.gov.in | auditor123 | — |

---

## Demo Projects

The seed data includes 6 projects, 3 of which are **intentionally suspicious** for SIH demo:

### 🔴 Project A: `MPLADS-KA-2025-0147` (Risk: 87/100 — CRITICAL)
- **Anomaly**: Progress-expenditure decoupling (42% physical vs 91% financial)
- **Anomaly**: Material cost +28% above benchmark
- **Alerts**: Financial mismatch, contractor concentration

### 🔴 Project B: `MPLADS-KA-2025-0203` (Risk: 82/100 — CRITICAL)
- **Anomaly**: 94% image similarity with Project A evidence
- **Alert**: Potential evidence reuse detected

### 🟠 Project C: `MPLADS-KA-2025-0089` (Risk: 76/100 — HIGH)
- **Anomaly**: Evidence captured 2.3 km outside geofence
- **Anomaly**: GPS accuracy very low (45m)
- **Alert**: Geofence violation

### 🟢 Project D: `MPLADS-KA-2025-0312` (Risk: 18/100 — LOW)
- Clean project with all verifications passed

---

## SIH 2026 Demo Flow

1. **Login as Admin** → Create new project → Assign Inspector INS-0042
2. **Login as Inspector (INS-0042)** → View assigned projects only
3. **Start Inspection** → Capture live evidence with GPS
4. **System validates**:
   - GPS coordinates
   - Geofence (distance from project site)
   - GPS accuracy
   - Timestamp
   - Evidence integrity (SHA-256 hash)
5. **AI Analysis runs**:
   - Image forensics
   - Duplicate detection across projects
   - Financial anomaly analysis
   - Composite risk score with explainability
6. **Risk Score: 87/100 (CRITICAL)**
7. **WHY?**
   - Financial expenditure 91% vs physical progress 42%
   - Evidence similarity 94% with another project
   - Material cost exceeds benchmark
8. **Login as District Officer** → Review high-risk projects → Escalate
9. **Login as Auditor** → View complete audit trail

---

## Security Features

### ✅ Inspector Authorization (Critical)
- Inspectors can **ONLY** access projects assigned to them
- Authorization enforced **server-side** in every API endpoint
- Attempting to access unauthorized project → `HTTP 403 Forbidden`
- No client-side workarounds possible

### ✅ Evidence Integrity
- Live-camera workflow restricts gallery uploads
- SHA-256 hash computed on submission
- GPS coordinates validated against project geofence
- GPS accuracy threshold enforcement
- Capture timestamp validation

### ✅ Audit Logging
- Every action logged with:
  - Actor, role, action type
  - Entity type and ID
  - Previous/new values
  - Timestamp
  - IP address (optional)
- Append-only logs (no deletion by regular users)

---

## Testing

### Run backend tests
```bash
cd backend
pytest tests/ -v
```

### Test coverage includes:
- Password hashing and JWT tokens
- Geofence distance calculations
- Mock AI providers (forensics, financial, risk engine)
- Authorization middleware
- Role-based access control

---

## API Endpoints

### Authentication
- `POST /api/auth/login` — Login with email/password
- `POST /api/auth/refresh` — Refresh access token
- `GET /api/auth/me` — Get current user

### Users (Admin only)
- `GET /api/users` — List users
- `POST /api/users` — Create user (inspector, officer, auditor)
- `PATCH /api/users/{id}` — Update user

### Projects
- `GET /api/projects` — List projects (filtered by role)
- `GET /api/projects/{id}` — Get project details
- `POST /api/projects` — Create project (Admin)
- `PATCH /api/projects/{id}` — Update project (Admin)
- `DELETE /api/projects/{id}` — Soft-delete project (Admin)

### Assignments (Admin only)
- `POST /api/assignments` — Assign inspector to project
- `GET /api/assignments/project/{id}` — Get assignment history
- `DELETE /api/assignments/{id}` — Revoke assignment

### Inspections
- `POST /api/inspections/start` — Start inspection
- `POST /api/inspections/{id}/evidence` — Upload evidence with GPS
- `POST /api/inspections/{id}/submit` — Submit inspection
- `GET /api/inspections/project/{id}` — List project inspections
- `GET /api/inspections/{id}/evidence` — List inspection evidence

### AI & Risk
- `POST /api/ai/analyze-evidence` — Trigger evidence analysis
- `POST /api/ai/evaluate-risk/{project_id}` — Calculate risk score
- `GET /api/ai/risk/{project_id}` — Get latest risk score
- `GET /api/ai/evidence-analysis/{evidence_id}` — Get analysis results

### Alerts
- `GET /api/alerts` — List alerts (filtered by role)
- `PATCH /api/alerts/{id}` — Update alert status/assignment

### Audit & Timeline
- `GET /api/audit` — List audit logs (Admin/Auditor only)
- `GET /api/timeline/{project_id}` — Get project timeline

### Dashboard
- `GET /api/dashboard/stats` — Get dashboard statistics

---

## Production Deployment Checklist

- [ ] Change `SECRET_KEY` to a secure random string (64+ characters)
- [ ] Set `DEBUG=false`
- [ ] Configure production database URL
- [ ] Use Alembic migrations instead of auto-create
- [ ] Configure CORS for production frontend domain
- [ ] Use S3/object storage for evidence files (replace local storage)
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting
- [ ] Set up monitoring and alerting
- [ ] Enable database backups
- [ ] Review and harden security settings
- [ ] Replace mock AI providers with production models
- [ ] Set `AI_MOCK_MODE=false`

---

## Future Enhancements

- [ ] Replace mock AI with production TruFor/forensics models
- [ ] Integrate real satellite imagery APIs (Google Earth Engine, ISRO Bhuvan)
- [ ] Neo4j graph database for contractor relationship analysis
- [ ] Mobile app for field inspectors (React Native)
- [ ] SMS/WhatsApp notifications for alerts
- [ ] Advanced financial DSR (detailed statement of rates) variance analysis
- [ ] Multi-language support (Hindi, regional languages)
- [ ] Offline mode for field inspectors
- [ ] Blockchain-based evidence immutability
- [ ] Integration with eMPLADS portal

---

## License

Proprietary — Built for Smart India Hackathon 2026

---

## Team

Developed for **SIH 2026 Problem Statement 102**

**Contact**: satark-mplads@sih2026.gov.in

---

## Acknowledgments

- Smart India Hackathon 2026
- Ministry of Statistics and Programme Implementation (MoSPI)
- All contributors and reviewers
