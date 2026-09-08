# Step 14: Device Query API

## Objective
Expose enrolled-device identity and current connectivity through minimal list/detail APIs.

## Requirement / Rationale
Operators need basic connectivity visibility without credentials, metrics, or interactive auth expansion.

## Prerequisites
Steps 02, 10, and 13.

## In Scope
`GET /api/v1/devices`, `GET /api/v1/devices/{device_id}`, read-only operator service-token authentication, pagination bounds, identity/status fields, last seen, agent version, and sanitized not-found behavior.

## Out of Scope
Enrollment management UI, credential management, metrics, charts, alerts, user/RBAC system, and write routes.

## Expected Files / Directories
`server/src/device_watch_server/api/`, query service/repository, API tests.

## Concrete Tasks
1. Define response models with an explicit allowlist.
2. Add bounded pagination and deterministic ordering.
3. Evaluate status at request time using injected server clock.
4. Require the protected operator service token without introducing interactive user/RBAC flows.
5. Preserve existing health routes and deployment path.

## Tests and Verification
API list/detail tests, empty state, pagination, not-found, no-secret assertions, route allowlist, Ruff, and mypy.

## Security Considerations
Never expose device credentials, hashes, bootstrap material, operator token, authorization data, or internal database fields. Keep the operator token out of logs and device persistence.

## Definition of Done
Operators can read enrolled-device identity and current connectivity safely.

## Handoff Information
Record endpoints, fields, pagination, access-boundary assumption, and response redaction evidence.

## Suggested Commit Message
`feat(stage2): add device connectivity query API`
