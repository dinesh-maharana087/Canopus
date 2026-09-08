# Device Watch Stage 1 Decomposed Plan

This decomposition preserves the approved design in [the Stage 1 specification](../../specs/2026-08-31-device-watch-stage-1-design.md) and the detailed original plan at [the original implementation plan](../2026-08-31-device-watch-stage-1.md). The original plan remains the technical source of truth; these files define safe execution boundaries.

## Execution Matrix

| Step | Name | Depends on | Status |
| --- | --- | --- | --- |
| 01 | Repository bootstrap and dependency locks | None | Complete |
| 02 | Server settings and configuration validation | 01 | Complete |
| 03 | SQLAlchemy engine and verified MySQL TLS boundary | 02 | Complete |
| 04 | Development MySQL service foundation | 01 | Complete |
| 05 | FastAPI factory and health endpoints | 02, 03 | Complete |
| 06 | Server logging and database-check CLI | 05 | Pending |
| 07 | Alembic metadata and schema-empty baseline | 03, 04 | Pending |
| 08 | Agent collector contracts and registry | 01 | Pending |
| 09 | Agent configuration and lifecycle | 08 | Pending |
| 10 | React application shell and theme | 01 | Pending |
| 11 | Hardened FastAPI production image | 05, 07 | Pending |
| 12 | Caddy image and path-preserving configuration | 10 | Pending |
| 13 | Production Compose topology and verifier | 11, 12 | Pending |
| 14 | Development smoke profile | 04, 11 | Pending |
| 15 | Repository security and Stage 1 scope audit | 06, 07, 09, 10, 13, 14 | Pending |
| 16 | Operational and architecture documentation | 09, 13, 15 | Pending |
| 17 | Full acceptance verification and evidence capture | 01-16 | Pending |

## Execution Order

Execute one step per coding session in numeric order unless the dependency table permits parallel work. Steps 02, 04, 08, and 10 can proceed independently after 01. Step 03 follows 02; steps 05 and 07 then build on the server foundation. Deployment and documentation remain later because they must describe verified artifacts.

## Dependency Notes

- 04 is intentionally separate from migrations: it provides only the isolated MySQL service and its topology test.
- 08 and 09 contain no server communication, database, Docker, or real collectors.
- 11 packages already-implemented server behavior; it does not add endpoints or domain models.
- 12 packages the web build and Caddy routing policy; 13 owns Compose topology and required-variable behavior.
- 15 is an executable audit, not a replacement for component tests.
- 17 may fix a defect only when a focused regression test and the affected step's checks prove it.

## Potentially Independent Work

After 01, steps 02, 04, 08, and 10 are independent. After 02, step 03 is independent of the agent and web work. After 08, step 09 is independent of the server. All later steps are deliberately sequential where packaging or audit evidence depends on earlier artifacts.

## Completed Work That Must Not Be Repeated

Before this decomposition, the repository contained only the approved Stage 1 specification and the original monolithic implementation plan. No application, deployment, test, progress, or decomposed planning implementation was found. The two committed documents are documentation inputs, not completed implementation steps.

## Recommended Next Step

Execute [Step 03: SQLAlchemy engine and verified MySQL TLS boundary](03-server-engine-tls.md) next, in a separate session. Do not begin any later step in the same session.

## Planning Risks

- Docker, MySQL, uv, and Node availability must be recorded when Step 01 runs; unavailable operator services must not be reported as verified.
- Exact dependency versions and the SQLAlchemy/PyMySQL TLS characterization in the original plan are intentionally locked requirements, not suggestions.
- The schema-empty migration baseline provides no business tables; later stages must not be pulled into Stage 1.
- The wildcard forwarded-header trust is valid only while Step 13 enforces the two-service private network and no published server port.
