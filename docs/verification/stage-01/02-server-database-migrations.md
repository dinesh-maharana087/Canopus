# Stage 1 Verification V02 - Server, Database, and Migrations

## Targeted re-verification after R2A-R2C

Date: 2026-09-10
Repository state: committed R2A/R2B repairs through `dc85419`, plus the
uncommitted R2C test-harness repair
Scope: Stage 1 Steps 04-07 only

Current overall result: **PASS WITH ENVIRONMENT BLOCKS**.

- **PASS:** all implementation, static, no-network, and available test contracts.
- **FAIL:** none.
- **BLOCKED BY ENVIRONMENT:** actual Docker Compose rendering/startup, MySQL
  health/connectivity, and the real baseline migration cycle.

This section supersedes the original result below for the current repository
state. The original 2026-09-09 verification is retained as historical defect
evidence. V07 and the consolidated Stage 1 baseline were not updated in this
task.

### Current result mapping

| Step | Contract | Result | Current evidence |
| --- | --- | --- | --- |
| 04 | Development MySQL image, sample environment, loopback port, named volume, health check, and isolation | **PASS** | The unchanged Compose definition retains the previously verified static contracts. The repaired test now invokes `docker compose ... config --format json`, parses the result, and asserts the rendered structures. |
| 04 | Host-environment isolation for development samples | **PASS** | A focused regression pollutes all four `MYSQL_*` interpolation variables with harmless values and proves none reach the Compose subprocess environment. |
| 04 | Actual Compose render, MySQL startup, and health | **BLOCKED BY ENVIRONMENT** | The single `docker version` availability check found no Docker executable. The rendered-topology test therefore recorded one explicit environment skip. |
| 05 | FastAPI factory uses the versioned router | **PASS** | `create_app()` includes `api_router`; the focused factory regression passed. |
| 05 | Liveness, database-backed readiness, generic failure, and owned-engine disposal | **PASS** | Focused application tests passed without a network connection. |
| 06 | Newline-delimited structured request logging, approved field set, and redaction | **PASS** | Focused tests parsed one JSON object per output line, accepted only `normalized_path`, and found no synthetic query/header/cookie secret. |
| 06 | Readiness warning event | **PASS** | The failure path emits `database_readiness_failed`; the focused log-record assertion passed. |
| 06 | Database-check CLI output, exit codes, redaction, and disposal | **PASS** | Focused success/failure tests passed with exact generic output. |
| 07 | Empty metadata and deterministic constraint naming | **PASS** | The regression generated deterministic PK/FK/UQ/CK/index names and confirmed `Base.metadata.tables == {}`. |
| 07 | Behavior-free scoped baseline and single settings source | **PASS** | The unchanged `20260831_0001` revision remains the scoped Stage 1 baseline and `sqlalchemy.url` remains empty in `alembic.ini`. |
| 07 | Validated Alembic URL/TLS boundary, percent-safe URL handling, and script resolution | **PASS** | Offline percent-URL and repository-root path tests passed; a no-network online test reached PyMySQL with the three approved TLS arguments, boolean verification flags, and no competing `ssl` mapping. |
| 07 | Configured integration environment reaches the migration test | **PASS** | With credential-free external settings, the selected integration regression passed and performed no database connection. |
| 07 | Real MySQL connectivity and `upgrade -> base -> upgrade` cycle | **BLOCKED BY ENVIRONMENT** | The prescribed development MySQL service cannot be started without Docker; no connection or migration mutation was attempted. |

### Repaired findings

| Finding | Result | Repair evidence |
| --- | --- | --- |
| V02-01 rendered topology test | **PASS** | The test consumes actual Compose JSON rather than YAML text and sanitizes host interpolation variables. Its live execution is separately environment-blocked. |
| V02-02 versioned router | **PASS** | R2A route-boundary regression passed. |
| V02-03 logging framing/fields | **PASS** | R2A multi-record and request-field regressions passed. |
| V02-04 readiness event | **PASS** | R2A event regression passed. |
| V02-05 CLI contract | **PASS** | R2A exact-output regressions passed. |
| V02-06 metadata convention | **PASS** | R2B deterministic-name regression passed. |
| V02-07 TLS and percent URLs | **PASS** | R2B offline and no-network driver-boundary regressions passed. |
| V02-08 Alembic script path | **PASS** | R2B repository-root `ScriptDirectory` regression passed. |
| V02-09 integration fixture | **PASS** | Integration-marked tests retain `DEVICE_WATCH_ENV` and `DATABASE_URL`; non-integration tests remain isolated and optional settings are still cleared. |

