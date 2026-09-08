# Step 03: SQLAlchemy Engine and Verified MySQL TLS Boundary

## Objective

Centralize SQLAlchemy engine creation and prove the effective PyMySQL production arguments enforce certificate and hostname verification.

## Why This Step Exists

The approved design requires one database URL, pre-ping/recycling, and boolean TLS verification without trusting URL translation alone.

## Prerequisites

Step 02.

## In Scope

Engine URL cleanup, validated production `connect_args`, SQLAlchemy/PyMySQL characterization test, engine options, and no-network interception tests.

## Out of Scope

Health endpoints, sessions/repositories, Alembic, Compose, migrations, and business tables.

## Expected Files/Directories

`server/src/device_watch_server/db/__init__.py`, `server/src/device_watch_server/db/engine.py`, `server/tests/unit/test_engine_tls.py`, and related test fixtures.

## Implementation Tasks

1. Lock and test SQLAlchemy 2.0.52/PyMySQL 1.2.0 URL translation.
2. Remove validated TLS query keys before URL translation can create competing nested options.
3. Pass exact flat `ssl_ca`, `ssl_verify_cert=True`, and `ssl_verify_identity=True` in production.
4. Configure pre-ping and 1,800-second recycle; intercept `do_connect` before network I/O.

## Tests and Verification

Run the characterization and effective-argument tests, then server Ruff and mypy. Dispose test engines and verify no connection is attempted.

## Definition of Done

- Development/test may omit TLS only in the isolated topology.
- Production effective arguments contain exactly the verified TLS keys with boolean flags.
- Engine options and single-URL ownership are tested.

## Handoff Information

Record package versions, characterization result, captured effective arguments, and commit ID for Steps 05 and 07.

## Suggested Commit Checkpoint

`feat(server): add verified MySQL engine boundary`
