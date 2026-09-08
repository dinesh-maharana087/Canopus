# Step 15: Repository Security and Stage 1 Scope Audit

## Objective

Add a repeatable repository audit that detects secrets, unsafe dependency/database scope, and executable Stage 2 behavior.

## Why This Step Exists

Stage 1 must prove absence of future workflows as well as presence of its foundation.

## Prerequisites

Steps 06, 07, 09, 10, 13, and 14.

## In Scope

Standard-library audit, positive MySQL allowlist, source-boundary checks, secret/example checks, dependency inspection hooks, and tests.

## Out of Scope

Fixing unrelated source defects, implementing future routes/tables/collectors/senders, CI provider setup, and deployment changes.

## Expected Files/Directories

`deploy/verify_repository.py`, `deploy/tests/test_verify_repository.py`.

## Implementation Tasks

1. Create positive/negative temporary repository fixtures.
2. Audit names/text for private keys, live env files, credentials, unknown databases, business routes, domain tables, concrete collectors, senders, API calls, and monitoring fixtures.
3. Exclude generated/VCS/recovery material and emit sanitized relative findings.
4. Run the audit against the real repository and inspect dependency trees.

## Tests and Verification

Run audit tests, `python deploy/verify_repository.py`, uv dependency trees, npm dependency listing, and `git diff --check`.

## Definition of Done

- Positive Stage 1 repository passes with zero findings.
- Forbidden executable future behavior is rejected by tests.
- Findings do not echo secret content.

## Handoff Information

Record audit result, dependency review, findings resolved, and commit ID for docs and final verification.

## Suggested Commit Checkpoint

`test: enforce security and Stage 1 repository boundaries`
