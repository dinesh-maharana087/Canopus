# Step 01: Repository Bootstrap and Dependency Locks

## Objective

Create the independent agent, server, and web project foundations with repository safeguards and frozen dependency metadata.

## Why This Step Exists

Every later component assumes stable boundaries, exact versions, and deterministic tool commands from the approved design.

## Prerequisites

None. Read the approved spec and original plan first.

## In Scope

Create root ignore/editor/config files, README baseline, agent/server manifests and locks, and web package manifest and lock. Record tool availability.

## Out of Scope

No application modules, routes, collectors, database schema, Dockerfiles, Compose services, UI screens, or runtime behavior.

## Expected Files/Directories

`.editorconfig`, `.dockerignore`, `.gitignore`, `.env.example`, `README.md`, `agent/pyproject.toml`, `agent/uv.lock`, `server/pyproject.toml`, `server/uv.lock`, `web/package.json`, `web/package-lock.json`.

## Implementation Tasks

1. Check Python, Node, npm, uv, Docker, and Compose versions.
2. Add the repository safeguards and exact dependency versions from the original plan.
3. Generate both uv locks and the npm lock without adding unrelated packages.
4. Verify independent install/tree commands and agent runtime dependency separation.

## Tests and Verification

Run manifest parsing, `uv sync --frozen` for agent and server, `uv tree --no-dev`, and `npm ci --ignore-scripts`. Record unavailable tools as prerequisites.

## Definition of Done

- All expected manifests and locks exist.
- Agent, server, and web resolve independently.
- Generated/private files are ignored.
- No runtime implementation was added.

## Handoff Information

Record tool versions, exact commands/results, files created, lock-generation caveats, and the commit ID in `docs/progress/current-status.md`.

## Suggested Commit Checkpoint

`build: establish independent project foundations`