### Commands and results

| Command/check | Result |
| --- | --- |
| `docker version` | **BLOCKED BY ENVIRONMENT** - command not found; checked once and not retried. |
| Focused pytest over `test_development_mysql.py`, `test_app.py`, `test_step06_logging_cli.py`, and `test_alembic_configuration.py` | **PASS** - 19 passed, 1 Docker-dependent skip, 2 dependency deprecation warnings. |
| Selected configured integration-environment preservation test | **PASS** - 1 passed; credential-free URL, no connection attempted. |
| Focused Ruff over Step 04-07 source/configuration tests | **PASS** - all checks passed. |
| V02 source-focused mypy plus the changed topology/fixture files | **PASS** - no issues in 13 files. |
| Polluted-host Compose-environment regression before/after sanitization | Expected red/green evidence: 1 failed before the repair, then passed. |
| Extra exploratory mypy including legacy test modules | Four pre-existing Pydantic-constructor annotation errors in `test_app.py` and `test_alembic_baseline.py`; outside the established V02 source-focused mypy scope and not changed as part of R2C. |

### Current defects and environment blocks

No V02 implementation **FAIL** remains in the requested Steps 04-07 scope.
Docker/Compose is unavailable, so the actual rendered document, live MySQL
health/connectivity, and baseline migration cycle remain **BLOCKED BY
ENVIRONMENT** and must not be represented as PASS.

An independent focused review found and then verified the repair for host
`MYSQL_*` precedence at the Compose subprocess boundary. It found no remaining
R2C defect. The historical `current-status.md` statement that rendering was
already verified was contradicted by the original V02 evidence; the test is now
correct, but live rendering is still blocked.

---

## Original verification - 2026-09-09

Date: 2026-09-09

Scope: Stage 1 Steps 04-07 only

Overall result: **FAIL**

Step results: **Step 04 FAIL; Step 05 FAIL; Step 06 FAIL; Step 07 FAIL**.
Docker/MySQL runtime checks are additionally **BLOCKED BY ENVIRONMENT**.

No source was changed. No agent, frontend, Caddy, later Stage 1 step, or Stage 2
implementation was reviewed.

## Inherited baseline context

V01 was read only as inherited context and was not re-audited. In particular,
V01-03 already records that uppercase settings names fail on case-sensitive POSIX
environments. That inherited defect also affects the module-level ASGI app and
Alembic's call to `load_settings()`; it is not counted again as a V02 defect.

## Components reviewed

- Approved design, master-index entries, current-status entries, execution cards,
  and original-plan sections directly relevant to Steps 04-07.
- The MySQL service portion of `deploy/compose.dev.yml`,
  `deploy/.env.dev.example`, and the focused Step 04 topology test.
- FastAPI factory, health routes, database probe, lifecycle ownership, logging,
  middleware, CLI, and their focused unit tests.
- `Base` metadata, `server/alembic.ini`, `server/alembic/env.py`, the
  `20260831_0001` baseline revision, and its baseline-specific integration test.

Newer migration files were not opened or assessed. The pinned baseline target in
the integration test was treated as the correct isolated V02 scope; repository
`head` now belongs to later work.

## Results

