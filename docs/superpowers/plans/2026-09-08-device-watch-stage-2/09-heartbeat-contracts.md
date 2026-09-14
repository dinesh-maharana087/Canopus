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

## Implementation Handoff — 2026-09-14

Status: **Complete at the contract boundary**. Resumed the existing Step 09
implementation at `43f5f54`; source and tests were preserved. Fresh focused
verification and the protocol handoff complete this step.

`domain/contracts.py` owns `HeartbeatRequest`, `HeartbeatResponse`,
`HeartbeatAccepted`, and the current-state `PersistenceBoundary`.
`domain/heartbeat.py` owns sanitized JSON parsers, `HeartbeatFailure`, and the
pure `decide_heartbeat()` function. These modules perform no I/O, authentication,
logging, persistence, or retries. An agent implementation can use the wire rules
below without importing server dependencies; no agent module is needed yet.

### JSON schemas

The executable schemas are available through `model_json_schema()` on
`HeartbeatRequest`, `HeartbeatResponse`, and `HeartbeatFailure`. Their structural
constraints are recorded below, omitting titles/descriptions and inlining the
response status enum. The additional validation rules below are also normative;
JSON Schema alone does not describe normalization or lexical number types.

Request:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["protocol_version", "submission_id", "agent_version"],
  "properties": {
    "protocol_version": {"type": "integer", "const": 1},
    "submission_id": {
      "type": "string",
      "format": "uuid",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    },
    "agent_version": {"type": "string", "minLength": 1, "maxLength": 64},
    "observed_at": {
      "anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}],
      "default": null,
      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
    }
  }
}
```

Success response:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["protocol_version", "device_id", "received_at", "status"],
  "properties": {
    "protocol_version": {"type": "integer", "const": 1},
    "device_id": {
      "type": "string",
      "format": "uuid4",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "received_at": {
      "type": "string",
      "format": "date-time",
      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
    },
    "status": {"type": "string", "enum": ["accepted", "duplicate"]}
  }
}
```

Failure model:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "detail": {
      "type": "string",
      "const": "Heartbeat failed",
      "default": "Heartbeat failed"
    }
  }
}
```

Serializing `HeartbeatFailure()` emits exactly `{"detail":"Heartbeat failed"}`.
The default permits constructing the model without an explicit `detail` value.
The public parsers and decision boundary raise only `HeartbeatError("Heartbeat
failed")` for invalid input, without exposing validation diagnostics. Later API
code must use these sanitized boundaries and the failure model, and must not log
headers, bodies, credentials, or raw validation exceptions. HTTP status handling
and authentication enforcement belong to the later API step.

### Version and compatibility rules

- Both envelopes require the JSON integer token `1`: missing versions, booleans,
  strings, floating-point numbers (including `1.0`), and other versions fail.
  There is no negotiation, coercion, fallback, or acceptance of unknown fields.
- UUIDs use lowercase canonical hyphenated strings. Submission UUID versions
  are unrestricted; response device identity must be UUIDv4. Identity and
  credentials do not appear in the request body. The approved transport uses
  path identity and an HTTPS bearer credential; implementing it is later work.
- `agent_version` is a string of 1–64 characters before trimming, is normalized
  with Python `str.strip()`, and must remain nonblank. No semantic-version
  grammar is imposed. Numbers and null are rejected.
- `observed_at` may be absent or null. Non-null timestamps must be real calendar
  datetimes with the exact pattern above, seconds, an explicit offset or `Z`,
  and at most six fractional digits. UTC conversion must remain representable.
  Naive timestamps, numeric epochs, invalid dates, and overflows fail. Accepted
  values normalize to UTC and serialize with `Z`; observation is diagnostic
  only and is not retained in current state.
- Success responses always contain all four fields. `HeartbeatAccepted` is a
  convenience model that defaults to and only permits `accepted`.
- Metrics, inventory, hostname/IP/MAC, history, credentials, and all other extra
  fields are rejected. Future envelope additions require an explicitly supported
  protocol change. Step 09 does not add metric or collector payloads.

### Idempotency and monotonic time

The chosen retention is **one latest submission ID per authenticated device**,
retained until a different ID replaces it, with no TTL or historical deduplication
table. A UUID is not a global key across devices.

| Submission | Response | Current-state effect |
| --- | --- | --- |
| First or different ID | `accepted` | Set latest ID/version and `last_seen_at = max(previous last_seen_at, received_at)`, or receipt time if previously unseen |
| Same latest ID, including a different but valid body | `duplicate` | Preserve every current-state field; `apply_update=False` |
| Older ID after another ID replaced it | `accepted` | Apply the different-ID rule; older IDs are outside the retention slot |

Every acknowledgement reports **this attempt's server receipt time**; it is not
a cached response, and it can differ from stored monotonic `last_seen_at` when
the server clock moves backward. Device observation time never drives either
value. Duplicate acknowledgement does not refresh last-seen or agent version.
Malformed retries still fail validation.

The later service must authenticate credential/device ownership before using
this decision, supply that device's current state, and apply the read/decision/
update atomically. The later sender must reuse its submission ID on retries and
finish that bounded operation before starting a new submission if it needs the
one-slot duplicate guarantee. No retention across superseded IDs is promised.
These are caller obligations, not runtime functionality implemented in Step 09.

### Focused verification

The fresh run of `server/tests/unit/test_heartbeat_contracts.py` and
`server/tests/unit/test_stage2_domain_contracts.py` passed **83 tests**, with no
failures or skips. Coverage includes serialization, schema fields, strict
versions, UUID/timestamp validation, forbidden fields, sanitized errors,
duplicate-ID retention, device scoping, and monotonic last-seen behavior.
See the [progress record](../../../progress/current-status.md) for the exact
command and environment note. No static command is mandated by this card.
