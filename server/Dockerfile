FROM ghcr.io/astral-sh/uv:0.12.6 AS uv
FROM python:3.12.6-slim-bookworm AS builder

COPY --from=uv /uv /uvx /bin/
WORKDIR /build
COPY server/pyproject.toml server/uv.lock ./server/
COPY server/src ./server/src
RUN uv sync --project server --frozen --no-dev

FROM python:3.12.6-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /build/server/.venv /opt/venv
COPY server/src ./src
COPY server/alembic ./alembic
COPY server/alembic.ini ./alembic.ini
RUN groupadd --system --gid 10001 devicewatch \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --no-create-home devicewatch \
    && chown -R devicewatch:devicewatch /app /opt/venv
USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=3)"]
CMD ["uvicorn", "device_watch_server.main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
