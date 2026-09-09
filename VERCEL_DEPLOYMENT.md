# Deploy the SATARK dashboard to Vercel

After the Render Blueprint finishes creating `satark-backend`, copy its public
URL (for example `https://satark-backend.onrender.com`).

1. Import `PiyushPoddar03/satark-mplads` in Vercel.
2. Set the project **Root Directory** to `frontend`.
3. Add the environment variable below for Production, Preview, and Development:

   ```text
   NEXT_PUBLIC_API_URL=https://YOUR-RENDER-BACKEND.onrender.com
   ```

4. Deploy and open the Vercel URL. The API health check should be available at
   `https://YOUR-RENDER-BACKEND.onrender.com/api/health`.

The Render free tier is suitable for this demo but can sleep when idle. Its free
Postgres database expires after 30 days, so export important data before then.
