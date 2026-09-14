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

## Stage 2 Step 03 Implementation — 2026-09-13

Status: **Implementation complete; full definition-of-done verification BLOCKED BY ENVIRONMENT**.

This entry supersedes the preceding historical statement that Step 03 had not
started. At session start, HEAD `8d91261` had a clean working tree and already
contained bootstrap cryptography, repository/service code, revision
`20260908_0003`, and unit tests. Those valid implementations were preserved.
The [Stage 1 baseline](../verification/stage-01/stage-01-baseline.md) remains the
foundation; no historical Stage 1 verification evidence was changed.

Completed only Step 03:

- Added the local `device-watch-bootstrap` command with `create` and `revoke`
  operations. Creation requires terminal stdout and emits plaintext once, only
  after commit. It refuses redirected output and accepts no secret arguments.
  Configuration, parser, database, commit, and invalid-state errors use the
  generic `Bootstrap operation failed` diagnostic without exception details.
- Bound `DEVICE_WATCH_BOOTSTRAP_HMAC_PEPPER` to the existing secret-safe setting
  in case-sensitive environments. MySQL/PyMySQL validation, production TLS
  policy, engine construction, health routes, and deployment remain unchanged.
- Aligned service timestamps with the existing MySQL whole-second `DATETIME`
  representation so returned/displayed expiration matches stored expiration.
- Added generation uniqueness, offline downgrade, environment-binding, timestamp,
  terminal-output, log-safety, and subprocess regression coverage. The existing
  missing bootstrap CLI was a direct Step 03 dependency and is now implemented.
- Added eight real-MySQL cases for schema reversal, durable digest/timestamps,
  unique fingerprint enforcement, expiry/revocation/consumption, rollback, and
  concurrent single use. Pinned the existing Step 02 integration test to
  revision `20260908_0002` so its unchanged assertions do not target the newer head.

Files created or modified in this session:

- `server/pyproject.toml`
- `server/src/device_watch_server/core/config.py`
- `server/src/device_watch_server/enrollment/cli.py`
- `server/src/device_watch_server/enrollment/service.py`
- `server/tests/unit/test_bootstrap_cli.py`
- `server/tests/unit/test_bootstrap_service.py`
- `server/tests/unit/test_bootstrap_primitives.py`
- `server/tests/unit/test_bootstrap_migration.py`
- `server/tests/integration/test_bootstrap_persistence.py`
- `server/tests/integration/test_device_identity_migration.py`
- `docs/progress/current-status.md`

Provisioning and persistence handoff:

- Provision with `device-watch-bootstrap create --expires-in-minutes 15 --label rack-a`;
  revoke with `device-watch-bootstrap revoke <bootstrap-id>`. The ID and label
  are audit metadata, not secrets. There is no show/reprint, consume CLI, or
  public bootstrap-management route.
- Supply `DEVICE_WATCH_ENV`, `DATABASE_URL`, and
  `DEVICE_WATCH_BOOTSTRAP_HMAC_PEPPER` through protected operator configuration
  or secret-manager injection. The pepper must contain at least 32 UTF-8 bytes;
  operators must generate it randomly and restrict access to the provisioning
  account and configuration. No pepper value belongs in command arguments,
  URLs, shell history, logs, or labels. Revocation by ID needs no pepper.
- Use a trusted terminal without session recording or output capture. Transfer
  the initially displayed bootstrap through a protected out-of-band workflow.
  If delivery fails after commit, revoke its ID if available or let it expire;
  a retry creates new material and cannot recover the previous plaintext.
- Wire format is `dwb_v1_` followed by 43 unpadded base64url characters encoding
  32 cryptographically random bytes. Stored `digest_version` is
  `hmac-sha256-v1`; `digest` is 32-byte HMAC-SHA-256 over the domain tag
  `device-watch/bootstrap-digest/v1` plus a NUL byte and the random payload.
  The unique 32-byte SHA-256 lookup fingerprint uses the separate domain tag
  `device-watch/bootstrap-fingerprint/v1` plus NUL and payload. Only the HMAC
  verifies authorization. The pepper and plaintext are never persisted in rows.
- Default expiration is 15 minutes; overrides are positive integer minutes,
  with unrepresentable dates rejected. All bootstrap service timestamps are
  server-owned UTC seconds. Labels are optional, trimmed, and at most 120
  characters. Changing the pepper deliberately invalidates outstanding values.
- Available records must be unexpired, unconsumed, and unrevoked. Exact expiry
  is invalid; consumed/revoked states are terminal. Lookup locks the row before
  validation and a guarded transition. Repository and service functions never
  commit; the caller owns the transaction. Step 05 must compose bootstrap
  consumption and device creation in that same transaction when authorized.
- Preserved migration chain: `20260831_0001 -> 20260908_0002 -> 20260908_0003`.
  Revision 0003 creates only `enrollment_bootstraps`, with a UUID primary key,
  unique fingerprint, digest/version, label, four lifecycle timestamps, and
  expiry/terminal-state constraints. Its downgrade removes only that table.

Verification executed with the existing `server/.venv/Scripts/python.exe -B`
and host interpreter access (the sandbox could not access the base interpreter).
The local console entry point was registered offline using cached build
dependencies; no runtime dependencies or lockfile changed.

| Check | Result |
| --- | --- |
| Focused bootstrap unit tests plus directly affected settings/engine and Step 01/02 checks | **PASS** — 91 tests (67 bootstrap, 24 boundary/prerequisite), exit 0 |
| Server Ruff, sources/migrations/tests | **PASS** — exit 0 |
| Strict mypy on bootstrap sources, changed config, central engine, and new integration test | **PASS** — 8 files, exit 0 |
| Strict mypy on all server sources | **FAIL, pre-existing and outside Step 03** — only `core/logging.py:127`, missing `StreamHandler` type argument; 22 files checked |
| Real-MySQL bootstrap and affected Step 02 integration checks | **BLOCKED BY ENVIRONMENT** — 9 skipped (8 bootstrap, 1 identity); no `DATABASE_URL`, Docker, or MySQL runtime available |
| Focused independent security review | No blocking implementation defect found; subprocess configuration-redaction coverage gap corrected |
| Git handoff checks | **PASS** — status/diff reviewed and `git diff --check` clean |

