# Stage 1 Verification V06 - Security and documentation

Date: 2026-09-09  
Scope: Stage 1 Steps 15-16 only  
Revision inspected: `fb88657c7a14a30e967cf13797ad005765499d96`  
Overall result: **FAIL**

The current repository tree was verified as-is. Source code was not modified. The locked Python environment could not be invoked inside the sandbox, and the required external-access request was rejected because the workspace approval service was out of credits. Consequently, the fresh repository-verifier and audit-test executions are classified as **BLOCKED BY ENVIRONMENT**; they were not retried through another execution path.

## R4C targeted documentation re-verification - 2026-09-11

Base revision: `60db4a8` plus the R4C worktree changes.

Repair scope: stale current-state/future-contract wording, native server
development mode, production environment-file guidance, and V06
re-verification only.

R4C documentation repair result: **PASS**.

Overall V06 result: **FAIL** remains unchanged because the current repository
still contains the three SQLite test-engine implementations reported by the
positive database allowlist. R4C does not alter those Stage 2 tests.

| R4C contract | Result | Current evidence |
| --- | --- | --- |
| Historical Stage 1 versus current repository state | **PASS** | README and architecture wording now identify the Stage 1 completion scope as historical while describing the current partial Stage 2 server foundation separately. Approved Stage 1 specifications, plans, progress history, and original verification evidence were not rewritten. |
| Staged/future capability wording | **PASS** | `docs/future-contracts.md` preserves the required ordered sequence, identifies the implemented device/bootstrap contracts, `devices` and `enrollment_bootstraps` tables, and bootstrap lifecycle services, and keeps public enrollment, stable device credentials, heartbeat/connectivity, monitoring/history, evaluation, and alerts explicitly future. |
| Native server development mode | **PASS** | Both PowerShell and POSIX native Uvicorn workflows now set `DEVICE_WATCH_ENV=development`; the optional MySQL integration-test workflow still sets `test`. All 11 focused settings tests pass. |
| Production environment-file guidance | **PASS** | `deploy/.env.prod.example` is documented only as a template. Actual production commands use the ignored operator-managed `deploy/.env.prod` path, whose ignore behavior was confirmed with `git check-ignore`. |
| R4B repository-audit implementation | **PASS** | All 9 focused audit tests pass. The current-scope audit reports only the three known SQLite test modules and no credential/private-key finding; documentation consistency was inspected separately. Historical Stage 1 scope also reports the current Stage 2 migrations/modules, as designed. |

### R4C V06 commands and results

| Command/check | Result |
| --- | --- |
| `pytest deploy/tests/test_verify_repository.py -q` | **PASS** - 9 passed. |
| `pytest server/tests/unit/test_config.py -q` | **PASS** - 11 passed. |
| Focused Ruff | **PASS** - all checks passed. |
| Focused mypy | **PASS** - no issues found in the two checked source files. |
| `python -m py_compile deploy/verify_repository.py` | **PASS**. |
| `python deploy/verify_repository.py --scope current` | **FAIL (known current content)** - exactly the three existing SQLite test-engine modules were reported. |
| `python deploy/verify_repository.py --scope stage-one` | **FAIL (expected scope distinction)** - the current Stage 2 migrations/modules and the same SQLite tests were reported. R4B's unchanged archived-Stage-1 PASS evidence remains valid. |

The original V06-03 documentation inconsistency, V06-04, and V06-05 are
repaired for the current tree. The retained original sections below remain
historical evidence. V07 and the consolidated Stage 1 baseline were not
updated, as explicitly required for R4C.

## R4B targeted repair re-verification - 2026-09-11

Base revision: `0ee27bb988733e0c05dd814244f171d8360f8d1a` plus the R4B worktree changes.

Repair scope: V06-01, V06-02, V06-03 audit detection, and the historical/current audit boundary.

R4B repair result: **PASS**.

Overall V06 result: **FAIL** remains unchanged because V06-04 and V06-05 are outside R4B, and the current repository still contains the detected SQLite test engines and Stage 2 implementation.

This addendum supersedes only the original blocked execution results and the audit-implementation findings for V06-01 through V06-03. It does not rewrite the historical verification below or treat the current Stage 2-containing tree as a Stage 1 tree.

