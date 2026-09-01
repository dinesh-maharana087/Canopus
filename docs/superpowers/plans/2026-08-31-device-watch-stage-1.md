# Device Watch Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a secure, bootable Device Watch foundation containing an independently runnable native agent, FastAPI service, React shell, MySQL migration foundation, and Caddy-only production ingress without implementing monitoring business workflows.

**Architecture:** The monorepo keeps the agent, server, and web application as separate installable projects. In production, Caddy is the sole public service and serves the compiled SPA while forwarding path-preserved `/api/*` requests to a private FastAPI container; FastAPI connects only through the required `DATABASE_URL` to an externally administered MySQL 8.x service. Local development remains native HTTP with Vite proxying `/api` and an optional, development-only MySQL Compose service.

**Tech Stack:** Python 3.12, FastAPI 0.141.1, Pydantic Settings 2.15.0, SQLAlchemy 2.0.52, Alembic 1.19.1, PyMySQL 1.2.0, Uvicorn 0.52.4, React 19.2.8, React Router 8.3.1, TypeScript, Vite 8.2.2, Tailwind CSS 4.3.3, MySQL 8.4.11, Caddy 2.11.4, Docker Compose, pytest, Vitest, Ruff, mypy, ESLint.

**Spec:** `docs/superpowers/specs/2026-08-31-device-watch-stage-1-design.md`

## Global Constraints

- Repository boundaries are exactly `agent/`, `server/`, `web/`, `deploy/`, and `docs/`; agent and server have separate `pyproject.toml` and `uv.lock` files, and web has its own `package.json` and `package-lock.json`.
- MySQL 8.x is the sole database target. `DATABASE_URL` is required, has no fallback, and must use `mysql+pymysql`.
- `DEVICE_WATCH_ENV` is required and accepts exactly `development`, `test`, or `production`; production startup must fail before engine creation when required configuration is missing or unsafe.
- Production accepts only a URL query containing the three unique entries `ssl_ca=/run/secrets/mysql-ca.pem`, `ssl_verify_cert=true`, and `ssl_verify_identity=true`; duplicate or additional production query keys are rejected. The effective PyMySQL connection arguments must contain boolean `True` values for both verification flags.
- The SQLAlchemy 2.0.52 and PyMySQL 1.2.0 URL translation behavior is locked by an automated characterization test. Regardless of that result, production engine creation supplies validated boolean TLS values through `connect_args` and never weakens certificate or hostname verification.
- Connection URLs, credentials, request bodies, authorization headers, and cookies must never be logged, represented, or returned by an API response.
- Stage 1 exposes only `GET /api/v1/health/live` and `GET /api/v1/health/ready`; it creates no business routes, domain tables, concrete collectors, sender, sample monitoring data, or partial future workflow.
- The baseline Alembic revision is schema-empty and must be verified against real MySQL with `upgrade head`, `downgrade base`, and `upgrade head`.
- The agent has no runtime dependency outside the Python standard library, boots with an empty collector registry, performs no collection or communication, and shuts down cleanly on a requested stop or normal termination signal.
- The frontend has exactly Dashboard, Devices, Alerts, Inventory, and Settings route boundaries. Each page contains its title and `Not implemented in Stage 1`; it performs no business API request and displays no fabricated monitoring state.
- Production Compose contains exactly `caddy` and `server`; only Caddy publishes TCP ports 80 and 443, FastAPI has no published host port, and MySQL remains external.
- Caddy reads the required domain from `DEVICE_WATCH_DOMAIN`, manages public TLS, persists `/data` and `/config`, preserves `/api/*`, targets exactly `server:8000`, and serves the SPA from static build output in a final image with no Node runtime.
- Production Uvicorn may trust forwarded headers from all addresses only while topology verification proves that its project network has exactly Caddy and FastAPI and that FastAPI has no published port.
- Local development uses HTTP, native FastAPI and Vite processes, no Caddy, and no certificate setup. The optional MySQL development service is separate from production and loopback-bound.
- Frozen lock files and exact container tags are committed; build and verification commands must consume the locks rather than resolving floating dependencies.
- Never commit live credentials, private keys, certificate state, local environment files, virtual environments, dependency directories, build artifacts, coverage output, or local database files.

---

## File Map

```text
.
|-- .editorconfig                    Repository text conventions
|-- .dockerignore                    Root-context image allowlist
|-- .env.example                     Non-secret root configuration index
|-- .gitignore                       Generated/private file exclusions
|-- README.md                        Operator and developer entry point
|-- agent/
|   |-- .env.example                 Agent-only sample settings
|   |-- pyproject.toml               Independent agent package and tools
|   |-- uv.lock                      Frozen agent environment
|   |-- src/device_watch_agent/
|   |   |-- __init__.py
|   |   |-- __main__.py              `python -m device_watch_agent`
|   |   |-- config.py                Strict environment parsing
|   |   |-- lifecycle.py             Signal-aware asynchronous loop
|   |   |-- logging.py               Standard-library JSON logging
|   |   |-- main.py                  Registry assembly and process entry
|   |   `-- collectors/
|   |       |-- __init__.py
|   |       |-- contracts.py         Collector protocol and result types
|   |       `-- registry.py          Unique-name collector registry
|   `-- tests/                        Agent unit and lifecycle tests
|-- server/
|   |-- Dockerfile                   Locked, non-root runtime image
|   |-- alembic.ini                  Alembic entry configuration
|   |-- pyproject.toml               Independent API package and tools
|   |-- uv.lock                      Frozen API environment
|   |-- alembic/
|   |   |-- env.py                   Shared settings and metadata bridge
|   |   |-- script.py.mako           Revision template
|   |   `-- versions/
|   |       `-- 20260831_0001_baseline.py  Schema-empty baseline
|   |-- src/device_watch_server/
|   |   |-- __init__.py
|   |   |-- app.py                   Application factory and lifespan
|   |   |-- cli.py                   Database connectivity command
|   |   |-- main.py                  Factory-created ASGI export
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- health.py            Liveness and readiness handlers
|   |   |   `-- router.py            Versioned health-only router
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py            Required settings and TLS validation
|   |   |   |-- logging.py           JSON logging and redaction
|   |   |   `-- middleware.py        Safe request completion logging
|   |   `-- db/
|   |       |-- __init__.py
|   |       |-- base.py              Empty naming-convention metadata
|   |       |-- engine.py            Engine construction and TLS args
|   |       `-- health.py            `SELECT 1` connectivity contract
|   `-- tests/
|       |-- conftest.py
|       |-- unit/                     Settings, app, logging, and CLI tests
|       `-- integration/              Real MySQL and Alembic tests
|-- web/
|   |-- eslint.config.js
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   |-- tsconfig.app.json
|   |-- tsconfig.json
|   |-- tsconfig.node.json
|   |-- vite.config.ts                Dev `/api` proxy and test config
|   `-- src/
|       |-- app/App.tsx               Router provider
|       |-- app/routes.tsx            Five route boundaries
|       |-- components/layout/        Responsive application shell
|       |-- components/ui/Button.tsx  Local accessible primitive
|       |-- main.tsx
|       |-- pages/                     Explicit Stage 1 pages
|       |-- styles.css                 Tailwind import and design tokens
|       |-- test/setup.ts
|       `-- theme/ThemeProvider.tsx    System/light/dark persistence
|-- deploy/
|   |-- .env.dev.example              Opt-in development values
|   |-- .env.prod.example             Required-production shape only
|   |-- compose.dev.yml               Development MySQL and smoke profile
|   |-- compose.prod.yml              Caddy and FastAPI only
|   |-- verify_repository.py          Dependency, secret, and scope audit
|   |-- verify_topology.py            Rendered Compose/Caddy assertions
|   |-- caddy/
|   |   |-- Caddyfile                 Small HTTPS/static/proxy policy
|   |   `-- Dockerfile                Node build stage, Caddy runtime stage
|   |-- systemd/
|   |   `-- device-watch-agent.service Native agent unit example
|   `-- tests/                         Executable deployment-verifier tests
`-- docs/
    |-- architecture.md
    |-- deployment.md
    |-- development.md
    `-- future-contracts.md
```

