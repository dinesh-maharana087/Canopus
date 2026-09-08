# Step 11: Authenticated Heartbeat Service and API

## Objective
Authenticate devices and apply minimal heartbeats to current state.

## Requirement / Rationale
Heartbeat acceptance must reject invalid/revoked devices and atomically update authoritative server-receipt state.

## Prerequisites
Steps 04, 09, and 10.

## In Scope
Bearer authentication dependency, device/credential matching, `POST /api/v1/devices/{device_id}/heartbeat`, transaction update, receipt timestamp, idempotency, and sanitized errors.

## Out of Scope
Agent sender, retry policy, device read API, metrics, history, alerts, and operator auth redesign.

## Expected Files / Directories
`server/src/device_watch_server/api/`, auth dependency, heartbeat service/repository, unit/API/integration tests.

## Concrete Tasks
1. Extract and redact authorization safely.
2. Verify credential status and device lifecycle.
3. Apply repeated submission semantics without moving time backward.
4. Return server receipt timestamp and no secret/database fields.

## Tests and Verification
API tests for success, invalid/revoked/mismatched credentials, malformed/unsupported payloads, duplicate submission, clock injection, and real-MySQL updates.

## Security Considerations
HTTPS deployment requirement, constant-time/hash verification, generic auth failures, no auth-header logging, and no credential response.

## Definition of Done
Only an active credential can update its device’s current state, and all accepted state is server-time authoritative.

## Handoff Information
Record endpoint/status contract, auth dependency, transaction behavior, idempotency outcome, and redaction evidence.

## Suggested Commit Message
`feat(stage2): add authenticated heartbeat endpoint`
