# Device Watch Stage 1 Status

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

## Current Recommendation

The next coding session must remain strictly at Step 06 only if the user explicitly requests it after Step 05's verification; this session did not start any later step.

## Step Status

Steps 01, 02, 03, 04, and 05 are Complete. Steps 06 through 17 remain Pending. No implementation beyond Step 05 has started.

At each handoff, record the completed step, files changed, commands and results, environment limitations, commit identifier, and the next permitted step here. Do not mark a step complete based only on planned work.
