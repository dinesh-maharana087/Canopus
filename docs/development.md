# Development

Device Watch is three independent projects. Install and run them separately; no component silently selects the development database.

## Agent

PowerShell:

```powershell
uv sync --project agent --frozen
$env:DEVICE_WATCH_AGENT_MODE = 'service'
$env:DEVICE_WATCH_AGENT_INTERVAL_SECONDS = '30'
uv run --project agent python -m device_watch_agent
uv run --project agent pytest agent/tests -q
```

POSIX shell:

```sh
uv sync --project agent --frozen
export DEVICE_WATCH_AGENT_MODE=service
export DEVICE_WATCH_AGENT_INTERVAL_SECONDS=30
uv run --project agent python -m device_watch_agent
uv run --project agent pytest agent/tests -q
```

Stage 1 starts an empty registry, waits for a stop signal, and performs no collection or communication. The configuration requires `DEVICE_WATCH_AGENT_MODE=service`; the interval defaults to `30.0` seconds and must be positive.

## Server

PowerShell:

```powershell
uv sync --project server --frozen
$env:DEVICE_WATCH_ENV = 'development'
$env:DATABASE_URL = 'mysql+pymysql://<user>:<password>@127.0.0.1:3307/device_watch'
uv run --project server uvicorn device_watch_server.main:app --reload
uv run --project server pytest server/tests/unit -q
uv run --project server ruff check server/src server/tests
uv run --project server mypy server/src
uv run --project server device-watch-db-check
uv run --project server alembic -c server/alembic.ini upgrade head
uv run --project server alembic -c server/alembic.ini current
```

POSIX shell:

```sh
uv sync --project server --frozen
export DEVICE_WATCH_ENV=development
export DATABASE_URL='mysql+pymysql://<user>:<password>@127.0.0.1:3307/device_watch'
uv run --project server uvicorn device_watch_server.main:app --reload
uv run --project server pytest server/tests/unit -q
uv run --project server ruff check server/src server/tests
uv run --project server mypy server/src
uv run --project server device-watch-db-check
uv run --project server alembic -c server/alembic.ini upgrade head
uv run --project server alembic -c server/alembic.ini current
```

The server requires `DEVICE_WATCH_ENV` and `DATABASE_URL`; it has no development-database fallback. At Stage 1 completion, the server exposed only `GET /api/v1/health/live` and `GET /api/v1/health/ready`. The current partial Stage 2 foundation has not added a public enrollment, heartbeat, or device API route.

## Web

```powershell
npm --prefix web ci
npm --prefix web run dev
npm --prefix web run test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

```sh
npm --prefix web ci
npm --prefix web run dev
npm --prefix web run test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

Vite proxies `/api` to `http://127.0.0.1:8000` in development without rewriting the path. Set `VITE_API_PROXY_TARGET` only when a different local server address is intentional. Caddy, certificates, and production TLS are unnecessary for native local web development.

## Optional MySQL

Docker Compose is optional for native development and is isolated to the development file:

```powershell
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml up -d --wait mysql
$env:DEVICE_WATCH_ENV = 'test'
$env:DATABASE_URL = 'mysql+pymysql://device_watch_dev:device_watch_dev@127.0.0.1:3307/device_watch'
uv run --project server pytest server/tests/integration -q
```

The opt-in server image smoke check uses the `verification` profile and service-name URL:

```powershell
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml --profile verification up -d --build --wait server-smoke
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml --profile verification ps server-smoke
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml down
```

MySQL binds only to `127.0.0.1:3307`; `server-smoke` is portless and does not start with the normal MySQL-only command.
