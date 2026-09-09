# Stage 1 Verification V05 — Deployment topology

Date: 2026-09-09  
Scope: Stage 1 Steps 11–14 only  
Overall result: **FAIL**

Docker and Docker Compose were checked once and were unavailable. No installation or retry was attempted. Static inspection, existing non-Docker tests, and direct verifier characterizations continued.

## Components reviewed

- `.dockerignore`
- `server/Dockerfile`
- `deploy/caddy/Dockerfile`
- `deploy/caddy/Caddyfile`
- `deploy/compose.prod.yml`
- `deploy/compose.dev.yml`
- `deploy/.env.prod.example` and `deploy/.env.dev.example`
- `deploy/verify_topology.py`
- `deploy/tests/test_production_topology.py`
- `deploy/tests/test_development_topology.py`
- `deploy/tests/test_development_mysql.py`
- Stage 1 design, index, status, execution cards, and plan sections limited to Steps 11–14

## Results

| Area | Result | Evidence |
| --- | --- | --- |
| Step 11 — hardened FastAPI image | PASS | Pinned multi-stage Python image; frozen runtime-only dependency sync; narrowly copied runtime files; fixed non-root UID/GID `10001`; port `8000`; stdlib readiness health check; and production Uvicorn command with `--proxy-headers --forwarded-allow-ips=*`. `.dockerignore` limits the build inputs. |
| Step 11 — built-image inspection and health | BLOCKED BY ENVIRONMENT | Docker CLI was unavailable, so image build, final-user/tooling inspection, and container health could not run. |
| Step 12 — Caddy image and routing assets | PASS | Pinned Node build stage and pinned Caddy runtime stage; `npm ci` uses the package lock; only `web/dist` and the Caddyfile enter the runtime image. `handle /api/*` proxies exactly to `server:8000` without `handle_path`; the fallback serves `/srv` with SPA routing. |
| Step 12 — path-preservation verifier | FAIL | The verifier rejects only `handle_path` and `strip_prefix`; a direct probe showed that an explicit `rewrite` directive is accepted. See V05-04. |
| Step 12 — image build and Caddy runtime validation | BLOCKED BY ENVIRONMENT | Docker CLI was unavailable, so the Caddy build, packaged `caddy validate`, runtime routing, and container health could not run. |
| Step 13 — production Compose asset | PASS | The source defines exactly `caddy` and `server`; only Caddy publishes `80/443`; server exposes only `8000`; both services are hardened; the CA secret target is `/run/secrets/mysql-ca.pem`; and Caddy has `caddy_data` and `caddy_config` volumes. |
| Step 13 — production environment example | FAIL | The example database URL contains literal `\&` separators. Direct parsing showed corrupted `ssl_ca` and `ssl_verify_cert` values, and the server's production settings rejected the value. See V05-01. |
| Step 13 — production topology verifier | FAIL | Direct probes found that rendered-style volume objects raise `unhashable type: 'dict'`, and the server can mount a different secret source while the verifier still passes. See V05-02 and V05-03. |
| Step 13 — Compose rendering and runtime topology | BLOCKED BY ENVIRONMENT | Docker CLI was unavailable, so production Compose rendering, required-variable rendering checks, image builds, runtime topology, and health transitions could not run. |
| Step 14 — development topology | PASS | MySQL is pinned to `8.4.11`, publishes only `127.0.0.1:3307`, uses a named data volume and health check, and the `server-smoke` service is opt-in through the `verification` profile with no published port. Existing focused tests passed. |
| Step 14 — development runtime | BLOCKED BY ENVIRONMENT | Docker CLI was unavailable, so Compose rendering and MySQL/server-smoke startup and health checks could not run. |

## Stable contracts verified

- The production server image has one centralized, non-root runtime and the approved Uvicorn/proxy command.
- The production web image is a multi-stage React build whose final image contains the static output served by Caddy.
- The checked-in Caddyfile preserves `/api/*`, has one upstream at exactly `server:8000`, and provides the Stage 1 SPA fallback.
- The checked-in production Compose file has exactly two services and keeps the FastAPI service private from host ports.
- The checked-in production Compose file declares the CA secret mount and both persistent Caddy volumes.
- The checked-in development Compose file provides the approved loopback-only MySQL topology and an opt-in `server-smoke` service under the `verification` profile.

These asset-level contracts pass. The overall V05 result is nevertheless FAIL because the production environment example and required verifier behavior are defective.

## Commands actually executed