| R4B contract | Result | Current evidence |
| --- | --- | --- |
| Credential/private-key detection | PASS | The verifier now recognizes quoted values and quoted JSON-style keys in non-example configuration, scans configuration formats outside production source directories, recognizes generic/encrypted/DSA and other private-key headers, and rejects common private-key filenames or key-container suffixes without printing their contents. Focused regressions cover TOML, JSON, PEM, `.key`, and `.p12` cases. The current repository produces no credential/private-key finding. |
| Positive MySQL allowlist | PASS | Database URL contexts and SQLAlchemy sync/async engine construction now accept only the exact `mysql+pymysql` scheme. Python tests are inspected for engine construction rather than skipped wholesale, while negative validation fixtures and unrelated HTTP callback URLs do not create false findings. Unknown schemes, an HTTPS value assigned to `DATABASE_URL`, and SQLite engine construction are covered by regression tests. |
| Stage 1 absence-rule coverage | PASS | Historical Stage 1 scope rejects migrations other than the Stage 1 baseline, detects `op.create_table`, and rejects server implementation modules outside the Stage 1 source allowlist. The current tree's two later migrations and six domain/enrollment modules are now reported. |
| Historical/current boundary | PASS | `--scope current` applies repository-wide credential, key, database, and production-topology rules without treating approved Stage 2 work as a Stage 1 absence violation. `--scope stage-one` adds the historical absence rules. The archived `1ee0b2b` Stage 1 snapshot passes `--scope stage-one`; applying that scope to the current tree intentionally fails. |
| Current repository MySQL-only content | FAIL | `--scope current` reports the three existing SQLite engine test modules named in V06-02. R4B repairs detection; it does not rewrite Stage 2 database tests. |
| Current repository Stage 1 absence | NOT APPLICABLE | The current repository contains later approved Stage 2 work. Historical Stage 1 absence is evaluated against the Stage 1 snapshot, while `--scope stage-one` remains available to show why the current tree cannot be represented as Stage 1. |

Targeted commands and results:

```text
pytest deploy/tests/test_verify_repository.py -q
# 9 passed

ruff check deploy/verify_repository.py deploy/tests/test_verify_repository.py
# All checks passed

mypy deploy/verify_repository.py
# Success: no issues found in 1 source file

python deploy/verify_repository.py --scope current
# exit 1: exactly the three existing SQLite engine test modules

python deploy/verify_repository.py --scope stage-one
# exit 1: the same database findings plus two later migrations/table operations
# and six domain/enrollment source modules

python deploy/verify_repository.py <archived-1ee0b2b-tree> --scope stage-one
# exit 0, no findings
```

The nonzero current-tree audit results are expected findings and demonstrate that the repaired rules no longer permit the known violations to evade the audit. They are not represented as verifier execution failures. Acceptance criteria 10 and 11 therefore retain their existing current-tree classifications, so V07 and the consolidated baseline are not changed by R4B.

## Components reviewed

- Stage 1 design, master-index, status, execution-card, and implementation-plan sections limited to Steps 15-16
- `deploy/verify_repository.py`
- `deploy/tests/test_verify_repository.py`
- `.gitignore`, `.env.example`, and component environment examples
- Agent, server, migration, and frontend source boundaries needed for the absence audit
- `README.md`
- `docs/architecture.md`
- `docs/development.md`
- `docs/deployment.md`
- `docs/future-contracts.md`
- `deploy/systemd/device-watch-agent.service`
- Runtime dependency manifests and locked dependency trees

## Results

| Contract | Result | Evidence |
| --- | --- | --- |
| Fresh repository verifier | BLOCKED BY ENVIRONMENT | The locked Python runner requires a host interpreter unavailable in the sandbox. External execution was rejected by the approval service before the verifier started. |
| Fresh repository-audit tests | BLOCKED BY ENVIRONMENT | The same environment condition prevented `deploy/tests/test_verify_repository.py` from starting. No complete component suite was attempted. |
| Credential/private-key detection implementation | FAIL | Static inspection found incomplete detection for quoted credential literals, common encrypted/DSA private-key headers, and credentials outside the selected production directories. Existing tests cover only an unquoted password and a generic private-key header. See V06-01. |
| Current tracked credential/private-key scan | PASS | Tracked environment-shaped files are examples only; no tracked certificate/private-key filename or actual private-key header was found. Findings were limited to paths and did not print values. |
| MySQL-only runtime boundary | PASS | Server settings require `mysql+pymysql`; the locked runtime tree contains PyMySQL/SQLAlchemy/Alembic and no competing database driver. The agent has no runtime dependency. |
| Repository-wide MySQL-only audit boundary | FAIL | The verifier uses a four-product denylist rather than the required positive MySQL allowlist, so other unsupported schemes can pass. It also skips tests, while current post-Stage-1 unit tests instantiate SQLite engines. See V06-02. |
| Stage 2 functionality absent from the current tree | FAIL | Post-Stage-1 migrations and enrollment/bootstrap server modules are present. The verifier does not audit Alembic revisions for created tables and does not reject these service modules. See V06-03. |
| No real monitoring collectors | PASS | Agent production source contains only collector contracts and the registry; the only `collect` definition is the protocol method. |
| No sender | PASS | No sender/transport module or outbound client exists in agent production source. |
| No monitoring fixtures/fake data | PASS | Targeted agent and frontend source searches found no monitoring records, device samples, or metric fixtures. |
| No frontend business API calls | PASS | Targeted frontend source searches found no `fetch`, `XMLHttpRequest`, Axios, or business API path. The frontend runtime dependencies contain no API/query client. |
| Trust-boundary documentation | PASS | The architecture document identifies Caddy as sole ingress, private FastAPI, external MySQL with verified TLS, outbound future agents, and the forwarded-header/network dependency. These statements match the checked-in Stage 1 deployment assets. |
| Development documentation consistency | FAIL | Native server development instructions set `DEVICE_WATCH_ENV=test`; the approved design assigns `development` to the development workflow and reserves `test` for automated tests. See V06-04. |
| Deployment documentation consistency | FAIL | Names, ports, volumes, host-gateway behavior, TLS keys, and commands otherwise match the deployment assets, but the instructions direct operators to copy/use an invalid production environment example already characterized in V05. See V06-05. |
| Future-contract documentation | FAIL | The document contains the required ordered sequence and security boundaries, but its statements that the contracts are unimplemented and the repository is schema-empty conflict with the current post-Stage-1 migrations and enrollment/bootstrap modules. This is part of V06-03. |
| systemd agent example | PASS | Dedicated unprivileged user/group, required operator environment file, native `python3 -m device_watch_agent`, `Restart=on-failure`, and `KillSignal=SIGTERM`; no Docker, shell polling, database, or sender invocation. |

