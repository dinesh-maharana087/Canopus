# Step 01: Domain Contracts and Persistence Boundaries

## Objective
Define shared Stage 2 identity, enrollment, credential, heartbeat, and connectivity contracts before implementation.

## Requirement / Rationale
All later migrations and APIs need one unambiguous vocabulary and must not smuggle Stage 3 metrics into connectivity behavior.

## Prerequisites
Completed Stage 1.

## In Scope
Typed server domain values, protocol version constants, UUID identity rules, status values, timestamp policy, minimal request/response shapes, persistence ownership decisions, and explicit Stage 3 exclusions.

## Out of Scope
Runtime routes, migrations, credential generation, collectors, senders, UI, and database code.

## Expected Files / Directories
`server/src/device_watch_server/domain/`, `server/tests/unit/`, `docs/acceptance/stage-02-device-connectivity.md` only if contract clarifications are needed.

## Concrete Tasks
1. Define device identity/status, bootstrap state, credential state, heartbeat envelope, and connectivity DTO contracts.
2. Define server-receipt timestamp semantics and protocol version handling.
3. Define no-history/no-metrics persistence boundary and response redaction rules.
4. Write unit tests for valid/invalid identity and minimal payload shapes.

## Tests and Verification
Run focused domain tests, Ruff, mypy, and inspect serialized payloads for excluded metrics and secrets.

## Security Considerations
Use UUIDv4 server-generated identities, bounded display names, strict protocol versions, and no secret fields in reusable DTOs.

## Definition of Done
Contracts are stable, typed, tested, minimal, and referenced by later plans without adding runtime behavior.

## Handoff Information
Record public names, version values, status semantics, timestamp rules, and unresolved protocol questions.

## Suggested Commit Message
`feat(stage2): define device connectivity contracts`