| Step | Contract | Result | Evidence |
| --- | --- | --- | --- |
| 04 | MySQL 8.4.11 development service definition | **PASS** | `deploy/compose.dev.yml` lines 2-24 define the pinned image, development env, health check, and isolated service configuration. |
| 04 | Loopback binding and development volume | **PASS** | `127.0.0.1:3307:3306` is at line 14; `mysql_dev_data` is mounted/declared at lines 16 and 53-55. |
| 04 | Conspicuous development-only sample credentials | **PASS** | `deploy/.env.dev.example` lines 1-4 use explicit root/dev sample values. No production import was found in the scoped MySQL definition. |
| 04 | Rendered/structural topology test | **FAIL** | The committed test searches raw text instead of inspecting rendered Compose data; see V02-01. |
| 04 | Compose render, MySQL startup, and health | **BLOCKED BY ENVIRONMENT** | The single `docker version` check failed because Docker is unavailable. No retry was made. |
| 05 | FastAPI application factory and injected database check | **PASS** | `create_app()` is at `app.py` lines 19-60; focused TestClient behavior passed. |
| 05 | Process-only liveness | **PASS** | Exact `200 {"status":"ok"}` behavior and zero database calls passed in `test_app.py`. |
| 05 | Database-backed readiness and generic failure | **PASS** | Success returns 200; a database `RuntimeError` returns exact generic `503 {"status":"unavailable"}` without exception/URL content. A no-network probe confirmed `check_database()` executes `SELECT 1`. |
| 05 | Owned engine lifecycle/disposal | **PASS** | Factory lifespan uses `finally` and disposes its internal engine at `app.py` lines 35-44; the focused test passed. |
| 05 | Versioned router is the application routing boundary | **FAIL** | `api_router` exists but the factory bypasses it and duplicates direct route registration; see V02-02. |
| 06 | Request secret redaction | **PASS** | An actual TestClient request with query/header/cookie secrets logged none of the synthetic values. Payload sanitization tests also passed. |
| 06 | Newline-delimited one-record-per-line JSON | **FAIL** | Two emitted records produced two JSON objects and zero newline delimiters; see V02-03. |
| 06 | Approved request-log fields | **FAIL** | Runtime output contains both `path` and `normalized_path`; the raw duplicate is outside the approved request fields. See V02-03. |
| 06 | Fixed readiness failure warning | **FAIL** | Required `database_readiness_failed` is absent; the lower database layer emits a different event. See V02-04. |
| 06 | Database-check CLI exit codes, `SELECT 1`, disposal, and redaction | **PASS** | No-network probes returned 0/1, disposed on both paths, executed `SELECT 1`, and excluded the synthetic secret. |
| 06 | Exact generic CLI status contract | **FAIL** | Actual messages differ from the approved strings and real failure also emits a JSON record; see V02-05. |
| 07 | Schema-empty metadata | **PASS** | A fresh scoped import reported `metadata_table_count=0`. |
| 07 | Deterministic metadata naming convention | **FAIL** | Metadata has only SQLAlchemy's default index convention and no explicit PK/FK/UQ/CK convention; see V02-06. |
| 07 | Behavior-free baseline revision | **PASS** | `20260831_0001`, `down_revision=None`, and docstring-only upgrade/downgrade bodies are at baseline lines 10-21. |
| 07 | No duplicate URL in `alembic.ini` | **PASS** | `server/alembic.ini` line 3 leaves `sqlalchemy.url` empty. |
| 07 | Same validated URL/settings source | **PASS** | `server/alembic/env.py` imports and calls `load_settings()`; V01's inherited POSIX-name defect still applies. |
| 07 | Same validated online connection arguments | **FAIL** | Online Alembic creation bypasses the verified connect-argument boundary; see V02-07. |
| 07 | URL-safe Alembic configuration | **FAIL** | A valid percent-encoded credential/query URL fails at `set_main_option()`; see V02-07. |
| 07 | Alembic repository-root command configuration | **FAIL** | The documented `Config("server/alembic.ini")` context resolves a nonexistent root `alembic` directory; see V02-08. |
| 07 | Configured real-MySQL integration test can execute | **FAIL** | The autouse fixture deletes `DATABASE_URL`, so an explicitly configured run skips; see V02-09. |
| 07 | Live baseline migration cycle | **BLOCKED BY ENVIRONMENT** | Docker/MySQL is unavailable. No database connection or migration mutation was attempted. |

## Defects discovered

### V02-01 - Step 04 topology test does not test rendered topology

**FAIL.** The approved plan requires assertions against a rendered configuration
dictionary (`2026-08-31-device-watch-stage-1.md` line 518), and the Step 04 card
requires a rendered topology test at line 29. The current test reads raw files and
checks substrings (`deploy/tests/test_development_mysql.py` lines 13-34). It cannot
prove actual service structure, port/volume placement, health-check structure, or
environment interpolation.

