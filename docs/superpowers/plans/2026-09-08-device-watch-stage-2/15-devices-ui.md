# Step 15: Devices Connectivity UI

## Objective
Replace the Stage 1 Devices empty boundary with a narrow connectivity-only view.

## Requirement / Rationale
Stage 2 needs operator visibility while preserving the prohibition on fabricated monitoring data.

## Prerequisites
Step 14.

## In Scope
Devices route API client, list/detail presentation, identity/display name, lifecycle, online/offline/never-seen state, last seen, agent version, empty/loading/error states, and tests.

## Out of Scope
Metrics, charts, scores, alerts, device commands, enrollment forms, credentials, and other route functionality.

## Expected Files / Directories
`web/src/pages/`, `web/src/app/`, API/query helpers, frontend tests.

## Concrete Tasks
1. Add the minimal typed client for device list/detail.
2. Render accessible state labels and timestamps without fake defaults.
3. Handle empty, loading, network error, and not-found states.
4. Audit the route for metrics/fixture leakage.

## Tests and Verification
Vitest/Testing Library tests for populated, empty, loading, error, and state variants; typecheck, lint, build, and no-unapproved-fetch audit.

## Security Considerations
Never render credentials, hashes, bootstrap values, arbitrary server errors, or unsafe HTML.

## Definition of Done
Devices shows only real API-backed connectivity information and honest empty/loading/error states.

## Handoff Information
Record API fields rendered, state copy, error behavior, and Stage 3 exclusions.

## Suggested Commit Message
`feat(stage2): add device connectivity view`