### Task 1: Repository Baseline and Independent Dependency Locks

**Files:**
- Create: `.editorconfig`
- Create: `.dockerignore`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `agent/pyproject.toml`
- Create: `agent/uv.lock`
- Create: `server/pyproject.toml`
- Create: `server/uv.lock`
- Create: `web/package.json`
- Create: `web/package-lock.json`

**Interfaces:**
- Consumes: approved design spec and exact dependency versions in Global Constraints.
- Produces: independently resolvable `device-watch-agent`, `device-watch-server`, and `device-watch-web` projects; console scripts `device-watch-agent` and `device-watch-db-check`; deterministic verification toolchains.

- [ ] **Step 1: Record a clean baseline and tool availability**

Run:

```powershell
git status --short --branch
python --version
node --version
npm --version
uv --version
docker version
docker compose version
```

Expected: the approved design is the only committed project artifact, Python and Node meet the pinned project requirements, and missing `uv` or Docker is recorded as an environment prerequisite rather than hidden.

- [ ] **Step 2: Add root safeguards and minimal project manifests**

Use `.gitignore` entries for `.env`, `.env.*` except `*.example`, `*.pem`, `*.key`, `.venv/`, `.tmp/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `dist/`, `coverage/`, `.coverage`, `.worktrees/`, `.superpowers/`, `.ai-memory/`, and interrupted-recovery metadata. Set UTF-8, LF, final newline, and four-space Python/two-space web indentation in `.editorconfig`.

Because both Dockerfiles use the repository root as build context, the root `.dockerignore` begins with `**` and re-includes only the exact server package/migration/lock inputs, exact web source/config/lock inputs, and `deploy/caddy/Caddyfile`. It never re-includes environment files, certificates, keys, tests, VCS metadata, caches, or build output.

The agent runtime dependency table remains empty. The server runtime table pins:

```toml
dependencies = [
  "alembic==1.19.1",
  "fastapi==0.141.1",
  "pydantic-settings==2.15.0",
  "pymysql==1.2.0",
  "sqlalchemy==2.0.52",
  "uvicorn==0.52.4",
]
```

Both Python projects use a `test` dependency group with `pytest==9.1.1`, `pytest-asyncio==1.4.0`, `ruff==0.16.4`, and `mypy==2.3.1`; server additionally includes `httpx` at the exact version resolved into its lock. Configure pytest markers so `integration` is declared and unit runs can exclude it without warnings.

- [ ] **Step 3: Generate frozen dependency locks**

Run:

```powershell
uv lock --project agent
uv lock --project server
npm --prefix web install --package-lock-only --ignore-scripts
```

Expected: two independent `uv.lock` files and one npm lock are created; the agent runtime package graph contains no server package.

- [ ] **Step 4: Verify dependency separation and manifest syntax**

Run:

```powershell
uv sync --project agent --frozen
uv sync --project server --frozen
uv tree --project agent --no-dev
uv tree --project server --no-dev
npm --prefix web ci --ignore-scripts
```

Expected: each frozen environment resolves independently and the agent runtime tree contains only the agent package plus Python standard-library imports.

- [ ] **Step 5: Commit the repository baseline**

```powershell
git add .editorconfig .dockerignore .gitignore .env.example README.md agent/pyproject.toml agent/uv.lock server/pyproject.toml server/uv.lock web/package.json web/package-lock.json
git commit -m "build: establish independent project foundations"
```

### Task 2: Server Configuration and Verified MySQL TLS Boundary

**Files:**
- Create: `server/src/device_watch_server/__init__.py`
- Create: `server/src/device_watch_server/core/__init__.py`
- Create: `server/src/device_watch_server/core/config.py`
- Create: `server/src/device_watch_server/db/__init__.py`
- Create: `server/src/device_watch_server/db/engine.py`
- Create: `server/tests/conftest.py`
- Create: `server/tests/unit/test_config.py`
- Create: `server/tests/unit/test_engine_tls.py`

**Interfaces:**
- Consumes: environment variables `DEVICE_WATCH_ENV`, `DATABASE_URL`, and optional `DEVICE_WATCH_ENABLE_DOCS`.
- Produces: `Environment(str, Enum)`, immutable `Settings` with `database_url: SecretStr`, `load_settings() -> Settings`, `database_engine_url(settings: Settings) -> URL`, `validated_connect_args(settings: Settings) -> dict[str, object]`, and `create_database_engine(settings: Settings) -> Engine`.

- [ ] **Step 1: Write strict-settings tests before settings code**

Cover these independent behaviors with literal inputs:

```python
def test_missing_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None: ...
def test_missing_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None: ...
def test_non_mysql_pymysql_dialect_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None: ...
def test_environment_accepts_only_three_named_modes(monkeypatch: pytest.MonkeyPatch) -> None: ...
def test_settings_repr_does_not_expose_database_credentials() -> None: ...
def test_invalid_url_error_does_not_expose_database_credentials() -> None: ...
def test_production_requires_exact_ca_path_and_true_verification_flags() -> None: ...
def test_production_rejects_duplicate_or_additional_query_keys() -> None: ...
def test_production_rejects_enabled_api_documentation() -> None: ...
def test_development_can_omit_tls_for_isolated_database() -> None: ...
```

The wrong-dialect fixture uses a syntactically malformed or unsupported `mysql://` form and never introduces another database implementation into project text.

