# Step 08: Agent Collector Contracts and Registry

## Objective

Define testable, standard-library collector result types and an empty registry without implementing a real collector.

## Why This Step Exists

Future collection can evolve behind stable contracts while Stage 1 explicitly performs no monitoring.

## Prerequisites

Step 01.

## In Scope

Collector status/result types, runtime-checkable protocol, unique-name registry, and unit tests using test-local doubles.

## Out of Scope

Configuration, lifecycle loop, signals, system metrics, GPU/service/disk/network/SMART/container collectors, HTTP, credentials, database, and shell commands.

## Expected Files/Directories

`agent/src/device_watch_agent/collectors/`, package init files, and `agent/tests/test_contracts.py`, `test_registry.py`.

## Implementation Tasks

1. Test success/unavailable/failure results, empty registry, order-preserving snapshots, duplicate/blank names, and protocol compatibility.
2. Implement frozen typed results with read-only scalar mappings.
3. Implement registry registration and tuple snapshots using standard library only.

## Tests and Verification

Run focused agent tests, Ruff, mypy, and `uv tree --no-dev`; confirm no production concrete collector is present.

## Definition of Done

- Contracts carry no device/metric/heartbeat fields.
- Empty registry is valid and snapshots are immutable.
- Duplicate and blank names fail clearly.
- Runtime dependency remains standard library only.

## Handoff Information

Record public contract names, registry semantics, tests, and commit ID for Step 09.

## Suggested Commit Checkpoint

`feat(agent): add collector contracts and registry`
