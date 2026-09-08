# Step 16: Operational and Architecture Documentation

## Objective

Document verified local, production, architecture, trust-boundary, future-contract, and native systemd usage without creating executable Stage 2 behavior.

## Why This Step Exists

Operators and future coding sessions need precise handoff instructions that match the implementation and preserve stage boundaries.

## Prerequisites

Steps 09, 13, and 15.

## In Scope

README, architecture/development/deployment/future-contract docs, environment guidance, and systemd unit example.

## Out of Scope

New runtime features, credentials, migrations, deployment changes, and implementing any future contract.

## Expected Files/Directories

`README.md`, `.env.example`, `docs/architecture.md`, `docs/development.md`, `docs/deployment.md`, `docs/future-contracts.md`, `deploy/systemd/device-watch-agent.service`.

## Implementation Tasks

1. Document independent commands, Vite proxy, optional dev MySQL, and no implicit database fallback.
2. Document external MySQL, TLS/CA requirements, Linux host gateway, Caddy ports/volumes, and validation commands.
3. Document trust boundaries and future sequences as explicitly non-executable contracts.
4. Add a native systemd unit reading a protected env file with normal SIGTERM and `Restart=on-failure`.
5. Cross-check names/paths/ports against executable configuration and run the repository audit.

## Tests and Verification

Run documentation/configuration cross-check searches, repository audit, and `git diff --check`. Do not claim services are verified solely from prose.

## Definition of Done

- Documentation matches actual variables, paths, routes, ports, and commands.
- Future contracts contain no executable routes, tables, credentials, or fixtures.
- Systemd example runs only the native empty agent.

## Handoff Information

Record docs cross-check, discrepancies corrected, and commit ID for Step 17.

## Suggested Commit Checkpoint

`docs: document Stage 1 architecture and operations`
