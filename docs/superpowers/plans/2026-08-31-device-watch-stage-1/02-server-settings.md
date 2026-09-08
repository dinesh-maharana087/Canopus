# Step 02: Server Settings and Configuration Validation

## Objective

Implement strict server settings for environment selection, required MySQL URL validation, documentation mode, and secret-safe representations.

## Why This Step Exists

Unsafe or ambiguous configuration must fail before engine creation, especially in production.

## Prerequisites

Step 01.

## In Scope

`Settings`, required `DEVICE_WATCH_ENV`, `DATABASE_URL` with `mysql+pymysql`, production TLS query validation, optional docs flag, and focused configuration tests.

## Out of Scope

Engine construction, database connections, API routes, logging, migrations, Docker, and business models.

## Expected Files/Directories

`server/src/device_watch_server/__init__.py`, `server/src/device_watch_server/core/config.py`, `server/tests/conftest.py`, `server/tests/unit/test_config.py`.

## Implementation Tasks

1. Write red tests for missing fields, invalid modes/dialect, production TLS exactness, duplicate/additional query keys, docs restrictions, and credential redaction.
2. Implement immutable Pydantic settings with no fallback database URL.
3. Use parsed query pairs so duplicate production keys are rejected.
4. Run focused tests, Ruff, and mypy.

## Tests and Verification

`uv run --project server pytest server/tests/unit/test_config.py -q`; run server lint and type checks for touched files. Assert errors and repr never expose credentials.

## Definition of Done

- Only `development`, `test`, and `production` are accepted.
- Production requires the exact three verified TLS query entries.
- Invalid configuration fails before any engine exists.
- Focused tests, lint, and types pass.

## Handoff Information

Record settings API, accepted environment variables, security-test results, and commit ID. Step 03 may now own engine behavior.

## Suggested Commit Checkpoint

`feat(server): enforce strict configuration validation`
