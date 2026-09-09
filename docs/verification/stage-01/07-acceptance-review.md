# Stage 1 Verification V07 - Acceptance review

Date: 2026-09-09  
Scope: Stage 1 acceptance review only  
Revision reviewed: `a366a8bf7fa2379ac0a3dfac9fda71ce1850abc1`  
Overall result: **FAIL**

Acceptance totals: **5 PASS, 6 FAIL, 5 BLOCKED BY ENVIRONMENT**.

This review maps the sixteen approved acceptance criteria at `docs/superpowers/specs/2026-08-31-device-watch-stage-1-design.md:372-389` exclusively to V01-V06 evidence. Application source was not independently re-audited and no prior test was rerun. A criterion is `FAIL` when existing evidence proves a deterministic violation, even if a related runtime check is also blocked. `BLOCKED BY ENVIRONMENT` is used only when no proved violation controls the criterion and required dynamic evidence is unavailable.

## Evidence reviewed

- V01: `01-repository-server-foundation.md` - Steps 01-03
- V02: `02-server-database-migrations.md` - Steps 04-07
- V03: `03-agent-foundation.md` - Steps 08-09
- V04: `04-frontend-foundation.md` - Step 10
- V05: `05-deployment-topology.md` - Steps 11-14
- V06: `06-security-documentation.md` - Steps 15-16
- Approved Stage 1 acceptance criteria and the Step 17 acceptance card

The verification commits after V01/V02 changed only verification documents (plus `AGENTS.md` in the first evidence commit), not application source. The six reports therefore describe the same application tree while adding evidence sequentially.

## Acceptance mapping

| # | Stage 1 acceptance criterion | Classification | Existing verification evidence and decision |
| --- | --- | --- | --- |
| 1 | The backend boots with valid configuration. | **FAIL** | V02 proves the injected application factory boots, but V01-03 proves documented uppercase `DEVICE_WATCH_ENV` and `DATABASE_URL` are not loaded by case-sensitive Pydantic settings on POSIX. The intended Linux production process therefore cannot boot from its valid documented environment. |
| 2 | The backend validates connectivity to configured MySQL. | **BLOCKED BY ENVIRONMENT** | V02 proves readiness and the CLI execute `SELECT 1`, return the expected success/failure status behavior, dispose the engine, and redact secrets without network access. No real configured MySQL was available, so actual connectivity was not established. V02-09's disabled integration path is counted under criterion 9. |
| 3 | Alembic applies, reverses, and reapplies the baseline against MySQL 8.x. | **FAIL** | V02-07 and V02-08 prove deterministic pre-network defects: Alembic bypasses validated production TLS arguments, mishandles percent-encoded URLs, and cannot resolve its script directory from the documented repository-root command. V02-09 also prevents the configured integration test from running. The live MySQL cycle is additionally blocked, but the proved defects control the classification. |
| 4 | The agent boots and shuts down cleanly. | **PASS** | V03 records 18 passing agent tests plus successful short boot/requested-stop, cancellation, cleanup, and supported-loop signal callback characterizations. The Windows host could not perform a real process-signal check, but clean boot/stop behavior itself has direct evidence. |
| 5 | Collector contracts and registry are testable without real collection. | **FAIL** | V03 proves the empty/no-collection boundary and basic tests pass, but V03-01 shows the public result type rejects the approved `Mapping` interface and V03-02 shows duplicate padded names are accepted. These are defects in the collector/registry contract this criterion accepts. |
| 6 | The frontend shell tests, type-checks, and builds. | **PASS** | V04 records 8 passing tests, strict TypeScript success, ESLint success, and a successful static production build. V04's theme, exact empty-state, local Button, and regression-coverage defects remain open but do not negate the four commands named by this criterion. |
| 7 | Caddy configuration validates. | **BLOCKED BY ENVIRONMENT** | V05 statically verifies the checked-in Caddyfile and image contract, but Docker/Caddy was unavailable, so packaged `caddy validate` and runtime validation were not executed. |
| 8 | Development and production Compose configurations validate. | **BLOCKED BY ENVIRONMENT** | V02/V05 statically verify the intended topology, but Docker Compose rendering was unavailable. V02-01 and V05-02/V05-03 show that the custom tests/verifier cannot substitute for rendered Compose validation. |
| 9 | Automated tests pass independently. | **FAIL** | Executed focused suites passed, but required automated coverage is demonstrably absent or ineffective: V01-04 (engine options), V02-01 and V02-09 (rendered topology and configured integration), V03-05 (signal wiring), V04-04 (frontend behavior), and V05's verifier-test gaps. V06's audit tests were also blocked. Passing incomplete suites is insufficient evidence for this criterion. |
| 10 | MySQL is the only database implementation represented in the project. | **FAIL** | V06-02 records current post-Stage-1 unit tests that instantiate SQLite engines and proves the repository audit is a limited denylist rather than a positive MySQL allowlist. Production runtime configuration remains MySQL/PyMySQL-only, but the criterion is repository-wide. |
| 11 | No fake or partial Stage 2 workflow exists. | **FAIL** | V06-03 records current device/bootstrap migrations and domain/enrollment implementation modules. V03 and V04 still prove there is no agent sender/real collector or frontend business API/fake data, but any current partial Stage 2 server workflow is enough to fail this criterion. |
| 12 | Only Caddy publishes production host ports. | **PASS** | V05 statically verifies the production Compose source contains exactly Caddy and server, with only Caddy publishing `80/443` and server using internal `expose: 8000`. The focused forbidden-server-port test passed. |
| 13 | Missing production domain or database configuration fails clearly. | **BLOCKED BY ENVIRONMENT** | V01 proves the database setting is required and validation messages are sanitized. V05 confirms required Compose interpolation exists statically, but the missing-domain/database Compose rendering checks could not run. |
| 14 | Production settings reject an unverified MySQL connection. | **PASS** | V01's focused tests prove exact production TLS parameters, duplicates, additions, false verification, and incorrect values are rejected before engine creation without exposing the URL. V05 additionally shows the malformed production example is rejected. |
| 15 | The packaged proxy preserves `/api` and targets `server:8000`. | **BLOCKED BY ENVIRONMENT** | V05 verifies the source Caddyfile uses path-preserving `handle /api/*` and exactly `server:8000`, but image build, packaged validation, and runtime routing were unavailable. V05-04 also shows the text verifier incompletely rejects rewrite directives. |
| 16 | Production Compose mounts the configured CA file read-only at `/run/secrets/mysql-ca.pem`. | **PASS** | V05 verifies the checked-in Compose asset binds required `MYSQL_CA_CERT_PATH` to `mysql_ca`, mounts that source as `mysql-ca.pem` with mode `0444`, and uses the exact production path. V05-03 remains a verifier-coverage defect; runtime mount inspection was blocked. |

