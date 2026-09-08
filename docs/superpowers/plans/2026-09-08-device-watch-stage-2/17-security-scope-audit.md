# Step 17: Stage 2 Security and Scope Audit

## Objective
Audit the completed Stage 2 implementation for credential safety, outbound-only behavior, and absence of Stage 3 features.

## Requirement / Rationale
Stage 2 must prove absence of dangerous or prematurely broad functionality as well as presence of connectivity behavior.

## Prerequisites
Step 16.

## In Scope
Repository audit extension, secret/log/header scans, plaintext credential/schema checks, local database detection, inbound management checks, metric/history/alert/command exclusions, dependency review, and negative fixtures.

## Out of Scope
Refactoring unrelated Stage 1 code, adding CI provider configuration, or implementing missing business features.

## Expected Files / Directories
`deploy/verify_repository.py`, Stage 2 audit tests, security documentation updates only if evidence requires them.

## Concrete Tasks
1. Add positive/negative fixtures for plaintext secrets, metrics, history, alerts, commands, SSH, and inbound agent routes.
2. Inspect migrations and schemas for credential hashes without plaintext and no metric tables.
3. Inspect agent transport for HTTPS/timeouts/retry bounds and no inbound listener.
4. Inspect logs/API responses/UI for secret leakage.

## Tests and Verification
Audit tests, full source scan, dependency trees, migration schema inspection, and complete prior test suites.

## Security Considerations
Findings must be sanitized; credentials and authorization headers must never be printed during audit.

## Definition of Done
The Stage 2 repository passes positive security checks and rejects every listed out-of-scope behavior.

## Handoff Information
Record audit rules, findings, resolved issues, residual risks, and exact command output summary.

## Suggested Commit Message
`test(stage2): enforce connectivity security boundaries`
