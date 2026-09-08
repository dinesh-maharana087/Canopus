# Step 07: Agent Secure Identity Storage

## Objective
Persist device identity and issued credential using the approved protected-file model.

## Requirement / Rationale
An agent must survive restart without a local database or repeated enrollment while failing closed on unsafe state.

## Prerequisites
Stage 1 agent package; Step 01 contracts.

## In Scope
Versioned file schema, configurable path, permissions/ownership checks, atomic write, read/validation, missing/malformed behavior, quarantine/delete transition.

## Out of Scope
HTTP enrollment, heartbeat sender, metrics, local database, credential generation, and server changes.

## Expected Files / Directories
`agent/src/device_watch_agent/identity.py` or equivalent, `agent/tests/`.

## Concrete Tasks
1. Define storage path configuration without server URL or secret defaults.
2. Implement restrictive parent/file permissions and atomic replacement.
3. Validate UUID, credential format, version, and timestamps.
4. Test missing, malformed, unsafe, interrupted, and valid restart cases.

## Tests and Verification
Linux permission tests where available, temporary-file tests on Windows-compatible paths, restart simulation, and Ruff/mypy.

## Security Considerations
Mode `0600`, dedicated owner expectations, no plaintext backup copies, no secret logs, and no local database.

## Definition of Done
Valid identity survives restart; unsafe or malformed state never produces authenticated traffic.

## Handoff Information
Record path/configuration contract, permission behavior by platform, and re-enrollment state transitions.

## Suggested Commit Message
`feat(stage2): add protected agent identity storage`