Affected file: `deploy/tests/test_development_mysql.py`.

### V02-02 - Step 05 factory bypasses its versioned router

**FAIL.** The Step 05 scope includes a versioned router (card line 17).
`api/router.py` lines 9-10 assemble `api_router`, but `app.py` lines 57-58 register
the health functions directly and never include that router. Current endpoint
behavior passes, but the approved routing boundary is dead code rather than the
factory's extension point.

Affected files: `server/src/device_watch_server/app.py`,
`server/src/device_watch_server/api/router.py`.

### V02-03 - Step 06 request logs violate record and field contracts

**FAIL.** Both setup branches set `handler.terminator = ""`
(`core/logging.py` lines 153 and 158). A two-record probe produced:

```text
json_objects 2 newline_delimiters 0
```

The records concatenate and are not newline-delimited JSON. The middleware also
emits both raw `path` and `normalized_path` (`core/middleware.py` lines 25, 37-38,
and 50-51), although the plan permits only normalized path among request-path
fields (original plan line 475). The focused middleware test at
`test_step06_logging_cli.py` lines 92-106 makes a request but captures and asserts
no log output, while the one-record formatter test explicitly expects raw `path`.

Affected files: `server/src/device_watch_server/core/logging.py`,
`server/src/device_watch_server/core/middleware.py`,
`server/tests/unit/test_step06_logging_cli.py`.

### V02-04 - Step 06 required readiness warning event is absent

**FAIL.** The approved event is exactly `database_readiness_failed` (original plan
line 475). `api/health.py` lines 28-35 returns the generic response without logging,
while `db/health.py` line 19 emits `database_unavailable`. A scoped search found no
`database_readiness_failed` implementation or assertion.

Affected files: `server/src/device_watch_server/api/health.py`,
`server/src/device_watch_server/db/health.py`, and
`server/tests/unit/test_app.py`.

### V02-05 - Step 06 CLI output differs from its stable contract

**FAIL.** The plan requires only `database connectivity: ok` or
`database connectivity: unavailable` (original plan line 475). `cli.py` lines 33
and 36 instead emit `Database check failed` and `Database is ready`. The no-network
probe confirmed exact output, correct exit codes, and disposal. With the real
`check_database()` failure path, stdout also contains a safe JSON
`database_unavailable` record before the stderr message. The focused test accepts
the implementation-specific phrases instead of enforcing the approved strings.

Affected files: `server/src/device_watch_server/cli.py`,
`server/tests/unit/test_step06_logging_cli.py`.

### V02-06 - Step 07 metadata lacks the approved naming convention

**FAIL.** The plan requires a `DeclarativeBase` with a deterministic naming
convention (original plan line 558). `db/base.py` lines 5-9 declares a bare base.
Runtime inspection showed only SQLAlchemy's built-in index convention:

```text
{'ix': 'ix_%(column_0_label)s'}
```

There is no explicit deterministic convention for primary keys, foreign keys,
unique constraints, or check constraints.

Affected file: `server/src/device_watch_server/db/base.py`.

### V02-07 - Step 07 Alembic bypasses the validated connection boundary

**FAIL.** The plan requires the validated URL and `connect_args` online (original
plan line 558). `alembic/env.py` imports only `load_settings()`, inserts the raw
secret value at line 18, and calls `engine_from_config()` at lines 41-45 without
validated PyMySQL arguments. Production migrations therefore do not inherit the
Step 03 boolean TLS boundary.

The raw ConfigParser handoff also rejects percent-encoded values. A no-network
probe using a URL with an encoded password and CA path failed in
`Config.set_main_option()` with `ValueError: invalid interpolation syntax`.

Affected file: `server/alembic/env.py`; missing regression coverage in
`server/tests/integration/test_alembic_baseline.py`.

### V02-08 - Step 07 Alembic script location fails from repository root

**FAIL.** `server/alembic.ini` line 2 sets `script_location = alembic`. Matching the
documented and test context, `ScriptDirectory.from_config(Config("server/alembic.ini"))`
from the repository root failed with:

```text
Path doesn't exist: alembic.
```

