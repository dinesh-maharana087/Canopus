# Device Watch Stage 1 Design

Date: 2026-08-31

Status: Approved in chat; awaiting written-spec review

## Purpose

Stage 1 creates a production-oriented, bootable foundation for Device Watch without implementing device-monitoring business workflows. The result is a monorepo whose native agent, API server, web application, and deployment assets are independently installable, runnable, and testable.

MySQL 8.x is the sole database target. The production database is external to the Docker Compose stack.

## Goals

- Provide a lightweight native Python agent lifecycle and collector contracts.
- Bootstrap a versioned FastAPI application with liveness and database-backed readiness checks.
- Configure SQLAlchemy and Alembic for MySQL through one required `DATABASE_URL`.
- Provide a React and TypeScript application shell with responsive navigation and theme support.
- Terminate production HTTPS and serve the API and web application through Caddy.
- Keep production and local-development topology clearly separated.
- Establish structured logging, graceful shutdown, health checks, migrations, and automated smoke tests.
- Document trust boundaries and stable contracts for future workflows.

## Non-goals

Stage 1 does not implement:

- Device enrollment or credential issuance.
- Heartbeat ingestion or outbound agent communication.
- Metrics, inventory, or service persistence.
- Device online/offline evaluation.
- Alert evaluation or delivery.
- Historical charts or monitoring dashboards.
- Real system, GPU, service, disk, network, SMART, container, or Docker collectors.
- Remote actions, reboot controls, SSH polling, or arbitrary command execution.
- A local agent database.

No endpoint, table, collector, sender, or user-interface fixture may imply that these capabilities already exist.

## Repository boundaries

```text
agent/   Native Python monitoring-agent foundation
server/  FastAPI backend and Alembic configuration
web/     React/TypeScript application shell
deploy/  Production and development deployment assets
docs/    Architecture and deployment documentation
```

The agent and server are separate Python projects with separate dependency sets and `uv.lock` files. The web application is a separate Node project with `package-lock.json`. No shared runtime package couples the three components in Stage 1. Python development and verification use `uv`; production images use frozen locks and contain neither `uv` nor build tooling at runtime.

Repository-wide files include `.gitignore`, `.editorconfig`, `.env.example`, and `README.md`. Component-specific environment examples may add only settings owned by that component; they must not duplicate configuration logic in code.

## Runtime topology

### Production

