# Stage 1 Independent Verification Baseline

Date: 2026-09-09  
Evidence revision: `91a52e0198ebb2a5ef428bf571ed48d42e30e98f`  
Scope: consolidated V01-V07 evidence; no implementation work or test rerun

## Baseline status

Stage 1 is **not accepted as a safe baseline**. V07 mapped the sixteen approved acceptance criteria as:

- **PASS:** 5 - criteria 4, 6, 12, 14, and 16
- **FAIL:** 6 - criteria 1, 3, 5, 9, 10, and 11
- **BLOCKED BY ENVIRONMENT:** 5 - criteria 2, 7, 8, 13, and 15

The `Complete` labels in `docs/progress/current-status.md` record implementation handoffs and earlier self-checks. Where they conflict with independent V01-V07 evidence, the independent evidence controls. In particular, the current tree contains later Stage 2 artifacts, so the Stage 1-only scope and schema-empty claims no longer describe the repository as a whole.

This file is an evidence baseline, not an acceptance waiver. Its PASS contracts may be reused within their stated scope; its FAIL and blocked areas remain open.

## Verified architecture and component boundaries

| Area | Verified boundary | Important qualification |
| --- | --- | --- |
| Repository | Independent `agent`, `server`, and `web` projects with separate Python locks and a frontend package lock; root Docker build context is allowlisted. | Server dependency classification and two ignore-rule categories fail V01. |
| Server | FastAPI factory; process liveness; database-backed readiness; owned engine disposal; required MySQL/PyMySQL settings; centralized SQLAlchemy engine; exact production driver TLS arguments. | Documented uppercase settings fail on POSIX; routing, logging/CLI, metadata, Alembic, and test-coverage defects remain. |
| Agent | Native standard-library project; typed collector status/result foundation; empty registry; efficient no-collection lifecycle; supported-loop stop callbacks; no network, server, database, subprocess, sender, or local database coupling. | Mapping annotation, padded duplicate names, non-finite intervals, JSON logging, and signal-test coverage fail V03. |
| Frontend | React/TypeScript shell; exactly five route boundaries; accessible navigation; persisted light/dark/system selection; no business API calls or fabricated monitoring data; path-preserving Vite `/api` proxy; static build. | System-mode reactivity, exact empty-state content, local Button boundary, and required tests fail V04. |
| Production deployment | Static contracts define a non-root FastAPI image, multi-stage web/Caddy image, path-preserving `/api/* -> server:8000`, exactly two services, Caddy-only host ports, persistent Caddy volumes, and the CA secret mount. | Production env example and topology verifier fail; all Docker/Compose/Caddy runtime evidence is blocked. |
| Development deployment | MySQL `8.4.11` is loopback-bound at `127.0.0.1:3307`, uses a named volume/health check, and has an opt-in portless `server-smoke` service under `verification`. | Rendered Compose and live health behavior are blocked; the Step 04 test is raw-text rather than rendered topology. |
| Security/docs | No tracked private-key material was found; no real agent collector/sender or frontend business API/fake monitoring data was found; trust-boundary and systemd contracts are present. | Audit detection/allowlist gaps, stale future-only claims, development-mode guidance, and production example guidance fail V06. |

## Stable contracts future stages may rely on

- Production topology remains Browser -> Caddy -> private FastAPI -> external MySQL; Caddy is the sole public ingress.
- Public Stage 1 application routing evidence is limited to `/api/v1/health/live` and `/api/v1/health/ready`; later server modules exist but were not shown to add public business routes.
- `DATABASE_URL` is intended to use exactly `mysql+pymysql`; production validation requires the exact CA path plus certificate and identity verification flags. The flat PyMySQL boundary and removal of competing URL-derived SSL arguments passed no-network characterization.
- The application owns its engine, distinguishes liveness from readiness, executes `SELECT 1` for readiness/database checks, disposes owned engines, and keeps errors credential-safe.
- The scoped Stage 1 revision `20260831_0001` is behavior-free and the scoped Stage 1 metadata import was empty. This does not mean current repository migration head is schema-empty.
- The agent starts with an empty registry, performs no collection or communication, waits without polling, and supports clean requested stop/cancellation.
- The frontend has the five approved route paths, accessible navigation, local theme persistence, no monitoring data or business API client, a non-rewriting development proxy, and static build output.
- Checked-in deployment assets statically preserve `/api`, target exactly `server:8000`, keep FastAPI off host ports, and declare the configured read-only CA mount.
- The trust model, future data-flow sequence, and native unprivileged systemd entry point are documented. Future-only wording must be updated as those contracts become implemented.

