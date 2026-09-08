# Step 13: Online/Offline Evaluator

## Objective
Derive deterministic current connectivity status from server receipt time.

## Requirement / Rationale
Operators need online/offline visibility without storing metric history or trusting device clocks.

## Prerequisites
Steps 10–11.

## In Scope
Pure evaluator, configurable interval/threshold policy, never-seen/online/offline states, exact-boundary behavior, clock injection, and status DTO.

## Out of Scope
Background scheduler, alerts, health scores, historical observations, metrics, and UI.

## Expected Files / Directories
`server/src/device_watch_server/connectivity/`, unit tests, configuration extension only if necessary.

## Concrete Tasks
1. Implement `never_seen` for null last-seen.
2. Define default interval and threshold floor/multiplier.
3. Make equality at threshold deterministic and test it.
4. Ensure list/detail reads use server current time.

## Tests and Verification
Pure boundary tests for null, exact threshold, threshold plus one, future timestamps, and configured interval changes.

## Security Considerations
Use server time only; do not accept client status or expose internal policy secrets.

## Definition of Done
Connectivity state is deterministic, explainable, and independent of metrics or a background polling process.

## Handoff Information
Record formula, defaults, configuration source, boundary semantics, and clock test strategy.

## Suggested Commit Message
`feat(stage2): add deterministic connectivity evaluator`
