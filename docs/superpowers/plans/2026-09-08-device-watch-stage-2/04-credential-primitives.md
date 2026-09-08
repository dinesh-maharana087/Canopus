# Step 04: Credential Hashing and Verification Primitives

## Objective
Implement isolated device credential generation, hashing, verification, lookup identifiers, and revocation primitives.

## Requirement / Rationale
The server must authenticate devices without persisting or exposing plaintext credentials.

## Prerequisites
Step 01; Stage 1 dependency policy review.

## In Scope
Opaque credential format, secure random generation, public key identifier, approved password-hash dependency, constant-time verification boundary, revocation state, and redaction tests.

## Out of Scope
Enrollment transaction, HTTP authentication dependency, agent file storage, routes, and migration wiring.

## Expected Files / Directories
`server/src/device_watch_server/auth/`, `server/pyproject.toml`/lock only if approved dependency is added, `server/tests/unit/`.

## Concrete Tasks
1. Characterize and pin the selected hash implementation.
2. Generate credentials with sufficient entropy and separate lookup identifier.
3. Verify valid, invalid, malformed, and revoked credentials.
4. Define rotation/revocation primitive for later service use.

## Tests and Verification
Hash/verify property tests, malformed-input tests, timing-safe API review, redaction tests, Ruff, mypy, and dependency-tree inspection.

## Security Considerations
Never log raw credentials or hashes; reject weak formats; avoid credential identifiers that reveal device identity.

## Definition of Done
Credential primitives are independently tested and expose no plaintext persistence requirement.

## Handoff Information
Record format, hash parameters, dependency rationale, revocation semantics, and rotation boundary.

## Suggested Commit Message
`feat(stage2): add device credential primitives`
