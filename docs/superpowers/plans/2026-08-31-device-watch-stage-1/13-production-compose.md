# Step 13: Production Compose Topology and Verifier

## Objective

Define and verify the two-service production topology, required variables, secrets, network trust boundary, and container hardening.

## Why This Step Exists

The approved deployment exposes only Caddy and keeps FastAPI and external MySQL private and correctly configured.

## Prerequisites

Steps 11 and 12.

## In Scope

Production env shape, `compose.prod.yml`, topology verifier, Caddy/server health checks, CA secret mount, required interpolation, ports, volumes, capabilities, and network assertions.

## Out of Scope

Development MySQL/smoke profile, application behavior, real certificates, database provisioning, and Stage 2 workflows.

## Expected Files/Directories

`deploy/.env.prod.example`, `deploy/compose.prod.yml`, `deploy/verify_topology.py`, and topology tests.

## Implementation Tasks

1. Write valid/invalid rendered JSON and Caddy fixtures before verifier code.
2. Define exactly `caddy` and `server`, only Caddy ports 80/443, external MySQL, exact server:8000 upstream, and two-member network.
3. Require domain/database/CA variables, mount CA read-only, add host gateway, enforce read-only/rootless/no-new-privileges controls.
4. Implement sanitized standard-library verifier using Compose rendered JSON.

## Tests and Verification

Run topology tests, Compose render, verifier, image builds, Caddy validation, and required-variable failure cases. Never echo `DATABASE_URL`.

## Definition of Done

- Valid topology passes and each forbidden topology fails.
- Only Caddy publishes production ports.
- FastAPI has no host port and production MySQL is absent from Compose.
- Proxy trust and CA/TLS mount assertions are executable.

## Handoff Information

Record rendered topology, image/health results, missing-variable failures, verifier commit ID, and any Docker limitation.

## Suggested Commit Checkpoint

`feat(deploy): enforce production Compose topology`
