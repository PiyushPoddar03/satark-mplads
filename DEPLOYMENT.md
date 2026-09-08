# 🚀 SATARK-MPLADS Cloud Deployment Guide

This guide details how to deploy **SATARK-MPLADS** to the internet. 

---

## 🌟 Architecture Overview

- **Frontend**: Next.js 16 (React 19, Tailwind CSS v4) $\to$ Deploy on **Vercel** (Free, instant global CDN)
- **Backend**: FastAPI (Python 3.11+, SQLAlchemy, Uvicorn) $\to$ Deploy on **Render**, **Railway**, or **Fly.io**
- **Database**: PostgreSQL on **Render**, **Neon.tech**, **Supabase**, or Railway (Free tiers available)

---

## ⚡ Method 1: The Recommended Free & Fast Cloud Stack (Vercel + Render)

### Step 1: Push your Code to GitHub

Open terminal in your project root (`satark-mplads`):

```bash
git init
git add .
git commit -m "feat: complete satark-mplads system"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/satark-mplads.git
git push -u origin main
```

---

### Step 2: Deploy Backend & Database on Render (Free)

1. Sign up / Log in to [Render.com](https://render.com).
2. Click **New +** $\to$ **Web Service**.
3. Connect your GitHub repository (`satark-mplads`).
4. Configure the Web Service:
   - **Name**: `satark-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Click **Advanced** $\to$ **Add Environment Variables**:
   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `SECRET_KEY` | *(generate a random 64-char string)* | JWT Signing Key |
   | `CORS_ORIGINS` | `*` | Allows your frontend Vercel domain |
   | `AI_MOCK_MODE` | `True` | AI Forensics engine mock simulation |
   | `DATABASE_URL` | `sqlite+aiosqlite:///./satark.db` *(or PostgreSQL URL)* | SQLite or Neon/Render PostgreSQL |
6. Click **Create Web Service**.
7. Wait ~2 minutes for the build to finish. Copy your live backend URL (e.g., `https://satark-backend.onrender.com`).
8. Verify by opening `https://satark-backend.onrender.com/api/health` in your browser. You should see:
   ```json
   {"status":"ok","app":"SATARK-MPLADS","version":"1.0.0"}
   ```

---

### Step 3: Deploy Frontend on Vercel (Free)

1. Sign up / Log in to [Vercel.com](https://vercel.com).
2. Click **Add New...** $\to$ **Project**.
3. Import your GitHub repository (`satark-mplads`).
4. In the configuration screen:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click **Edit** and select `frontend`.
5. Expand **Environment Variables** and add:
   | Variable | Value |
   | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | `https://satark-backend.onrender.com` *(your live Render backend URL from Step 2)* |
6. Click **Deploy**.
7. In ~1 minute, your site will be live on a global HTTPS URL (e.g., `https://satark-mplads.vercel.app`)! 🎉

---

## 🐳 Method 2: 1-Command Docker Compose (VPS / AWS EC2 / DigitalOcean)

If you have a Linux VPS (Ubuntu / Debian / AWS EC2):

1. **Clone the repository on your server**:
   ```bash
   git clone https://github.com/<YOUR_GITHUB_USERNAME>/satark-mplads.git
   cd satark-mplads
   ```

2. **Run with Docker Compose**:
   ```bash
   docker compose up -d --build
   ```

3. **Check status**:
   ```bash
   docker compose ps
   ```
   - Frontend is running at `http://<SERVER_IP>:3000`
   - Backend API is running at `http://<SERVER_IP>:8000`
   - Interactive Swagger API docs: `http://<SERVER_IP>:8000/docs`

---

## 🚂 Method 3: Railway 1-Click Full Stack

1. Log in to [Railway.app](https://railway.app).
2. Click **New Project** $\to$ **Deploy from GitHub Repo**.
3. Add a **PostgreSQL** database service in the canvas.
4. Add the **Backend** service pointing to `backend/` directory:
   - Set environment variable `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - Set `CORS_ORIGINS` = `*`
   - Start Command: `python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add the **Frontend** service pointing to `frontend/` directory:
   - Set `NEXT_PUBLIC_API_URL` = `https://${{Backend.RAILWAY_PUBLIC_DOMAIN}}`
6. Click **Deploy**.

---

## 🔑 Default Demo Credentials for Live Site

Once deployed, the database automatically seeds with default demonstration accounts:

| Role | Email | Password | Permissions & Dashboard Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@satark.gov.in` | `Admin@123` | Full access, project creation/deletion, inspector approval & management |
| **District Officer** | `officer.bangalore@satark.gov.in` | `Officer@123` | District project oversight, inspector summons directives, requests |
| **Field Inspector 1** | `inspector.rajesh@satark.gov.in` | `Inspector@123` | Live GPS camera capture, material expense bill upload & AI audit |
| **Field Inspector 2** | `inspector.priya@satark.gov.in` | `Inspector@123` | Assigned projects verification, bill uploads, summons response |
| **Auditor** | `auditor.cag@satark.gov.in` | `Auditor@123` | Read-only forensic audits, risk scores, immutable audit trail logs |

---

## 🛡️ Production Checklist

- [x] **CORS Origins**: Configured to support Vercel preview domains and production origins.
- [x] **Database Auto-Migration**: Automatic table creation on startup.
- [x] **Seed Data**: Automatic seeding of sample projects, forensic alerts, risk scores, and material price benchmarks.
- [x] **Hardware-Enforced GPS Geofencing**: Operates smoothly in browser via HTML5 Geolocation API.
- [x] **Dark / Light Mode**: Persistent across browser sessions.
