# Device Watch

Device Watch is a monorepo for a native agent, FastAPI server, React web application, and deployment assets.

The agent, server, and web application are independent projects. Stage 1 established their installable project boundaries and frozen dependency metadata. The current repository also contains a partial Stage 2 server foundation for device identity and one-time enrollment bootstrap handling; monitoring workflows remain unimplemented.

See the approved Stage 1 design in `docs/superpowers/specs/2026-08-31-device-watch-stage-1-design.md`, its implementation plan in `docs/superpowers/plans/2026-08-31-device-watch-stage-1.md`, and the approved Stage 2 design in `docs/superpowers/specs/2026-09-08-device-watch-stage-2-design.md`.

## Stage 1 completion scope (historical)

Stage 1 exposes only the health API, an empty native agent lifecycle, and a static web shell. It creates no business tables, monitoring records, concrete collectors, sender, or device workflow.

- Local workflows: [docs/development.md](docs/development.md)
- Architecture and trust boundaries: [docs/architecture.md](docs/architecture.md)
- Production operations: [docs/deployment.md](docs/deployment.md)
- Staged and future contracts: [docs/future-contracts.md](docs/future-contracts.md)

The projects remain independently runnable. Production values are required explicitly; there is no silent development database fallback. Docker/MySQL-dependent checks must be run on a host with those services available.
