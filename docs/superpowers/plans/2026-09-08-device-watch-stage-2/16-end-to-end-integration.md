# Step 16: End-to-End Enrollment and Heartbeat Integration

## Objective
Prove the complete Stage 2 flow across real MySQL, server API, agent storage/client, and device visibility.

## Requirement / Rationale
Unit contracts cannot prove transaction, authentication, persistence, and retry behavior together.

## Prerequisites
Steps 06, 08, 11, 12, 14, and 15.

## In Scope
Ephemeral integration environment, bootstrap provisioning, enrollment, restart persistence, authenticated heartbeat, duplicate retry, revocation, current-state API, and Devices UI contract fixtures.

## Out of Scope
Production rollout, Stage 3 metrics, historical data, alerts, remote actions, and infrastructure redesign.

## Expected Files / Directories
`server/tests/integration/`, `agent/tests/integration/` if needed, `web/src/**/*.test.tsx`, acceptance fixtures.

## Concrete Tasks
1. Run migrations from the Stage 1 baseline on real MySQL.
2. Enroll once and capture only test-local credential material safely.
3. Restart agent storage and send authenticated heartbeat.
4. Verify receipt-time state, duplicate safety, revocation rejection, and device API/UI output.
5. Assert no metric/history tables or payloads appear.

## Tests and Verification
Full cross-project integration command matrix, database schema inspection, API logs/redaction capture, and teardown.

## Security Considerations
Use disposable test secrets, never echo them, isolate test database, and verify revocation and credential absence in responses.

## Definition of Done
A clean environment demonstrates the full intended Stage 2 connectivity flow without Stage 3 behavior.

## Handoff Information
Record migration IDs, flow evidence, failure/retry cases, environment requirements, and residual blocks.

## Suggested Commit Message
`test(stage2): verify enrollment and heartbeat flow`