The configured path resolves against the repository root rather than the
configuration file's directory, so the committed CLI/integration invocation cannot
locate `server/alembic`.

Affected file: `server/alembic.ini`.

### V02-09 - Step 07 integration fixture always removes database configuration

**FAIL.** The autouse fixture in `server/tests/conftest.py` lines 6-14 deletes
`DATABASE_URL` for every server test. The integration test reads that variable and
skips when absent (`test_alembic_baseline.py` lines 18-21). A no-network diagnostic
started pytest with a deliberately invalid, present sentinel URL; the test still
reported:

```text
SKIPPED: DATABASE_URL is not configured for integration testing
```

Thus a configured real-MySQL cycle cannot execute under the committed test setup,
independently of the current Docker environment block.

Affected files: `server/tests/conftest.py`,
`server/tests/integration/test_alembic_baseline.py`.

## Commands actually executed

| Command/check | Result |
| --- | --- |
| `git status --short --untracked-files=all` (initial) | **PASS** - only pre-existing `AGENTS.md` and V01 evidence were untracked. |
| `docker version` | **BLOCKED BY ENVIRONMENT** - executable not found; checked once only. |
| focused pytest for Step 04 topology, Step 05 app, and Step 06 logging/CLI | **PASS** - 11 passed, 2 dependency deprecation warnings. |
| focused Ruff check over Step 04-07 source/tests | **PASS** - all checks passed. |
| focused mypy over 9 Step 05-07 source files | **PASS** - no issues found. |
| actual request-log synthetic-secret probe | **PASS** redaction; **FAIL** approved field set because raw `path` is present. |
| two-record JSON logging probe | **FAIL** - two objects, zero newline delimiters. |
| fake-engine `SELECT 1` probe | **PASS**. |
| fake-engine CLI success/failure/disposal probe | **PASS** exit/disposal/redaction; **FAIL** exact output strings. |
| `Base.metadata` table-count probe | **PASS** - zero tables. |
| metadata naming-convention probe | **FAIL** - only the default index convention exists. |
| Alembic `ScriptDirectory` repository-root probe | **FAIL** - script path does not exist. |
| Alembic percent-encoded URL probe | **FAIL** - ConfigParser interpolation error. |
| integration test with present invalid sentinel `DATABASE_URL` | **FAIL** - 1 skipped because the fixture deleted the variable; no network attempted. |
| `git diff --check` (final) | **PASS**. |
| `git status --short` (final) | **PASS with inherited files** - V02 adds only this evidence document; `AGENTS.md` and V01 were already untracked. |

The initially proposed combined unit/integration invocation was rejected before
process creation because the integration test can mutate an arbitrary configured
database. After Docker was confirmed unavailable, no live database test or
migration command was attempted.

## Environment block

**BLOCKED BY ENVIRONMENT:** Docker and Docker Compose are unavailable, so V02 could
not render Compose, start/health-check MySQL, test live connectivity, inspect live
tables/revisions, or execute the real baseline upgrade/base/upgrade cycle. The
availability check was performed once and was not retried. No Docker/MySQL software
was installed.

## Stable source locations

- Development MySQL definition: `deploy/compose.dev.yml` lines 2-24 and 53-55;
  sample inputs: `deploy/.env.dev.example` lines 1-4.
- Factory/lifecycle: `server/src/device_watch_server/app.py` lines 19-60.
- Health and database probe: `server/src/device_watch_server/api/health.py` and
  `server/src/device_watch_server/db/health.py`.
- Logging and CLI: `server/src/device_watch_server/core/logging.py`,
  `server/src/device_watch_server/core/middleware.py`, and
  `server/src/device_watch_server/cli.py`.
- Migration metadata/configuration: `server/src/device_watch_server/db/base.py`,
  `server/alembic.ini`, and `server/alembic/env.py`.
- Scoped baseline: `server/alembic/versions/20260831_0001_baseline.py`.

Future work must not treat the rendered topology test, versioned router boundary,
request-log record/schema contract, readiness event, CLI messages, deterministic
metadata convention, Alembic connection/path handling, or real-MySQL integration
harness as verified until these failures are resolved in a separately authorized
implementation session.
