# Device Health Portal - Codex Instructions

## Project workflow

This project is implemented in small numbered steps and focused repair/verification batches.

Always work on ONLY the step, repair batch, or verification scope explicitly requested by the user.

Do not automatically continue to the next step.

Before making changes:

1. Read the relevant approved specification.
2. Read the relevant implementation/repair plan or execution card.
3. Read the relevant current verification/baseline evidence when applicable.
4. Inspect the existing implementation.
5. Identify the exact files required for the requested task.

Do not redesign previously approved architecture unless the requested task cannot be implemented correctly without doing so.

If an architectural change appears necessary, explain the conflict and keep the change as small as possible.

---

## Source-of-truth priority

When project documents disagree, use this priority:

1. Explicit current user request
2. Approved stage design/specification
3. Approved execution/repair plan for the requested task
4. Independent verification/baseline evidence
5. Current implementation and tests
6. Progress/status documents
7. Historical implementation summaries

`docs/progress/current-status.md` is progress history, not stronger evidence than an independent verification result.

A previous `Complete` label does not override a later verified `FAIL`.

Do not silently resolve contradictions. Report them when they materially affect the requested task.

---

## Scope control

Never expand the task beyond the explicitly requested step, repair batch, or verification area.

If unrelated defects are discovered:

- do not fix them automatically
- record them in the final report
- continue only if they do not block the requested task
- if they block the requested task, explain the dependency before making any broader change

Avoid speculative refactoring.

Avoid cleanup unrelated to the current task.

Prefer the smallest correct change.

Do not implement functionality from a later stage merely because it is convenient.

---

## Token and context efficiency

Keep the main Codex thread focused on:

- requirements
- implementation decisions
- important defects
- verification results
- handoff state

Do not paste large logs into the main conversation.

Prefer quiet/concise command options.

When command output is large:

- save full output to a temporary file if needed
- inspect only relevant sections
- summarize results
- include only actionable errors

Do not repeatedly re-read large specification or plan files unless necessary.

Do not repeatedly summarize the entire repository.

Do not scan unrelated project areas when the requested task already provides a focused file boundary.

Prefer existing verification evidence and execution cards over reconstructing old context from scratch.

---

## Interrupted-session / resume workflow

A task may be interrupted by model/session limits.

When resuming an interrupted task:

1. Do not restart the task from scratch.
2. Read the relevant execution/repair/verification plan.
3. Read the latest progress or evidence document.
4. Inspect:
   - `git status`
   - `git diff --stat`
   - `git diff`
5. Identify:
   - work already completed
   - partially implemented work
   - unverified work
   - missing work
6. Preserve correct uncommitted changes.
7. Continue only the unfinished portion of the same task.
8. Run the complete verification required for that task before declaring it complete.
9. Do not begin the next task.

Never discard interrupted-session changes merely because they are uncommitted.

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

Prefer at most 1-3 focused subagents for a task.

The main agent owns the final implementation decision.

Subagents should normally inspect/review rather than independently edit the same files.

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

# Implementation workflow

For each requested implementation step:

## 1. Inspect

Read:

- the relevant execution card
- relevant approved design sections
- current progress/baseline context
- existing implementation directly related to the step

Do not inspect unrelated components without a concrete dependency.

## 2. Implement

Make only the changes required for the requested step.

Preserve completed work.

Do not implement later-step functionality.

## 3. Verify

Run focused tests first.

Use broader tests only when they provide meaningful additional confidence or are explicitly required by the step.

## 4. Review

For important boundaries, use one focused review subagent when useful.

Examples:

- database/TLS boundary
- authentication/security boundary
- deployment boundary
- agent lifecycle
- migrations

## 5. Fix

During implementation or repair tasks, fix confirmed problems that are within the requested scope.

During verification-only tasks, do NOT repair discovered defects unless the user explicitly requested verification-and-fix.

Do not introduce unrelated improvements.

## 6. Report

Return a concise summary containing:

- implemented
- files changed
- tests/checks run
- result
- remaining issues
- whether the step acceptance criteria are satisfied

STOP after reporting.

Do not begin the next step.

---

# Verification and repair workflow

Verification sessions and repair sessions are separate tasks.

## Verification sessions

When the user asks for verification:

- do not implement fixes unless explicitly requested
- do not refactor
- inspect only the verification scope requested
- classify findings as:
  - PASS
  - FAIL
  - BLOCKED BY ENVIRONMENT
- record concrete evidence for every FAIL
- do not convert an implementation failure into an environment block
- do not rerun unrelated test suites
- do not repeatedly retry unavailable external infrastructure
- write/update only the requested verification evidence
- stop after the requested verification scope

If Docker, MySQL, Node, browser tooling, or another external dependency is unavailable:

1. establish unavailability once
2. record `BLOCKED BY ENVIRONMENT`
3. continue with checks that do not require it
4. do not spend the session attempting to install/fix unrelated infrastructure

A verification session must not silently repair defects.

---

## Repair sessions

When the user asks to repair verification findings:

1. Read the consolidated baseline first.
2. Read the detailed verification evidence for the affected area.
3. Read only the relevant design/plan sections.
4. Inspect only the affected implementation/tests.
5. Repair only the explicitly requested FAIL items.
6. Reproduce each defect with a focused regression test where practical.
7. Make the smallest correct change.
8. Do not repair unrelated failures discovered during the session.
9. Run the affected component checks.
10. Do not mark the finding PASS until verification actually succeeds.
11. Stop after the requested repair batch.

Do not implement later-stage functionality during a baseline repair task.

---

