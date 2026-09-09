# Free deployment: Supabase + Vercel

This deployment uses two Vercel projects and one Supabase project:

- `backend/` → Vercel FastAPI API
- `frontend/` → Vercel Next.js dashboard
- Supabase → PostgreSQL database and persistent evidence-file storage

## 1. Create Supabase resources

Create a free Supabase project, then in **Storage** create a private bucket
named `satark-evidence`. In **Connect**, copy the **Transaction pooler** URI
(port `6543`) and in **Settings → API** copy the project URL and `service_role`
key. The service-role key belongs only in Vercel's backend environment settings.

## 2. Deploy the API Vercel project

Import this GitHub repository and set **Root Directory** to `backend`. Add each
variable for Production, Preview, and Development:

```text
DATABASE_URL=<Supabase transaction-pooler URI>
SUPABASE_URL=<Supabase project URL>
SUPABASE_SERVICE_ROLE_KEY=<Supabase service_role key>
SUPABASE_STORAGE_BUCKET=satark-evidence
SERVERLESS=true
SECRET_KEY=<new random 64+ character value>
CORS_ORIGINS=*
AI_MOCK_MODE=true
```

Deploy it and confirm `https://YOUR-API.vercel.app/api/health` responds with
`{"status":"ok", ...}`.

## 3. Deploy the dashboard Vercel project

Import the same repository again, with **Root Directory** set to `frontend`.
Set this variable for all environments:

```text
NEXT_PUBLIC_API_URL=https://YOUR-API.vercel.app
```

Deploy, then sign in with `admin@satark.gov.in` and `admin123`.

The Supabase free tier includes 500 MB PostgreSQL and 1 GB file storage, but
pauses inactive projects after one week. Vercel's Python runtime runs FastAPI
as a serverless function, so startup may be slower after inactivity.
