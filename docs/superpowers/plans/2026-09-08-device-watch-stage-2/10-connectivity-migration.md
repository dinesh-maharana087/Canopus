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

## Implementation Handoff — 2026-09-14

Status: **Implemented; real-MySQL verification BLOCKED BY ENVIRONMENT**.
The master-index status remains **Pending** until the required database checks
pass. No Step 11 work was started.

### Schema and retention decision

Revision `20260914_0005` in
`server/alembic/versions/20260914_0005_current_connectivity.py` revises the existing
head `20260913_0004`. The path from the Step 02 head is
`20260908_0002 -> 20260908_0003 -> 20260913_0004 -> 20260914_0005`.
The intervening revisions are preserved; this migration does not fork or rewrite
the established migration history.

The chosen layout adds **device columns**, using the existing `devices.device_id`
primary key to bind exactly one current-state tuple to each device. It creates
no new table or foreign key. The three additions are:

| Column | MySQL type | Null/default policy | Meaning |
| --- | --- | --- | --- |
| `last_seen_at` | `DATETIME(6)` | Nullable, no default or automatic update | Server receipt time, stored as UTC without timezone metadata, preserving microseconds |
| `last_heartbeat_submission_id` | `VARCHAR(36)` | Nullable, no default | Latest canonical submission UUID for this device |
| `last_agent_version` | `VARCHAR(64)` | Nullable, no default | Version from the latest accepted submission |

Existing and newly enrolled devices have null connectivity inputs until the
later authenticated service writes them. There is no observation-time column,
stored connectivity status, credential/hash column, raw body, metrics, or history.

- Check constraint `ck_devices_submission_requires_last_seen` enforces
  `last_heartbeat_submission_id IS NULL OR last_seen_at IS NOT NULL`, matching
  the existing domain boundary.
- Nonunique index `ix_devices_last_seen_at` indexes `last_seen_at` for current
  last-seen lookup. Existing primary-key uniqueness is unchanged. There is no
  global submission-ID uniqueness; different devices may use the same UUID.
- Deduplication retains only the latest submission ID per device until replaced,
  with no TTL or history. Step 09's duplicate and monotonic-time decisions remain
  the contract. The migration does not implement those update decisions, receipt
  clock ownership, authentication, or the evaluator.
- `server/src/device_watch_server/db/connectivity.py` defines a SQLAlchemy Core
  projection of the same physical `devices` table containing its key and the
  three current-state columns. Alembic owns physical schema creation. The
  identity-only enrollment projection and shared Stage 1 metadata are unchanged;
  no `create_all()` or new ORM ownership is introduced.

### Downgrade and evidence

The single-revision downgrade to `20260913_0004` drops the last-seen index and
submission/timestamp check before dropping the three new columns. It deliberately
discards current connectivity values and preserves device identity, bootstraps,
and credentials. Re-upgrade starts those three columns at null. Returning all
the way to Step 02 also executes the existing 0004/0003 downgrades; those earlier
tables are not dropped by the Step 10 revision itself.

| Focused check | Result |
| --- | --- |
| Revision chain and single head | **PASS**, `0005` follows `0004`; path to `0002` is linear |
| MySQL offline upgrade/downgrade SQL | **PASS**, only three nullable columns, one check, and one nonunique index in the Step 10 delta; inverse removes only those additions |
| Offline path from/to Step 02 | **PASS**, traverses existing revisions and preserves `devices` identity storage |
| Current-state metadata and enrollment-query boundary | **PASS**, compiled MySQL schema/query checks match the migration and leave enrollment queries at their existing identity boundary |
| Focused pytest | **6 passed, 1 skipped**, exit 0; the skip is the real-MySQL test and is not a PASS |
| Ruff and strict mypy | **PASS**, limited to four new Step 10 source/test files |
| Bounded migration/metadata/fixture review | **PASS**, no remaining implementation blocker |
| Real-MySQL schema inspection, constraints and round trips | **BLOCKED BY ENVIRONMENT**, `DATABASE_URL` absent and Docker unavailable |

The guarded real-MySQL test is
`server/tests/integration/test_connectivity_migration_mysql.py`. It requires
protected `DATABASE_URL` configuration for a dedicated disposable MySQL 8.x
database, `DEVICE_WATCH_ENV=test`, and `DEVICE_WATCH_DISPOSABLE_DATABASE=1`.
It runs serially, accepts only an empty database or empty baseline/Step 02 schema,
and refuses unexpected revisions/tables, views, and existing device rows before
mutation. It seeds only synthetic device identities, checks null initialization,
microsecond storage, submission/timestamp constraints, per-device retention,
absence of history tables, and identity preservation through upgrade/downgrade/
re-upgrade. It deletes only its fixture identities and finishes at Step 02.
No live database was changed in this session.

Exact focused commands and the environment limitation are recorded in the
[progress document](../../../progress/current-status.md). No newly identified
out-of-scope finding remains, and no earlier-step implementation was changed.