## Stable contracts verified

- The checked-in agent remains dependency-free at runtime and contains neither a concrete collector nor a sender.
- The checked-in frontend remains free of business API calls and fabricated monitoring data.
- Runtime server configuration and dependencies retain the MySQL/PyMySQL boundary.
- The architecture documentation records the approved Stage 1 trust boundaries.
- The future-contract document contains the required ordered sequence and the intended credential, submission, retry, receipt-time, persistence-separation, and evaluation boundaries.
- The native systemd unit retains the approved empty-agent lifecycle contract.

These passing subcontracts do not override the current Stage 2 scope violation or the audit/documentation defects.

## Commands actually executed

```text
git status --short
rg --files server/src server/alembic/versions agent/src web/src
rg -n <scoped boundary patterns> server/src server/alembic/versions agent/src web/src
git ls-files "*.env" "*.pem" "*.key" "*.p12" "*.pfx" "*.crt" "*.cer"
git grep -l -I -E -e <private-key-header pattern> -- <tracked paths excluding verifier fixtures>
rg -n <documentation/configuration contract names> README.md docs deploy agent/.env.example .env.example
& 'D:\Dinesh\deviceHealth\.tmp\uv-tool\Scripts\uv.exe' --cache-dir 'D:\Dinesh\deviceHealth\.tmp\uv-cache' --no-python-downloads --offline tree --project agent --no-dev --frozen
& 'D:\Dinesh\deviceHealth\.tmp\uv-tool\Scripts\uv.exe' --cache-dir 'D:\Dinesh\deviceHealth\.tmp\uv-cache' --no-python-downloads --offline tree --project server --no-dev --frozen
npm.cmd --prefix web ls --depth=0
git log -6 --oneline --decorate
git diff --check
git status --short
git diff --stat
git diff
```

The following required commands were requested but blocked before process creation by the environment approval service:

```text
& 'D:\Dinesh\deviceHealth\.tmp\uv-tool\Scripts\uv.exe' --no-python-downloads --offline --cache-dir 'D:\Dinesh\deviceHealth\.tmp\uv-cache' run --project server --frozen --group test pytest deploy/tests/test_verify_repository.py -q
& 'D:\Dinesh\deviceHealth\.tmp\uv-tool\Scripts\uv.exe' --no-python-downloads --offline --cache-dir 'D:\Dinesh\deviceHealth\.tmp\uv-cache' run --project server --frozen --group test python deploy/verify_repository.py
```

### Supporting-check results

- Agent locked runtime tree: **PASS** - zero runtime dependencies.
- Server locked runtime tree: **PASS** - MySQL support is PyMySQL through SQLAlchemy/Alembic; no competing database driver appeared.
- Frontend direct dependency listing: **PASS** - no HTTP/query client or monitoring/chart package.
- Scoped collector/sender/frontend fixture/API searches: **PASS** - no prohibited production artifact found.
- Tracked secret-shaped filename and private-key-header checks: **PASS** - examples only; no key material found.
- Fresh audit test count/result: **BLOCKED BY ENVIRONMENT** - process did not start.
- Fresh real-repository audit result: **BLOCKED BY ENVIRONMENT** - process did not start.

