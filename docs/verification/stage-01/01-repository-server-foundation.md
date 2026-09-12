# Stage 1 Verification V01 — Repository and Server Foundation

## R5C repository safeguard repair - 2026-09-12

Base revision: `1b440ac755503155e3f74be6e24787fafa0856e6`
(`stage01:wip R5c repaire`), which includes the preserved user changes and
the preceding V07 remap. Scope: local-database files and operator-managed
environment files only, with committed environment examples kept trackable.

**R5C requested repair: PASS.** Before the repair, repository-only
`git check-ignore --no-index -v` returned exit 1 with no matches for
`device-watch.sqlite`, `local.db`, and `deploy/.env.prod`. The current
`.gitignore` lacked the previously approved database and environment rules.

The repair adds only these two groups to `.gitignore`:

```gitignore
# Operator-managed environment files; keep committed examples trackable.
.env
.env.*
!.env.example
!.env.*.example

# Local databases and their journal/WAL sidecars.
*.db
*.db-*
*.sqlite
*.sqlite-*
*.sqlite3
*.sqlite3-*
```

Existing tool/editor rules are preserved. No application, Stage 2, dependency,
deployment, example, or operator file was changed. No database/environment
fixture was created, and no tracked file was removed from the index.

### Focused regression verification

Every case was checked separately using
`git -c core.excludesFile=NUL check-ignore --no-index -q -- <path>`.
Expected exit status is 0 for an ignored path and 1 for a trackable path;
any other result fails the check. Global excludes were disabled, and
`--no-index` ensures committed examples do not mask incorrect ignore rules.

| Check | Result |
| --- | --- |
| Local database files and sidecars | **PASS — 16/16.** Root `.db`, `.sqlite`, `.sqlite3` files; each family's `-journal`, `-wal`, and `-shm` sidecars; and nested `server/local.db`, `server/local.db-wal`, `agent/state/device-watch.sqlite`, `agent/state/local.sqlite3-shm`. |
| Operator environment files | **PASS — 6/6.** `.env`, `.env.local`, `deploy/.env.prod`, `deploy/.env.prod.local`, `deploy/.env.dev`, `server/.env.production`. |
| Trackable examples/configuration | **PASS — 8/8.** `.env.example`, `agent/.env.example`, `deploy/.env.dev.example`, `deploy/.env.prod.example`, `.env.prod.example`, `deploy/.env.prod.local.example`, `server/.env.production.example`, `deploy/version.env`. |
| Exact reported failures, verbose confirmation | **PASS — exit 0.** `device-watch.sqlite` matches `*.sqlite`, `local.db` matches `*.db`, and `deploy/.env.prod` matches `.env.*`, all from the repository `.gitignore`. |
| Committed example preservation | **PASS.** `git ls-files --error-unmatch` confirms all four committed `.env*.example` files remain tracked; `git diff --quiet HEAD` confirms those files and `deploy/version.env` are unchanged. |

The two PowerShell assertion matrices exited 0: **22/22 protected paths and
8/8 trackable paths passed**. These checks exercise Git's actual matcher and
provide the focused regression evidence without adding a test harness or
requiring Python, Docker, or MySQL. No broad test suite was run.

This section supersedes only the local-database/environment ignore failures
recorded in the earlier V01/V07 evidence. Other safeguard categories mentioned
by V07, including keys, virtual environments, caches, dependencies, build output,
and coverage, were outside the explicitly requested R5C scope and were not
restored or classified as passing. This is not an overall V01 PASS or a new
criterion 9 remap. V05 records the corresponding operator-env result. V07 and
the final Stage 1 baseline are unchanged by this repair.

## Earlier V01 re-verification (historical)

Date: 2026-09-09

Scope: Stage 1 Steps 01–03 only

Overall result after R1 re-verification: **FAIL**

V01 status: **NOT REPAIRED / NOT VERIFIED**. All four implementation failures from
the initial pass remain present in the checked-out tree. No V01 repair commit,
tracked repair-path diff, or repair stash was available to verify at `HEAD`
`91a52e0`.

