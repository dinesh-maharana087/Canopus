# Step 05: FastAPI Factory and Health Endpoints

## Objective

Create the factory-based FastAPI application with lifecycle ownership and only the two approved health routes.

## Why This Step Exists

The server needs a bootable process that distinguishes process liveness from database readiness without introducing Stage 2 workflows.

## Prerequisites

Steps 02 and 03.

## In Scope

Application factory, lifespan disposal, health response model, versioned router, liveness/readiness handlers, production docs disablement, and route tests.

## Out of Scope

Structured logging, request middleware, database CLI, Alembic, domain routes, sessions, repositories, and deployment images.

## Expected Files/Directories

`server/src/device_watch_server/api/`, `app.py`, `main.py`, `db/health.py`, and `server/tests/unit/test_app.py`.

## Implementation Tasks

1. Test exact health responses, injected readiness behavior, route allowlist, docs mode, and engine disposal.
2. Implement `create_app(settings, database_check)` and internal engine ownership.
3. Implement `SELECT 1` checking and generic `503` readiness failure.
4. Export the factory-created ASGI app from `main.py`.

## Tests and Verification

Run focused app tests, then the server unit slice. Confirm liveness never calls the database and failures expose neither exception details nor URLs.

## Definition of Done

- Exactly `/api/v1/health/live` and `/api/v1/health/ready` exist.
- Liveness is process-only; readiness is database-backed.
- Internal engines are disposed during lifespan shutdown.
- Production OpenAPI routes are disabled unless explicitly allowed in development.

## Handoff Information

Record route list, response contracts, lifecycle behavior, tests, and commit ID for Step 06 and packaging.

## Suggested Commit Checkpoint

`feat(server): add health-only FastAPI foundation`
