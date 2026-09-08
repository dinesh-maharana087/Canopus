# Step 17: Full Acceptance Verification and Evidence Capture

## Objective

Run the complete Stage 1 verification matrix and record fresh evidence without expanding implementation scope.

## Why This Step Exists

The approved design has cross-component acceptance criteria that individual checkpoints cannot prove alone.

## Prerequisites

Steps 01 through 16.

## In Scope

All independent unit/lint/type/build checks, real MySQL/migrations, Compose rendering, image/Caddy validation, smoke profile, audits, status/diff review, and evidence handoff.

## Out of Scope

Unrequested redesign, speculative fixes, Stage 2 implementation, empty commits, and representing blocked environment checks as passing.

## Expected Files/Directories

No planned source changes. Modify an earlier owned file only when a reproduced failure has a focused regression test; update progress status/evidence.

## Implementation Tasks

1. Run agent, server, deployment, and web quality gates.
2. Run real MySQL connectivity and head/base/head migration cycle.
3. Render both Compose files, verify topology, build images, validate Caddy, and run server-smoke.
4. Test missing production variables fail closed.
5. Run dependency/repository audits and inspect final tree/status/diff against all acceptance criteria.
6. Record blocked commands and environmental causes precisely.

## Tests and Verification

Use the full command matrix in the original implementation plan and approved spec. Every result must be fresh and labeled pass, fail, or blocked.

## Definition of Done

- All sixteen acceptance criteria are backed by code or command evidence.
- No unverified Docker/MySQL/Caddy result is reported as successful.
- Progress status contains final evidence, residual risks, and the next stage boundary.

## Handoff Information

Record final tree, commands/results, TLS characterization, migration cycle, topology/image evidence, audit result, unresolved operator risks, and commit ID if a correction was necessary.

## Suggested Commit Checkpoint

`fix: satisfy Stage 1 acceptance verification`
