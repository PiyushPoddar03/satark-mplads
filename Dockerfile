FROM node:20-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./

# An empty URL makes the browser call the same public Space URL. nginx then
# routes /api and /evidence to FastAPI.
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build


FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=7860 \
    DATABASE_URL=sqlite+aiosqlite:////data/satark.db \
    DATABASE_URL_SYNC=sqlite:////data/satark.db \
    EVIDENCE_STORAGE_PATH=/data/evidence \
    CORS_ORIGINS=*

WORKDIR /srv/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev nginx supervisor curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
COPY backend/ ./

# The official Node image supplies Node 20 and its shared libraries, required
# by Next.js at runtime.
COPY --from=frontend-build /usr/local /usr/local
COPY --from=frontend-build /build/frontend/.next /srv/frontend/.next
COPY --from=frontend-build /build/frontend/public /srv/frontend/public
COPY --from=frontend-build /build/frontend/node_modules /srv/frontend/node_modules
COPY --from=frontend-build /build/frontend/package.json /srv/frontend/package.json

COPY hf/nginx.conf /etc/nginx/conf.d/default.conf
COPY hf/supervisord.conf /etc/supervisor/conf.d/satark.conf

RUN mkdir -p /data/evidence /var/log/supervisor

EXPOSE 7860
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