## R1 re-verification

Scope was limited to the four reported V01 failures and their existing focused
regression checks. The final Stage 1 baseline was read for inherited context but was
not modified.

| Repaired finding | Result | Current evidence |
| --- | --- | --- |
| `httpx` dependency classification | **FAIL** | `server/pyproject.toml` still declares `httpx==0.28.1` in `[project].dependencies`, not the `test` group. `server/uv.lock` still records it as a direct runtime dependency, and the frozen `--no-dev` tree contains top-level `httpx`, `httpcore`, and `certifi`. |
| Local-database/editor ignore rules | **FAIL** | Repository `.gitignore` still has no local-database or editor-metadata patterns. With the global excludes file disabled, none of `device-watch.sqlite`, `local.db`, `.vscode/settings.json`, or `.idea/workspace.xml` matched; `git check-ignore` exited 1. |
| POSIX uppercase settings handling | **FAIL** | `Settings` still combines lowercase fields with `case_sensitive=True` and no uppercase aliases. A case-sensitive mapping containing `DEVICE_WATCH_ENV` and `DATABASE_URL` produced `uppercase_keys []` and exited 1. |
| SQLAlchemy pool option assertions | **FAIL** | The no-network runtime probe still confirms `(pool._pre_ping, pool._recycle) == (True, 1800)`, but `server/tests/unit/test_engine_tls.py` still contains no assertion for `pool_pre_ping`, `pool_recycle`, `_pre_ping`, or `_recycle`; the scoped search exited 1. |

### Focused regression results

| Command/check | Result |
| --- | --- |
| workspace `uv ... tree --project server --no-dev --frozen` | **FAIL** contract check — the locked runtime tree still includes direct `httpx`. |
| repository-only `git check-ignore --no-index` for the four required safeguard examples | **FAIL** — no path matched. |
| case-sensitive `EnvSettingsSource` uppercase-name probe | **FAIL** — `uppercase_keys []`. |
| scoped pool-assertion search in `server/tests/unit/test_engine_tls.py` | **FAIL** — no committed pool-option assertion found. |
| workspace `uv ... pytest server/tests/unit/test_config.py server/tests/unit/test_engine_tls.py -q` | **PASS** — 14 passed in 0.71s. |
| workspace `uv ... ruff check` on the V01 configuration/engine source and tests | **PASS** — all checks passed. |
| workspace `uv ... mypy` on `core/config.py` and `db/engine.py` | **PASS** — no issues in 2 source files. |
| no-network engine pool probe | **PASS** — `pool_options (True, 1800)`. |
| `git diff --check -- docs/verification/stage-01/01-repository-server-foundation.md` | **PASS** — the V01 evidence update has no whitespace error. |
| repository-wide `git diff --check` | **FAIL outside V01 scope** — pre-existing user modification `AGENTS.md:548` has a blank line at EOF; the file was not changed in this session. |
| `git status --short` | V01 evidence modified as intended; pre-existing modified `AGENTS.md` and untracked `stage-01-baseline.md` remain untouched. |

The first sandboxed Python invocation could not reach the existing host interpreter;
the identical locked, offline command succeeded with approved host-interpreter
access. No dependency or system software was installed. There are no unresolved
environment blocks for this R1 re-verification.

### R1 re-verification commands actually executed

- `git status --short`; `git log -10 --oneline --decorate`; scoped `git diff` and
  reachable-ref/stash searches for R1 changes.
- workspace `uv --offline --no-python-downloads tree --project server --no-dev --frozen`.
- `git -c core.excludesFile=NUL check-ignore --no-index -v -- device-watch.sqlite local.db .vscode/settings.json .idea/workspace.xml`.
- workspace `uv ... pytest server/tests/unit/test_config.py server/tests/unit/test_engine_tls.py -q`.
- workspace `uv ... ruff check` on the four V01 source/test files.
- workspace `uv ... mypy server/src/device_watch_server/core/config.py server/src/device_watch_server/db/engine.py`.
- case-sensitive `EnvSettingsSource` uppercase-name characterization using the
  locked server environment.
