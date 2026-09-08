# SATARK-MPLADS Quick Reference Guide

## 🚀 Start Both Servers

**Terminal 1 - Backend:**
```bash
cd C:\Users\podda\Desktop\code\satark-mplads\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd C:\Users\podda\Desktop\code\satark-mplads\frontend
npm run dev
```

## 🌐 Access URLs

- **Frontend Application**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔐 Login Credentials

| Role | Email | Password | Inspector ID | Best For Testing |
|------|-------|----------|--------------|------------------|
| **Admin** | admin@satark.gov.in | `admin123` | - | Create projects, assign inspectors, trigger AI risk eval |
| **Inspector 1** | inspector1@satark.gov.in | `inspector123` | INS-0042 | Live field inspection with camera & GPS |
| **Inspector 2** | inspector2@satark.gov.in | `inspector123` | INS-0078 | View multiple assigned projects |
| **Inspector 3** | inspector3@satark.gov.in | `inspector123` | INS-0105 | Hyderabad projects |
| **District Officer** | officer@satark.gov.in | `officer123` | - | Alert management |
| **Auditor** | auditor@satark.gov.in | `auditor123` | - | Audit trail review |

**Quick Login:** On the login page, click any role button for instant 1-click login (no typing needed)

## 📱 Page Navigation

### All Users
- `/login` - Login page with demo quick-login
- `/dashboard` - Role-specific dashboard with stats

### Admin / Officer / Auditor
- `/projects` - Projects listing with search/filters
  - Admin: "Add New Project" button (modal with geofence config)
- `/projects/{id}` - **Forensic detail page** with evidence gallery, AI analysis, risk breakdown, timeline
- `/alerts` - Alert management (Admin/Officer only)
- `/audit` - Audit logs (Admin/Auditor only)

### Field Inspectors
- `/inspections` - **Live field inspection page**
  - Click "Start Live Capture" → Opens camera modal with GPS geofence validation

## 🎯 5-Minute Demo Flow

1. **Login as Inspector 1** → Dashboard shows 1 assigned project
2. **Navigate to `/inspections`** → Click "Start Live Capture" on MPLADS-KA-2025-0456
3. **LiveCameraModal opens**:
   - GPS permission → Shows distance from project
   - If outside geofence: Use DevTools to simulate location (12.9716, 77.5946)
   - Camera permission → Live video stream
   - Capture 2-3 photos (SHA-256 hash calculated)
   - Submit inspection
4. **Navigate to `/projects`** → Click "Forensic View" on the project
5. **Evidence Tab** → Click any photo → See AI forensics analysis & duplicate detection
6. **Risk Tab** → See explainable AI risk breakdown
7. **Login as Admin** → Navigate to `/alerts` → See critical alerts for suspicious projects

## 🧪 Testing Geofence Without Being On-Site

### Chrome DevTools Method:
1. Press `F12` → Open DevTools
2. Click **⋮** (three dots) → **More tools** → **Sensors**
3. Under **Location**, select **"Custom location"**
4. Enter coordinates: `12.9716` (Lat), `77.5946` (Lon)
5. Refresh page/modal → GPS shows "Within Geofence"

### Firefox Method:
1. Press `F12` → Console tab
2. Type: `about:config` in address bar → Search `geo.enabled` → Set to `true`
3. Install extension: "Location Guard" or use manual override

## 🔍 Key Features to Highlight

### 1. Hardware GPS Geofencing ✅
- Real-time distance calculation using Haversine formula
- Server-side validation (can't fake)
- Green badge if within radius, red warning if outside

### 2. SHA-256 Evidence Integrity ✅
- Client-side hash calculated before upload
- Prevents post-capture tampering
- Visible in evidence detail modal

### 3. AI Forensics Analysis ✅
- Image manipulation detection (ELA, EXIF)
- Duplicate detection across projects
- Risk score with explainable factors

### 4. Strict RBAC Security ✅
- Inspector 1 sees only 1 assigned project
- Try accessing another project → 403 Forbidden
- Server-side authorization (not just frontend hiding)

### 5. Complete Audit Trail ✅
- Every action logged with timestamp
- Expandable rows show JSON before/after diff
- Filter by role/entity type

## 📊 Seeded Data Summary

- **6 Projects**: 3 suspicious (risk 70-82), 3 clean (risk 15-28)
- **3 Critical Alerts**: Financial mismatch, duplicate evidence, geofence violations
- **6 Users**: Admin, 3 inspectors, officer, auditor
- **Inspector Assignments**:
  - INS-KA-001: 1 project (MPLADS-KA-2025-0456)
  - INS-KA-002: 2 projects (includes one suspicious)
  - INS-TS-003: 1 project (MPLADS-TS-2025-0123, suspicious)

## 🐛 Troubleshooting

### Frontend won't start
```bash
cd frontend
npm install
npm run dev
```

### Backend error on startup
```bash
cd backend
pip install -r requirements.txt
python app/seed.py  # Re-seed database if needed
```

### Port already in use
```bash
# Check what's using port 3000 or 8000
Get-NetTCPConnection -LocalPort 3000
Get-NetTCPConnection -LocalPort 8000

# Kill process if needed (replace PID)
Stop-Process -Id <PID> -Force
```

### Camera/GPS not working
- Ensure HTTPS or localhost (required for camera/GPS APIs)
- Check browser permissions (camera + location)
- Use Chrome DevTools Sensors tab to simulate GPS

### 403 Forbidden as Inspector
- **This is correct!** Inspectors can only access assigned projects
- Login as Admin to see all projects
- Check seed data to see which projects each inspector can access

## 📁 Important Files

### Backend Core
- `backend/app/main.py` - FastAPI entry point
- `backend/app/api/routes/inspections.py` - Live inspection workflow
- `backend/app/models/models.py` - Database schema
- `backend/tests/test_rbac_security.py` - RBAC tests

### Frontend Core
- `frontend/src/app/inspections/page.tsx` - Live inspection page
- `frontend/src/components/LiveCameraModal.tsx` - Camera + GPS modal
- `frontend/src/app/projects/[id]/page.tsx` - Forensic detail page
- `frontend/src/lib/api.ts` - API client

### Configuration
- `backend/.env.example` - Environment template
- `backend/requirements.txt` - Python dependencies
- `frontend/package.json` - Node dependencies

## 🎓 Tech Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.0, SQLite, JWT, bcrypt
- **Frontend**: Next.js 15, React 19, TypeScript 5, Tailwind CSS 3
- **APIs**: HTML5 getUserMedia, Geolocation, Canvas, Web Crypto (SHA-256)
- **Testing**: pytest, pytest-asyncio, httpx

## 📞 Support

For issues or questions:
1. Check `IMPLEMENTATION_SUMMARY.md` for detailed documentation
2. Review API docs at http://localhost:8000/docs
3. Run tests: `cd backend && pytest -v`
4. Check browser console for frontend errors (F12)

---

**Status**: ✅ Production-Ready  
**Last Updated**: 2026-09-08  
**Version**: 1.0.0 - SIH 2026 Demo