Do not rely on a stable contract beyond its qualification or use it to infer that the whole owning step passed.

## PASS areas

- Repository project separation and committed dependency locks.
- Server mode enum, MySQL dialect validation, production TLS rejection, secret-safe validation, centralized engine construction, pool behavior, flat TLS driver mapping, and no competing SSL mapping.
- FastAPI factory, liveness/readiness semantics, `SELECT 1`, engine disposal, request/CLI secret redaction, and behavior-free Stage 1 baseline revision.
- Agent status/result immutability, empty registry/order/snapshots, no concrete collector, no sender/database/network coupling, and requested-stop lifecycle.
- Frontend shell quality commands, five routes, navigation semantics, basic theme persistence, no fake data/API client, Vite proxy, and static output.
- Static server/Caddy image boundaries, Caddy source routing, production two-service/Caddy-port/CA-volume declarations, and development MySQL/smoke topology.
- Current tracked secret/key scan, agent/frontend Stage 1 absence boundaries, architecture trust-boundary document, and systemd unit.

## FAIL areas

| Evidence | Open failures |
| --- | --- |
| V01 | `httpx` classified as server runtime rather than test-only; missing local-database/editor ignore rules; documented uppercase server settings fail on POSIX; pool options lack committed assertions. |
| V02 | Development topology test is not rendered; app bypasses its versioned router; server logs are not newline-delimited and include an extra raw path; readiness event name is wrong; CLI messages/output shape differ; metadata naming convention is incomplete; Alembic bypasses validated TLS arguments, breaks percent URLs, resolves the wrong script path, and has an integration fixture that deletes its database configuration. |
| V03 | Collector result public mapping type is too narrow; padded duplicate names pass; `nan`/`inf` intervals pass; agent logging is plain text rather than structured JSON; signal registration lacks required automated coverage. |
| V04 | Route pages include prohibited extra content; system theme does not react to OS changes; required local Button primitive is absent; route/navigation/system-theme regression coverage is incomplete. |
| V05 | Production env example has literal `\&` TLS separators; rendered-style volume objects break the topology verifier; CA secret source is not checked; general Caddy `rewrite` directives are not rejected. |
| V06 | Credential/private-key detection misses important forms/surfaces; database checking is a denylist rather than a positive MySQL allowlist; current Stage 2 migrations/modules violate the Stage 1-only boundary and evade the audit; native development docs select `test`; deployment docs rely on the invalid production example. |

These failures are not converted to environment blocks merely because related Docker/MySQL checks could not run.

## Environment-blocked areas

- Real configured MySQL connectivity and the MySQL `head -> base -> head` Stage 1 migration cycle.
- Development and production Compose rendering, including live missing-variable failure behavior.
- Server and Caddy image builds; final-image user/tool inspection; packaged `caddy validate`; runtime proxy behavior; container health; and server-smoke startup.
- Runtime verification of the production secret mount.
- Real process-level agent signal behavior on the Windows Proactor loop.
- Frontend interaction in an in-app browser and execution on a Node version satisfying React Router's `>=22.22.0` engine requirement.
- Fresh V06 repository-verifier and audit-test execution, blocked by unavailable host-interpreter approval capacity.

Do not report any blocked item as PASS from static configuration alone. When suitable infrastructure becomes available, run only the corresponding blocked check unless its owning files also changed.

## Important source locations

