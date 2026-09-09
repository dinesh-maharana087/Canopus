# Device Health Portal - Codex Instructions

## Project workflow

This project is implemented in small numbered steps.

Always work on ONLY the step explicitly requested by the user.

Do not automatically continue to the next step.

Before making changes:

1. Read the relevant approved specification.
2. Read the relevant implementation plan.
3. Inspect the existing implementation.
4. Identify the exact files required for the requested step.

Do not redesign previously approved architecture unless the requested
step cannot be implemented correctly without doing so.

---

## Scope control

Never expand the task beyond the explicitly requested step.

If unrelated defects are discovered:

- do not fix them automatically
- record them in the final report
- continue only if they block the requested step

Avoid speculative refactoring.

Avoid cleanup unrelated to the current task.

Prefer the smallest correct change.

---

## Token and context efficiency

Keep the main Codex thread focused on:

- requirements
- implementation decisions
- important defects
- final verification

Do not paste large logs into the main conversation.

Prefer quiet/concise command options.

When command output is large:

- save full output to a temporary file if needed
- inspect only relevant sections
- summarize results
- include only actionable errors

Do not repeatedly re-read large specification or plan files unless needed.

Do not repeatedly summarize the entire repository.

---

## Subagent policy

Do NOT spawn subagents automatically for every task.

Use subagents only when there is a clear benefit.

Good subagent tasks:

- running large test suites
- investigating a specific failing test
- architecture/specification compliance review
- security review
- database/TLS review
- searching a large codebase
- analyzing verbose logs
- independent verification after implementation

Avoid using multiple agents to make overlapping code changes.

Prefer at most 1-3 focused subagents for a step.

The main agent owns the final implementation decision.

Subagents should normally inspect/review rather than independently edit
the same files.

---

## Subagent output hygiene

When delegating work, tell the subagent to return only:

- conclusion
- defects found
- affected files
- relevant evidence
- recommended action

Do not return routine successful command output.

For tests return only:

- command
- exit status
- number of tests passed/failed
- failing test names
- important error excerpts

---

## Implementation workflow

For each requested implementation step:

### 1. Inspect

Read the step specification and existing implementation.

### 2. Implement

Make only the changes required for the requested step.

### 3. Verify

Run focused tests first.

Use broader tests only when they provide meaningful additional confidence.

### 4. Review

For important boundaries, use one focused review subagent when useful.

Examples:

- database/TLS boundary
- authentication/security boundary
- deployment boundary
- agent lifecycle
- migrations

### 5. Fix

Fix confirmed problems found during verification.

Do not introduce unrelated improvements.

### 6. Report

Return a concise summary containing:

- implemented
- files changed
- tests run
- result
- remaining issues
- whether the step acceptance criteria are satisfied

STOP after reporting.

Do not begin the next step.

---

## Architecture

Repository areas:

- `agent/` - native Python monitoring agent
- `server/` - FastAPI backend and Alembic
- `web/` - React/TypeScript frontend
- `deploy/` - development and production deployment assets
- `docs/` - architecture, specifications and implementation plans

Production topology:

Browser
-> HTTPS
-> Caddy
   -> `/api/*` -> FastAPI
   -> `/*` -> React static files

Only Caddy exposes public HTTP/HTTPS ports.

Production database is external MySQL.

MySQL connections must follow the approved TLS requirements.

Do not weaken security requirements for convenience.

---

## Testing discipline

Prefer focused tests for the current implementation step.

Do not automatically run every repository test after every minor change.

Run the full relevant suite when:

- a shared component changed
- database infrastructure changed
- application startup changed
- deployment behavior changed
- the step specification explicitly requires it

Never claim tests passed unless they were actually executed successfully.

---

## Git discipline

Do not commit automatically unless explicitly requested.

Do not change branches unless explicitly requested.

Do not modify unrelated user files.

Before completing a step inspect:

git status
git diff --stat
git diff

Report unexpected modifications.

---

## Completion rule

A step is complete only when:

1. requested implementation exists
2. relevant tests pass
3. acceptance criteria have been checked
4. no known blocking defect remains

After that, STOP and wait for the next explicit step.