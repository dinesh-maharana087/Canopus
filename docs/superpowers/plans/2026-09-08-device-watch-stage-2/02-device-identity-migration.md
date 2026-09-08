# Step 02: Device Identity Migration

## Objective
Add the first Alembic migration for server-owned device identity.

## Requirement / Rationale
Enrollment needs a durable UUID identity independent of mutable hostname, IP, or MAC values.

## Prerequisites
Step 01; Stage 1 baseline `20260831_0001`.

## In Scope
Device table migration, UUID primary key, bounded display name, created timestamp, lifecycle status, uniqueness constraints, downgrade, and real-MySQL migration tests.

## Out of Scope
Credentials, bootstrap material, heartbeat state, routes, repositories, metrics, and UI.

## Expected Files / Directories
`server/alembic/versions/`, `server/src/device_watch_server/db/`, `server/tests/integration/`.

## Concrete Tasks
1. Add migration from the Stage 1 baseline.
2. Choose MySQL-compatible UUID/timestamp/status representations.
3. Verify upgrade/downgrade and uniqueness against real MySQL.
4. Keep metadata and naming conventions deterministic.

## Tests and Verification
Run migration unit characterization, real-MySQL upgrade/downgrade, schema inspection, Ruff, and mypy.

## Security Considerations
Do not derive identity from machine properties; never include credentials or bootstrap data in the device table.

## Definition of Done
A reversible migration creates only the device identity schema with constraints and no Stage 3 tables.

## Handoff Information
Record revision ID, columns, indexes, downgrade evidence, and database compatibility notes.

## Suggested Commit Message
`feat(stage2): add device identity migration`
