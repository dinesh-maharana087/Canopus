# Device Watch Stage 1 Status

## Current independent verification — 2026-09-12

**STAGE 1 VERIFIED WITH ENVIRONMENT BLOCKS** — **9 PASS, 0 FAIL, 7 BLOCKED**.
Blocked criteria: **2, 3, 7, 8, 9, 13, 15**. No deterministic Stage 1
acceptance failure remains after the verified R5A/R5B/R5C and safeguard repairs.

The authoritative handoff is the [V08 final baseline](../verification/stage-01/stage-01-baseline.md),
with the [current V07 mapping](../verification/stage-01/07-acceptance-review.md).
Stage 2+ may reuse the qualified PASS contracts; real MySQL, Docker/Compose/
Caddy and other recorded runtime checks still require targeted verification.
This is not a claim of full runtime acceptance or current Stage 2 completeness.

The implementation handoffs below are historical. Their `Complete` labels and
older counts do not override independent verification. V08 consolidated existing
evidence without rerunning suites or starting Stage 2 work.

## Planning Status

Planning decomposition is complete. The master index is [docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md](../superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md).

Step 01 is complete. Future coding sessions must execute **exactly one numbered step at a time**, run that step's checks, update this document, and stop at the checkpoint.

## Work Existing Before Decomposition

The repository already contained the approved Stage 1 design specification and the original 11-task implementation plan. No application source, deployment assets, tests, progress document, or decomposed step files existed. The untracked `.vscode/settings.json` is editor configuration and is unrelated to Stage 1 implementation.

## Step 01 Completion

Status: **Complete**.

Implemented the repository safeguards, independent project manifests, and all three required dependency locks. The Python locks were generated with `uv 0.12.10` from the workspace environment; the web lock was already present and was verified with npm.

Files created or modified:

- `.editorconfig`
- `.dockerignore`
- `.gitignore`
- `.env.example`
- `README.md`
- `agent/pyproject.toml`
- `server/pyproject.toml`
- `agent/uv.lock`
- `server/uv.lock`
- `web/package.json`
- `web/package-lock.json`

Verification executed:

- `python --version`: passed, Python 3.12.6.
- `node --version`: passed, v22.14.0.
- `npm --version`: passed, 10.9.2.
- `python -c "...tomllib..."`: passed for both Python manifests.
- `uv lock --project agent`: passed.
- `uv lock --project server`: passed.
- `uv sync --project agent --frozen`: passed.
- `uv sync --project server --frozen`: passed.
- `uv tree --project agent --no-dev`: passed; no runtime dependencies beyond the package itself.
- `uv tree --project server --no-dev`: passed; independent server runtime tree.
- `npm ci --ignore-scripts --no-audit --no-fund` from `web/`: passed; emitted a Node engine warning because React Router 8.3.1 requires Node 22.22+ while this host has 22.14.0, plus dependency deprecation warnings.
- Required-file and no-source-directory checks: passed.
- `git diff --check`: passed during final handoff review.
- Docker version and Compose version: blocked because Docker is not installed or on PATH.

Decisions and deviations: the approved dependency versions were preserved. The Vite React plugin is 6.1.1 because it is the compatible release for approved Vite 8.2.2; ESLint and `@eslint/js` are 9.39.1 because the selected React Hooks plugin does not accept ESLint 10. No forced or legacy npm peer resolution was used. No later-step source or runtime files were created.

Unresolved issues: Docker and Compose remain unavailable, so their version checks were not run; they are not required for the Step 01 definition of done. The host Node version is below React Router's declared engine minimum and should be upgraded before web execution in a later step.

## Step 02 Completion

Status: **Complete**.

Implemented strict server settings and secret-safe validation without creating an engine, database connection, API route, or later-step runtime behavior.

Files created or modified:

- `server/src/device_watch_server/__init__.py`
- `server/src/device_watch_server/core/__init__.py`
- `server/src/device_watch_server/core/config.py`
- `server/tests/conftest.py`
- `server/tests/unit/test_config.py`
- `docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md`
- `docs/progress/current-status.md`

Verification executed:

- `uv run --project server --group test pytest server/tests/unit/test_config.py -q`: passed, 10 tests.
- `uv run --project server --group test ruff check server/src server/tests/unit/test_config.py`: passed.
- `uv run --project server --group test mypy server/src`: passed, no issues.
- Final `git diff --check`: pending final handoff review.