The first dependency-tree invocation selected an inaccessible user cache. Re-running the read-only tree command with the existing workspace cache succeeded offline; no package was installed or changed.

## Defects discovered

### V06-01 - credential and private-key detection is incomplete

**FAIL.** `deploy/verify_repository.py:55-60` recognizes generic, RSA, EC, and OpenSSH private-key headers but not common `ENCRYPTED PRIVATE KEY` or `DSA PRIVATE KEY` headers. Its credential pattern requires the first value character to be unquoted, so common assignments such as a quoted password are missed. Credential scanning is also restricted to `server/src`, `agent/src`, `web/src`, `deploy`, or a file named exactly `.env`, rather than all non-example repository configuration. `deploy/tests/test_verify_repository.py:29-37` covers only an unquoted password and generic private-key header.

### V06-02 - database enforcement is a denylist, not a positive MySQL allowlist

**FAIL.** `deploy/verify_repository.py:56` names only PostgreSQL, SQLite, MongoDB, and Redis URL schemes. Any other unsupported database family is not rejected. Database checks are also disabled for paths classified as tests at line 115. Current post-Stage-1 tests instantiate SQLite engines in `server/tests/unit/test_bootstrap_cli.py:45-47`, `server/tests/unit/test_bootstrap_service.py:44`, and `server/tests/unit/test_bootstrap_repository.py:35`, despite the Stage 1 acceptance contract that MySQL be the only database implementation represented. The configured production runtime remains MySQL/PyMySQL-only, but the broader repository boundary and its positive-allowlist enforcement fail. The audit test at `deploy/tests/test_verify_repository.py:32` exercises only PostgreSQL.

### V06-03 - current repository contains Stage 2 behavior that the Stage 1 audit misses

**FAIL.** The current tree includes:

- `server/alembic/versions/20260908_0002_device_identity.py`, which calls `op.create_table` at line 23;
- `server/alembic/versions/20260908_0003_bootstrap_provisioning.py`, which calls `op.create_table` at line 22; and
- `server/src/device_watch_server/domain/` and `server/src/device_watch_server/enrollment/` implementation modules.

The domain-table rule in `deploy/verify_repository.py:118-123` is applied only under `server/src` and looks only for declarative `Base`/`__tablename__` patterns. It does not inspect Alembic `op.create_table` calls or reject the current enrollment/bootstrap service modules. The synthetic Stage 2 test covers a declarative model, route, collector, sender, frontend call, and fixture, but no migration or service-module case. This also makes the absolute "future only" and "schema-empty" statements in `docs/future-contracts.md:3,17-25` and `docs/architecture.md:27` inconsistent with the current tree.

### V06-04 - native development instructions select test mode

**FAIL.** `docs/development.md:35,50` sets `DEVICE_WATCH_ENV=test` for the native Uvicorn development workflow. The approved Stage 1 design at `docs/superpowers/specs/2026-08-31-device-watch-stage-1-design.md:104` assigns `development` to development workflows and `test` to automated tests.

### V06-05 - deployment instructions rely on an invalid production example

**FAIL.** `docs/deployment.md:7-11,33-42` tells operators to copy and use `deploy/.env.prod.example`. V05 established that line 3 of that example contains literal `\&` query separators and is rejected by production settings. See `docs/verification/stage-01/05-deployment-topology.md:80-84`.

## Environment blocks

The workspace approval service reported that it was out of credits. The existing locked Python environment therefore could not access its host interpreter, blocking only:

- fresh execution of `deploy/verify_repository.py`; and
- fresh execution of `deploy/tests/test_verify_repository.py`.

No software was installed, no alternate execution path was attempted, and no complete agent/server/web suite was run.

## Source locations future stages may rely on

- Repository audit: `deploy/verify_repository.py`
- Audit behavior tests: `deploy/tests/test_verify_repository.py`
- Trust boundaries: `docs/architecture.md`
- Independent development workflows: `docs/development.md`
- Production operations: `docs/deployment.md`
- Future security/data-flow contracts: `docs/future-contracts.md`
- Native agent service example: `deploy/systemd/device-watch-agent.service`
- Agent absence boundary: `agent/src/device_watch_agent/collectors/`, `agent/src/device_watch_agent/main.py`
- Frontend absence boundary: `web/src/`
- Current migration boundary: `server/alembic/versions/`

## Final repository checks

- `git diff --check`: **PASS** - no output.
- `git status --short`: **PASS** - only `?? docs/verification/stage-01/06-security-documentation.md` is expected.
- `git diff --stat` and `git diff`: **PASS** - no tracked file differs from `HEAD`.
- No application, test, deployment, configuration, or pre-existing documentation file was modified.
