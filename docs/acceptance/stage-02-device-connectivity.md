# Stage 2 Acceptance: Device Connectivity

Status: Proposed contract; implementation not started.

Stage 2 is accepted only when every criterion below has fresh evidence. No criterion permits metrics, history, alerts, remote actions, or interactive-user authentication.

| ID | Expected behavior | Verification |
| --- | --- | --- |
| A01 | A clean agent has no identity/credential file and is explicitly unenrolled. | Agent storage unit test and clean temp-directory integration test. |
| A02 | An operator-provisioned bootstrap secret is random, expires, is single-use, and is never stored or logged in plaintext. | Bootstrap lifecycle tests, database integration, redaction capture, provisioning command review. |
| A03 | Successful enrollment creates one server-owned UUID identity and returns the credential exactly once. | API contract and transaction integration tests. |
| A04 | Server persistence contains only a credential identifier and secure hash; responses never contain hashes or raw credentials. | Schema inspection, persistence test, response assertions, repository audit. |
| A05 | Enrollment replay, expiry, revocation, malformed input, and concurrent consumption fail safely without duplicate devices. | API, transaction, race/locking, and sanitized-error tests. |
| A06 | Agent writes identity/credential atomically with protected ownership and permissions, and malformed files fail closed. | File-permission, interrupted-write, malformed-file, restart tests. |
| A07 | Agent enrollment uses outbound HTTPS with explicit timeouts and bounded retries; it never requires inbound device access. | HTTP client tests with fake server and retry traces. |
| A08 | Authenticated heartbeat accepts only valid, active device credentials and minimal versioned payloads. | API contract tests for success, malformed, unsupported, invalid, and revoked cases. |
| A09 | Heartbeat processing uses server receipt time and does not store Stage 3 metrics or history. | Persistence integration test, clock injection, schema audit, payload assertions. |
| A10 | Repeated submission IDs are safe and do not move last-seen backward or create duplicate effects. | Retry/idempotency API and database tests. |
| A11 | Agent heartbeat retries are bounded, use timeout/backoff/jitter, stop retrying authentication failures, and cancel cleanly. | Retry unit tests and shutdown test. |
| A12 | Online/offline/never-seen state is deterministic at threshold boundaries and uses server time. | Pure evaluator tests at null, exact threshold, and threshold-plus-one. |
| A13 | Device list/detail APIs require the read-only operator service token and expose only identity and current connectivity fields, with no credential material. | API authorization, response, and redaction tests. |
| A14 | Devices UI shows enrolled identity, state, last seen, loading, empty, and error states only. | Frontend component tests and static source audit for metrics/charts/fake data. |
| A15 | Existing Stage 1 health, TLS, logging, deployment, and empty-collector contracts remain green. | Full Stage 1 regression matrix. |
| A16 | Real MySQL migrations, enrollment, credential revocation, heartbeat last-seen updates, and acceptance flow pass on a Docker/MySQL-capable host. | Integration command matrix and captured evidence. |

## Required Negative Evidence

The audit must reject plaintext credential columns or files, secret/log/header exposure, local agent databases, inbound-agent management assumptions, Stage 3 metric collectors/tables/UI, historical metric retention, alert behavior, remote commands, SSH polling, arbitrary command execution, and fake monitoring data.

## Stage Boundary

When A01–A16 are complete, Stage 2 is complete. Monitoring metrics, historical data, charts, scoring, alerts, and remote actions remain later-stage work.
