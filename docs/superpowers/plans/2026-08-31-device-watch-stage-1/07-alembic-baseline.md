# Step 07: Alembic Metadata and Schema-Empty Baseline

## Objective

Configure Alembic from the same server settings and establish a real-MySQL schema-empty baseline revision.

## Why This Step Exists

Migration mechanics must be real and reversible without inventing Stage 2 domain tables.

## Prerequisites

Steps 03 and 04.

## In Scope

Empty SQLAlchemy metadata, Alembic configuration/environment/template, revision `20260831_0001`, and integration migration cycle.

## Out of Scope

Business models, repositories, sessions, data migrations, production Compose, and monitoring persistence.

## Expected Files/Directories

`server/src/device_watch_server/db/base.py`, `server/alembic.ini`, `server/alembic/`, `server/tests/integration/`, and migration tests.

## Implementation Tasks

1. Write real-MySQL connectivity and `upgrade head -> downgrade base -> upgrade head` tests.
2. Define deterministic empty metadata and make Alembic consume `DATABASE_URL` only through settings.
3. Add behavior-free baseline revision with no mapped tables.
4. Run the cycle and inspect current revisions and tables.

## Tests and Verification

Start the Step 04 database, run integration tests and explicit Alembic commands, and assert the expected revision after every transition.

## Definition of Done

- Alembic has one schema-empty baseline revision.
- No business table exists after upgrade.
- URL configuration is not duplicated in `alembic.ini`.
- Real MySQL cycle passes, or the environmental block is recorded.

## Handoff Information

Record revision IDs, MySQL evidence, table inspection, and commit ID.

## Suggested Commit Checkpoint

`feat(server): add schema-empty Alembic baseline`