- scoped `rg` assertion search in `server/tests/unit/test_engine_tls.py`.
- no-network SQLAlchemy engine pool characterization using the locked server
  environment.
- `git diff --check`; scoped evidence-file `git diff --check`; `git diff --stat`;
  `git status --short`.

## Original V01 evidence (initial pass)

Initial step results: **Step 01 FAIL; Step 02 FAIL; Step 03 FAIL**. Step 03's
implemented runtime behavior passed, but its required committed regression coverage
did not.

No implementation was changed during the initial pass and no Stage 1 baseline was
created then. V01 found four contract defects. Docker/Compose availability and the
supported Node runtime check also had environment blocks.

## Components reviewed

- Approved Stage 1 design sections for repository boundaries, configuration,
  backend engine ownership, verification, safeguards, and acceptance.
- Stage 1 master-index entries, current-status entries, and execution cards for
  Steps 01–03.
- The original implementation-plan constraints and Task 1/Task 2 portions consumed
  by those cards.
- Root safeguards and project metadata: `.gitignore`, `.dockerignore`,
  `.editorconfig`, `.env.example`, `README.md`, both `pyproject.toml`/`uv.lock`
  pairs, and `web/package.json`/`package-lock.json`.
- Step 02–03 implementation and focused tests in
  `server/src/device_watch_server/core/config.py`,
  `server/src/device_watch_server/db/engine.py`, `server/tests/conftest.py`,
  `server/tests/unit/test_config.py`, and
  `server/tests/unit/test_engine_tls.py`.

No Step 04–17, frontend implementation, deployment configuration, Caddy,
unrelated agent implementation, or Stage 2 behavior was reviewed.

## Results and stable contracts

| Step | Contract | Result | Evidence |
| --- | --- | --- | --- |
| 01 | Repository component boundaries | **PASS** | The five approved component roots exist; agent, server, and web have separate manifests. Design lines 40–50. |
| 01 | Independent agent/server Python projects | **PASS** | `agent/pyproject.toml` and `server/pyproject.toml` define distinct packages and environments. |
| 01 | Independent frozen Python locks | **PASS** | Both `uv sync --frozen` commands and both locked tree commands completed. The agent runtime tree contains only `device-watch-agent`. |
| 01 | Frontend package lock | **PASS** | `npm ci --ignore-scripts --no-audit --no-fund` completed from `web/`; `npm ls --omit=dev --depth=0` resolved the three runtime packages. |
| 01 | Runtime/development dependency separation | **FAIL** | Agent and web are separated, but server declares test-only `httpx==0.28.1` as runtime metadata; see V01-01. |
| 01 | Environment, key, virtualenv, cache, dependency, build, and coverage safeguards | **PASS** | Repository `.gitignore` lines 1–20 were exercised with `git check-ignore`; the allowlist-style `.dockerignore` was inspected directly. |
| 01 | Local-database and editor-artifact safeguards | **FAIL** | The design requires both categories (design line 368), but repository `.gitignore` has neither; see V01-02. |
| 02 | Required `DEVICE_WATCH_ENV` under its documented uppercase name | **FAIL** | The field has no default, but uppercase input is not discovered by a case-sensitive POSIX settings source; see V01-03. |
| 02 | Accepted modes are exactly `development`, `test`, and `production` | **PASS** | `Environment` contains exactly those values (`config.py` lines 13–18); focused tests passed. |
| 02 | Required `DATABASE_URL` under its documented uppercase name | **FAIL** | The field has no default and is secret-typed, but the same POSIX name-casing defect prevents uppercase discovery; see V01-03. |
| 02 | Exact `mysql+pymysql` enforcement | **PASS** | `make_url` output is checked for the exact driver at `config.py` lines 61–73; focused tests passed. |
| 02 | Production TLS validation | **PASS** | The exact three values are defined at `config.py` lines 25–29 and raw query pairs are checked at lines 85–97, including duplicate/additional rejection. |
| 02 | Credential/URL-safe representations and validation errors | **PASS** | `SecretStr`, hidden validation input, sanitized `load_settings()`, and redaction tests passed. |
| 03 | Centralized application engine creation | **PASS** | The sole application `create_engine()` call is in `db/engine.py` lines 41–49; application callers use the factory. |
| 03 | Connection pre-ping and 1,800-second recycling | **PASS** | Source lines 46–47 and a no-network V01 engine probe confirmed `_pre_ping=True` and `_recycle=1800`. |
| 03 | Production TLS reaches the PyMySQL boundary as exact flat boolean arguments | **PASS** | The 14-test focused suite passed the locked translation and `do_connect` capture assertions. |
| 03 | No competing/incorrect SSL mapping | **PASS** | `database_engine_url()` strips validated query keys before translation; tests confirmed no nested `ssl` mapping at the driver boundary. |
| 03 | TLS characterization requires no network connection | **PASS** | The `do_connect` listener raises `ConnectionIntercepted` before driver I/O; the focused test passed. |
| 03 | Required committed regression coverage for engine options | **FAIL** | Engine behavior is correct, but the execution-card definition of done requires engine options to be tested and no pool-option assertion exists; see V01-04. |