| Contract area | Source locations | Primary evidence |
| --- | --- | --- |
| Projects, locks, safeguards | `.gitignore`, `.dockerignore`, `agent/pyproject.toml`, `agent/uv.lock`, `server/pyproject.toml`, `server/uv.lock`, `web/package.json`, `web/package-lock.json` | V01 |
| Server settings/engine | `server/src/device_watch_server/core/config.py`, `server/src/device_watch_server/db/engine.py` | V01 |
| App/health/logging/CLI | `server/src/device_watch_server/app.py`, `server/src/device_watch_server/api/`, `server/src/device_watch_server/db/health.py`, `server/src/device_watch_server/core/logging.py`, `server/src/device_watch_server/core/middleware.py`, `server/src/device_watch_server/cli.py` | V02 |
| Alembic baseline | `server/src/device_watch_server/db/base.py`, `server/alembic.ini`, `server/alembic/env.py`, `server/alembic/versions/20260831_0001_baseline.py` | V02 |
| Agent | `agent/src/device_watch_agent/collectors/`, `agent/src/device_watch_agent/config.py`, `logging.py`, `lifecycle.py`, `main.py` | V03 |
| Frontend | `web/src/app/`, `web/src/components/layout/`, `web/src/pages/FoundationPage.tsx`, `web/src/theme/ThemeProvider.tsx`, `web/vite.config.ts` | V04 |
| Images/topology | `server/Dockerfile`, `deploy/caddy/Dockerfile`, `deploy/caddy/Caddyfile`, `deploy/compose.prod.yml`, `deploy/compose.dev.yml`, `deploy/.env.prod.example` | V05 |
| Verifiers/docs/service | `deploy/verify_topology.py`, `deploy/verify_repository.py`, `docs/architecture.md`, `docs/development.md`, `docs/deployment.md`, `docs/future-contracts.md`, `deploy/systemd/device-watch-agent.service` | V05-V06 |

## Commands and evidence locations

The exact commands, outputs, probe descriptions, defects, and source line references remain in:

- [V01 - repository/server foundation](01-repository-server-foundation.md)
- [V02 - server/database/migrations](02-server-database-migrations.md)
- [V03 - agent foundation](03-agent-foundation.md)
- [V04 - frontend foundation](04-frontend-foundation.md)
- [V05 - deployment topology](05-deployment-topology.md)
- [V06 - security/documentation](06-security-documentation.md)
- [V07 - acceptance mapping](07-acceptance-review.md)

Representative successful evidence includes 14 focused server settings/engine tests, 11 focused server/deployment tests, 18 agent tests plus Ruff/mypy, 8 frontend tests plus typecheck/lint/build, and 6 non-Docker deployment tests. Passing suites do not close the recorded coverage defects. V06's fresh verifier/test commands were blocked and have no PASS result.

No test or infrastructure command was rerun while creating this consolidation.

## Reuse and invalidation rules

**Unchanged Stage 1 components do not require a full re-audit during every future stage.** Reuse the relevant V01-V07 PASS evidence when later work does not modify the verified contract or a component that implements it.

A baseline area is invalidated only when later work:

- changes one of that area's source/configuration files listed above;
- changes an externally visible contract it verified, including routes, settings names, TLS mapping, database behavior, logging schema, agent lifecycle/collector APIs, frontend routes/theme/API behavior, proxy paths, ports, secrets, or trust boundaries;
- changes the area's manifest, lock, toolchain requirement, build input, or relevant test/verifier;
- adds new source that crosses an absence/security boundary, such as an agent sender/collector, frontend business API/fake data, database family, credential material, public server route, or deployment peer/port; or
- repairs a recorded failure or gains the infrastructure needed to close a blocked result.

When invalidated, re-run only the affected verification area and its direct downstream acceptance criteria:

- repository/settings/engine -> V01;
- app/health/logging/CLI/Alembic/development MySQL -> V02;
- agent contracts/config/lifecycle/logging -> V03;
- frontend shell/theme/routes/proxy -> V04;
- images/Caddy/Compose/topology -> V05;
- repository audit/docs/systemd/absence boundaries -> V06;
- any changed acceptance result -> update V07 and this consolidation.

Unrelated Stage 2 additions do not invalidate PASS evidence for untouched Stage 1 components. Changes to shared Stage 1 files do require targeted regression verification, even when made as part of Stage 2. Criterion 11 is already FAIL on the current tree; do not use repeated discovery of additional scoped Stage 2 files as a reason to re-audit unrelated components.

`current-status.md` should be treated as historical progress context until its claims are reconciled with the independent failures above.

STAGE 1 NOT YET SAFE AS BASELINE
