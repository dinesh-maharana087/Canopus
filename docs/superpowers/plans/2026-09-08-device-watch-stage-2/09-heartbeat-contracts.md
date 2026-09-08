# Step 09: Heartbeat Protocol Contracts and Idempotency

## Objective
Define the minimal authenticated heartbeat request/response and duplicate-submission semantics.

## Requirement / Rationale
Connectivity needs a stable protocol without introducing metrics or history.

## Prerequisites
Steps 01 and 04.

## In Scope
Versioned envelope, UUID submission ID, optional diagnostic observation time, agent version, response receipt time, validation, and idempotency rules.

## Out of Scope
Heartbeat route, persistence migration, sender, retry implementation, metrics, and UI.

## Expected Files / Directories
`server/src/device_watch_server/domain/heartbeat.py`, shared protocol tests, agent-compatible contract module if needed.

## Concrete Tasks
1. Define exact minimal JSON schemas.
2. Reject unknown/unsupported protocol versions and metric-like fields where practical.
3. Define repeated submission behavior and monotonic last-seen rule.
4. Define sanitized error and response models.

## Tests and Verification
Serialization, validation, duplicate-ID, timestamp, and forbidden-field tests.

## Security Considerations
No credential fields in body; observation time is non-authoritative; no headers/body in logs.

## Definition of Done
Server and agent can implement the same minimal heartbeat contract without ambiguity.

## Handoff Information
Record JSON schemas, version policy, idempotency retention decision, and compatibility rules.

## Suggested Commit Message
`feat(stage2): define minimal heartbeat protocol`
