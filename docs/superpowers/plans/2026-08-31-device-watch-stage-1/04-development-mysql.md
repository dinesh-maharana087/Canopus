# Step 04: Development MySQL Service Foundation

## Objective

Provide the isolated, loopback-bound MySQL 8.4 development service used by later integration and smoke checks.

## Why This Step Exists

Real migration and container-health verification need a repeatable MySQL instance while production keeps MySQL external.

## Prerequisites

Step 01.

## In Scope

`deploy/.env.dev.example`, the initial `mysql` service in `deploy/compose.dev.yml`, health check, development volume, sample credentials, and topology test.

## Out of Scope

Server image, server-smoke profile, Caddy, production Compose, Alembic files, application code, and production credentials.

## Expected Files/Directories

`deploy/.env.dev.example`, `deploy/compose.dev.yml`, `deploy/tests/test_development_mysql.py`.

## Implementation Tasks

1. Test rendered configuration for exactly one loopback-bound `mysql:8.4.11` service.
2. Use conspicuous non-production sample values and a development-only named volume.
3. Render and start the service, recording whether Docker/MySQL is available.

## Tests and Verification

Run the focused topology test, `docker compose ... config --format json`, and `up -d --wait mysql` when Docker is available.

## Definition of Done

- MySQL is the only service in this initial dev file.
- Port binding is `127.0.0.1:3307:3306`.
- Health and volume configuration are validated.
- Production files are neither imported nor modified.

## Handoff Information

Record render/start results, image health, connection values used for test-only work, and commit ID.

## Suggested Commit Checkpoint

`build(deploy): add isolated development MySQL`
