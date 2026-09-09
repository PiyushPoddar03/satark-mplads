---
title: SATARK-MPLADS
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# SATARK-MPLADS — Citizen & Authority Monitoring Platform

An evidence-driven monitoring and fraud/anomaly detection platform for the **MPLADS** (Members of Parliament Local Area Development Scheme).

## 🚀 Features

- **Evidence-Driven Inspections**: Geo-tagged photo/video verification, tamper checks, live camera capture with GPS validation.
- **AI-Powered Risk Scoring**: Real-time project risk assessment, deviation detection, duplicate image hash matching.
- **Automated Fraud Detection**: Geo-distance mismatch alerts, timeline anomaly warnings, material price inflation checks.
- **Auditing & Compliance**: Immutable audit trails, automated inspection summons, vendor expense bill tracking.
- **Interactive Dashboards**: Role-based views for Citizens, Inspectors, and Authorities with interactive Leaflet GIS maps.

## 🛠️ Architecture

- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS, Lucide Icons, Leaflet Maps.
- **Backend**: FastAPI, SQLAlchemy Async, SQLite / PostgreSQL, JWT Authentication.
- **Reverse Proxy**: NGINX (serving frontend on `/`, API on `/api/`, evidence on `/evidence/`, and Swagger at `/docs`).
- **Process Manager**: Supervisord running backend, frontend, and NGINX concurrently.
