# Step 06: Server Logging and Database-Check CLI

## Objective

Add secret-safe structured request logging and a nonzero-on-failure database connectivity command.

## Why This Step Exists

Operators need sanitized observability and an explicit readiness check without leaking credentials or dependency exceptions.

## Prerequisites

Step 05.

## In Scope

JSON logging setup, request middleware, readiness failure event, `check_database`, `device-watch-db-check`, and focused tests.

## Out of Scope

Agent logging, Caddy logs, rate limiting, migrations, deployment, and business telemetry.

## Expected Files/Directories

`server/src/device_watch_server/core/logging.py`, `core/middleware.py`, `db/health.py`, `cli.py`, and unit logging/CLI tests.

## Implementation Tasks

1. Test one-line JSON fields, generic CLI output, and redaction of URLs, credentials, headers, cookies, bodies, and exception details.
2. Implement fixed readiness warning events without exception text.
3. Add middleware fields for event, method, normalized path, status, and duration.
4. Make CLI dispose the engine and return 0/ nonzero correctly.

## Tests and Verification

Run server unit tests, Ruff, and mypy with synthetic credential-bearing failures. Inspect captured logs and stderr for absence of secret values.

## Definition of Done

- Logs contain only approved operational fields.
- CLI success/failure exit behavior is tested.
- No request body, authorization, cookie, URL, or exception detail is emitted.

## Handoff Information

Record command name, log schema, sanitized failure behavior, and commit ID.

## Suggested Commit Checkpoint

`feat(server): add sanitized logging and database check`
