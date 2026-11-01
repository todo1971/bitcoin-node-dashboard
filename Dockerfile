# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
FROM python:3.11-slim-bookworm

ARG DASHBOARD_UID=1010
ARG DASHBOARD_GID=1010
ARG APP_VERSION=1.21.2

LABEL org.opencontainers.image.licenses="GPL-3.0-only" \
      org.opencontainers.image.authors="Hardy (todo1971) <hb@308-arms.de>" \
      org.opencontainers.image.title="Bitcoin Node Dashboard" \
      org.opencontainers.image.description="Read-only monitoring dashboard for Bitcoin Core" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/todo1971/bitcoin-node-dashboard"

RUN groupadd --gid "${DASHBOARD_GID}" dashboard \
    && useradd --uid "${DASHBOARD_UID}" --gid dashboard \
        --home-dir /app --shell /usr/sbin/nologin dashboard \
    && install -d -o dashboard -g dashboard -m 0750 /var/lib/bitcoin-dashboard

WORKDIR /app
COPY --chown=dashboard:dashboard app.py ./
COPY --chown=dashboard:dashboard LICENSE NOTICE ./
COPY --chown=dashboard:dashboard static ./static

USER dashboard:dashboard
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DASHBOARD_HOST=0.0.0.0 \
    DASHBOARD_PORT=8787 \
    DATABASE_PATH=/var/lib/bitcoin-dashboard/history.sqlite3 \
    ADMIN_UPDATES_ENABLED=0

EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=8s --start-period=30s --retries=3 \
  CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/healthz', timeout=5).read()"]

CMD ["python3", "/app/app.py"]