```text
Browser / future remote agent
        | HTTPS
        v
      Caddy
       |-- /api/* --> FastAPI on a private Compose network
       `-- /*      --> built React static files

FastAPI
   |
   v
External MySQL 8.x
```

`deploy/compose.prod.yml` contains Caddy and FastAPI only. Caddy is the only service that publishes host ports, using TCP 80 and 443. FastAPI has no published production port. MySQL is not a service in the production stack.

Caddy obtains its site address from the required `DEVICE_WATCH_DOMAIN` environment variable. It redirects HTTP to HTTPS, manages public certificates automatically, and stores certificate and runtime state in persistent `caddy_data` and `caddy_config` volumes.

The production Caddy image uses a multi-stage build. Node builds the web application in a build stage, and only static output is copied into the final Caddy image. The final image contains no Node runtime.

Caddy uses a path-preserving `handle /api/*` route with the exact upstream `server:8000`; no URI rewrite or prefix stripping is permitted. FastAPI binds `0.0.0.0:8000` inside its container. All other paths use an SPA fallback and static file serving.

Caddy's normal forwarded headers are retained. The production Uvicorn command explicitly enables proxy headers and uses `--forwarded-allow-ips=*`. The wildcard is acceptable only because the project-scoped production network has exactly two members, Caddy and FastAPI, and FastAPI publishes no host port. Compose validation and an automated topology assertion enforce those conditions. Adding another network peer or publishing the server port requires replacing the wildcard with an exact trusted-proxy range before deployment.

FastAPI receives its complete MySQL connection information from the required `DATABASE_URL`. For a database on the Linux Docker host, Compose adds:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Documentation explicitly rejects `localhost` as a way for a backend container to reach a host database.

### Local development

Local development uses HTTP and requires neither Caddy nor certificates:

- FastAPI runs directly on a developer-selected local port.
- Vite runs the React development server and proxies `/api` to FastAPI.
- The agent runs as a native Python process.
- Developers may run any component independently.

`deploy/compose.dev.yml` optionally runs MySQL 8.x for integration and migration verification. Its port binds to loopback, its data uses a development-only volume, and its sample credentials are explicitly non-production. An opt-in `verification` profile adds a `server-smoke` container built from the production server image, connected only to the development MySQL service, with no published port. This profile exists solely to assert the image's Docker health transition; normal local development still runs FastAPI natively. No production file imports or silently selects development database values.

## Configuration and failure behavior

Server settings use Pydantic settings and environment variables. `DEVICE_WATCH_ENV` is required and accepts exactly `development`, `test`, or `production`; it has no default. Production Compose sets it to `production`, the development workflow sets it to `development`, and automated tests set it to `test`. `DATABASE_URL` has no default and is validated to use the `mysql+pymysql` SQLAlchemy dialect. Missing or invalid required configuration stops application construction with a clear message. Connection strings and credentials are never included in logs, representations, or API responses.

When `DEVICE_WATCH_ENV=production`, the URL must contain all three exact query parameters: `ssl_ca=/run/secrets/mysql-ca.pem`, `ssl_verify_cert=true`, and `ssl_verify_identity=true`. Any missing parameter, different CA path, or false verification value is rejected before engine creation. Production Compose requires `MYSQL_CA_CERT_PATH`, defines a Compose secret from that operator-supplied host file, and mounts it read-only at `/run/secrets/mysql-ca.pem`. The `development` and `test` modes may omit TLS only for the isolated development/test database topology.

Production Compose uses required-variable interpolation for `DEVICE_WATCH_DOMAIN`, `DATABASE_URL`, and `MYSQL_CA_CERT_PATH`, so configuration rendering fails before containers start when any is absent. Development examples are opt-in files copied or supplied explicitly by the developer; the application contains no automatic development-database fallback.

An unavailable database does not make the process lie about its state:

- Liveness continues to describe whether the API process is running.
- Readiness returns a generic `503` and logs the internal failure without secrets.
- A database-check command exits nonzero when connectivity validation fails.

The agent configuration uses a dedicated environment prefix, strict parsing, and a 30-second default collection interval. Stage 1 has no server URL, device credential, or enrollment setting because no communication exists yet.

## Backend foundation

The server uses an application factory so tests can construct an app with explicit settings and injected database-check behavior. Production imports expose the factory-created ASGI application for Uvicorn.

The initial package boundaries are:

```text
server/src/device_watch_server/
  api/       Versioned routing and health endpoints
  core/      Settings and structured logging
  db/        Engine ownership and connectivity checks
  app.py     Application factory and lifespan
  main.py    Production ASGI entry point
```

Only these Stage 1 routes exist:

- `GET /api/v1/health/live` returns `200` when the process is serving requests.
- `GET /api/v1/health/ready` executes `SELECT 1`, returning `200` on success and `503` on failure.

Production API documentation is disabled by default. Development may explicitly enable documentation under the `/api` namespace. Request and response validation uses Pydantic. A small request-logging middleware records structured operational fields without logging bodies, authorization headers, cookies, connection strings, or environment values.

SQLAlchemy 2.x uses PyMySQL, centralized engine creation, connection pre-ping, and stale-connection recycling. The application lifespan owns engine cleanup and disposes the pool during graceful shutdown. Stage 1 creates no sessions or repositories until a business operation needs them.

The backend container runs as a non-root user, contains no build toolchain, and has no published port. Compose applies a read-only filesystem where practical, a temporary writable directory, dropped capabilities, and `no-new-privileges` without preventing Python or health checks from operating.

## Migration foundation

Alembic reads the same settings and `DATABASE_URL` as the application and imports the server's SQLAlchemy metadata. There is no second database URL in Alembic configuration.

The initial revision is an intentionally schema-empty baseline. Applying it records real Alembic version state in MySQL without inventing business tables whose contracts belong to later stages. Migration verification uses an actual MySQL 8.x instance and performs:

```text
upgrade head
downgrade base
upgrade head
```

The verification asserts the expected Alembic revision after each transition. Future domain migrations begin from this baseline.

## Agent foundation

The agent favors the Python standard library and has no runtime dependency on FastAPI, SQLAlchemy, Docker, a database, or a shell command. Its package boundaries are:

```text
agent/src/device_watch_agent/
  collectors/  Collector protocol, result types, and registry
  config.py    Typed environment configuration
  lifecycle.py Signal-aware runtime loop
  logging.py   Small structured logging setup
  main.py      Native process entry point
```

The collector contract provides a stable collector name and a typed result that can distinguish success, unavailability, and failure without requiring every metric to succeed. A registry enforces unique collector names and is valid when empty. Tests provide local test doubles; production contains no pretend collector.

The lifecycle uses standard-library asynchronous primitives, waits efficiently between configured intervals, and handles `SIGINT` and `SIGTERM`. The default registry is empty, so Stage 1 performs no collection and sends nothing. Shutdown cancels pending waits, completes cleanup, and exits successfully. A systemd unit example runs the native module, reads a protected environment file, restarts only on failure, and uses normal termination signals.

Future collection orchestration will isolate collector failures. Future HTTP delivery, authentication, retry, and backoff behavior are contracts in documentation only.

## Frontend foundation

The web project uses Vite, React, TypeScript, Tailwind CSS, React Router, and small shadcn-style local primitives. Its application boundaries separate routing, layout, reusable UI, theme state, and route-level pages.

The application shell provides:

- Responsive navigation for Dashboard, Devices, Alerts, Inventory, and Settings.
- Accessible navigation state and controls.
- CSS-variable design tokens for restrained, high-density infrastructure UI.
- System, light, and dark theme modes with local persistence.
- Explicit Stage 1 empty states with no fabricated device or health data.
- An SPA fallback that works through Caddy.

The five route boundaries are intentionally present because navigation is a Stage 1 deliverable. Each page contains only its title and an explicit “Not implemented in Stage 1” message. It contains no counts, statuses, charts, sample devices, API calls, or wording that suggests monitoring is active.

Recharts is the selected future chart library but is not installed until a real chart is implemented. No API client or query library is added because Stage 1 makes no business API request.

The frontend can run independently with Vite. Its production build is static and is the only web artifact copied into the Caddy runtime image.

## Logging, health, and shutdown

Server and agent logs are structured JSON produced with small standard-library configurations. Caddy retains structured access logs. Application loggers do not record secrets or full request payloads.

The FastAPI container health check calls its database-backed readiness endpoint with a small Python standard-library probe. The Caddy container health check runs `caddy validate` against the loaded Caddyfile; Docker separately treats an exited Caddy process as stopped. The server distinguishes liveness from readiness so operators can tell process failure from a dependency outage. Container stop signals flow to Uvicorn and the agent lifecycle, and owned resources are closed during shutdown.

Rate limiting is not implemented in Stage 1. The single Caddy ingress and FastAPI middleware boundary provide explicit insertion points for a later policy without changing public paths.

## Trust boundaries

The production trust boundaries are:

1. The public network terminates at Caddy. Only ports 80 and 443 are public.
2. Caddy-to-FastAPI traffic stays on the Compose network.
3. FastAPI initiates database connections to the separately administered MySQL service.
4. Future agents initiate outbound HTTPS to Caddy; the central platform never requires inbound device access or SSH credentials.
5. The local agent process runs with only the operating-system permissions its future collectors require; elevated access is not assumed globally.

Outbound agent connections are preferred over SSH polling because they avoid inbound firewall openings, central storage of device login credentials, and central arbitrary-command capability. They also work through common NAT and segmented network topologies.

External MySQL operators must restrict listening interfaces and firewall rules to the intended Docker host or subnet. Production database transport always uses verified TLS through supported PyMySQL connection options in `DATABASE_URL`; the database account must also be configured to require encrypted transport. Database backups, least-privilege accounts, grants, and certificate lifecycle remain deployment-operator responsibilities.

## Future contracts

The future data path is:

```text
Remote Agent
    | HTTPS
    v
  Caddy
    | /api
    v
 FastAPI
    |
    v
 MySQL
```

The future business sequence is:

```text
device enrollment
-> credentials/token
-> heartbeat submission
-> current health update
-> historical metric storage
-> health evaluation
-> alert generation
```

Enrollment will exchange a one-time bootstrap secret for a stable device identity and revocable device credential. The server will store only a credential hash; the agent will store the issued secret in a root-readable file rather than a local database.

Future submissions will use a versioned JSON envelope containing device identity, observation time, agent version, idempotency identity, and independent collector results. Sending will apply timeouts, bounded retries, and backoff. Server receipt time, rather than the device clock, will drive online/offline evaluation. Current state and historical observations remain distinct persistence concerns. Health evaluation runs after persistence and produces alert events rather than coupling alerts to collection or transport.

These statements define boundaries, not implemented routes, schemas, tables, or credentials.

## Testing and verification

Each component owns independent commands and tests.

### Agent

- Configuration parsing and validation.
- Collector protocol compatibility using test-only implementations.
- Empty and populated registry behavior.
- Duplicate-name rejection.
- Efficient boot and clean requested shutdown.
- Collector result status variants using test-only implementations.

### Server

- Required and invalid settings behavior.
- Application factory initialization.
- Liveness response.
- Readiness success and sanitized failure responses.
- Database-check command exit behavior.
- Structured logging redaction expectations.
- Real MySQL connectivity integration test.
- Alembic upgrade, downgrade, and re-upgrade verification.

### Web

- Application-shell render.
- Navigation route behavior.
- Theme selection and persistence.
- Strict TypeScript check.
- Linting.
- Production build.

### Deployment

- Development and production Compose rendering.
- Required production-variable failure behavior.
- Caddy configuration validation in the built Caddy image with an example domain.
- Automated inspection that the proxy upstream is `server:8000`, `/api` is not stripped, only Caddy publishes ports, and only Caddy and FastAPI join the production application network.
- Server and Caddy image builds.
- FastAPI container health transition against the development MySQL service.
- Caddy health-check command success against the packaged configuration.

### Repository audit

- Inspect direct and transitive dependencies for avoidable packages.
- Scan project files for credential-like values and private key material.
- Confirm MySQL is the only configured database family.
- Confirm Stage 2 endpoints, tables, collectors, senders, and mock monitoring data are absent.
- Inspect repository status and diff before handoff.

`deploy/verify_repository.py` performs the repeatable file audit with the Python standard library. It walks tracked and pending project files while excluding generated dependency/build directories, rejects tracked private-key or live-environment files, checks example-secret values against an explicit sample-value policy, rejects unknown database-related tokens outside a positive MySQL/SQLAlchemy allowlist, and enforces the Stage 1 source boundaries: health-only server routes, a schema-empty baseline, contract-only collector files, no sender module, and no frontend business API calls or monitoring fixtures.

Python projects use independent `pyproject.toml` and `uv.lock` files. The frontend commits `package-lock.json`. Runtime and development dependencies remain separated. Commands are deterministic and suitable for later CI use, but Stage 1 does not assume a hosted CI provider.

The authoritative verification matrix below is run from the indicated component directory. PowerShell examples set environment variables with `$env:NAME=...`; POSIX documentation provides equivalent `NAME=value` forms.

```powershell
# agent/
uv sync --frozen
uv run pytest
uv run ruff check .
uv run mypy src

# server/
uv sync --frozen
uv run pytest -m "not integration"
uv run ruff check .
uv run mypy src

# web/
npm ci
npm run test -- --run
npm run typecheck
npm run lint
npm run build

# repository root: real database and migrations
docker compose -f deploy/compose.dev.yml up -d --wait mysql
$env:DEVICE_WATCH_ENV='test'
$env:DATABASE_URL='mysql+pymysql://device_watch_dev:device_watch_dev@127.0.0.1:3307/device_watch'
uv run --project server pytest -m integration
uv run --project server alembic -c server/alembic.ini upgrade head
uv run --project server alembic -c server/alembic.ini downgrade base
uv run --project server alembic -c server/alembic.ini upgrade head
docker compose -f deploy/compose.dev.yml --profile verification up -d --build --wait server-smoke
docker compose -f deploy/compose.dev.yml --profile verification ps server-smoke
docker compose -f deploy/compose.dev.yml down

# repository root: deployment
docker compose --env-file deploy/.env.prod.example -f deploy/compose.prod.yml config
docker compose -f deploy/compose.dev.yml config
docker compose --env-file deploy/.env.prod.example -f deploy/compose.prod.yml build server caddy
docker run --rm --entrypoint caddy -e DEVICE_WATCH_DOMAIN=example.com device-watch-caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
python deploy/verify_topology.py --env-file deploy/.env.prod.example

# repository root: audit
uv tree --project agent --no-dev
uv tree --project server --no-dev
npm --prefix web ls --omit=dev
python deploy/verify_repository.py
git diff --check
git status --short
```

`README.md` and `docs/development.md` provide shell-specific examples without changing the underlying checks.

## Documentation deliverables

- `README.md`: architecture, components, local setup, commands, environment setup, and production topology.
- `docs/architecture.md`: components, trust boundaries, outbound-agent rationale, data flow, and future sequence.
- `docs/development.md`: independent workflows and optional development MySQL.
- `docs/deployment.md`: external MySQL, Linux host access, Caddy/TLS, volumes, environment requirements, startup, health, and validation.
- `docs/future-contracts.md`: future enrollment, identity, submission envelope, persistence separation, evaluation, and alert boundaries.

Environment examples contain conspicuous non-secret sample values. Ignore rules cover environment files, certificate state, virtual environments, caches, dependency directories, build output, coverage, local databases, and editor artifacts.

## Acceptance criteria

Stage 1 is complete only when:

1. The backend boots with valid configuration.
2. The backend validates connectivity to configured MySQL.
3. Alembic applies, reverses, and reapplies the baseline against MySQL 8.x.
4. The agent boots and shuts down cleanly.
5. Collector contracts and registry are testable without real collection.
6. The frontend shell tests, type-checks, and builds.
7. Caddy configuration validates.
8. Development and production Compose configurations validate.
9. Automated tests pass independently.
10. MySQL is the only database implementation represented in the project.
11. No fake or partial Stage 2 workflow exists.
12. Only Caddy publishes production host ports.
13. Missing production domain or database configuration fails clearly.
14. Production settings reject an unverified MySQL connection.
15. The packaged proxy preserves `/api` and targets `server:8000`.
16. Production Compose mounts the configured CA file read-only at `/run/secrets/mysql-ca.pem`.

## Principal risks

- External MySQL reachability depends on host firewall, bind-address, routing, grants, and TLS configuration outside this repository.
- Automatic public certificates require correct DNS and inbound access to the configured domain.
- The schema-empty baseline proves migration mechanics but intentionally provides no application table to exercise later domain mapping.
- Forwarded-header trust is safe only while FastAPI remains unexposed behind Caddy.
- Stage 1 defines future security contracts but cannot validate enrollment or credential rotation until those workflows are implemented.
- Package and container versions require routine security updates after the initial lock is created.
