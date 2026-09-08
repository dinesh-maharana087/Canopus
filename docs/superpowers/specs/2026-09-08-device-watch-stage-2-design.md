# Device Watch Stage 2 Design

Date: 2026-09-08
Status: Proposed for review

## Purpose

Stage 2 adds device enrollment, stable device identity, authenticated minimal heartbeats, and current connectivity state to the completed Stage 1 foundation. It does not implement monitoring metrics, historical observations, health scoring, alerts, remote actions, or interactive user authentication.

## Stage 1 Contracts Preserved

- `agent/`, `server/`, and `web/` remain independent projects.
- MySQL 8.x remains the only database target and all schema changes use Alembic from revision `20260831_0001`.
- Caddy remains the only public ingress. Agents initiate outbound HTTPS; the server never requires inbound device access.
- Existing health routes, logging redaction, production TLS validation, app factory, and deployment topology remain stable.
- Stage 1's empty collector registry remains empty in Stage 2. Heartbeat transport is not a metrics collector.
- No plaintext credential, authorization header, bootstrap secret, database URL, or issued secret is logged or returned.

## Scope

Stage 2 implements:

1. Operator-provisioned one-time enrollment bootstrap material.
2. Server-owned stable device identities.
3. Revocable device credentials represented server-side only by secure hashes.
4. Protected agent identity/credential file storage.
5. Outbound enrollment and authenticated heartbeat clients.
6. Server receipt-time last-seen state and deterministic online/offline/never-seen status.
7. Minimal device list/detail API and a Devices UI showing identity and connectivity only.

Stage 2 does not implement CPU, GPU, RAM, disk, temperature, driver, network-interface, SMART, Docker/container, or other metrics; historical metrics; charts; scoring; alerts; remote commands; SSH; reboot controls; or arbitrary command execution.

## Device Identity

The server owns identity. A device identifier is a canonical UUIDv4 generated with a cryptographically secure random source and stored as a UUID primary key. It is never derived from hostname, IP address, MAC address, or another mutable machine property.

A device has:

- immutable `id` / public device identifier;
- operator-controlled `display_name`, required and length-bounded;
- `created_at`, assigned by the server in UTC;
- lifecycle status `active` or `revoked`;
- optional `agent_version` from the latest accepted heartbeat.

The identifier is unique by primary-key constraint. Display names are not identity keys and need not be globally unique in Stage 2. Server timestamps are authoritative.

## Enrollment Bootstrap Secret

An operator creates a bootstrap record through an out-of-band provisioning command or protected operator input; Stage 2 does not create a general user/RBAC system or a public bootstrap-management route. The command generates a cryptographically random 32-byte secret and displays the plaintext once to the operator without logging it.

The server stores only a versioned HMAC-SHA-256 digest derived from a server-held bootstrap pepper, plus a unique lookup fingerprint, creation time, expiration time, consumed time, revoked time, and optional operator label. The plaintext is never persisted. Bootstrap records are single-use and must be unexpired, unrevoked, and unconsumed.

Consumption and device creation occur in one database transaction. A row lock or equivalent atomic update prevents concurrent requests from consuming one bootstrap twice. Invalid, expired, revoked, and consumed values return the same generic enrollment failure. Failed attempts do not reveal which state caused rejection. Bootstrap secrets are never placed in URLs or logs.

The operator obtains bootstrap material through a protected terminal or secret-management workflow outside the application. The provisioning command must avoid shell history guidance where practical and must never print the value after initial display.

The bootstrap HMAC pepper is an operator-managed server secret supplied through protected deployment configuration. It is required for provisioning and verification, is never returned or logged, and changing it invalidates outstanding bootstrap records by explicit operational decision.

## Device Credential

The issued device credential is an opaque, URL-safe random value containing a public key identifier and secret component, for example `dwc_<key-id>_<secret>`. The exact wire format is an implementation contract covered by tests, not a human identifier.

The server stores:

- a random public credential identifier for indexed lookup;
- a memory-hard or approved slow password-hash representation of the secret component using Argon2id through a reviewed dependency, or a separately approved equivalent;
- device foreign key;
- created, last-used, revoked, and optional replaced timestamps.

The complete credential is returned exactly once in the successful enrollment response and is never returned again. Verification looks up the public identifier, checks revocation, and verifies the secret with constant-time/password-hash verification. Credential hashes and raw credentials never appear in API responses or logs.

Revocation is a server-side state transition. Rotation is defined as issuing a new credential and revoking the old credential atomically; a rotation API is deferred unless required by implementation evidence. A rejected credential causes the agent to stop authenticated sends and enter an explicit re-enrollment-required state rather than retrying forever.

Transport uses `Authorization: Bearer <device-credential>` over HTTPS only. Authorization headers are excluded from request logging.

## Agent Credential Storage

The agent stores its identity and issued credential in one operator-configured file, defaulting to a platform-appropriate path supplied by configuration. The file contains a versioned object with `device_id`, `credential`, and `created_at`; it contains no database and no metric data.

On Linux, the parent directory is created with restrictive permissions and the file is owned by the dedicated agent user with mode `0600`. Writes use a same-directory temporary file, flush/sync where practical, permission application, and atomic rename. The previous valid file is retained until the replacement succeeds.

