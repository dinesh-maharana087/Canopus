# Device Watch

Device Watch is a Stage 1 monorepo foundation for a native agent, FastAPI server, React web application, and deployment assets.

The agent, server, and web application are independent projects. Stage 1 establishes their installable project boundaries and frozen dependency metadata without implementing monitoring workflows.

See the approved design in `docs/superpowers/specs/2026-08-31-device-watch-stage-1-design.md` and the implementation plan in `docs/superpowers/plans/2026-08-31-device-watch-stage-1.md`.

## Stage 1

Stage 1 exposes only the health API, an empty native agent lifecycle, and a static web shell. It creates no business tables, monitoring records, concrete collectors, sender, or device workflow.

- Local workflows: [docs/development.md](docs/development.md)
- Architecture and trust boundaries: [docs/architecture.md](docs/architecture.md)
- Production operations: [docs/deployment.md](docs/deployment.md)
- Documentation-only future contracts: [docs/future-contracts.md](docs/future-contracts.md)

The projects remain independently runnable. Production values are required explicitly; there is no silent development database fallback. Docker/MySQL-dependent checks must be run on a host with those services available.