## Re-verification

After a repair:

- rerun only the verification area invalidated by changed files/contracts
- do not repeat unrelated verification areas
- preserve existing PASS evidence for unchanged components
- update the affected verification evidence
- update acceptance mapping only when an acceptance result changes
- regenerate the consolidated baseline only after targeted re-verification is complete

Example:

```text
V01 failure
    ↓
R1 repair
    ↓
rerun V01 only
    ↓
update V07 if acceptance mapping changed
    ↓
update final baseline



Do not run the complete repository verification matrix after every repair unless explicitly required.

Verification context efficiency

For verification or repair tasks:

Read the requested verification/repair evidence file first.
Read only the corresponding design/plan sections.
Inspect only files directly related to the requested verification area.
Do not re-read all Stage 1 documents unless explicitly performing a full acceptance review.
Do not re-scan the entire repository when a focused source list already exists.
Reuse existing PASS evidence for unchanged components.
Do not rerun expensive or blocked checks without a reason.

If a baseline document lists important source locations, use those locations as the initial inspection boundary.

Stage 1 baseline protection

Stage 1 independent verification lives under:

docs/verification/stage-01/

The consolidated baseline is:

docs/verification/stage-01/stage-01-baseline.md

When working on Stage 1 repairs:

treat the consolidated baseline as the current finding summary
use V01-V07 evidence for detailed findings
repair one focused batch at a time
do not implement Stage 2 during Stage 1 repair work
preserve PASS areas unless the repair directly affects them
rerun only the affected V-area after a repair
update V07 only when acceptance results change
regenerate the final baseline only after targeted re-verification

Do not treat historical Complete labels as stronger evidence than independent verification.

A Stage 1 verification area is invalidated only when later work changes:

one of its verified implementation/configuration files
an externally visible contract
a relevant test/verifier
dependency or toolchain requirements
security/absence boundaries
deployment topology
an environment-blocked area after the necessary environment becomes available

Unchanged verified Stage 1 components do not require full re-audit during later stages.

Stage transition rule

Do not treat a stage as a safe foundation for later stages while unresolved implementation FAIL findings remain.

A stage may be used as a baseline when:

applicable implementation checks are PASS
unresolved non-PASS checks are only clearly documented environment blocks
acceptance mapping has been updated
the consolidated baseline reflects the current repository state

Environment blocks must never be represented as PASS.

When the final baseline says a stage is not safe, repair and re-verify before depending on the failed contracts.

Architecture

Repository areas:

agent/ - native Python monitoring agent
server/ - FastAPI backend and Alembic
web/ - React/TypeScript frontend
deploy/ - development and production deployment assets
docs/ - architecture, specifications, plans, verification, and progress

Production topology:

Browser / Remote Agent
        |
      HTTPS
        |
        v
      Caddy
       |
       |-- /api/* -> FastAPI
       |
       `-- /* -> React static files

FastAPI
   |
   v
External MySQL

Only Caddy exposes public HTTP/HTTPS ports.

Production database is external MySQL.

MySQL connections must follow the approved TLS requirements.

Do not weaken security requirements for convenience.

Future remote agents use outbound communication.

Do not introduce inbound SSH polling or arbitrary command execution unless a later approved stage explicitly changes that architecture.

Testing discipline

Prefer focused tests for the current implementation/repair step.

Do not automatically run every repository test after every minor change.

Run broader relevant suites when:

a shared component changed
database infrastructure changed
application startup changed
deployment behavior changed
a stable public contract changed
the step specification explicitly requires it

For a regression repair:

reproduce the defect where practical
add/fix focused regression coverage
make the correction
run the focused test
run the affected component suite when warranted

Never claim tests passed unless they were actually executed successfully.

Never convert skipped, unavailable, or blocked checks into PASS.

Security discipline

Never expose in logs, reports, tests, or final responses:

database credentials
full database URLs containing credentials
device credentials
bootstrap secrets
authorization headers
cookies
private keys
production secret values

Use sanitized representations in diagnostics.

Do not weaken:

MySQL TLS validation
credential hashing
secret-file protections
Caddy/FastAPI trust boundaries
production port restrictions

solely to make a test or local environment pass.

Git discipline

Do not commit automatically unless explicitly requested.

Do not change branches unless explicitly requested.

Do not modify unrelated user files.

Before completing a task inspect:

git status
git diff --stat
git diff

For verification/repair handoff also run when appropriate:

git diff --check

Report unexpected modifications.

Do not reset, clean, discard, or overwrite unrelated work.

Documentation discipline

Update only documentation required by the requested task.

Implementation steps should update the relevant progress/status document when required by their execution card.

Verification tasks should update the requested verification evidence.

Repair tasks should update evidence only after the repair has been re-verified.

Do not overwrite historical evidence merely to make current status appear cleaner.

When an old statement becomes stale, distinguish:

historical fact
current implementation
current verification status
Completion rules
Implementation task

An implementation step is complete only when:

requested implementation exists
relevant tests pass
acceptance/definition-of-done criteria have been checked
no known blocking defect remains in the requested scope
Repair task

A repair batch is complete only when:

the requested defect has been reproduced where practical
the minimum repair is implemented
regression/focused checks pass
the relevant verification evidence is updated
no requested FAIL remains unresolved
Verification task

A verification task is complete when:

the requested scope has been inspected
required checks have been attempted
results are classified PASS / FAIL / BLOCKED BY ENVIRONMENT
concrete evidence is recorded
no implementation repair was performed unless explicitly requested

After completing any task:

STOP.

Wait for the next explicit user instruction.
