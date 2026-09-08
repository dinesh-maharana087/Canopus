# Step 18: Stage 2 Acceptance Verification and Evidence

## Objective
Run the complete Stage 2 acceptance matrix and record evidence without expanding scope.

## Requirement / Rationale
The enrollment-to-connectivity contract requires cross-component proof and a clear handoff boundary.

## Prerequisites
Step 17 and all prior Stage 2 steps.

## In Scope
Unit/API/integration/agent/web tests, real MySQL migration and flow, retry/revocation evidence, audit, final tree/status/diff review, and acceptance document updates.

## Out of Scope
Speculative redesign, Stage 3 implementation, unrelated fixes, empty commits, and reporting blocked infrastructure as passing.

## Expected Files / Directories
`docs/acceptance/stage-02-device-connectivity.md`, `docs/progress/current-status.md`, Stage 2 master index only.

## Concrete Tasks
1. Run all project quality gates and the real MySQL flow where available.
2. Verify enrollment exactly-once behavior, secure storage, authenticated heartbeat, state boundaries, and device API/UI.
3. Run security/scope audit and inspect final dependency/tree/diff state.
4. Mark each acceptance criterion pass, fail, or blocked with command/test evidence.
5. Record Stage 3 boundary and unresolved operational risks.

## Tests and Verification
Use every criterion in `docs/acceptance/stage-02-device-connectivity.md`; preserve explicit Docker/MySQL blocks.

## Security Considerations
Do not echo bootstrap secrets, credentials, hashes, database URLs, or auth headers in evidence.

## Definition of Done
All acceptance criteria have evidence, no Stage 3 behavior exists, and Stage 2 is marked complete only when required infrastructure evidence is pass or explicitly blocked.

## Handoff Information
Record final revisions, protocol versions, timeout/retry policy, status formula, audit result, residual risks, and next-stage boundary.

## Suggested Commit Message
`test(stage2): capture device connectivity acceptance evidence`
