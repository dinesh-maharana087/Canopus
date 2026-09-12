# Stage 1 V08 — Final Verification Baseline

Date: 2026-09-12. Scope: latest V01–V07 evidence; consolidation only.

**STAGE 1 VERIFIED WITH ENVIRONMENT BLOCKS**

Evidence state: `f150b8a34f46b33fe9a171febd8ccfea16f174ca` **plus the verified,
uncommitted `.gitignore` repair and V01/V07 updates**. HEAD alone lacks that
completed repair. This replaces the 2026-09-09 summary; historical findings
remain in V01–V07 and Git history. No source audit, suite, or infrastructure
check was rerun for V08.

## Final acceptance

| Classification | Total | Criteria |
| --- | --- | --- |
| PASS | **9** | **1, 4, 5, 6, 10, 11, 12, 14, 16** |
| FAIL | **0** | **None** |
| BLOCKED BY ENVIRONMENT | **7** | **2, 3, 7, 8, 9, 13, 15** |

PASS covers backend boot (1), agent lifecycle/contracts (4–5), frontend quality
gates (6), MySQL-only representation (10), historical Stage 1 absence of Stage 2
workflow (11), Caddy-only public ports (12), MySQL TLS rejection (14), and the
configured read-only CA mount (16). [V07](07-acceptance-review.md) maps all
sixteen [approved criteria](../../superpowers/specs/2026-08-31-device-watch-stage-1-design.md#acceptance-criteria).

**No deterministic Stage 1 acceptance FAIL remains. Stage 1 is safe as the
foundation for approved Stage 2+ work within the verified contracts below.**
This does not establish full runtime acceptance or deployment readiness.
A blocked contract needs targeted verification before work relies on it as
proved. This baseline does not authorize or start another stage.

## Stable contracts and important source locations

Paths are repository-relative; braces group filenames beneath the same path.

| Area / owner | Verified contract | Important source locations |
| --- | --- | --- |
| Repository / V01 | Independent Python projects/locks and frontend lock; server `httpx` is test-only. Database/env/key/generated-artifact ignores pass; examples remain trackable. Ignores do not remove existing tracked files. | `.gitignore`, `.dockerignore`, `agent/{pyproject.toml,uv.lock}`, `server/{pyproject.toml,uv.lock}`, `web/{package.json,package-lock.json}` |
| Settings/MySQL / V01–V02 | Uppercase settings; exact `mysql+pymysql`; centralized engine, pre-ping and 1,800-second recycling. Production requires `/run/secrets/mysql-ca.pem` and true certificate/identity verification. Flat PyMySQL TLS arguments have no competing URL SSL mapping; diagnostics are sanitized. | `server/src/device_watch_server/core/config.py`, `server/src/device_watch_server/db/engine.py`, `server/tests/unit/{test_config.py,test_engine_tls.py}` |
| Server/Alembic / V02 | Versioned factory; health live/ready routes; readiness/DB CLI execute `SELECT 1`; engine disposal; structured JSON logs/redaction. Validated percent-safe Alembic URL/TLS handling and deterministic naming pass. Stage 1 revision **20260831_0001** is behavior-free. | `server/src/device_watch_server/{app.py,api/,core/logging.py,core/middleware.py,db/health.py,db/base.py,cli.py}`, `server/alembic.ini`, `server/alembic/env.py`, `server/alembic/versions/20260831_0001_baseline.py` |
| Agent / V03 | Native standard-library lifecycle; immutable collector mapping, normalized duplicate rejection, finite positive intervals, empty registry, efficient waiting, requested stop/cancellation, structured logging. No real collector/sender/network/database behavior. | `agent/src/device_watch_agent/{collectors/,config.py,logging.py,lifecycle.py,main.py}`, `agent/tests/` |
| Frontend / V04 | Five routes with exact empty states, accessible navigation, reactive persisted light/dark/system theme, local Button, no business API/fake monitoring data. Vite preserves `/api`; static build passes. | `web/src/{app/,components/layout/,components/ui/Button.tsx,pages/FoundationPage.tsx,theme/ThemeProvider.tsx}`, `web/vite.config.ts` |
| Deployment / V05 | Browser/future outbound agent → HTTPS Caddy → private FastAPI → external MySQL. Only Caddy publishes `80/443`; `/api/*` preserves its path to `server:8000`. Non-root image contract, persistent Caddy state, `mysql_ca` source/`mysql-ca.pem` target/mode `0444` pass static checks. Development MySQL is loopback-bound; `server-smoke` is opt-in and portless. | `server/Dockerfile`, `deploy/caddy/{Dockerfile,Caddyfile}`, `deploy/compose.{dev,prod}.yml`, `deploy/.env.prod.example`, `deploy/verify_topology.py`, `deploy/tests/` |
| Audit/docs / V06 | Positive MySQL allowlist, credential/key detection, and genuine Stage 1 dependency/route leakage checks pass. Native development uses `development`; production examples are templates, operational env files are ignored. Future agents communicate outbound. | `deploy/verify_repository.py`, `deploy/tests/test_verify_repository.py`, `docs/{architecture,development,deployment,future-contracts}.md`, `deploy/systemd/device-watch-agent.service` |

## Remaining environment limitations

Static checks, doubles, skips, and successful host builds do not prove these
runtime contracts. Recorded unavailability is retained, not rechecked by V08.

| Criterion | Evidence still required | Owner |
| --- | --- | --- |
| **2** | Actual configured MySQL connectivity / `SELECT 1`. | V02 |
| **3** | Real MySQL 8.x Stage 1 baseline `upgrade → base → upgrade` cycle. | V02 |
| **7** | Packaged Caddy configuration validation. | V05 |
| **8** | Actual development and production Compose rendering. | V02/V05 |
| **9** | Complete environment-dependent automated checks: Docker render test, real MySQL path, supported-runtime execution. Deterministic safeguards now pass. | V01–V06 |
| **13** | Actual missing-production-domain/database Compose render failures. | V05 |
| **15** | Image packaging and runtime path-preserving proxy behavior to `server:8000`. | V05 |

Also retained: image user/tool inspection, container health, MySQL/server-smoke
startup and runtime CA mount inspection (V05); real Windows process signals
on the recorded Proactor loop (V03); browser interaction and supported Node
execution (V04: recorded 22.14.0 was below the locked >=22.22.0 requirement).
These do not negate the specific passing static/unit contracts.

## Historical Stage 1 / current Stage 2 boundary

Criterion 11's PASS belongs to commit
`1ee0b2b723e6323531162ebe8e353f6f4670ff36`, checked by today's verifier with
`--scope stage-one --stage-one-ref <commit>`. It reads raw committed files
without checkout or historical code execution; invalid refs cannot fall back.
Later approved Stage 2 additions do not retroactively invalidate this result.
Current repository security/database checks use `--scope current`.

Empty metadata/schema absence applies to Stage 1, not current Stage 2 modules
or migration heads. This baseline does not certify Stage 2 completeness.
V06's missing `enrollment.cli`/bootstrap console entry point and nine bootstrap
mypy diagnostics remain separate Stage 2 defects. V02's legacy test annotations
remain outside its established source-focused type gate. No full-current-tree
test PASS is claimed; these findings are not repaired or relabeled as blocks.

## Verification evidence index

Use the latest scoped addenda, not stale original FAIL/Complete headings.
Exact commands and case lists remain in the owning reports.

| Evidence | Latest reusable evidence |
| --- | --- |
| [V01 — repository/server](01-repository-server-foundation.md) | Safeguards: **33 protected / 10 trackable** checks pass. V07 retains post-R1 **16-test** settings/engine evidence and test-only `httpx` classification. |
| [V02 — server/database/migrations](02-server-database-migrations.md) | R2A–R2C: **19 passed, 1 Docker skip**, plus one no-network integration-environment test; focused Ruff/source mypy pass. |
| [V03 — agent](03-agent-foundation.md) | R3A/R3B: **27 tests**, Ruff, source mypy, locked dependency-free runtime check pass. |
| [V04 — frontend](04-frontend-foundation.md) | R3B: **10 tests**, strict type-check, lint, build pass; supported-Node/browser blocks retained. |
| [V05 — deployment](05-deployment-topology.md) | R4A/R4C: **12 passed, 1 Docker skip**, focused lint/type checks pass; R5C restores operator-env ignores. |
| [V06 — security/docs](06-security-documentation.md) | R4B/R4C and R5A/R5B: current/historical audits pass. Latest criterion 10/11 run: **30 passed, 3 unrelated tests deselected**, Ruff/strict mypy pass. |
| [V07 — acceptance](07-acceptance-review.md) | Current post-R5C remap: **9 PASS / 0 FAIL / 7 BLOCKED**; historical reviews preserved. |

V01's original R1 FAIL report predates its repair; V07 resolves that evidence
gap. V07's older printed revision does not resolve locally: its recorded
results and reachable checkpoint `cd40866` control, not that unavailable object.
Explicit user scope and approved specifications outrank plans; independent
verification outranks progress history. Old `Complete` labels are not waivers.

## Baseline reuse and invalidation

1. Reuse unchanged PASS contracts within their qualifications. Starting a later
   stage does not require repeating V01–V06.
2. Re-verify the affected area when its source/configuration, externally visible
   contract, relevant test/verifier, dependency/lock/toolchain, security/absence
   boundary, build input, or deployment topology changes. Stage 2 changes to
   shared Stage 1 files count; unrelated additions do not.
3. When a required environment becomes available, run only the blocked check
   and direct dependent checks. Historical PASS never certifies changed current
   code; blocked results require executed evidence before becoming PASS.
4. Use the owners above: V01 settings/safeguards, V02 server/database/migrations,
   V03 agent, V04 frontend, V05 deployment, V06 audit/docs/security. Update V07
   and this baseline after changed acceptance results; avoid a full matrix for
   an unrelated edit.
5. Approved Stage 2+ work may extend the factory/router, validated MySQL/Alembic
   boundary, collector/lifecycle contracts, frontend shell and Caddy topology.
   Preserve MySQL-only storage, TLS validation, secret handling, outbound-agent
   communication, and Caddy-only public ingress.

V08 changed only this baseline and the required progress summary. Existing
verified repair/evidence changes were preserved. No application/Stage 2
implementation changed, and no next stage was started.