Missing storage means unenrolled and permits enrollment. Malformed, version-unsupported, or permission-unsafe storage fails closed with a sanitized operator error and does not send heartbeats. A `401`/revocation response deletes or quarantines the credential atomically and transitions the runtime to re-enrollment required; it does not silently enroll with an unknown bootstrap value.

## Enrollment Protocol

Endpoint: `POST /api/v1/enrollment`.

Request:

```json
{
  "protocol_version": 1,
  "bootstrap_secret": "one-time plaintext supplied by the operator",
  "display_name": "operator label",
  "agent_version": "0.2.0"
}
```

Response `201`:

```json
{
  "protocol_version": 1,
  "device_id": "uuid",
  "display_name": "operator label",
  "credential": "issued exactly once",
  "created_at": "server UTC timestamp"
}
```

The request has no idempotency replay that returns a credential. A successful transaction consumes the bootstrap and creates one device and credential. A client timeout after server commit cannot safely repeat enrollment with the same bootstrap; the operator must use an explicit recovery/rotation procedure rather than receiving the credential again. Invalid input, unsupported protocol version, and invalid bootstrap material return sanitized generic errors with no secret echo.

## Heartbeat Protocol

Endpoint: `POST /api/v1/devices/{device_id}/heartbeat`.

Authentication: HTTPS plus `Authorization: Bearer <device-credential>`.

Minimal request:

```json
{
  "protocol_version": 1,
  "submission_id": "uuid",
  "agent_version": "0.2.0",
  "observed_at": "optional device UTC timestamp"
}
```

The server response contains the accepted protocol version, device identifier, and authoritative `received_at` timestamp. The device observation timestamp is diagnostic only and never drives connectivity evaluation. No metrics, inventory, hostname, IP, MAC, heartbeat history, or collector payload is included.

`submission_id` is a client-generated UUID used for safe retry semantics. The server may keep a bounded deduplication record or use a current-state uniqueness mechanism so replaying the same submission does not create duplicate effects. A repeated authenticated submission is acknowledged idempotently and does not move `last_seen_at` backward. Credential/device mismatch, invalid credential, revoked device, unsupported protocol, and malformed body fail without leaking sensitive detail.

## Current Connectivity State

Stage 2 stores only current state on the device record or a one-to-one connectivity-state record:

- `last_seen_at`: server receipt timestamp, nullable;
- `last_heartbeat_submission_id`: latest accepted submission identity, nullable;
- `last_agent_version`, nullable;
- `status`: derived as `never_seen`, `online`, or `offline`.

The status is derived, not independently trusted. Let heartbeat interval be $I$ and offline grace multiplier be $3$; the default offline threshold is $T = 3I$, with a minimum operational floor of 90 seconds. The implementation must make the configured $I$ and resulting threshold explicit and test them at boundaries. At time $R$, a device is online when `last_seen_at` is non-null and $R - last_seen_at <= T`; it is offline when last seen exists and the difference is greater than $T`; it is never-seen when last seen is null. Equality at the threshold is online.

No background scheduler is required for current-state derivation in Stage 2. List/detail reads evaluate status against server current time, while persisted last-seen remains authoritative input.

## Retry and Shutdown

The agent uses explicit connect and read timeouts for enrollment and heartbeat requests. Retries are bounded per operation, use exponential backoff with capped delay and jitter, and apply only to connection failures, timeouts, and selected `5xx` responses. `4xx`, authentication failures, malformed responses, and protocol failures are not blindly retried. Shutdown cancels pending waits/backoff and closes the HTTP client cleanly.

Enrollment failures do not create duplicate identities: the server's single-use transaction is authoritative, and the client does not automatically regenerate or reuse unknown bootstrap material. Heartbeat retries reuse the same `submission_id` for the bounded retry window.

## Device API

Stage 2 uses a deployment-provided read-only operator service token for the device read API. This is a machine/service boundary, not interactive-user authentication or a general user/RBAC system. The token is supplied through protected deployment configuration, compared using a secure verifier, excluded from logs, and never stored with device records. Minimum endpoints:

- `GET /api/v1/devices`: paginated enrolled-device list with id, display name, created time, lifecycle status, last seen, agent version, and derived connectivity state;
- `GET /api/v1/devices/{device_id}`: the same fields for one device.

Responses never contain bootstrap secrets, credentials, credential hashes, authorization data, or internal database fields. Stage 2 does not introduce interactive user/RBAC authentication unless implementation review proves a boundary requires it.

## Testing and Security

Every migration is verified against real MySQL where available. Unit tests cover identity validation, bootstrap lifecycle, hash verification, revocation, secure file writes, protocol models, status boundaries, redaction, and retry decisions. API tests cover enrollment success/failure, authenticated heartbeat, invalid/revoked credentials, idempotent retry, and device list/detail sanitization. Agent tests cover first enrollment, restart, malformed storage, timeout/backoff, server rejection, and shutdown. Web tests cover only device identity/connectivity states and empty/loading/error behavior.

Stage 2 acceptance is defined in `docs/acceptance/stage-02-device-connectivity.md`. Any later metrics or monitoring feature requires a new scope and must not be hidden in heartbeat payloads or current-state tables.