## Contradiction review

No irreconcilable factual contradiction was found. The apparent conflicts resolve as follows:

- **Schema-empty baseline versus later tables:** V02 explicitly verified only `20260831_0001` and excluded newer migrations. V06 evaluated the current whole tree and found later Stage 2 migrations. Both statements are true; criterion 11 uses the broader current-tree evidence.
- **MySQL-only runtime versus SQLite representation:** V01/V06 show that configured production dependencies and settings remain MySQL/PyMySQL-only. V06 separately found current test code instantiating SQLite. Criterion 10 is repository-wide, so the narrower runtime PASS does not control it.
- **Static deployment PASS versus runtime BLOCKED:** V05's Dockerfiles, Caddyfile, and Compose source checks are static. They do not establish Compose rendering, image packaging, Caddy parsing, or container behavior; criteria 7, 8, and 15 remain blocked.
- **Passing test commands versus failed steps:** V01-V06 repeatedly found behavior and mandatory coverage defects outside the assertions in passing suites. This is consistent and is why criterion 9 fails.
- **V05 Python execution versus V06 Python block:** V05 obtained access to the existing host interpreter; V06's later request was rejected because the workspace approval service was out of credits. This is an environment-state difference, not conflicting test output.
- **No agent/frontend Stage 2 behavior versus partial Stage 2 workflow:** V03/V04/V06 agree that agent sender/collector and frontend business behavior remain absent. V06 found partial Stage 2 behavior in server migrations and enrollment modules, which is sufficient to fail criterion 11.

## Environment blocks retained

No Docker, Compose, Caddy, container-health, or real-MySQL command was retried in V07. Existing blocks remain for:

- real configured MySQL connectivity;
- real MySQL baseline migration cycling;
- Caddy image/configuration validation;
- development and production Compose rendering;
- image builds and packaged proxy/runtime routing;
- container-health transitions; and
- production runtime secret-mount inspection.

V03's real Windows signal check, V04's supported-Node/browser checks, and V06's fresh repository-verifier/audit-test execution also remain environment-limited. They do not replace or downgrade the deterministic failures mapped above.

## V07 commands

Only lightweight evidence-integrity checks were run:

```text
Get-Content -Raw docs/verification/stage-01/01-repository-server-foundation.md
Get-Content -Raw docs/verification/stage-01/02-server-database-migrations.md
Get-Content -Raw docs/verification/stage-01/03-agent-foundation.md
Get-Content -Raw docs/verification/stage-01/04-frontend-foundation.md
Get-Content -Raw docs/verification/stage-01/05-deployment-topology.md
Get-Content -Raw docs/verification/stage-01/06-security-documentation.md
Get-Content <Stage 1 acceptance-criteria section>
Get-Content -Raw docs/superpowers/plans/2026-08-31-device-watch-stage-1/17-acceptance-verification.md
git log --oneline --reverse -- docs/verification/stage-01
git show --format= --name-only c32fa69eae0c2faa7ae6bad32b5b8f3f5caf1ae9
git diff --name-only c32fa69eae0c2faa7ae6bad32b5b8f3f5caf1ae9..HEAD
git status --short
git rev-parse HEAD
Select-String <V07 acceptance-table rows and PASS/FAIL/BLOCKED counts>
git diff --check
git status --short
git diff --stat
git diff
```

No agent, server, frontend, deployment, Docker, Caddy, or MySQL test was rerun.

## Acceptance conclusion

Stage 1 does not satisfy acceptance. Six criteria have proved failures and five more lack required environmental evidence. Criteria classified PASS retain their exact evidence scope and do not imply that the associated implementation step is defect-free. All defects recorded in V01-V06 remain open until addressed in a separately authorized implementation session.

## Final repository checks

- Acceptance-table integrity: **PASS** - exactly 16 rows: 5 PASS, 6 FAIL, and 5 BLOCKED BY ENVIRONMENT.
- `git diff --check`: **PASS** - no output.
- `git status --short`: **PASS** - only `?? docs/verification/stage-01/07-acceptance-review.md` is expected.
- `git diff --stat` and `git diff`: **PASS** - no tracked file differs from `HEAD`.
- No application, test, configuration, deployment, or earlier verification file was modified.
