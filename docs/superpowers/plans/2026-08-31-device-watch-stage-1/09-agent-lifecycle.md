# Step 09: Agent Configuration and Lifecycle

## Objective

Implement strict agent configuration and a signal-aware empty-registry runtime that waits efficiently and shuts down cleanly.

## Why This Step Exists

The native process must be independently runnable without communication or collection in Stage 1.

## Prerequisites

Step 08.

## In Scope

Agent env parsing, structured standard-library logging, async runtime, signal handling, module entry point, and lifecycle tests.

## Out of Scope

Server URL, enrollment, credentials, sender, retries, database, Docker, real collectors, and collector orchestration.

## Expected Files/Directories

`agent/.env.example`, `config.py`, `logging.py`, `lifecycle.py`, `main.py`, `__main__.py`, and config/lifecycle tests.

## Implementation Tasks

1. Test required `DEVICE_WATCH_AGENT_MODE=service`, default/positive interval, unknown prefixed variables, efficient wait, cancellation, signals, and no collector invocation.
2. Implement `AgentRuntime.run` with `asyncio.wait_for` and clean cancellation.
3. Build an empty registry in `main`, install SIGINT/SIGTERM where supported, and return 0 after cleanup.

## Tests and Verification

Run all agent tests, Ruff, mypy, and a short boot/stop check. Verify no outbound I/O and no registered test collector call.

## Definition of Done

- Missing/invalid configuration fails clearly.
- Default interval is 30 seconds.
- Requested stop and normal termination exit successfully.
- Stage 1 performs no collection or communication.

## Handoff Information

Record env contract, shutdown evidence, platform limitations, and commit ID.

## Suggested Commit Checkpoint

`feat(agent): add empty native lifecycle`
