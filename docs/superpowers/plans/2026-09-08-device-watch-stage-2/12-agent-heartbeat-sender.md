# Step 12: Agent Heartbeat Sender and Retry Policy

## Objective
Send minimal authenticated heartbeats from an enrolled agent with bounded timeout/backoff behavior.

## Requirement / Rationale
Agents initiate communication; transient failures must not become infinite loops or duplicate submissions.

## Prerequisites
Steps 07, 09, and 11.

## In Scope
Periodic sender integration with lifecycle, stable submission ID across retry window, connect/read timeouts, capped exponential backoff/jitter, response handling, auth rejection transition, and cancellation.

## Out of Scope
Metrics collectors, inbound server control, heartbeat history, alerting, and arbitrary retry queues.

## Expected Files / Directories
`agent/src/device_watch_agent/transport/`, lifecycle integration, agent tests.

## Concrete Tasks
1. Load protected identity or remain unenrolled.
2. Send only the minimal heartbeat envelope.
3. Retry connection/timeout/selected 5xx failures within fixed limits.
4. Stop on auth/protocol rejection and require re-enrollment.
5. Cancel HTTP work and backoff on shutdown.

## Tests and Verification
Fake-server tests for success, timeout, 5xx, 4xx, revoked credential, backoff bounds/jitter, duplicate submission ID, and shutdown.

## Security Considerations
HTTPS only, no authorization/body logs, no infinite retries, and no credential persistence changes on transient failures.

## Definition of Done
An enrolled agent sends bounded authenticated heartbeats and cleanly stops without collecting metrics.

## Handoff Information
Record timeout/retry constants, retry classification, sender lifecycle, and revocation behavior.

## Suggested Commit Message
`feat(stage2): add bounded heartbeat sender`