## Defects discovered

### V01-01 — Step 01 server runtime includes test-only `httpx`

**FAIL.** The approved runtime table contains exactly Alembic, FastAPI, Pydantic
Settings, PyMySQL, SQLAlchemy, and Uvicorn; the following plan sentence places
server-specific `httpx` with the `test` dependency group
(`2026-08-31-device-watch-stage-1.md` lines 172–185). Current
`server/pyproject.toml` instead lists `httpx==0.28.1` in runtime dependencies at
line 13 and omits it from the test group at lines 23–29. The lock consequently
records it in `requires-dist` at `server/uv.lock` lines 144–151, and the
runtime-only tree includes `httpx`, `httpcore`, and `certifi`.

Affected files: `server/pyproject.toml`, `server/uv.lock`.

### V01-02 — Step 01 ignore rules omit two required safeguard categories

**FAIL.** The approved design says ignore rules cover local databases and editor
artifacts (`2026-08-31-device-watch-stage-1-design.md` line 368).
Repository `.gitignore` lines 1–20 contain no corresponding patterns. With the
global Git excludes file disabled, `git check-ignore --no-index` matched the
positive-control private/generated paths but did not match `device-watch.sqlite`,
`local.db`, `.vscode/settings.json`, or `.idea/workspace.xml`.

Affected file: `.gitignore`.

### V01-03 — Step 02 documented uppercase settings fail on POSIX

**FAIL.** `Settings` combines lowercase field names with
`case_sensitive=True` (`config.py` lines 35–44), while the stable external
contract uses uppercase `DEVICE_WATCH_ENV` and `DATABASE_URL`. A case-sensitive
`EnvSettingsSource` probe against the locked Pydantic Settings 2.15.0 returned no
keys for the uppercase mapping and returned both keys for the lowercase mapping:

```text
uppercase_keys []
lowercase_keys ['database_url', 'device_watch_env']
```

Windows environment lookup is case-insensitive, so the committed Windows test run
does not expose the production Linux failure. Correctly supplied uppercase
variables will be reported missing before engine construction on POSIX.

Affected file: `server/src/device_watch_server/core/config.py`; coverage gap in
`server/tests/unit/test_config.py`.

### V01-04 — Step 03 pool options lack required committed regression assertions

**FAIL.** The Step 03 execution card requires pre-ping and 1,800-second recycling
at line 32 and states that engine options are tested at line 42. The implementation
is correct (`db/engine.py` lines 46–47), and the V01 no-network probe passed, but a
targeted search of `server/tests` found no assertion for `pool_pre_ping`,
`pool_recycle`, `_pre_ping`, or `_recycle` in the Step 03 unit tests.

