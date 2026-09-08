# Architecture

Stage 1 keeps the native agent, FastAPI server, and React web application as independent projects. Caddy is the only public production ingress.

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

The schema-empty Alembic baseline records migration state without business tables. The agent registry is empty and its contracts are testable without a concrete collector. The web routes are empty Stage 1 boundaries without API calls or fabricated monitoring data.