Exact final check commands, run from the repository root:

```powershell
& server/.venv/Scripts/python.exe -B -m pytest server/tests/unit/test_bootstrap_cli.py server/tests/unit/test_bootstrap_service.py server/tests/unit/test_bootstrap_repository.py server/tests/unit/test_bootstrap_primitives.py server/tests/unit/test_bootstrap_migration.py server/tests/unit/test_config.py server/tests/unit/test_engine_tls.py server/tests/unit/test_device_identity_migration.py server/tests/unit/test_stage2_domain_contracts.py -q --tb=short
& server/.venv/Scripts/python.exe -B -m ruff check server/src server/alembic server/tests
& server/.venv/Scripts/python.exe -B -m mypy --config-file server/pyproject.toml server/src
& server/.venv/Scripts/python.exe -B -m mypy --config-file server/pyproject.toml server/src/device_watch_server/enrollment server/src/device_watch_server/core/config.py server/src/device_watch_server/db/engine.py server/tests/integration/test_bootstrap_persistence.py
& server/.venv/Scripts/python.exe -B -m pytest server/tests/integration/test_bootstrap_persistence.py server/tests/integration/test_device_identity_migration.py -q -rs --tb=short
git status --short
git diff --stat
git diff --check
```

The new MySQL module requires a dedicated disposable MySQL 8.x database and
`DEVICE_WATCH_ENV=test`. It rejects unknown schema objects/revisions before
migration, recreates only bootstrap storage, preserves device rows, and leaves
revision 0003 installed. Run it serially; do not point it at an application database.
Blocked runtime checks were not retried or represented as PASS. A standalone
mypy invocation for the new test initially could not discover typed local
sources; checking the test together with those sources passed without ignores.

The unrelated logging typing defect was not repaired. Tracked Python bytecode
rewritten by a subprocess check was restored byte-for-byte to its clean starting
state; subprocess tests now disable bytecode writes. No commit or branch change
was made. An unexpected, unrelated `.gitignore` trailing-whitespace/newline change
appeared during final checks; it was inspected and left untouched.

Step 03's requested implementation and available focused checks are complete,
but real-MySQL persistence and concurrency have not executed successfully here.
Full definition-of-done verification is therefore not confirmed; its master-index
row remains **Pending**, as requested. The next numbered step permitted on a new
explicit instruction is **Step 04 — Credential hashing and verification primitives**
(it depends on Step 01). Step 03 runtime re-verification remains outstanding;
Step 05 must not treat its blocked persistence evidence as PASS.
No Step 04, device credentials, enrollment/device-creation service or API, agent,
heartbeat, connectivity, metrics, or frontend behavior was implemented.

## Stage 2 Step 04 Completion — 2026-09-13

Status: **Complete — Step 04 definition of done satisfied**.

Executed only the credential-primitives card from clean HEAD `36106a1`.
The preceding Step 03 statements are its historical handoff. Its runtime
verification blocks remain unchanged; Step 04 depends on Step 01 and needs
no database execution. The Stage 1 baseline and historical evidence were preserved.

Implemented independently tested primitives in
`device_watch_server.auth.credentials`:

- `CredentialValue.parse()` / `to_wire()` define an 83-character format:
  `dwc_v1_<32 lowercase hex characters>_<43 unpadded base64url characters>`.
  The lookup ID uses 16 random bytes; the secret uses a separate 32 random
  bytes. Neither is derived from device identity. Parsing rejects unsupported
  versions, noncanonical encodings, wrong types/lengths, padding and whitespace.
- `issue_credential()` returns separate transient `CredentialValue` and
  hash-only `CredentialRecord` inputs. `hash_credential()` hashes only the secret
  with a fresh library-generated salt. The record carries key ID, encoded hash,
  and aware UTC created/revoked/replaced timestamps; no plaintext, device foreign
  key, last-used update, or database schema is introduced in this step.
- `verify_credential()` returns only a boolean. It rejects malformed/unknown,
  mismatched-ID, revoked, replaced, or unsupported-hash inputs. Native Argon2
  verification compares the secret; hashes are never compared with a custom
  password comparison. Stored PHC encodings must be exactly 97 characters with
  the supported parameters and canonical Base64 before native work begins.
- `revoke_credential()` returns an immutable terminal record and rejects repeated
  transitions or timestamps before creation. `rotate_credential()` prepares a
  fresh issuance plus the old record with equal revoked/replaced timestamps.
  The original remains unchanged, including if replacement hashing fails.
  **The future caller must validate current state and persist both rotation
  records in one transaction before delivering the replacement.** No writes,
  transaction service, HTTP authentication, or rotation API were added.
- Secret-bearing carriers mask their default string/repr output. Native hashing
  errors become `Credential operation failed` without chained diagnostics;
  verification errors return false. Callers must never log `.secret`,
  `.secret_hash`, or `to_wire()`, and must never serialize a persistence record
  as an API response. Plaintext remains transient for later one-time delivery.

Dependency and timing review:

- Added exact runtime pin `argon2-cffi==25.1.0`. The lock adds only
  `argon2-cffi-bindings==26.1.0`, `cffi==2.1.1`, and `pycparser==3.0` beneath it.
  A parsed comparison against HEAD confirmed zero existing locked versions
  changed. Installation and native hashing/verification succeeded on the
  existing CPython 3.12.10 Windows environment; no agent dependency was added.
