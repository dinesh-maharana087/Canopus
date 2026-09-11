# Architecture

The Stage 1 foundation keeps the native agent, FastAPI server, and React web application as independent projects. The current repository adds partial Stage 2 server-side device identity and enrollment-bootstrap foundations without changing the production topology. Caddy remains the only public production ingress.

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

## Trust Boundaries

- Future agents initiate outbound HTTPS; the Stage 1 agent has no sender, credentials, database, or network client.
- Caddy publishes ports 80 and 443, serves the compiled SPA, and forwards `/api/*` unchanged to private `server:8000`.
- FastAPI publishes no host port. Its only approved routes are `/api/v1/health/live` and `/api/v1/health/ready`.
- MySQL is external to production Compose and is administered separately. The server receives its complete connection string through required `DATABASE_URL` and production TLS is verified through the CA mounted at `/run/secrets/mysql-ca.pem`.
- The production Compose network contains exactly Caddy and FastAPI. The server command trusts forwarded headers from the private network; any topology change requires narrowing that trust instead of retaining a wildcard.
- Linux production Compose supplies `host.docker.internal:host-gateway` for deployments whose external database is on the Docker host. `localhost` inside the server container means the container itself and does not reach the host database.

The historical Stage 1 Alembic revision `20260831_0001` records migration state without business tables. The current migration head extends that baseline with the Stage 2 `devices` and `enrollment_bootstraps` tables. Current Stage 2 server code also contains typed device/bootstrap contracts and bootstrap cryptography, persistence, and lifecycle services, but no public enrollment, heartbeat, or device API route exists yet. The agent registry remains empty without a concrete collector or sender, and the web retains its Stage 1 route boundaries without business API calls or fabricated monitoring data.