- [ ] **Step 2: Run settings tests and verify the red state**

Run:

```powershell
uv run --project server pytest server/tests/unit/test_config.py -q
```

Expected: collection fails because `device_watch_server.core.config` does not exist.

- [ ] **Step 3: Implement immutable settings and URL validation**

Implement `Settings` with `SettingsConfigDict(env_prefix="", extra="forbid", frozen=True)` and required fields. Parse the URL with `sqlalchemy.engine.make_url`; require `url.drivername == "mysql+pymysql"`. In production, use `urllib.parse.parse_qsl(..., keep_blank_values=True)` to retain duplicate query keys, require the query multimap to contain exactly one value for each key in this literal map and no other key, and reject enabled API documentation before any engine exists:

```python
PRODUCTION_TLS_QUERY = {
    "ssl_ca": "/run/secrets/mysql-ca.pem",
    "ssl_verify_cert": "true",
    "ssl_verify_identity": "true",
}
```

Store `database_url: SecretStr`. Catch lower-level URL parsing errors and raise a fixed validation message that names `DATABASE_URL` but never includes its value; `repr(settings)`, structured logs, CLI output, and validation exceptions must remain credential-free.

- [ ] **Step 4: Run settings tests and verify green**

Run:

```powershell
uv run --project server pytest server/tests/unit/test_config.py -q
```

Expected: all settings cases pass with no warnings.

- [ ] **Step 5: Write the locked SQLAlchemy-to-PyMySQL characterization test**

Create an engine URL with the exact locked package versions and call the dialect boundary directly:

```python
def test_locked_sqlalchemy_pymysql_url_translation_characterization() -> None:
    url = make_url(
        "mysql+pymysql://user:secret@db:3306/device_watch"
        "?ssl_ca=%2Frun%2Fsecrets%2Fmysql-ca.pem"
        "&ssl_verify_cert=true&ssl_verify_identity=true"
    )
    dialect = MySQLDialect_pymysql()
    _, translated = dialect.create_connect_args(url)

    assert importlib.metadata.version("SQLAlchemy") == "2.0.52"
    assert importlib.metadata.version("PyMySQL") == "1.2.0"
    assert translated["ssl"] == {"ca": "/run/secrets/mysql-ca.pem"}
    assert translated["ssl_verify_cert"] == "true"
    assert translated["ssl_verify_identity"] == "true"
```

This test deliberately captures SQLAlchemy 2.0.52 moving `ssl_ca` into a nested `ssl` mapping while retaining both verification flags as strings. If a future lock changes that complete TLS shape, the test must fail and force a review of the effective connection policy.

- [ ] **Step 6: Write the effective driver-argument security tests**

Test the application boundary rather than trusting URL translation:

```python
def test_production_connect_args_use_boolean_certificate_and_identity_checks(
    production_settings: Settings,
) -> None:
    assert validated_connect_args(production_settings) == {
        "ssl_ca": "/run/secrets/mysql-ca.pem",
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    }


def test_engine_passes_validated_tls_values_to_pymysql(
    production_settings: Settings,
) -> None:
    class ConnectionIntercepted(Exception):
        pass

    captured: dict[str, object] = {}
    engine = create_database_engine(production_settings)

    @event.listens_for(engine, "do_connect")
    def capture_effective_parameters(
        dialect: Dialect,
        connection_record: ConnectionPoolEntry,
        positional: list[object],
        keyword: dict[str, object],
    ) -> None:
        del dialect, connection_record, positional
        captured.update(keyword)
        raise ConnectionIntercepted

    with pytest.raises(ConnectionIntercepted):
        engine.connect()

    assert captured["ssl_ca"] == "/run/secrets/mysql-ca.pem"
    assert captured["ssl_verify_cert"] is True
    assert captured["ssl_verify_identity"] is True
    assert "ssl" not in captured
    engine.dispose()
```

The `do_connect` event capture observes final connection parameters immediately before PyMySQL receives them, raises a sentinel exception before network I/O, and asserts the real SQLAlchemy event payload rather than a mock call.

- [ ] **Step 7: Run TLS tests and verify the red state**

Run:

```powershell
uv run --project server pytest server/tests/unit/test_engine_tls.py -q
```

Expected: failures name the absent `validated_connect_args` and `create_database_engine` behaviors while the upstream characterization result is visible.

- [ ] **Step 8: Implement centralized engine construction**

`validated_connect_args` returns an empty mapping outside production and the exact flat PyMySQL mapping in production only after settings validation succeeded. Before engine creation, `database_engine_url(settings)` removes the three already-validated TLS keys from the SQLAlchemy URL so URL translation cannot create a competing nested `ssl` mapping. All credentials, endpoint, port, and database selection still originate exclusively in `DATABASE_URL`. `create_database_engine` calls:

```python
create_engine(
    database_engine_url(settings),
    pool_pre_ping=True,
    pool_recycle=1_800,
    connect_args=validated_connect_args(settings),
)
```

Never convert verification values with generic truthiness such as `bool("false")`. The effective-parameter test must assert the complete TLS key set is exactly `ssl_ca`, `ssl_verify_cert`, and `ssl_verify_identity`, with no nested `ssl` value and no string verification flag.

- [ ] **Step 9: Run all configuration and engine tests**

Run:

```powershell
uv run --project server pytest server/tests/unit/test_config.py server/tests/unit/test_engine_tls.py -q
uv run --project server mypy server/src
uv run --project server ruff check server/src server/tests/unit/test_config.py server/tests/unit/test_engine_tls.py
```

Expected: tests, types, and lint pass without output containing connection credentials.

- [ ] **Step 10: Commit the secure configuration boundary**

```powershell
git add server/src server/tests/conftest.py server/tests/unit/test_config.py server/tests/unit/test_engine_tls.py
git commit -m "feat(server): enforce verified MySQL configuration"
```

### Task 3: FastAPI Boot, Health, Logging, and Database Check

**Files:**
- Create: `server/src/device_watch_server/api/__init__.py`
- Create: `server/src/device_watch_server/api/health.py`
- Create: `server/src/device_watch_server/api/router.py`
- Create: `server/src/device_watch_server/app.py`
- Create: `server/src/device_watch_server/cli.py`
- Create: `server/src/device_watch_server/core/logging.py`
- Create: `server/src/device_watch_server/core/middleware.py`
- Create: `server/src/device_watch_server/db/health.py`
- Create: `server/src/device_watch_server/main.py`
- Create: `server/tests/unit/test_app.py`
- Create: `server/tests/unit/test_cli.py`
- Create: `server/tests/unit/test_logging.py`