The tests cover required environment variables, exactly three supported modes, the `mysql+pymysql` dialect, immutable settings, credential-safe representations/errors, exact production TLS query entries, duplicate/additional query rejection, production documentation rejection, and development TLS omission. No Docker or MySQL verification was required for this step.

Important decision: `load_settings()` uses Pydantic Settings environment loading and converts validation failures to `SettingsError` messages without connection-string values. Production TLS query validation parses raw query pairs so duplicate keys cannot be silently collapsed.

Unresolved issues: none for Step 02. The next step owns engine construction and effective PyMySQL TLS arguments.

## Step 03 Completion

Status: **Complete**.

Implemented the centralized SQLAlchemy engine boundary and verified the effective MySQL TLS arguments at the `do_connect` boundary without attempting a network connection.

Files created or modified:

- `server/src/device_watch_server/db/__init__.py`
- `server/src/device_watch_server/db/engine.py`
- `server/tests/unit/test_engine_tls.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md`

Verification executed:

- `uv run --project server --group test pytest tests/unit/test_config.py tests/unit/test_engine_tls.py -q`: passed, 14 tests.
- `uv run --project server --group test ruff check src tests/unit/test_config.py tests/unit/test_engine_tls.py`: passed.
- `uv run --project server --group test mypy src`: passed, no issues.
- `git diff --check`: not run in this session; the step-level verification above is the current evidence base.

Important evidence:

- SQLAlchemy package version is `2.0.52` and PyMySQL is `1.2.0`.
- The upstream `MySQLDialect_pymysql().create_connect_args()` characterization shows the nested `ssl` mapping plus string verification flags, which the app boundary intentionally strips and re-asserts as a flat mapping: `ssl_ca`, `ssl_verify_cert=True`, `ssl_verify_identity=True`.
- The engine removes the already-validated TLS query keys before SQLAlchemy URL translation so a competing nested `ssl` mapping is not created from the URL itself.
- The `do_connect` event capture records final keyword arguments immediately before the database driver receives them; no network connection is attempted in the tests.

Unresolved issues: none for Step 03. Step 04 remains out of scope and was not started.

## Step 04 Completion

Status: **Complete**.

Implemented the isolated development MySQL topology for later integration and migration checks without creating production Compose or server code.

Files created or modified:

- `deploy/.env.dev.example`
- `deploy/compose.dev.yml`
- `deploy/tests/test_development_mysql.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md`

Verification executed:

- `uv run --project server --group test pytest deploy/tests/test_development_mysql.py -q`: passed, 1 test.
- Docker/Compose availability check: blocked because Docker is not installed or not on PATH in this environment.

Important evidence:

- The development Compose definition contains exactly one service, `mysql`, using the required image `mysql:8.4.11`.
- The service binds to `127.0.0.1:3307:3306`, uses a health check, and mounts the development-only named volume `mysql_dev_data`.
- Sample credentials are non-production and sourced from the development env example file only.
- No production Compose or server files were modified as part of Step 04.

Unresolved issues: Docker/Compose runtime startup itself could not be executed here because the CLI is unavailable. The topology and render contract for Step 04 are still verified by the unit-style topology test.

## Step 05 Completion

Status: **Complete**.

Implemented the FastAPI application factory and the two approved health endpoints without introducing later-step behavior or database-specific domains.

Files created or modified:

- `server/src/device_watch_server/api/__init__.py`
- `server/src/device_watch_server/api/health.py`
- `server/src/device_watch_server/api/router.py`
- `server/src/device_watch_server/app.py`
- `server/src/device_watch_server/db/health.py`
- `server/src/device_watch_server/main.py`
- `server/tests/unit/test_app.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md`

Verification executed:

- `uv run --project server --group test pytest tests/unit/test_app.py -q`: passed, 6 tests.
- `uv run --project server --group test ruff check src tests/unit/test_app.py`: passed.
- `uv run --project server --group test mypy src`: passed, no issues.

Important evidence:

- Only `/api/v1/health/live` and `/api/v1/health/ready` are registered.
- Liveness is process-only; readiness invokes the injected database-check callback and returns a generic `503` without exposing exception details or credentials.
- The app owns its internal engine during lifespan shutdown and disposes it before exit.
- Production disables OpenAPI docs unless explicitly enabled through settings.

Unresolved issues: none for Step 05. Step 06 remains out of scope and was not started.

## Step 06 Completion

Status: **Complete**.

Implemented secret-safe structured request logging, a sanitized request middleware, and a CLI database-check command that returns a nonzero status when connectivity fails without exposing secrets, credentials, URLs, cookies, or exception detail.

Files created or modified:

- `server/src/device_watch_server/core/logging.py`
- `server/src/device_watch_server/core/middleware.py`
- `server/src/device_watch_server/db/health.py`
- `server/src/device_watch_server/cli.py`
- `server/tests/unit/test_step06_logging_cli.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md`

Verification executed:

- `uv run --project server --group test pytest tests/unit/test_step06_logging_cli.py -q`: passed, 4 tests.
- `uv run --project server --group test pytest tests/unit/test_app.py -q`: passed, 6 tests.
- `uv run --project server --group test ruff check src tests/unit/test_app.py tests/unit/test_step06_logging_cli.py`: passed.
- `uv run --project server --group test mypy src`: passed, no issues.

Important evidence:

- Request logs are single-line JSON with only the approved operational fields: event, method, normalized path, status, duration, and timestamp.
- URL, header, cookie, body, and credential values are sanitized before emission.
- The database-check CLI exits with 0 on success and 1 on failure while printing only a generic status line.
- No Step 07 work was started.

## Step 07 Completion

Status: **Complete**.

Implemented the server Alembic metadata and the schema-empty baseline revision while keeping the Stage 1 scope to no domain tables or runtime behavior beyond migration state.

Files created or modified:

- `server/src/device_watch_server/db/base.py`
- `server/alembic.ini`
- `server/alembic/env.py`
- `server/alembic/script.py.mako`
- `server/alembic/versions/20260831_0001_baseline.py`
- `server/tests/integration/test_alembic_baseline.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md`

Verification executed:

- `uv run --project server --group test pytest server/tests/unit -q`: passed, 24 tests.
- `uv run --project server --group test ruff check server/src server/tests`: passed.
- `uv run --project server --group test mypy server/src`: passed, no issues.

Important evidence:

- Alembic consumes the validated `DATABASE_URL` from the server settings and does not duplicate the URL in configuration.
- The baseline revision is `20260831_0001` and the metadata is intentionally empty.
- The migration cycle is structured for a real MySQL upgrade/downgrade/upgrade verification, with no business tables created.

Unresolved issues: the actual real-MySQL runtime verification remains environment-dependent because Docker/MySQL execution is unavailable in this host.

## Step 08 Completion

Status: **Complete**.

Implemented the agent-side collector contracts and registry using only the Python standard library, with a strict empty-registry and unique-name model and no concrete production collectors.

Files created or modified:

- `agent/src/device_watch_agent/__init__.py`
- `agent/src/device_watch_agent/collectors/__init__.py`
- `agent/src/device_watch_agent/collectors/contracts.py`
- `agent/src/device_watch_agent/collectors/registry.py`
- `agent/tests/test_contracts.py`
- `agent/tests/test_registry.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-08-31-device-watch-stage-1/00-master-index.md`

Verification executed:

- `uv run --project agent --group test pytest agent/tests/test_contracts.py agent/tests/test_registry.py -q`: passed, 6 tests.
- `uv run --project agent --group test ruff check agent/src agent/tests`: passed.
- `uv run --project agent --group test mypy agent/src`: passed, no issues.

Important evidence:

- Contracts carry only typed result status, scalar values, and optional detail text.
- The registry rejects duplicates and blank names while preserving insertion order.
- The registry starts empty and the package remains free of concrete collector implementations.

Unresolved issues: none for Step 08. The next permitted work is Step 09 only if explicitly requested.

## Step 09 Completion

Status: **Complete**.

Implemented strict native-agent configuration and an empty, signal-aware lifecycle with no collection, network, database, or server coupling.

Files created or modified:

- `agent/.env.example`
- `agent/src/device_watch_agent/__main__.py`
- `agent/src/device_watch_agent/config.py`
- `agent/src/device_watch_agent/logging.py`
- `agent/src/device_watch_agent/lifecycle.py`
- `agent/src/device_watch_agent/main.py`
- `agent/tests/test_config.py`
- `agent/tests/test_lifecycle.py`

Verification executed:

- `uv run --project agent --group test pytest agent/tests -q`: passed, 18 tests.
- `uv run --project agent --group test ruff check agent/src agent/tests`: passed.
- `uv run --project agent --group test mypy agent/src`: passed, no issues.
- `uv tree --project agent --no-dev`: passed; runtime dependency remains standard-library only.

## Step 10 Completion

Status: **Complete**.

Implemented the responsive React/TypeScript Stage 1 shell with five empty routes, accessible navigation, persistent system/light/dark theme state, reduced-motion styling, and a development-only `/api` proxy.

Files created or modified:

- `web/index.html`
- `web/eslint.config.js`
- `web/tsconfig.json`
- `web/tsconfig.app.json`
- `web/tsconfig.node.json`
- `web/vite.config.ts`
- `web/vitest.config.ts`
- `web/src/`

Verification executed:

- `npm --prefix web run test -- --run`: passed, 8 tests.
- `npm --prefix web run typecheck`: passed.
- `npm --prefix web run lint`: passed.
- `npm --prefix web run build`: passed; static output generated in `web/dist`.

## Step 11 Completion

Status: **Complete**.

Added the locked, non-root server image definition using the pinned UV builder, frozen server lock data, minimal runtime inputs, health probe, read-only-compatible `/tmp`, and the approved Uvicorn proxy-header command.

Files created or modified:

- `.dockerignore`
- `server/Dockerfile`

The actual image build and inspection are blocked because Docker is unavailable on this host.

## Step 12 Completion

Status: **Complete**.

Added the multi-stage Caddy image and exact path-preserving Caddyfile. The final stage copies only the web build and Caddy configuration into the pinned Caddy runtime; `/api/*` proxies unchanged to `server:8000`, and all other paths use SPA fallback.

Files created or modified:

- `.dockerignore`
- `deploy/caddy/Caddyfile`
- `deploy/caddy/Dockerfile`

Caddy image build and `caddy validate` remain blocked by Docker unavailability.

## Step 13 Completion

Status: **Complete**.

Implemented the production env example, exact two-service Compose topology, CA secret mount, host gateway, health checks, rootless/read-only capability controls, persistent Caddy volumes, and a standard-library rendered-topology verifier.

Files created or modified:

- `deploy/__init__.py`
- `deploy/.env.prod.example`
- `deploy/compose.prod.yml`
- `deploy/verify_topology.py`
- `deploy/tests/test_production_topology.py`

Verification executed:

- `uv run --project server --group test pytest server/tests/unit deploy/tests -q`: passed, 29 tests.
- `uv run --project server --group test ruff check server/src server/tests deploy`: passed.
- `uv run --project server --group test mypy server/src`: passed, no issues.
- `uv run --project server --group test pytest deploy/tests/test_production_topology.py -q`: passed, 4 tests.
- `python -m py_compile deploy/verify_topology.py`: passed.

Environment limitation: Docker and Docker Compose are not installed or available on PATH, so Compose rendering, image builds, health probes, Caddy validation, and live missing-variable failure checks could not be executed. No `DATABASE_URL` value was echoed.

## Step 14 Completion

Status: **Complete**.

Extended the isolated development Compose file with an opt-in `verification` profile containing a portless `server-smoke` service. It uses the Step 11 server image, points at the `mysql` service name, sets `DEVICE_WATCH_ENV=test`, and waits for healthy MySQL without changing normal native development startup.

Files created or modified:

- `deploy/compose.dev.yml`
- `deploy/tests/test_development_topology.py`

Verification executed:

- `uv run --project server --group test pytest deploy/tests/test_development_topology.py -q`: passed.
- Full server/deployment suite including Step 14 tests: 34 passed.

Environment limitation: Docker and Docker Compose remain unavailable, so profile rendering, container health transition, and teardown could not be run.

## Step 15 Completion

Status: **Complete**.

Added a repeatable standard-library repository audit for secrets, unsupported database URLs, live environment files, Stage 2 routes/tables/collectors/senders, frontend network calls, monitoring fixtures, and forbidden production topology. Findings contain only relative paths, rule identifiers, and sanitized messages.

