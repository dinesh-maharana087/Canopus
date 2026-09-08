# Step 14: Development Smoke Profile

## Objective

Extend the isolated development Compose file with an opt-in server image health transition against development MySQL.

## Why This Step Exists

The production server image must prove its Docker health behavior without changing normal native local development or production topology.

## Prerequisites

Steps 04 and 11.

## In Scope

`verification` profile, unexposed `server-smoke`, dependency on healthy MySQL, test environment URL, and development topology tests.

## Out of Scope

Caddy, certificates, production Compose, new server endpoints, migration implementation, and normal developer startup requirements.

## Expected Files/Directories

Modify `deploy/compose.dev.yml` and `.env.dev.example` only as needed; add development topology tests.

## Implementation Tasks

1. Test that MySQL remains loopback-bound and `server-smoke` is profile-gated and portless.
2. Add service-name database URL, `DEVICE_WATCH_ENV=test`, health dependency, and no production values.
3. Render, start MySQL, start the profile, inspect health, and tear down.

## Tests and Verification

Run focused topology tests and the complete Docker smoke sequence when Docker is available.

## Definition of Done

- Normal dev file still supports native FastAPI/Vite workflows.
- Opt-in server-smoke reaches healthy against MySQL.
- No Caddy, certificates, or published server port are introduced.

## Handoff Information

Record profile render/health/teardown evidence and commit ID for Step 15.

## Suggested Commit Checkpoint

`feat(deploy): add development server smoke profile`