- Parameters are explicit Argon2id version 19, 65,536 KiB memory, three passes,
  four lanes, 16-byte random salts, and 32-byte outputs. This implements the
  library's [RFC 9106 low-memory profile](https://raw.githubusercontent.com/hynek/argon2-cffi/25.1.0/src/argon2/profiles.py)
  rather than depending on mutable defaults. The
  [reviewed package](https://pypi.org/project/argon2-cffi/25.1.0/) supplies typed
  APIs and native bindings, avoiding a custom password-hash implementation.
- The [Python verification API](https://argon2-cffi.readthedocs.io/en/25.1.0/api.html#argon2.PasswordHasher.verify)
  trusts encoded hash parameters; the primitive therefore bounds and validates
  them before verification. The
  [native comparison](https://github.com/P-H-C/phc-winner-argon2/blob/f57e61e19229e23c4445b85494dbf7c07de721cb/src/argon2.c#L219)
  processes all hash bytes without an early mismatch exit. Malformed inputs,
  public lookup mismatches, and terminal states may return early: this is not
  an equal-time guarantee for future HTTP requests or database lookups.
  Allow 64 MiB per active hash operation when later services size concurrency.
  Any future hash-profile migration requires an explicit compatibility change.

Files created or modified:

- `server/src/device_watch_server/auth/__init__.py`
- `server/src/device_watch_server/auth/credentials.py`
- `server/tests/unit/test_credential_primitives.py`
- `server/pyproject.toml`
- `server/uv.lock`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`

Verification (repository root; existing interpreter used with host access):

| Check | Result |
| --- | --- |
| `python -B -m pytest server/tests/unit/test_credential_primitives.py server/tests/unit/test_stage2_domain_contracts.py -q --tb=short` | **PASS**, 49 tests: 42 credential and 7 prerequisite-contract tests |
| `python -B -m ruff check server/src/device_watch_server/auth server/tests/unit/test_credential_primitives.py` | **PASS**, exit 0 |
| `python -B -m mypy --config-file server/pyproject.toml server/src/device_watch_server/auth server/tests/unit/test_credential_primitives.py` | **PASS**, strict checking of 3 files, exit 0 |
| `uv tree --project server --locked --no-dev` | **PASS**, reviewed Argon2 chain and preserved existing runtime dependencies |
| `uv tree --project agent --locked --no-dev` | **PASS**, agent remains runtime-dependency-free |
| Dependency lock comparison against HEAD | **PASS**, only the four expected packages added; no prior version changed |
| Focused security/API review | **PASS**, no blocking defect; stored-hash canonical-encoding negative coverage added |
| `git status --short`, `git diff --stat`, `git diff`, `git diff --check` | **PASS**, only the listed files changed; no whitespace errors |

The `python` commands above used `server/.venv/Scripts/python.exe`. The tests
first failed on the absent auth module, then passed against the implementation
and pinned native library. Coverage includes secure random generation, repeated
hashing with fresh salts, wrong secrets/IDs, malformed values, unsupported or
excessive-cost hashes, noncanonical salt/digest encodings, lifecycle transitions,
immutable rotation, sanitized native failures, and log/representation redaction.

No Step 04 FAIL or environment block remains. The earlier full-server logging
annotation finding and Step 03 MySQL blocks are outside this scope and were not
repaired, rerun, or relabeled. No unchanged Stage 1 suite was re-audited. Only
Step 04 is marked Complete in the master index; Step 03 remains Pending.
Step 05 was not started. It requires a new explicit instruction and review of
its prerequisites, including the outstanding Step 03 persistence evidence.
No commit or branch change was made.

## Stage 2 Step 05 Implementation — 2026-09-13

Status: **Implementation present; required MySQL verification BLOCKED BY
ENVIRONMENT. Step 05 remains Pending; its full definition of done is not yet
verified.** No known implementation FAIL remains within this step.

Executed only the enrollment-transaction card. The session began at `e0b78f8`
and resumed from the user's `0ce8af2` WIP commit with a clean working tree.
Existing Step 01–04 work and the committed Step 05 implementation were
preserved. The preceding Step 04 handoff is historical. Step 03's outstanding
MySQL checks remain blocked; Step 04 remains Complete. The consolidated Stage 1
baseline and historical verification evidence were reused without modification
or a full re-audit of unchanged components.

Implementation and handoff contracts:

- `enrollment.transaction.enroll_device(engine, bootstrap_secret,
  configured_pepper, *, display_name, clock)` uses one `engine.begin()`
  connection for bootstrap consumption, UUIDv4 device insertion, and credential
  insertion. It composes the existing Step 03 HMAC/pepper validation and Step 04
  Argon2id issuance primitives without changing them.
- The existing bootstrap lookup performs `SELECT ... FOR UPDATE` followed by
  lifecycle validation and a guarded consume update. The live server clock is
  passed through so expiry is evaluated after obtaining the lock. The lock is
  held until the complete transaction commits or rolls back. No isolation-level
  override is introduced: the central MySQL engine retains the database's
  configured transactional isolation. **All three participating tables must use
  InnoDB**, which the MySQL fixture checks. No autocommit or SQLite alternative
  is introduced.
- Device creation and credential creation share an aware UTC timestamp rounded
  to whole seconds, matching existing MySQL `DATETIME` precision. Persistence
  explicitly converts to naive UTC; returned identity metadata remains aware
  UTC. The existing display-name and UUIDv4 contracts remain authoritative.
- `enrollment.persistence` exposes insert-only helpers that use the supplied
  connection and never commit independently. Only the public credential ID,
  device foreign key, Argon2id hash, and lifecycle timestamps are persisted.
  Bootstrap plaintext, device credential plaintext, and the pepper are never
  passed to these inserts.
- `EnrollmentResult` contains only device metadata and the transient
  `CredentialValue`; its repr/string output is redacted. The service returns
  it only after successful commit. No result contains a hash or bootstrap, and
  there is no stored plaintext from which to reconstruct a replay response.
- Error taxonomy: invalid bootstrap states, invalid identity values, issuance
  failures, and expected connection/storage/commit failures map to the single
  opaque `EnrollmentError("Enrollment failed")` with suppressed exception
  context. The service emits no logs. Transaction-body failures roll back all
  three effects. A commit exception returns no success; if the server committed
  before a connection failed, the outcome may be uncertain to the caller.
  There is no automatic retry or credential replay. Confirmed rollback leaves
  the bootstrap reusable while valid; uncertain commit or lost delivery needs
  operator recovery, never retrieval of the old credential.

The prerequisite schema contained no credential persistence. The minimal
Alembic extension required for this step is `20260913_0004`, following
`20260831_0001 -> 20260908_0002 -> 20260908_0003`. It creates only
`device_credentials`: a 32-character public key primary key, 36-character device
foreign key with restricted deletion, 97-character encoded hash, and
created/last-used/revoked/replaced timestamps. A nonunique device index permits
future credential replacement without implementing rotation here. Checks
reject use/revocation before creation and require replacement to coincide with
revocation. The new table explicitly uses InnoDB. Downgrade drops only this
table; earlier migrations are unchanged. The Step 03 offline migration test
now targets its own revision instead of the moving `head`, preserving its
original bootstrap-only assertions.

Files created or modified across the Step 05 session and continuation:

- `server/src/device_watch_server/enrollment/transaction.py`
- `server/src/device_watch_server/enrollment/persistence.py`
- `server/alembic/versions/20260913_0004_device_credentials.py`
- `server/tests/unit/test_enrollment_transaction.py`
- `server/tests/unit/test_credential_persistence_migration.py`
- `server/tests/unit/test_bootstrap_migration.py`
- `server/tests/integration/test_enrollment_transaction_mysql.py` (renamed from
  the WIP `test_enrollment_transaction.py` to avoid colliding with the unit module)
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`

Verification commands, run from the repository root using the existing
`server/.venv/Scripts/python.exe` with host access and `-B`:

```powershell
& server/.venv/Scripts/python.exe -B -m pytest server/tests/unit/test_enrollment_transaction.py server/tests/unit/test_credential_persistence_migration.py server/tests/unit/test_bootstrap_migration.py server/tests/unit/test_bootstrap_service.py server/tests/unit/test_bootstrap_repository.py server/tests/unit/test_bootstrap_primitives.py server/tests/unit/test_credential_primitives.py server/tests/unit/test_stage2_domain_contracts.py server/tests/unit/test_device_identity_migration.py -q --tb=short
& server/.venv/Scripts/python.exe -B -m pytest server/tests/unit/test_enrollment_transaction.py server/tests/integration/test_enrollment_transaction_mysql.py -q --tb=short -rs
& server/.venv/Scripts/python.exe -B -m ruff check server/src/device_watch_server/enrollment/transaction.py server/src/device_watch_server/enrollment/persistence.py server/alembic/versions/20260913_0004_device_credentials.py server/tests/unit/test_enrollment_transaction.py server/tests/unit/test_credential_persistence_migration.py server/tests/unit/test_bootstrap_migration.py server/tests/integration/test_enrollment_transaction_mysql.py
& server/.venv/Scripts/python.exe -B -m mypy --config-file server/pyproject.toml server/src/device_watch_server/enrollment/transaction.py server/src/device_watch_server/enrollment/persistence.py server/alembic/versions/20260913_0004_device_credentials.py server/tests/unit/test_enrollment_transaction.py server/tests/unit/test_credential_persistence_migration.py server/tests/integration/test_enrollment_transaction_mysql.py
```

| Check | Result |
| --- | --- |
| Focused unit, prerequisite, and offline MySQL-dialect migration tests | **PASS**, 119 tests, exit 0; includes 12 enrollment service cases and 2 new credential migration cases |
| Combined unit/MySQL module collection and execution | **12 PASS**, **6 BLOCKED BY ENVIRONMENT** (pytest skips), exit 0; missing `DATABASE_URL` prevents all real-MySQL cases |
| Scoped Ruff check | **PASS**, 7 Python files, exit 0 |
| Strict mypy | **PASS**, 6 Step 05 Python files, exit 0 |
| Transaction/security review | **PASS** within inspected code; hash-bearing test assertions changed to fixed diagnostics, then reviewed again with no remaining concrete defect |
| Final Git status/diff/stat/whitespace inspection | **PASS**, only scoped continuation changes; `git diff --check` reports no whitespace errors |

Unit coverage checks the shared connection and commit-before-return ordering,
real Argon2 hash verification against captured insert parameters, redaction,
begin/device-insert/credential-insert/commit failure mapping, rollback behavior
at the service boundary, invalid bootstrap/identity, issuance failure, and UTC
and post-lock clock handling. Doubles do not prove database atomicity.

The six MySQL cases cover success and replay rejection, four simultaneous
consumers with exactly one winner, rollback after each real insert, expiry
advancing while a row lock is awaited, and revision downgrade/upgrade plus
database key/lifecycle constraints. They require an empty, dedicated disposable
MySQL 8.x database, protected `DATABASE_URL`, `DEVICE_WATCH_ENV=test`, and
`DEVICE_WATCH_DISPOSABLE_DATABASE=1`. The fixture refuses unknown schemas,
revisions, views, and pre-existing rows before mutation. It cleans only its
test rows and leaves revision `20260913_0004` installed. Docker/MySQL commands
were unavailable when checked in this session; no unrelated installation or
infrastructure repair was attempted. Skips are not database PASS evidence.

Intermediate failures were resolved within scope: the bootstrap test followed
the moving migration head, duplicate unit/integration module names blocked
combined mypy, and the new integration module needed four type annotations and
import ordering. The earlier full-server logging annotation finding remains
outside scope and was not repaired, rerun, or relabeled. No full-server quality
gate is claimed.

Full Step 05 acceptance still requires the real-MySQL checks above; retain its
Pending matrix status and the Step 03 persistence evidence block. The next
permitted continuation is that outstanding verification in a suitable
environment. Step 06 remains unstarted and requires a separate explicit request
and review of these prerequisites. No HTTP endpoint, agent enrollment,
heartbeat, connectivity, metric, or frontend behavior was added. No commit or
branch change was made by the agent. Stop after this handoff.

## Stage 2 Step 06 Completion — 2026-09-13

Status: **Complete — Step 06 API-layer definition of done satisfied.**

Executed only the enrollment API card from clean HEAD `d343676`. The user's
commit preserved the completed Step 05 implementation work; its commit title
does not supersede the recorded real-MySQL verification block. The explicit
Step 06 request authorized API work using those implemented service contracts,
without treating the outstanding persistence checks as proved. Steps 03 and 05
remain Pending. The preceding Step 05 handoff is historical.

Implemented `POST /api/v1/enrollment` through the existing versioned router and
app factory. The synchronous handler executes the blocking transaction through
FastAPI's worker-thread handling. Factory wiring supplies the configured
bootstrap pepper and one shared, centrally constructed engine to the existing
Step 05 service. Readiness uses that same cached engine. Lazy initialization is
protected by a lock; lifespan still owns disposal. An injected readiness check
retains its existing health behavior. The transaction, credential primitives,
bootstrap primitives, MySQL/TLS configuration, migrations, and deployment files
were not changed.

Wire contract and handoff:

- All four JSON request fields are required; extra fields are rejected.
  `protocol_version` must be integer `1`, including rejection of boolean,
  floating-point, and string equivalents. `bootstrap_secret` must be the
  canonical 50-character Step 03 wire value. It is held as `SecretStr` in the
  request model. `display_name` and `agent_version` must be strings of 1–120 and
  1–64 characters respectively, trimmed and nonblank. Length limits apply before
  trimming, consistent with the existing domain contract. Agent version is
  validated here; storing the latest version remains later heartbeat work.
- A committed success returns **201** with exactly `protocol_version`,
  `device_id`, `display_name`, `credential`, and `created_at`. The returned
  identity is UUIDv4 with the service's UTC timestamp. Explicit field mapping
  excludes lifecycle, bootstrap, hash, and persistence records. The credential
  is exposed only in this success response; its model representation is masked.
  This is the approved one-time delivery exception to the specification's
  general credential-absence language, not permission to expose it elsewhere.
- Invalid/missing fields, malformed JSON, invalid UTF-8, unsupported protocol,
  non-JSON bodies, and the service's opaque `EnrollmentError` return **400** with
  exactly `{"detail":"Enrollment failed"}`. Invalid, expired, consumed, and
  revoked bootstraps already converge on that error at the service boundary.
  Expected database/issuance errors that Step 05 maps to `EnrollmentError` also
  receive 400; no internal failure taxonomy is exposed.
- Unexpected service or response-validation/serialization failures return
  **500** with the same generic body. A route-local `APIRoute` wrapper prevents
  FastAPI's default detailed validation body or exception diagnostics from
  exposing input or transient output. Its intentional final `Exception` catch
  has a narrowly documented Ruff exception for this secret boundary. Other
  routes retain their existing exception handling.
- Success and handled failures set `Cache-Control: no-store`. OpenAPI documents
  the request, five-field success, and generic failures without the default
  detailed 422 validation schema. The existing request middleware still emits
  only normalized route metadata; no body, authorization header, bootstrap,
  credential, or error traceback is logged by this endpoint.
- There is no enrollment replay or automatic service retry. A response lost or
  failing serialization after commit does not make the bootstrap reusable;
  callers need operator recovery for an uncertain outcome. A failure response
  never retrieves or redisplays the earlier credential.

Deployment assumptions are unchanged: agents use outbound **HTTPS** to Caddy;
Caddy preserves `/api/*` while proxying to the private FastAPI service. TLS
terminates at Caddy, so the internal upstream may use HTTP. No public backend
port, new proxy route, authentication system, or TLS workaround was added.
Production OpenAPI remains disabled. The existing Caddy route and server launch
configuration were inspected for this boundary; no container runtime check or
broader deployment re-audit was performed.

Files created or modified:

- `server/src/device_watch_server/api/enrollment.py`
- `server/src/device_watch_server/api/enrollment_schemas.py`
- `server/src/device_watch_server/api/router.py`
- `server/src/device_watch_server/app.py`
- `server/tests/unit/test_enrollment_api.py`
- `server/tests/unit/test_app.py` (current route allowlist only)
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`

Verification (repository root, existing host-access interpreter):

```powershell
& server/.venv/Scripts/python.exe -B -m pytest server/tests/unit/test_enrollment_api.py server/tests/unit/test_app.py server/tests/unit/test_step06_logging_cli.py server/tests/unit/test_enrollment_transaction.py -q --tb=short
& server/.venv/Scripts/python.exe -B -m ruff check server/src/device_watch_server/api/enrollment.py server/src/device_watch_server/api/enrollment_schemas.py server/src/device_watch_server/api/router.py server/src/device_watch_server/app.py server/tests/unit/test_enrollment_api.py server/tests/unit/test_app.py
& server/.venv/Scripts/python.exe -B -m mypy --config-file server/pyproject.toml server/src/device_watch_server/api/enrollment.py server/src/device_watch_server/api/enrollment_schemas.py server/src/device_watch_server/api/router.py server/src/device_watch_server/app.py server/tests/unit/test_enrollment_api.py
```

| Check | Result |
| --- | --- |
| Focused pytest suite | **PASS**, 66 tests: 40 API, 8 app/health/lifespan, 6 existing logging/CLI, and 12 Step 05 service tests; exit 0 |
| Scoped Ruff | **PASS**, 6 Python files, exit 0 |
| Strict mypy | **PASS**, 5 changed/new source and API-test files, exit 0; legacy app-test annotations remain outside this source-focused gate |
| Independent API/security review | **PASS**, no concrete correctness, security, or scope defect found |
| Final Git status, diff, diff-stat, and whitespace checks | **PASS**, only the eight scoped files changed; no whitespace errors |
| Real MySQL atomicity, concurrency, rollback, and migration evidence | **BLOCKED BY ENVIRONMENT**, inherited from Steps 03/05; unchanged and not rerun or relabeled by Step 06 |

The initial API run failed because the route and factory wiring were absent
(37 failed, 7 existing tests passed). The final suite covers required fields,
strict types/version, canonical bootstrap format, text bounds, malformed body
shapes/encoding, success projection, service rejection without replay output,
generic unexpected and response-validation failures, log capture, model
representations, OpenAPI, route allowlist, health regressions, and shared engine
ownership/disposal. API tests isolate the service boundary; they do not replace
the pending MySQL tests or establish full A03/A05/A16 runtime acceptance.

Two warnings come from the already pinned TestClient dependency stack:
Starlette's `httpx` deprecation and AnyIO's `BlockingPortal` alias deprecation.
No dependency installation or unrelated warning repair was performed. The
earlier full-server logging annotation finding was not repaired or relabeled;
no full-server mypy gate is claimed. Historical Stage 1 evidence is unchanged;
the affected current health/router/lifecycle behavior was checked by the focused
regressions above. No Step 06 implementation FAIL remains.

Only Step 06 is newly marked Complete. Step 07 requires a separate explicit
request; no agent storage/enrollment, heartbeat, connectivity, metrics, UI,
operator/RBAC, listing, or credential-rotation endpoint was started. No commit
or branch change was made. Stop after this handoff.

## Stage 2 Step 07 Implementation — 2026-09-14

Status: **Implementation present and Windows verified; Linux runtime verification
BLOCKED BY ENVIRONMENT. Step 07 remains Pending; its definition of done is not
fully verified across the implemented platforms.** No confirmed implementation
FAIL remains in this step.

Executed only secure agent identity storage from clean HEAD `e84f2d3`. The
interrupted inspection/design sessions had no Step 07 source changes; work
resumed without discarding existing files. Read the execution card, approved
storage specification, Step 01 identity contracts, current master/status, and
consolidated Stage 1 baseline. Unchanged server, deployment, frontend, and Stage 1
historical verification evidence were preserved. Step 03/05 MySQL blocks remain
unchanged and are not prerequisites for these local file checks.

Configuration and file contract:

- Added `DEVICE_WATCH_AGENT_IDENTITY_PATH`, exposed as
  `AgentSettings.identity_path`. It requires an absolute local file path;
  relative/traversing/NUL paths are rejected. Windows also rejects UNC paths,
  alternate data streams, reserved DOS names, and trailing dots/spaces. Errors
  do not echo the configured value. No server URL or credential default exists.
- Default Linux path: `/var/lib/device-watch-agent/identity.json`. Default
  Windows path: `%LOCALAPPDATA%/DeviceWatch/identity.json`, using the current
  user's `AppData/Local` directory if that variable is absent. A dedicated
  service account must own the identity directory. Operators must provision the
  Linux default directory for that account when `/var/lib` is not writable.
  Storage can create the immediate private parent when permitted; ancestors
  must already exist. Existing unsafe directories are rejected, never repaired.
- `AgentIdentity` validates UUIDv4, the canonical 83-character `dwc_v1_` wire
  credential, and an aware creation timestamp normalized to UTC. It does not
  generate identities/credentials or import server code. The frozen carrier's
  default repr/string hides all fields.
- The UTF-8 JSON file contains exactly `version`, `device_id`, `credential`, and
  `created_at`. File version is integer `1`; duplicate/extra/missing fields,
  boolean/float versions, noncanonical UUID/credential encodings, naive/invalid
  timestamps, and UTC conversion overflow are rejected. Reads are limited to
  4,096 bytes with an extra sentinel-byte check, so a valid JSON prefix cannot
  hide oversized input. No database, metrics, bootstrap material, or backup
  schema is introduced.

Persistence and transition contract:

- `IdentityStore(path).load()` returns an `AgentIdentity` for a valid protected
  file, `None` only for missing storage, and the generic
  `IdentityError("Identity storage unavailable")` for malformed/unsafe storage.
  It creates no directories during reads and retains no cached credential.
- `save(identity)` validates existing storage before replacement. It creates an
  exclusive, private temporary file in the same directory, writes/flushes/fsyncs
  it, closes it, then atomically replaces the destination. The previous valid
  file survives failures before replacement. Cleanup deletes only a temporary
  file created by that attempt, including on simulated fsync/replace failure;
  an exclusive-create collision never deletes an existing file.
- Only the configured final filename is read. No backup or fallback copy is
  maintained. A process killed before replacement can leave a protected
  temporary file; it is never treated as an enrolled identity. The helper does
  not sweep unrelated temporary files. One writer per identity path is the
  supported agent usage contract.
- `invalidate()` checks protected storage, deletes the file without making a
  backup, and returns `IdentityState.REENROLLMENT_REQUIRED`. The future caller
  must discard its in-memory identity and stop authenticated sends. Failure to
  delete raises the same generic storage error and must also fail closed.
  Missing storage makes this transition idempotent. Deletion is ordinary file
  removal, not a promise of forensic erasure or remote credential revocation.
  No automatic enrollment or HTTP-status handler is added in this step.

Permission behavior:

- POSIX: require the current effective user to own the immediate directory with
  mode `0700` and the regular, single-link file with mode `0600`. Traverse using
  directory descriptors and `O_NOFOLLOW`, rejecting untrusted writable ancestors
  except root-owned sticky traversal directories such as `/tmp`. File reads use
  descriptor checks and nonblocking open so special files cannot hang the
  reader. Replacement/deletion use the held parent descriptor; directory fsync
  follows committed updates. Linux execution remains unverified here.
- Windows: use standard-library `ctypes` and native security APIs. New
  directories/files receive an explicit protected owner-only DACL before any
  plaintext is written. Validate the actual opened object's owner, DACL, file
  type, reparse attributes, and link count. Reject broad/inherited ACLs, junctions,
  and hard links. Directory handles pin all ancestors against rename while an
  operation runs. This does not rely on
  [Windows `chmod`, which only controls the read-only flag](https://docs.python.org/3.12/library/os.html#os.chmod).
  The native checks use [GetSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo)
  and replacement uses [MoveFileEx with write-through](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw).
  There is no portable Windows directory-fsync equivalent; deletion durability
  through power loss is not promised. Same-user processes and privileged
  administrators remain outside the account-based file protection boundary.
- A post-replacement durability error can occur after the new file is visible;
  callers must treat the operation as uncertain and reload before relying on it.
  No plaintext or raw OS exception is logged by these modules.

Files created or modified:

- `agent/src/device_watch_agent/identity.py`
- `agent/src/device_watch_agent/_identity_posix.py`
- `agent/src/device_watch_agent/_identity_windows.py`
- `agent/src/device_watch_agent/config.py`
- `agent/tests/test_identity.py`
- `agent/tests/test_identity_windows.py`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`

Verification used the existing server test-tool interpreter because no agent
virtual environment exists. `PYTHONPATH` points exclusively at the agent source
for these commands; no server runtime dependency is imported or added to the
agent. Agent runtime dependencies remain empty, with pyproject/lock unchanged.

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'agent/src')
& server/.venv/Scripts/python.exe -B -m pytest agent/tests -q --tb=short -rs
& server/.venv/Scripts/python.exe -B -m ruff check agent/src/device_watch_agent agent/tests
& server/.venv/Scripts/python.exe -B -m mypy --config-file agent/pyproject.toml agent/src/device_watch_agent agent/tests/test_identity.py agent/tests/test_identity_windows.py
& server/.venv/Scripts/python.exe -B -m mypy --platform linux --config-file agent/pyproject.toml agent/src/device_watch_agent/identity.py agent/src/device_watch_agent/_identity_posix.py agent/src/device_watch_agent/config.py agent/tests/test_identity.py
```

| Check | Result |
| --- | --- |
| Agent pytest suite | **PASS**, 69 tests: 31 shared storage/configuration, 11 native Windows ACL/filesystem, and 27 existing agent tests; 2 POSIX skips remain blocked, exit 0 |
| Agent Ruff | **PASS**, source and tests, exit 0 |
| Native Windows strict mypy | **PASS**, 14 source/test files, exit 0 |
| Linux-platform strict mypy | **PASS**, 4 files, exit 0; static typing does not prove Linux filesystem behavior |
| Security review and focused regressions | **PASS** within reviewed scope; oversized JSON-prefix acceptance and UTC timestamp overflow reproduced and corrected |
| Linux/POSIX permissions, ownership, symlink/FIFO runtime tests | **BLOCKED BY ENVIRONMENT**, 2 tests skipped; `wsl.exe --list --quiet` exited 1 because WSL is not installed; Docker was unavailable; no installation attempted |
| Final Git status/diff/stat/whitespace checks | **PASS**, only the eight scoped files changed; historical Stage 1 evidence and agent dependency files unchanged |

The first new tests failed on missing modules. Native Windows tests also caught
and verified a fix for metadata-only directory handles failing to prevent
rename. Final tests cover restart, exact schema, malformed/oversized data,
canonical formats, timezone bounds, private ACLs, link/junction rejection,
interrupted writes, exclusive creation, deletion/invalidation, and the unchanged
agent lifecycle/collector behavior. Permission-unsafe or malformed storage
returns no usable identity; no authenticated transport exists in this slice.

Step 07 implementation is ready for its outstanding Linux verification; retain
Pending until that runtime permission boundary is checked. Step 08 requires a
separate explicit request and prerequisite review. No agent HTTP enrollment,
heartbeat, metrics, credential generation, server changes, or local database
was started. No commit or branch change was made. Stop after this handoff.

## Stage 2 Step 08 Completion — 2026-09-14

Status: **Complete at the agent enrollment-client boundary.** The current user
explicitly authorized Step 08 using the existing Step 07 implementation, with
Step 07 remaining verification-pending. The previous section is the historical
Step 07 handoff; its Linux/runtime evidence was not reopened or relabeled.

Implemented only outbound enrollment and its configuration, command, and tests:

- `device-watch-agent --enroll` (or `python -m device_watch_agent --enroll`)
  performs one explicit enrollment action and exits. An existing valid identity
  is loaded before any network request or requirement for enrollment inputs.
  Repeating the command after successful persistence therefore sends no POST.
  Ordinary service startup does not initiate enrollment, even if bootstrap
  configuration remains present. Do not configure a service supervisor to
  repeat `--enroll`; the command is an operator action.
- In addition to the existing `DEVICE_WATCH_AGENT_MODE=service` and identity
  path, first enrollment requires `DEVICE_WATCH_AGENT_SERVER_URL`,
  `DEVICE_WATCH_AGENT_BOOTSTRAP_SECRET`, and `DEVICE_WATCH_AGENT_DISPLAY_NAME`.
  All three default to absent. The URL must be an HTTPS origin, optionally with
  a trailing slash, without user info, path prefix, query, or fragment. Bootstrap
  input uses the canonical server wire format and is excluded from settings
  representations. Display names are nonblank, at most 120 characters, and
  trimmed consistently with the server. Secrets are not command-line arguments.
- The client sends exactly `protocol_version`, `bootstrap_secret`,
  `display_name`, and package-version value `agent_version=0.1.0` to
  `POST /api/v1/enrollment`. Only a `201` JSON response with the exact five-field
  response contract is accepted. Version/type, display name, canonical UUIDv4,
  credential, and aware timestamp validation precede the existing
  `IdentityStore.save()` atomic handoff. Malformed/unsafe existing storage
  prevents enrollment. No Step 07 source or tests were changed by this task.
- Added pinned runtime dependency `httpx==0.28.1` and updated `agent/uv.lock`
  offline. Existing locked package versions were preserved. HTTPS certificate
  verification remains enabled; redirects, environment proxies/netrc, and
  transport-level retries are disabled. The enrollment client controls retries.
- Connect/pool timeouts are **5 seconds**; read/write timeouts are **10 seconds**.
  Each network attempt also has a **30-second total deadline**. There are at most
  **3 attempts**, with **0.5-second and 1-second** cancellable delays, exclusively
  for connection-establishment errors/timeouts. No HTTP response, read/write
  failure, protocol failure, or total deadline triggers a replay. Timeout and
  retry choices follow the [HTTPX timeout](https://www.python-httpx.org/advanced/timeouts/)
  and [transport](https://www.python-httpx.org/advanced/transports/) contracts.

Enrollment state and shutdown handoff:

- Missing identity starts `UNENROLLED`; missing explicit inputs or exhausted
  safe connection retries leave it `UNENROLLED` and return a sanitized error.
- A configured action becomes `ENROLLING`, then `ENROLLED` only after accepting
  and storing the issued identity. A valid stored identity goes directly to
  `ENROLLED`, without network traffic.
- Unsafe/malformed storage, non-201 responses, invalid success responses,
  uncertain send/read/timeout outcomes, and storage failure after a response
  move to `REENROLLMENT_REQUIRED`. Further calls on that client cannot replay.
  There is no automatic restart enrollment or persisted bootstrap/recovery
  credential. The operator must reconcile a possibly committed enrollment and
  obtain a fresh bootstrap when necessary; a lost response is not recoverable
  by retrying this API. The command returns 1 for an enrollment/configuration
  failure and logs only generic diagnostics and state.
- Stop signals supported by the existing event-loop handlers cancel and await
  the pending enrollment operation; cancellation closes the async HTTP client
  and conservatively requires recovery. Keyboard interruption retains the
  entry point's clean-exit behavior. Network I/O and retry waits are cancellable;
  once a response is accepted, the short synchronous atomic storage operation
  finishes without an intervening await. No collector orchestration or
  authenticated sender was added.

Files created or modified for Step 08:

- `agent/src/device_watch_agent/transport/__init__.py`
- `agent/src/device_watch_agent/transport/enrollment.py`
- `agent/src/device_watch_agent/config.py`
- `agent/src/device_watch_agent/main.py`
- `agent/tests/test_enrollment.py`
- `agent/pyproject.toml`
- `agent/uv.lock`
- `docs/progress/current-status.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`

Focused verification (repository root, existing host-access interpreter):

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'agent/src')
$step08Temp=Join-Path '.tmp' ('step08-final-' + [guid]::NewGuid().ToString('N'))
& server/.venv/Scripts/python.exe -B -m pytest agent/tests/test_enrollment.py agent/tests/test_config.py agent/tests/test_main.py -q --tb=short -p no:cacheprovider --basetemp $step08Temp
& server/.venv/Scripts/python.exe -B -m ruff check agent/src/device_watch_agent/config.py agent/src/device_watch_agent/main.py agent/src/device_watch_agent/transport agent/tests/test_enrollment.py
& server/.venv/Scripts/python.exe -B -m mypy --config-file agent/pyproject.toml --cache-dir .tmp/step08-mypy agent/src/device_watch_agent/config.py agent/src/device_watch_agent/main.py agent/src/device_watch_agent/transport agent/tests/test_enrollment.py
& .tmp/uv-tool/Scripts/uv.exe lock --project agent --check --offline --python 'C:/Users/dkmah/AppData/Local/Programs/Python/Python312/python.exe'
```

| Check | Result |
| --- | --- |
| Step 08 and directly affected pytest | **PASS**, 71 tests: 57 enrollment/configuration/command tests, 13 existing configuration tests, 1 existing signal-wiring test; no skips; exit 0 |
| Scoped Ruff | **PASS**, Step 08 source and tests |
| Strict mypy | **PASS**, 5 source/test files; initial dynamic test-field typing errors corrected |
| Agent lockfile consistency | **PASS**, offline check resolved 21 packages; all six HTTP dependency versions in the test environment match the agent lock |
| Bounded Step 08 acceptance check | **PASS**, no directly blocking Step 08 defect identified |

The first enrollment test run failed because the transport module was absent;
the command/shutdown tests then failed on missing entry-point wiring. Final
tests use fake HTTP server/transport responses and failure traces, with real
protected storage for the enrollment-to-restart path. They cover exact request
shape, validation, safe bounded retry exhaustion, no replay after uncertain
outcomes, redirects/HTTP errors, sanitized logs/errors, storage failure, and
transport cleanup on cancellation. This evidence does not claim a live
Caddy/MySQL end-to-end check or Linux permission verification.

No Step 08 blocker remains. No new out-of-scope finding was investigated or
repaired. The inherited Step 07 Linux evidence gap and Steps 03/05 MySQL blocks
remain unchanged. The initial Step 07 identity source/test hashes were preserved.
No Step 07 tests, repository-wide suite, broad review, or Step 09 work was run.
Existing work was preserved, including externally recorded commit `f537b0d`
during this session; the agent made no commit or branch change. Stop here.

## Stage 2 Step 09 Completion — 2026-09-14

Status: **Complete at the heartbeat-contract boundary; Step 09 definition of done
satisfied.** Resumed clean HEAD `43f5f54` (`stage02: wip step 09`). That commit
already contained the Step 09 source and tests, while the master index still
said Pending and the preceding handoff said it had not started. Those labels
were stale; fresh focused verification and this handoff establish current status.
Existing implementation and earlier completed work were preserved without
source changes, commits, or branch changes.

The existing implementation defines exact minimal v1 request/response models,
strict versions and UUID/timestamp validation, forbidden extra fields, sanitized
parsers/failure responses, and a pure current-state decision. A duplicate of the
latest submission ID preserves all stored fields. A different ID updates only
latest submission/version and monotonic server-derived last-seen. Observation
time is diagnostic only. Retention is one latest ID per device, with no TTL or
history; older IDs outside that slot are treated as new. Acknowledgements report
this attempt's receipt time. Authentication and atomic application remain caller
obligations for later steps.

The [Step 09 execution card](../superpowers/plans/2026-09-08-device-watch-stage-2/09-heartbeat-contracts.md)
now records all three JSON schemas, compatibility/normalization rules, retention
limits, response semantics, and the server/agent handoff. No agent dependency or
contract module is needed to consume these language-independent wire rules.

Files changed in this resume session:

- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/09-heartbeat-contracts.md`
- `docs/superpowers/plans/2026-09-08-device-watch-stage-2/00-master-index.md`
- `docs/progress/current-status.md`

Preserved implementation verified: `server/src/device_watch_server/domain/contracts.py`,
`server/src/device_watch_server/domain/heartbeat.py`,
`server/tests/unit/test_heartbeat_contracts.py`, and
`server/tests/unit/test_stage2_domain_contracts.py`.

Focused verification (repository root):

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'server/src')
& server/.venv/Scripts/python.exe -B -m pytest server/tests/unit/test_heartbeat_contracts.py server/tests/unit/test_stage2_domain_contracts.py -q --tb=short -p no:cacheprovider
```

- **PASS**, 83 tests (76 heartbeat-contract cases and 7 directly affected domain
  cases), no failures or skips, exit 0. Coverage includes serialization,
  validation, schemas, forbidden fields, sanitized errors without logging,
  duplicate-ID handling, latest-slot/device scoping, and monotonic timestamps.
- The initial sandbox invocation could not reach the venv's base interpreter.
  The identical focused command passed with approved host access to the existing
  interpreter. No interpreter, dependency, or infrastructure was installed or
  repaired; no environment block remains for Step 09.
- **PASS**, bounded independent static review of only heartbeat/domain contracts
  and their tests: no concrete Step 09 acceptance blocker. This does not claim
  authentication, database, transport, or later-step runtime verification.
- **PASS**, all three documented JSON schemas parsed and matched generated model
  structural schemas exactly, after omitting annotations and inlining the status
  enum. The card requires no Ruff/mypy command; no broader static or test suite
  was run.
- **PASS**, `git diff --check`; final status/stat/diff inspection found only the
  three intended documentation changes and no source or test modifications.

Blockers: **None for Step 09**. Out-of-scope findings: **None newly identified**.
The inherited Steps 03/05 MySQL and Step 07 Linux evidence blocks remain unchanged
and do not block this pure contract step. No previous-step verification area was
reopened. No route, migration, persistence, sender, retry implementation, metrics,
history, collector, or UI behavior was added. Step 10 remains Pending. Stop here.