**Interfaces:**
- Consumes: `Settings`, `create_database_engine(settings)`, and an injected `DatabaseCheck = Callable[[], None]`.
- Produces: `check_database(engine: Engine) -> None`, `create_app(settings: Settings | None = None, database_check: DatabaseCheck | None = None) -> FastAPI`, `main() -> int` for the database check, and module-level `app` in `device_watch_server.main`.

- [ ] **Step 1: Write API behavior tests first**

Use `TestClient` with explicit test settings and real route dispatch. Cover:

```python
def test_liveness_returns_process_status_without_calling_database() -> None: ...
def test_readiness_returns_200_when_select_one_succeeds() -> None: ...
def test_readiness_returns_generic_503_when_database_fails() -> None: ...
def test_only_two_stage_one_routes_are_registered() -> None: ...
def test_production_disables_openapi_routes() -> None: ...
def test_lifespan_disposes_owned_engine() -> None: ...
```

Assert exact response bodies such as `{"status": "ok"}` and `{"status": "unavailable"}`; failure responses contain neither exception text nor URLs.

- [ ] **Step 2: Run API tests and verify the red state**

Run:

```powershell
uv run --project server pytest server/tests/unit/test_app.py -q
```

Expected: import failures identify the missing application factory and health modules.

- [ ] **Step 3: Implement the smallest health-only FastAPI app**

Use a Pydantic response model:

```python
class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
```

Register only the two health handlers under `/api/v1/health`. `check_database` runs `connection.execute(text("SELECT 1"))` inside `engine.connect()`. The app lifespan owns an engine only when one was constructed internally and always calls `dispose()` on shutdown. Production docs URLs are `None`; development docs remain under `/api/docs`, `/api/redoc`, and `/api/openapi.json` only when explicitly enabled.

- [ ] **Step 4: Add failing CLI and structured-log tests**

Cover database-check exit `0` on success and nonzero on failure, generic stderr output, one-line JSON records, request method/path/status/duration, and redaction of URL credentials, authorization, cookies, request bodies, and exception details from public output.

- [ ] **Step 5: Run CLI and logging tests and verify the red state**

Run:

```powershell
uv run --project server pytest server/tests/unit/test_cli.py server/tests/unit/test_logging.py -q
```

Expected: failures identify missing CLI and logging functions.

- [ ] **Step 6: Implement safe JSON logging, middleware, and CLI**

The middleware emits only `event`, `method`, normalized path, integer status, and duration. The readiness handler catches the dependency exception, emits only the fixed warning event `database_readiness_failed` without exception text or traceback, and returns a generic response. The CLI constructs settings and an engine, calls `check_database`, disposes the engine in `finally`, and prints only `database connectivity: ok` or `database connectivity: unavailable`. Tests capture every log and CLI stream with a synthetic credential-bearing exception and assert that the username, password, full URL, and exception detail never appear.

- [ ] **Step 7: Verify the complete server unit slice**

Run:

```powershell
$env:DEVICE_WATCH_ENV='test'
$env:DATABASE_URL='mysql+pymysql://device_watch_test:sample@127.0.0.1:3307/device_watch'
uv run --project server pytest server/tests/unit -q
uv run --project server ruff check server/src server/tests
uv run --project server mypy server/src
```

Expected: unit suite, lint, and types pass; no test attempts a network connection unless marked `integration`.

- [ ] **Step 8: Commit the bootable API foundation**

```powershell
git add server/src server/tests/unit
git commit -m "feat(server): add health-only FastAPI foundation"
```

### Task 4: Alembic Baseline and Real MySQL Verification

**Files:**
- Create: `deploy/.env.dev.example`
- Create: `deploy/compose.dev.yml`
- Create: `deploy/tests/test_development_mysql.py`
- Create: `server/src/device_watch_server/db/base.py`
- Create: `server/alembic.ini`
- Create: `server/alembic/env.py`
- Create: `server/alembic/script.py.mako`
- Create: `server/alembic/versions/20260831_0001_baseline.py`
- Create: `server/tests/integration/test_database.py`
- Create: `server/tests/integration/test_migrations.py`

**Interfaces:**
- Consumes: `load_settings()`, `validated_connect_args(settings)`, and `Base.metadata` with no business tables.
- Produces: a loopback-bound development-only MySQL 8.4.11 service, revision identifier `20260831_0001`, a live `SELECT 1` integration test, and a migration cycle asserting head, base, and head against MySQL 8.x.

- [ ] **Step 1: Write the minimal development-MySQL topology test first**

Test a rendered configuration dictionary that requires exactly one initial service named `mysql`, image `mysql:8.4.11`, loopback-only host binding `127.0.0.1:3307:3306`, a health check, development-only named volume `mysql_dev_data`, and conspicuous sample credentials loaded only from `deploy/.env.dev.example`. Assert the production Compose path is not read or extended.

- [ ] **Step 2: Run the development-MySQL test and verify red**

Run:

```powershell
uv run --project server pytest deploy/tests/test_development_mysql.py -q
```

Expected: failure identifies the absent development Compose file.

- [ ] **Step 3: Implement and start the isolated development database**

Create the one-service development Compose file and sample env file, render it with `docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml config --format json`, then run:

```powershell
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml up -d --wait mysql
```

Expected: the development-only MySQL 8.4.11 service becomes healthy on loopback port 3307. No server or Caddy service is present yet.

- [ ] **Step 4: Write integration tests before Alembic configuration**

Mark both tests with `pytest.mark.integration`. `test_database.py` constructs the real engine from environment settings and executes `SELECT 1`. `test_migrations.py` invokes Alembic's Python API with `Config("server/alembic.ini")`, asserts the database current revision after `upgrade("head")`, `downgrade("base")`, and a second `upgrade("head")`, and verifies that `Base.metadata.tables == {}`.

- [ ] **Step 5: Run integration tests against the configured MySQL and verify red**

Run after the development database is available:

```powershell
$env:DEVICE_WATCH_ENV='test'
$env:DATABASE_URL='mysql+pymysql://device_watch_dev:device_watch_dev@127.0.0.1:3307/device_watch'
uv run --project server pytest server/tests/integration -q
```

Expected: the connectivity case can pass only when MySQL is reachable; the migration case fails because Alembic files do not exist.

- [ ] **Step 6: Implement shared metadata and Alembic environment**

Define a `DeclarativeBase` subclass with a deterministic naming convention and no mapped class. In online mode, use the already validated URL and `connect_args`; in offline mode, configure the same URL without making a connection. Keep `sqlalchemy.url` empty in `alembic.ini` so there is no second configuration source.

- [ ] **Step 7: Add the schema-empty baseline revision**

The revision body is exactly behavior-free:

```python
revision = "20260831_0001"
down_revision = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

Only Alembic's own version table may appear in MySQL after upgrade.

- [ ] **Step 8: Run and record the full real migration cycle**

Run:

```powershell
uv run --project server pytest server/tests/integration -q
uv run --project server alembic -c server/alembic.ini upgrade head
uv run --project server alembic -c server/alembic.ini current
uv run --project server alembic -c server/alembic.ini downgrade base
uv run --project server alembic -c server/alembic.ini current
uv run --project server alembic -c server/alembic.ini upgrade head
uv run --project server alembic -c server/alembic.ini current
```

Expected: `20260831_0001`, no revision, and `20260831_0001` in that order.

- [ ] **Step 9: Commit migration infrastructure**

```powershell
git add deploy/.env.dev.example deploy/compose.dev.yml deploy/tests/test_development_mysql.py server/alembic.ini server/alembic server/src/device_watch_server/db/base.py server/tests/integration
git commit -m "feat(server): add schema-empty MySQL migration baseline"
```

### Task 5: Lightweight Native Agent Foundation

**Files:**
- Create: `agent/.env.example`
- Create: `agent/src/device_watch_agent/__init__.py`
- Create: `agent/src/device_watch_agent/__main__.py`
- Create: `agent/src/device_watch_agent/config.py`
- Create: `agent/src/device_watch_agent/logging.py`
- Create: `agent/src/device_watch_agent/lifecycle.py`
- Create: `agent/src/device_watch_agent/main.py`
- Create: `agent/src/device_watch_agent/collectors/__init__.py`
- Create: `agent/src/device_watch_agent/collectors/contracts.py`
- Create: `agent/src/device_watch_agent/collectors/registry.py`
- Create: `agent/tests/test_config.py`
- Create: `agent/tests/test_contracts.py`
- Create: `agent/tests/test_registry.py`
- Create: `agent/tests/test_lifecycle.py`

**Interfaces:**
- Consumes: required `DEVICE_WATCH_AGENT_MODE=service` and optional `DEVICE_WATCH_AGENT_INTERVAL_SECONDS` with default `30.0` and a positive-value constraint; every other mode is rejected in Stage 1.
- Produces: `CollectorStatus` with values `success`, `unavailable`, and `failure`; `CollectorScalar = str | int | float | bool | None`; frozen `CollectorResult(status: CollectorStatus, values: Mapping[str, CollectorScalar], detail: str | None)`; runtime-checkable `Collector` protocol with `name: str` and `async collect() -> CollectorResult`; `CollectorRegistry.register()`, `CollectorRegistry.snapshot() -> tuple[Collector, ...]`; `AgentRuntime.run(stop_event: asyncio.Event) -> None`; and `main() -> int`.

- [ ] **Step 1: Write contract and registry tests first**

Test a test-local collector class against `Collector`, construct literal success/unavailable/failure results, accept an empty registry, preserve registration order, return an immutable snapshot, and reject duplicate names and blank names. Production files must contain no concrete collector.

- [ ] **Step 2: Run the contract tests and verify red**

Run:

```powershell
uv run --project agent pytest agent/tests/test_contracts.py agent/tests/test_registry.py -q
```

Expected: imports fail because the contracts and registry do not exist.

- [ ] **Step 3: Implement minimal typed contracts and registry**

Use only standard-library `dataclasses`, `enum`, `types`, `typing`, and collections. A result contains a read-only mapping of generic scalar values plus optional machine-readable detail; it contains no device, metric, heartbeat, or monitoring field. `snapshot()` returns `tuple[Collector, ...]`.

- [ ] **Step 4: Write configuration and lifecycle tests first**

Cover missing agent mode, every mode other than the literal `service`, default 30-second interval, non-positive interval rejection, empty-registry boot, efficient wait via an injected wait function, requested stop, signal-handler registration where supported, and proof that a registered test-local collector's `collect()` method is never invoked by the Stage 1 lifecycle.

- [ ] **Step 5: Run lifecycle tests and verify red**

Run:

```powershell
uv run --project agent pytest agent/tests/test_config.py agent/tests/test_lifecycle.py -q
```

Expected: failures name missing configuration and lifecycle objects.

- [ ] **Step 6: Implement standard-library configuration, logging, and lifecycle**

Parse only the dedicated agent variables, reject unknown `DEVICE_WATCH_AGENT_` keys, and never define a server URL or credential field. `AgentRuntime.run` uses `asyncio.Event`, `asyncio.wait_for(stop_event.wait(), timeout=interval)`, handles cancellation, and completes without invoking registry collectors or performing outbound I/O. `main()` builds an empty registry, installs `SIGINT`/`SIGTERM` handlers on supported platforms, runs the lifecycle, and exits `0` after cleanup. Collector orchestration and failure isolation remain documentation-only future contracts.

- [ ] **Step 7: Verify independent agent quality gates**

Run:

```powershell
uv run --project agent pytest agent/tests -q
uv run --project agent ruff check agent/src agent/tests
uv run --project agent mypy agent/src
uv tree --project agent --no-dev
```

Expected: the suite is green, types and lint are clean, and runtime dependencies contain no third-party package.

- [ ] **Step 8: Commit the agent foundation**

```powershell
git add agent
git commit -m "feat(agent): add contract-only native lifecycle"
```

### Task 6: React and TypeScript Application Shell

**Files:**
- Create: `web/index.html`
- Create: `web/eslint.config.js`
- Create: `web/tsconfig.json`
- Create: `web/tsconfig.app.json`
- Create: `web/tsconfig.node.json`
- Create: `web/vite.config.ts`
- Create: `web/src/main.tsx`
- Create: `web/src/styles.css`
- Create: `web/src/app/App.tsx`
- Create: `web/src/app/routes.tsx`
- Create: `web/src/components/layout/AppShell.tsx`
- Create: `web/src/components/layout/Navigation.tsx`
- Create: `web/src/components/ui/Button.tsx`
- Create: `web/src/pages/FoundationPage.tsx`
- Create: `web/src/theme/ThemeProvider.tsx`
- Create: `web/src/test/setup.ts`
- Create: `web/src/app/App.test.tsx`
- Create: `web/src/theme/ThemeProvider.test.tsx`

**Interfaces:**
- Consumes: browser history, `localStorage` key `device-watch-theme`, and local HTTP `/api` proxy target from `VITE_API_PROXY_TARGET` defaulting to `http://127.0.0.1:8000` only inside Vite development configuration.
- Produces: `ThemeMode = "system" | "light" | "dark"`, `ThemeProvider`, `useTheme()`, five routes, responsive accessible navigation, and a static production build in `web/dist`.

- [ ] **Step 1: Write application-shell tests first**

Use Testing Library with the real router. Assert navigation landmark and links, each path's exact heading, exact `Not implemented in Stage 1` copy, current-page accessibility state, theme cycling/persistence, system-mode media handling, and absence of fabricated counts or status labels.

