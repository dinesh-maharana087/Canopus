# Stage 1 Verification V06 - Security and documentation

Date: 2026-09-09  
Scope: Stage 1 Steps 15-16 only  
Revision inspected: `fb88657c7a14a30e967cf13797ad005765499d96`  
Overall result: **FAIL**

The current repository tree was verified as-is. Source code was not modified. The locked Python environment could not be invoked inside the sandbox, and the required external-access request was rejected because the workspace approval service was out of credits. Consequently, the fresh repository-verifier and audit-test executions are classified as **BLOCKED BY ENVIRONMENT**; they were not retried through another execution path.

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