Affected file: `server/tests/unit/test_engine_tls.py`.

## Commands actually executed

| Command/check | Result |
| --- | --- |
| `git status --short` (initial) | **PASS** — only pre-existing untracked `AGENTS.md`. |
| workspace `uv --version`; `node --version`; `npm.cmd --version` | **PASS** — uv 0.12.6, Node v22.14.0, npm 10.9.2. |
| `Get-Command docker` | **BLOCKED BY ENVIRONMENT** — Docker/Compose unavailable. |
| workspace `uv ... sync --project agent --frozen` | **PASS**. |
| workspace `uv ... sync --project server --frozen` | **PASS**. |
| workspace `uv ... tree --project agent --no-dev --locked` | **PASS** — agent package only. |
| workspace `uv ... tree --project server --no-dev --locked` | **FAIL** contract check — runtime tree contains test-only `httpx`. |
| `npm.cmd ci --ignore-scripts --no-audit --no-fund` from `web/` | **PASS** — 275 packages; emitted the Node engine warning below. |
| `npm.cmd ls --omit=dev --depth=0` from `web/` | **PASS** — React, React DOM, and React Router only. |
| workspace `uv ... pytest server/tests/unit/test_config.py server/tests/unit/test_engine_tls.py -q` | **PASS** — 14 passed in 0.47s. |
| workspace `uv ... ruff check` on Step 02–03 source/tests | **PASS** — all checks passed. |
| workspace `uv ... mypy` on `core/config.py` and `db/engine.py` | **PASS** — no issues in 2 source files. |
| case-sensitive `EnvSettingsSource` uppercase/lowercase probe | **FAIL** — uppercase produced zero fields; lowercase produced both fields. |
| no-network engine pool/URL probe | **PASS** — pre-ping, recycle, and configured URL fields confirmed. |
| scoped `rg` scan for application `create_engine()` calls | **PASS** — one centralized production call. |
| repository-only `git check-ignore -v --no-index` safeguard probe | **FAIL** — local-database/editor paths unmatched. |
| `git diff --check` (final) | **PASS**. |
| `git diff --stat`; `git diff` (final) | **PASS** — no tracked-file change; the evidence document is untracked. |
| `git status --short` (final) | **PASS with pre-existing item** — new V01 evidence document plus pre-existing untracked `AGENTS.md`. |

The first sandboxed npm cache access and an offline Ruff dependency lookup were
retried successfully using the existing host cache and the committed locked test
dependency set. No system software was installed.

## Environment blocks

- **BLOCKED BY ENVIRONMENT:** Docker and Docker Compose are not installed or not
  available on `PATH`, so the Step 01 tool-version check could not run. No Step
  01–03 functional verification requires Docker.
- **BLOCKED BY ENVIRONMENT:** Node v22.14.0 is below React Router 8.3.1's declared
  minimum of Node 22.22.0 (`web/package-lock.json` lines 3769–3778). The frozen
  install completed with `EBADENGINE`, but supported frontend runtime compatibility
  cannot be claimed on this host.

## Source locations for dependent stages

- Project and lock contracts: `agent/pyproject.toml`, `agent/uv.lock`,
  `server/pyproject.toml`, `server/uv.lock`, `web/package.json`, and
  `web/package-lock.json`.
- Environment enum, production TLS constants, settings validation, and safe loader:
  `server/src/device_watch_server/core/config.py` lines 13–117.
- Flat production driver arguments, sanitized engine URL, and engine factory:
  `server/src/device_watch_server/db/engine.py` lines 15–49.
- Current focused characterization suites:
  `server/tests/unit/test_config.py` and
  `server/tests/unit/test_engine_tls.py`.

Future stages must not treat the Step 01 dependency/safeguard contracts, the
uppercase POSIX settings-loading path, or the Step 03 pool-option regression
coverage as verified until the defects above are resolved in a separately
authorized implementation session.
