# Step 03: Bootstrap Provisioning and Persistence

## Objective
Define operator-controlled creation and server persistence of one-time enrollment bootstrap material.

## Requirement / Rationale
Enrollment must be authorized without introducing a general user/RBAC system or storing plaintext bootstrap secrets.

## Prerequisites
Steps 01–02.

## In Scope
Provisioning command/service boundary, random secret generation, HMAC digest/fingerprint, expiration, consumed/revoked states, labels, and bootstrap migration/table.

## Out of Scope
Enrollment HTTP route, device creation transaction, device credentials, interactive authentication, and agent code.

## Expected Files / Directories
`server/alembic/versions/`, `server/src/device_watch_server/enrollment/`, `server/tests/unit/`, `server/tests/integration/`.

## Concrete Tasks
1. Add bootstrap persistence migration from the device identity head.
2. Implement protected operator provisioning that displays plaintext once without logging it.
3. Implement digest lookup and lifecycle state transitions.
4. Test expiration, revocation, single-use state, and safe output.

## Tests and Verification
Unit lifecycle tests, subprocess/output redaction tests, uniqueness tests, and real-MySQL persistence tests.

## Security Considerations
Use cryptographic randomness, server-held pepper/HMAC, no plaintext column, no URL transport, and generic invalid-state errors.

## Definition of Done
An operator can create auditable one-time bootstrap material whose stored representation cannot recover the plaintext and whose lifecycle is testable.

## Handoff Information
Record provisioning interface, digest format, expiration policy, state transitions, and operator handling assumptions.

## Suggested Commit Message
`feat(stage2): add enrollment bootstrap persistence`