Files created or modified:

- `deploy/verify_repository.py`
- `deploy/tests/test_verify_repository.py`

Verification executed:

- `uv run --project server --group test pytest deploy/tests/test_verify_repository.py -q`: passed, 4 tests.
- `python deploy/verify_repository.py`: passed with zero findings.
- `uv run --project server --group test ruff check server/src server/tests deploy`: passed.
- `uv run --project server --group test mypy server/src`: passed, no issues.
- `uv tree --project agent --no-dev`: passed with no runtime dependencies.
- `uv tree --project server --no-dev`: passed.
- `npm --prefix web ls --depth=0`: passed.
- `git diff --check`: passed.

The full web checks also remained green: 8 tests, strict typecheck, lint, and production build. Docker-dependent checks remain blocked by host availability; no secret values were echoed.

## Step 16 Completion

Status: **Complete**.

Added operational, architecture, deployment, development, future-contract, and native systemd documentation without creating new runtime behavior or credentials.

Files created or modified:

- `README.md`
- `.env.example`
- `docs/architecture.md`
- `docs/development.md`
- `docs/deployment.md`
- `docs/future-contracts.md`
- `deploy/systemd/device-watch-agent.service`

Verification executed:

- `python deploy/verify_repository.py`: passed with zero findings.
- Executable-name cross-check for `DEVICE_WATCH_*`, `DATABASE_URL`, `MYSQL_CA_CERT_PATH`, health routes, `3307`, and `server:8000`: completed; documented values match the implementation.
- `git diff --check`: passed.

The systemd example runs only `python -m device_watch_agent`, reads an operator-managed protected environment file, uses a dedicated unprivileged user, restarts on failure, and retains normal `SIGTERM` handling.

## Step 17 Completion

Status: **Complete with documented environment blocks**.

The full non-container acceptance matrix was rerun fresh:

- Agent: 18 tests passed; Ruff and mypy passed.
- Server: 24 tests passed, 1 real-MySQL integration test skipped because no configured database was available; Ruff and mypy passed.
- Deployment: 10 tests passed; topology and repository audits passed.
- Web: 8 tests passed; strict typecheck, ESLint, and production build passed.
- Dependency review: agent and server `uv tree --no-dev`, plus `npm ls --depth=0`, passed.
- Syntax and hygiene: verifier modules compiled and `git diff --check` passed.
- Repository audit: zero findings.

Blocked commands, not reported as successful:

- Real MySQL `SELECT 1` and Alembic `head -> base -> head` cycle: blocked because Docker/MySQL is unavailable.
- Development and production Compose rendering: blocked because Docker Compose is unavailable.
- Server/Caddy image builds, Caddy validation, final-image inspection, and server-smoke health transition: blocked because Docker is unavailable.
- Production missing-variable render failures: blocked because Compose is unavailable; required `${NAME:?message}` interpolation and verifier coverage are present in code.

No secret or database URL value was echoed. The final evidence run included focused Step 15 audit refinements for generated worktrees, synthetic test fixtures, and documentation headings; no application runtime behavior was expanded. Stage 1 acceptance evidence is complete for the available environment, with container/database evidence reserved for a Docker/MySQL-capable host.

## Stage 1 Status (historical implementation handoff)

Stage 1 is **Complete**. Steps 01 through 17 are complete, with the Docker/MySQL-dependent evidence explicitly blocked by host capability. No later numbered implementation step is defined by this plan.

At each handoff, preserve this evidence boundary: do not represent blocked infrastructure checks as passing, and do not add Stage 2 routes, tables, collectors, senders, credentials, or monitoring fixtures without a new approved scope.

## Stage 2 Planning Status

Status: **Planning complete; implementation not started**.

Stage 2 planning is recorded in:

- Design specification: `docs/superpowers/specs/2026-09-08-device-watch-stage-2-design.md`
- Master index: `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`
- Acceptance contract: `docs/acceptance/stage-02-device-connectivity.md`
- Execution cards: `docs/superpowers/plans/2026-09-08-device-watch-stage-2/01-domain-contracts.md` through `18-acceptance-evidence.md`

