# Step 06: Enrollment API Contract and Endpoint

## Objective
Expose the versioned enrollment endpoint over the existing FastAPI/Caddy path.

## Requirement / Rationale
Agents need one narrow outbound enrollment protocol while operators retain control of bootstrap provisioning.

## Prerequisites
Step 05.

## In Scope
`POST /api/v1/enrollment`, request/response validation, `201` success, generic failure statuses, protocol versioning, logging redaction, and API tests.

## Out of Scope
Heartbeat, operator/RBAC authentication, credential rotation endpoint, device listing, metrics, and UI.

## Expected Files / Directories
`server/src/device_watch_server/api/`, enrollment schemas/service wiring, unit/API tests.

## Concrete Tasks
1. Register the single enrollment route without weakening existing health behavior.
2. Validate display name, protocol version, agent version, and bootstrap input.
3. Map invalid, expired, consumed, revoked, and unsupported cases safely.
4. Add API contract tests proving no secret echo.

## Tests and Verification
FastAPI API tests, route allowlist regression, malformed body tests, redaction capture, Ruff, and mypy.

## Security Considerations
HTTPS is required by deployment; never log body/bootstrap/authorization; successful credential is returned once only.

## Definition of Done
A valid one-time enrollment request returns the specified identity and credential contract, and invalid requests are generic and safe.

## Handoff Information
Record route, schemas, status codes, error shape, and deployment assumptions.

## Suggested Commit Message
`feat(stage2): add device enrollment endpoint`