```text
Get-Command docker -ErrorAction SilentlyContinue
& 'D:\Dinesh\deviceHealth\.tmp\uv-tool\Scripts\uv.exe' --no-python-downloads --offline --cache-dir 'D:\Dinesh\deviceHealth\.tmp\uv-cache' run --project server --frozen --group test pytest deploy/tests/test_production_topology.py deploy/tests/test_development_topology.py deploy/tests/test_development_mysql.py -q
& 'D:\Dinesh\deviceHealth\.tmp\uv-tool\Scripts\uv.exe' --no-python-downloads --offline --cache-dir 'D:\Dinesh\deviceHealth\.tmp\uv-cache' run --project server --frozen --group test python -m py_compile deploy/verify_topology.py
git diff --check
git status --short
```

Additional read-only inline Python characterizations called `validate_topology`, `validate_caddyfile`, and the server `Settings` model for:

- rendered-style Caddy volume objects;
- an incorrect service secret source;
- an explicit Caddy `rewrite` directive; and
- the production example's URL query values without printing the URL or credentials.

Read-only `rg`/`Get-Content` inspections were limited to the components listed above. Final repository checks are recorded below.

### Test results

- Focused deployment tests: **PASS** — 6 passed, 0 failed.
- `deploy/verify_topology.py` byte-compilation: **PASS**.
- Existing production verifier test adequacy: **FAIL** — the handcrafted fixture uses short-form string volumes rather than rendered-style mount objects, omits the service secret source, and has no explicit `rewrite` case. Consequently, the focused tests pass while V05-02 through V05-04 remain undetected.

The first sandbox-only rerun could not access the existing host Python interpreter. The same locked, offline commands were then run with access to that pre-existing interpreter and passed; no software was installed.

## Defects discovered

### V05-01 — production environment example fails the required TLS contract

**FAIL.** `deploy/.env.prod.example:3` escapes both ampersands in the database URL as `\&`. Docker documents escape processing for double-quoted values; backslashes in an unquoted value remain part of that value. The direct characterization observed the backslash in the first two TLS values, and production `Settings` rejected the URL because it did not contain the exact required TLS parameters.

Reference: <https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/>

### V05-02 — topology verifier cannot consume rendered-style volume objects

**FAIL.** `deploy/verify_topology.py:79` converts `caddy.volumes` directly to a set. A representative rendered JSON mount shaped as `{type, source, target}` therefore raises `unhashable type: 'dict'`. The verifier itself obtains JSON from `docker compose config --format json`, while the existing test fixture at `deploy/tests/test_production_topology.py:36` supplies short-form strings. Docker's service-volume model supports the object form with `type`, `source`, and `target` fields.

Reference: <https://docs.docker.com/reference/compose-file/services/#volumes>

### V05-03 — CA mount source is not verified

**FAIL.** `deploy/verify_topology.py:84-86` verifies only the mounted target/mode and separately checks that a top-level `mysql_ca` secret exists. It never requires the server mount's `source` to equal `mysql_ca`. A direct probe using `source: wrong_ca` returned no violations. The valid test fixture also omits `source`, so this contract is untested.

### V05-04 — general Caddy rewrites are not rejected

**FAIL.** `deploy/verify_topology.py:48-49` searches for `handle_path` and `strip_prefix`, but not `rewrite`. A direct probe containing an explicit rewrite returned no violation, contrary to the Step 12 path-preservation verification requirement. The checked-in Caddyfile itself does not rewrite the API path.

## Environment blocks

Docker CLI/Compose was unavailable on the host. The following remain **BLOCKED BY ENVIRONMENT**:

- FastAPI and Caddy image builds;
- final-image non-root and build-tool exclusion inspection;
- production and development Compose rendering;
- packaged Caddy configuration validation and runtime route checks;
- production container-health checks; and
- development MySQL and opt-in server-smoke startup/health checks.

## Source locations future stages may rely on

- Server image contract: `server/Dockerfile`
- Build-context safeguards: `.dockerignore`
- Static web/Caddy image: `deploy/caddy/Dockerfile`
- API and SPA routing: `deploy/caddy/Caddyfile`
- Production topology and secret/volume wiring: `deploy/compose.prod.yml`
- Development MySQL and smoke profile: `deploy/compose.dev.yml`
- Topology policy verifier: `deploy/verify_topology.py`
- Deployment tests: `deploy/tests/test_production_topology.py`, `deploy/tests/test_development_topology.py`, `deploy/tests/test_development_mysql.py`
- Environment templates: `deploy/.env.prod.example`, `deploy/.env.dev.example`

## Final repository checks

- `git diff --check`: **PASS** — no output.
- `git status --short`: **PASS** — only `?? docs/verification/stage-01/05-deployment-topology.md` is expected.
- No application, test, deployment, or configuration source was modified.