The proposed decomposition contains 18 implementation steps. All Stage 2 steps remain **Pending**. This planning session created no Stage 2 application code, database migration, route, table, collector, sender, credential, or UI functionality.

The plan preserves Stage 1 architecture and contracts. No Stage 1 structural change was identified as necessary; Stage 2 extends the existing app factory, Alembic baseline, agent lifecycle, Caddy ingress, and Devices route boundary through separately verified steps.

Planning decisions added during review: Stage 2 device list/detail access uses a protected deployment-provided read-only operator service token rather than interactive user/RBAC authentication, and bootstrap verification uses an operator-managed server pepper. Neither value is a device credential, persisted in device records, logged, or returned by an API.

## Stage 2 Step 01 Completion

Status: **Complete**.

Implemented only the typed Stage 2 domain contracts and persistence boundary definitions. No ORM mapping, database migration, route, credential generation, collector, sender, or UI behavior was added.

Files created or modified:

- `server/src/device_watch_server/domain/__init__.py`
- `server/src/device_watch_server/domain/contracts.py`
- `server/tests/unit/test_stage2_domain_contracts.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`

Contract decisions verified:

- Device identity is UUIDv4 with bounded non-blank display names, server-owned UTC creation time, and active/revoked lifecycle state.
- Bootstrap and credential lifecycle states are explicit enums without secret fields.
- Heartbeats are protocol version `1` and contain only submission ID, agent version, and optional timezone-aware observation time.
- Device summaries expose only identity/current-connectivity fields; credential, hash, bootstrap, metric, and inventory fields are absent.
- Persistence contracts contain only current last-seen/submission/version values and require a timestamp when a submission identity exists.
- Contract models are strict (`extra=forbid`) and immutable (`frozen=True`).

Verification executed:

- `uv run --project server --group test pytest server/tests/unit/test_stage2_domain_contracts.py -q`: passed, 7 tests.
- `uv run --project server --group test ruff check server/src server/tests/unit/test_stage2_domain_contracts.py`: passed.
- `uv run --project server --group test mypy server/src`: passed, no issues.

Stage 1 regression status: the Step 01 change touched only new Stage 2 domain/test files; completed Stage 1 verification remains preserved. The next permitted work is Step 02 only.

## Stage 2 Step 02 Completion

Status: **Complete**.

Added the first Stage 2 Alembic revision for server-owned device identity. The migration is chained from the schema-empty Stage 1 revision and creates only the constrained `devices` identity table.

Files created or modified:

- `server/alembic/versions/20260908_0002_device_identity.py`
- `server/alembic.ini`
- `server/tests/unit/test_device_identity_migration.py`
- `server/tests/integration/test_device_identity_migration.py`
- `server/tests/integration/test_alembic_baseline.py`
- `server/src/device_watch_server/core/logging.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`

Migration decisions verified:

- Revision `20260908_0002` revises `20260831_0001`.
- `devices.device_id` is a non-null canonical UUID string column with the primary-key constraint `pk_devices`.
- `display_name` is required and bounded at 120 characters; names are not globally unique.
- `created_at` is required and server-owned; `lifecycle` is required with the `active`/`revoked` check constraint `ck_devices_lifecycle` and an `active` default.
- No credentials, bootstrap material, heartbeat state, connectivity state, metrics, history, or UI fields are included.
- Downgrade removes only `devices` and returns to the Stage 1 baseline.

Verification executed:

- `uv run --project server --group test pytest server/tests/unit -q`: passed, 32 tests.
- `uv run --project server --group test pytest server/tests/unit/test_device_identity_migration.py -q`: passed, 1 offline SQL characterization test.
- `uv run --project server --group test pytest server/tests/integration/test_alembic_baseline.py server/tests/integration/test_device_identity_migration.py -q`: 2 skipped because no `DATABASE_URL`/real MySQL was available.
- `uv run --project server --group test ruff check server/src server/alembic server/tests`: passed.
- `uv run --project server --group test mypy server/src`: passed, no issues.
- `git diff --check`: passed.

Adjacent regression repair: `setup_logging()` now re-enables the existing server logger and safely replaces stale stdout handlers so the completed Step 06 logging test remains stable across repeated app construction and pytest capture. Its JSON/redaction contract is unchanged; the full server unit suite passes.

The next permitted work is Step 03 only. Step 03 has not been started.
