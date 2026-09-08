# Step 10: React Application Shell and Theme

## Objective

Create the responsive React/TypeScript navigation shell with five empty Stage 1 route boundaries and persistent system/light/dark theme state.

## Why This Step Exists

Navigation is a Stage 1 deliverable, but no monitoring UI or fabricated health data may exist.

## Prerequisites

Step 01.

## In Scope

Vite/TypeScript configuration, CSS-variable tokens, router, layout/navigation, local UI primitive, theme provider, five pages, and frontend tests.

## Out of Scope

API clients, query libraries, charts, device data, counts/statuses, backend routes, Caddy, and TLS.

## Expected Files/Directories

`web/index.html`, Vite/ESLint/TS configs, `web/src/app/`, `components/`, `pages/`, `theme/`, styles, test setup, and shell/theme tests.

## Implementation Tasks

1. Test accessible navigation, exact headings/message, active route state, theme persistence/system mode, and absence of fabricated data.
2. Implement the literal Dashboard, Devices, Alerts, Inventory, and Settings route table.
3. Add responsive shell, focus states, reduced-motion handling, and theme CSS variables.
4. Configure only the Vite development `/api` proxy with no rewrite; build static output.

## Tests and Verification

Run Vitest, strict typecheck, lint, and production build. Confirm tests perform no business API calls.

## Definition of Done

- All five routes render only their title and `Not implemented in Stage 1`.
- Navigation is accessible and responsive.
- Theme modes persist under the specified local key.
- Web quality gates pass and `dist` is build output only.

## Handoff Information

Record route paths, theme behavior, build result, and commit ID for Step 12.

## Suggested Commit Checkpoint

`feat(web): add accessible Stage 1 application shell`
