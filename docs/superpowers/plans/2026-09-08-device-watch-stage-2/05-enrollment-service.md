# Step 05: Enrollment Transaction Service

## Objective
Implement the server transaction that consumes a valid bootstrap, creates one device, issues one credential, and commits atomically.

## Requirement / Rationale
Concurrent or retried enrollment must not create duplicate identities or expose a credential more than once.

## Prerequisites
Steps 02–04.

## In Scope
Transaction boundary, bootstrap lock/atomic consumption, device creation, credential persistence, one-time response object, and failure mapping.

## Out of Scope
HTTP routing, operator UI, agent client, heartbeat, device listing, and user authentication.

## Expected Files / Directories
`server/src/device_watch_server/enrollment/`, repositories/services, unit and integration tests.

## Concrete Tasks
1. Lock or atomically claim bootstrap material.
2. Create device and hashed credential in one transaction.
3. Ensure rollback on any failure and no duplicate identity on concurrency.
4. Return the raw credential only in the in-memory success result.

## Tests and Verification
Service unit tests, concurrent transaction integration tests on MySQL, rollback tests, and response redaction assertions.

## Security Considerations
Generic invalid bootstrap failures, no secret logging, no plaintext database fields, and no credential replay response.

## Definition of Done
Exactly one successful consumer receives a new identity and credential; all other attempts fail safely.

## Handoff Information
Record transaction isolation/locking strategy, error taxonomy, and retry behavior.

## Suggested Commit Message
`feat(stage2): implement enrollment transaction service`
