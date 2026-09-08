# Step 10: Current Connectivity-State Migration

## Objective
Add only the persistence required for current last-seen connectivity state.

## Requirement / Rationale
The server needs authoritative current state without introducing heartbeat history or metrics storage.

## Prerequisites
Steps 02 and 09.

## In Scope
Alembic migration for nullable last-seen, latest submission identity, latest agent version, and any bounded deduplication state; indexes and downgrade.

## Out of Scope
Heartbeat API/service, evaluator, historical tables, metrics, alerts, and UI.

## Expected Files / Directories
`server/alembic/versions/`, server DB metadata/models, integration tests.

## Concrete Tasks
1. Choose one-to-one device state versus device columns intentionally.
2. Add MySQL-compatible timestamps and uniqueness/foreign-key constraints.
3. Define bounded idempotency retention without heartbeat history.
4. Verify upgrade/downgrade from the Step 02 head.

## Tests and Verification
Real-MySQL migration/schema inspection, constraint tests, empty-history assertion, Ruff, and mypy.

## Security Considerations
No credential/hash columns; no raw heartbeat body retention; timestamps are server-owned.

## Definition of Done
Migration stores only current connectivity inputs and is reversible without metric/history tables.

## Handoff Information
Record revision, columns, indexes, retention/deduplication choice, and downgrade evidence.

## Suggested Commit Message
`feat(stage2): add current connectivity migration`
