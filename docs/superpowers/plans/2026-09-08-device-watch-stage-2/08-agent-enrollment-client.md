# Step 08: Agent Enrollment Client

## Objective
Implement outbound agent enrollment against the Stage 2 API and persist the one-time result.

## Requirement / Rationale
Enrollment must be explicit, timeout-bounded, and safe across first boot and uncertain network outcomes.

## Prerequisites
Steps 06–07.

## In Scope
HTTPS client boundary, enrollment request, explicit connect/read timeouts, bounded retry policy for safe failures, response validation, secure storage handoff, and re-enrollment-required state.

## Out of Scope
Heartbeat, collector orchestration, inbound management, local database, automatic bootstrap generation, and UI.

## Expected Files / Directories
`agent/src/device_watch_agent/transport/` or equivalent, config extension, agent tests.

## Concrete Tasks
1. Add only the configured server URL/bootstrap input needed for enrollment.
2. Validate `201` response and store identity/credential atomically.
3. Define timeout/retry behavior for connection failures versus `4xx`/protocol failures.
4. Ensure uncertain post-commit timeout does not blindly replay enrollment.

## Tests and Verification
Fake-server tests, timeout/retry traces, malformed response tests, storage integration, and no-secret log assertions.

## Security Considerations
HTTPS-only policy, no URL secrets, no authorization logging, bounded retries, and no secret echo.

## Definition of Done
An unenrolled agent can enroll once, persist the result safely, and restart without repeating enrollment.

## Handoff Information
Record HTTP client dependency, timeout values, retry limits, enrollment state machine, and shutdown behavior.

## Suggested Commit Message
`feat(stage2): add outbound enrollment client`