- [ ] **Step 2: Run web tests and verify red**

Run:

```powershell
npm --prefix web run test -- --run
```

Expected: tests fail because the application and theme modules are absent.

- [ ] **Step 3: Implement design tokens, theme state, layout, and routes**

Use CSS variables for background, surface, text, muted text, border, focus, and accent; preserve visible focus rings and reduced-motion preferences. The route table is literal:

```typescript
export const routes = [
  { path: "/", label: "Dashboard" },
  { path: "/devices", label: "Devices" },
  { path: "/alerts", label: "Alerts" },
  { path: "/inventory", label: "Inventory" },
  { path: "/settings", label: "Settings" },
] as const;
```

Every element renders through `FoundationPage` with only its heading and the required Stage 1 message. Do not install an HTTP client, query package, or chart package.

- [ ] **Step 4: Configure independent Vite development and production builds**

Proxy `/api` with no rewrite:

```typescript
server: {
  proxy: {
    "/api": {
      target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
      changeOrigin: true,
    },
  },
}
```

Keep Caddy and TLS entirely outside the development command.

- [ ] **Step 5: Run the complete frontend quality gates**

Run:

```powershell
npm --prefix web run test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

Expected: tests, strict type checking, lint, and the static production build succeed without network calls.

- [ ] **Step 6: Commit the frontend shell**

```powershell
git add web
git commit -m "feat(web): add accessible Stage 1 application shell"
```

### Task 7: Hardened Server Image, Caddy Image, and Production Compose

**Files:**
- Modify: `.dockerignore`
- Create: `server/Dockerfile`
- Create: `deploy/.env.prod.example`
- Create: `deploy/caddy/Caddyfile`
- Create: `deploy/caddy/Dockerfile`
- Create: `deploy/compose.prod.yml`
- Create: `deploy/tests/test_production_topology.py`
- Create: `deploy/verify_topology.py`

**Interfaces:**
- Consumes: required Compose values `DEVICE_WATCH_DOMAIN`, `DATABASE_URL`, and `MYSQL_CA_CERT_PATH`; server image health endpoints; `web/dist` build contract.
- Produces: production images `device-watch-server:stage1` and `device-watch-caddy:stage1`, persistent volumes `caddy_data` and `caddy_config`, secret mount `/run/secrets/mysql-ca.pem`, and `verify_topology.py --env-file PATH` with zero/nonzero exit status.

- [ ] **Step 1: Write topology-verifier tests before deployment assets**

Create controlled valid and invalid rendered-JSON/Caddy fixtures in pytest temporary directories. Test that the verifier rejects a server published port, a third production service, a third application-network peer, missing persistent Caddy volumes, missing CA secret mount, non-read-only secret mount, URI rewrite/prefix stripping, wrong upstream, unpinned images, missing required-variable interpolation, missing `host.docker.internal:host-gateway`, wrong `DEVICE_WATCH_ENV`, a non-read-only server filesystem, missing server `/tmp` tmpfs, retained capabilities, missing `no-new-privileges`, an incorrect root build context, or an incorrect Dockerfile path. Test that an exact two-service fixture passes.

- [ ] **Step 2: Run topology tests and verify red**

Run:

```powershell
uv run --project server pytest deploy/tests/test_production_topology.py -q
```

Expected: import or behavioral failures identify the missing verifier.

- [ ] **Step 3: Implement the standard-library topology verifier**

Implement pure validation functions that consume Python dictionaries loaded from JSON; do not parse YAML in Python. For real files, invoke `docker compose ... config --format json` and inspect that rendered JSON plus the packaged Caddyfile. Exit nonzero with one sanitized message per violation; never print `DATABASE_URL`.

- [ ] **Step 4: Write the minimal path-preserving Caddyfile**

Use exactly this routing shape:

```caddyfile
{$DEVICE_WATCH_DOMAIN} {
    encode zstd gzip

    handle /api/* {
        reverse_proxy server:8000
    }

    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }
}
```

Do not add `uri strip_prefix`, `handle_path`, a development certificate directive, or a second site address. Caddy's automatic HTTPS supplies certificate management and redirects.

- [ ] **Step 5: Implement locked multi-stage images**

Both Compose builds use repository-root context `..` relative to `deploy/compose.prod.yml`; server selects `server/Dockerfile` and Caddy selects `deploy/caddy/Dockerfile`. The root `.dockerignore` allowlist is therefore the security boundary that prevents environment files, credentials, certificates, unrelated project files, and generated directories from entering either build context.

The server Dockerfile uses a locked Python 3.12 slim base plus a pinned `ghcr.io/astral-sh/uv:0.12.6` builder binary, installs from `server/uv.lock`, copies only the virtual environment and application/Alembic files, creates a fixed non-root UID/GID, and runs:

```text
uvicorn device_watch_server.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
```

Its health check uses Python standard-library HTTP against `/api/v1/health/ready`. The final server image contains no `uv`, compiler, package manager cache, or build toolchain. The Caddy Dockerfile uses `node:24.20.0-alpine3.24` only to run `npm ci` and `npm run build`, then copies `web/dist` and the Caddyfile into `caddy:2.11.4-alpine`; the final stage contains no Node executable.

- [ ] **Step 6: Implement production Compose security controls**

Define only `caddy` and `server` with explicit image names `device-watch-caddy:stage1` and `device-watch-server:stage1`. Publish `80:80` and `443:443` on Caddy only. Give both services dropped capabilities and `no-new-privileges`; grant Caddy only the bind-service capability required for ports below 1024; make both root filesystems read-only with writable named Caddy state volumes and `/tmp` tmpfs mounts; do not expose or publish server port 8000. Require variables with `${NAME:?message}` syntax. Mount the CA secret read-only into server, set `DEVICE_WATCH_ENV=production`, add Linux host mapping, and attach both services to a project-scoped bridge network. Do not set the bridge to `internal: true`, because FastAPI must reach external MySQL and Caddy must reach public certificate authorities.

The server health check probes `/api/v1/health/ready` with Python's standard library. The Caddy health check runs `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`; normal process exit remains Docker's runtime-failure signal.

- [ ] **Step 7: Verify production rendering, topology, images, and Caddy**

Run:

```powershell
docker compose --env-file deploy/.env.prod.example -f deploy/compose.prod.yml config
python deploy/verify_topology.py --env-file deploy/.env.prod.example
docker compose --env-file deploy/.env.prod.example -f deploy/compose.prod.yml build server caddy
docker run --rm --entrypoint caddy -e DEVICE_WATCH_DOMAIN=example.com device-watch-caddy:stage1 validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker run --rm --entrypoint sh device-watch-caddy:stage1 -c "if command -v node; then exit 1; fi"
docker image inspect device-watch-server:stage1 --format '{{.Config.User}}'
docker run --rm --entrypoint sh device-watch-server:stage1 -c "if command -v uv || command -v gcc || command -v make; then exit 1; fi"
```

Expected: Compose and verifier pass, both images build, Caddy validates, Node is absent from the final Caddy image, the server image declares a non-root user, and server build tooling is absent.

- [ ] **Step 8: Commit production deployment**

```powershell
git add .dockerignore server/Dockerfile deploy/.env.prod.example deploy/caddy deploy/compose.prod.yml deploy/verify_topology.py deploy/tests/test_production_topology.py
git commit -m "feat(deploy): add Caddy-only production ingress"
```

### Task 8: Local Development Compose and Container Smoke Verification

**Files:**
- Modify: `deploy/.env.dev.example`
- Modify: `deploy/compose.dev.yml`
- Create: `deploy/tests/test_development_topology.py`

**Interfaces:**
- Consumes: server image and MySQL health semantics from earlier tasks.
- Produces: optional `mysql` service bound to `127.0.0.1:3307`, development-only `mysql_dev_data` volume, and opt-in `verification` profile with an unexposed `server-smoke` service.

- [ ] **Step 1: Write development-topology tests first**

Test rendered configuration behavior starting from Task 4's passing MySQL service: MySQL remains tagged `mysql:8.4.11`, its port remains loopback-only, credentials remain conspicuous sample values, it never appears in production Compose, `server-smoke` belongs to `verification`, it publishes no port, and the file defines neither Caddy nor certificates.

- [ ] **Step 2: Run development-topology tests and verify red**

Run:

```powershell
uv run --project server pytest deploy/tests/test_development_topology.py -q
```

Expected: the existing MySQL assertions pass and the new smoke-profile assertions fail because `server-smoke` is absent.

- [ ] **Step 3: Implement the isolated development topology**

Retain the verified MySQL health check, named development volume, loopback port, and sample credentials from the explicit dev env file. Add `server-smoke` under `profiles: ["verification"]`, depend on healthy MySQL, use `DEVICE_WATCH_ENV=test`, point its URL to service name `mysql`, and publish no host port. Do not share values with the production env example.

- [ ] **Step 4: Verify local rendering and the server health transition**

Run:

```powershell
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml config
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml up -d --wait mysql
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml --profile verification up -d --build --wait server-smoke
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml --profile verification ps server-smoke
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml down
```

Expected: MySQL and server-smoke become healthy; no Caddy or certificate setup is involved.

- [ ] **Step 5: Commit development deployment assets**

```powershell
git add deploy/.env.dev.example deploy/compose.dev.yml deploy/tests/test_development_topology.py
git commit -m "feat(deploy): add isolated development verification stack"
```

### Task 9: Repository Security and Stage-Scope Audit

**Files:**
- Create: `deploy/verify_repository.py`
- Create: `deploy/tests/test_verify_repository.py`

**Interfaces:**
- Consumes: tracked and pending project paths, manifests, lock files, server routes, Alembic revision, agent modules, frontend source, and environment examples.
- Produces: `audit_repository(root: Path) -> list[Finding]` and a CLI that exits `0` only when dependency, secret, database, and Stage 1 boundary checks are clean.

- [ ] **Step 1: Write audit behavior tests first**

Build small temporary repositories with explicit positive and negative fixtures. Verify rejection of private-key blocks, non-example environment files, credential-like live values, an unknown database driver/token, a business API route, a mapped domain table, a concrete production collector, a sender module, frontend `fetch`/XHR use, fabricated monitoring records, and forbidden production services or ports. Verify allowed sample credentials in named example files and the exact health-only project shape pass.

- [ ] **Step 2: Run audit tests and verify red**

Run:

```powershell
uv run --project server pytest deploy/tests/test_verify_repository.py -q
```

Expected: import failure identifies the missing audit implementation.

- [ ] **Step 3: Implement a positive-allowlist, standard-library audit**

Walk project files while excluding VCS metadata, recovery metadata, environments, dependency directories, caches, coverage, and builds. Inspect both names and decoded text. Use a positive database allowlist centered on MySQL, PyMySQL, SQLAlchemy, and Alembic rather than embedding a catalog of other database product names. Validate actual source boundaries structurally where feasible and emit relative path plus rule identifier without echoing secret content.

- [ ] **Step 4: Run the audit tests and real repository audit**

Run:

```powershell
uv run --project server pytest deploy/tests/test_verify_repository.py -q
python deploy/verify_repository.py
```

Expected: tests pass and the real audit reports zero findings.

- [ ] **Step 5: Commit the repeatable repository audit**

```powershell
git add deploy/verify_repository.py deploy/tests/test_verify_repository.py
git commit -m "test: enforce security and Stage 1 repository boundaries"
```

### Task 10: Architecture, Development, Deployment, and Future-Contract Documentation

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Create: `docs/architecture.md`
- Create: `docs/development.md`
- Create: `docs/deployment.md`
- Create: `docs/future-contracts.md`
- Create: `deploy/systemd/device-watch-agent.service`

**Interfaces:**
- Consumes: commands, variables, route names, image topology, and trust decisions already verified by code.
- Produces: complete operator/developer instructions and documentation-only future boundaries with no executable Stage 2 artifact.

- [ ] **Step 1: Document the repository and independent local workflows**

In `README.md` and `docs/development.md`, give copy-paste PowerShell and POSIX commands for agent install/run/test, server install/run/test/database check/Alembic, web install/dev/test/build, and optional development MySQL. State that Vite proxies `/api` without rewriting, Caddy and certificates are unnecessary locally, components can run independently, and no setting silently selects the development database.

- [ ] **Step 2: Document production security and deployment**

In `docs/deployment.md`, document DNS and ports, required variables, operator-supplied CA path, exact production TLS URL query, persistent Caddy volumes, external MySQL grants/firewall/bind address/account encrypted-transport requirement, `host.docker.internal:host-gateway` on Linux, and why `localhost` inside server does not reach host MySQL. Include Compose render, build, Caddy validation, start, health inspection, and rollback-safe stop commands. Never include a usable secret.

- [ ] **Step 3: Document architecture and trust boundaries**

In `docs/architecture.md`, include the exact future path:

```text
Remote Agent
    | HTTPS
    v
  Caddy
    | /api
    v
 FastAPI
    |
    v
 MySQL
```

Explain that Caddy is the sole ingress, FastAPI is private, MySQL is separately administered, future agents initiate outbound HTTPS, the wildcard proxy trust depends on the enforced two-member network, and a network-topology change requires narrowing trusted proxy addresses.

- [ ] **Step 4: Document future contracts without executable business behavior**

In `docs/future-contracts.md`, include exactly this ordered sequence:

```text
device enrollment
-> credentials/token
-> heartbeat submission
-> current health update
-> historical metric storage
-> health evaluation
-> alert generation
```

Describe boundaries for one-time bootstrap exchange, hashed server-side credentials, root-readable agent secret storage, versioned submission envelopes, independent collector results, timeouts/bounded retry/backoff, server receipt time, separate current/history persistence, and evaluation-after-persistence. Clearly label every item as a future contract, not a route, table, credential, or implemented workflow.

- [ ] **Step 5: Add the native systemd example**

Run `python -m device_watch_agent`, read an operator-created protected environment file, set a dedicated unprivileged user, use `Restart=on-failure`, and retain normal `SIGTERM`. Do not invoke Docker, a shell polling loop, a database, or a sender.

- [ ] **Step 6: Cross-check documentation against executable configuration**

Run:

```powershell
python deploy/verify_repository.py
rg -n "DEVICE_WATCH_|DATABASE_URL|MYSQL_CA_CERT_PATH|/api/v1/health|3307|server:8000" README.md docs deploy agent/.env.example .env.example
git diff --check
```

Expected: documented names and paths match implementation exactly, the audit passes, and whitespace is clean.

- [ ] **Step 7: Commit documentation and service example**

```powershell
git add README.md .env.example docs/architecture.md docs/development.md docs/deployment.md docs/future-contracts.md deploy/systemd/device-watch-agent.service
git commit -m "docs: document Stage 1 architecture and operations"
```

### Task 11: Full Acceptance Verification and Evidence Capture

**Files:**
- Modify only when a failing gate is reproduced by a new regression test: files owned by the failing task.
- Verify: all Stage 1 project files.

**Interfaces:**
- Consumes: every prior task's commands and acceptance contract.
- Produces: fresh command output for the final repository tree, unit/integration tests, real migration cycle, frontend build, Caddy validation, Compose rendering, container health, security audit, and clean Git diff.

- [ ] **Step 1: Run independent Python project gates**

```powershell
uv sync --project agent --frozen
uv run --project agent pytest agent/tests -q
uv run --project agent ruff check agent/src agent/tests
uv run --project agent mypy agent/src
uv sync --project server --frozen
uv run --project server pytest server/tests/unit deploy/tests -q
uv run --project server ruff check server/src server/tests deploy
uv run --project server mypy server/src
```

Expected: every command exits `0` with no warnings or failures.

- [ ] **Step 2: Run frontend gates from the committed npm lock**

```powershell
npm --prefix web ci
npm --prefix web run test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

Expected: tests, types, lint, and build exit `0`.

- [ ] **Step 3: Verify real MySQL connectivity and migrations**

```powershell
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml up -d --wait mysql
$env:DEVICE_WATCH_ENV='test'
$env:DATABASE_URL='mysql+pymysql://device_watch_dev:device_watch_dev@127.0.0.1:3307/device_watch'
uv run --project server device-watch-db-check
uv run --project server pytest server/tests/integration -q
uv run --project server alembic -c server/alembic.ini upgrade head
uv run --project server alembic -c server/alembic.ini downgrade base
uv run --project server alembic -c server/alembic.ini upgrade head
```

Expected: connectivity succeeds, integration tests pass, and the three migrations complete in order against MySQL 8.x.

- [ ] **Step 4: Verify container, Compose, Caddy, and ingress contracts**

```powershell
docker compose --env-file deploy/.env.prod.example -f deploy/compose.prod.yml config
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml config
python deploy/verify_topology.py --env-file deploy/.env.prod.example
docker compose --env-file deploy/.env.prod.example -f deploy/compose.prod.yml build server caddy
docker run --rm --entrypoint caddy -e DEVICE_WATCH_DOMAIN=example.com device-watch-caddy:stage1 validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker run --rm --entrypoint sh device-watch-caddy:stage1 -c "if command -v node; then exit 1; fi"
docker image inspect device-watch-server:stage1 --format '{{.Config.User}}'
docker run --rm --entrypoint sh device-watch-server:stage1 -c "if command -v uv || command -v gcc || command -v make; then exit 1; fi"
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml --profile verification up -d --build --wait server-smoke
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml --profile verification ps server-smoke
docker compose --env-file deploy/.env.dev.example -f deploy/compose.dev.yml down
```

Expected: both Compose files render, topology and Caddy validate, images build, and server-smoke reaches healthy without a published FastAPI port.

- [ ] **Step 5: Prove required production variables fail closed**

Run production `docker compose ... config` three times with one of `DEVICE_WATCH_DOMAIN`, `DATABASE_URL`, or `MYSQL_CA_CERT_PATH` absent each time.

Expected: each command exits nonzero before container creation and identifies only the missing variable name, never a credential value.

- [ ] **Step 6: Run dependency and repository audits**

```powershell
uv tree --project agent --no-dev
uv tree --project server --no-dev
npm --prefix web ls --omit=dev
python deploy/verify_repository.py
git diff --check
git status --short --branch
```

Expected: dependency graphs match project scope, repository audit returns zero findings, whitespace is clean, and only intentional Stage 1 changes are present.

- [ ] **Step 7: Inspect the final tree and diff against every acceptance criterion**

Run:

```powershell
git diff --stat main...HEAD
git diff --name-status main...HEAD
tree /F /A
```

Check all sixteen spec acceptance criteria against code or fresh command evidence. Record environmental limitations explicitly rather than representing an unrun Docker, Caddy, or MySQL gate as successful.

- [ ] **Step 8: Commit any test-proven verification corrections**

If a gate exposed a defect, first add a focused failing regression test, then apply the minimal correction, rerun the affected gate and the full relevant component suite, and commit:

```powershell
git add server agent web deploy
git commit -m "fix: satisfy Stage 1 acceptance verification"
```

If every gate was already clean, create no empty commit.

## Final Handoff Content

The completion response must include:

- The final repository tree, excluding generated dependencies, VCS internals, caches, and test output.
- Exact commands run and their fresh pass/fail/blocked results.
- The SQLAlchemy 2.0.52 to PyMySQL 1.2.0 URL-translation characterization result and the effective boolean TLS argument proof.
- Real MySQL connectivity evidence and Alembic `head -> base -> head` evidence.
- Development and production Compose render results, Caddy validation, final-image Node absence, and server-smoke health result.
- Confirmation that only Caddy publishes production ports and FastAPI/MySQL have no production public exposure.
- Repository-audit result proving MySQL-only scope and absence of executable future workflows.
- Architectural and operational risks that remain outside Stage 1.
- Any verification gate that could not run because a required local daemon or operator-owned service was unavailable, stated plainly with the exact command and error.
