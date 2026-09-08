# Step 11: Hardened FastAPI Production Image

## Objective

Package the verified server and migration foundation in a locked, non-root, minimal runtime image.

## Why This Step Exists

Production topology requires FastAPI to be private, health-checkable, and free of build tooling at runtime.

## Prerequisites

Steps 05 and 07.

## In Scope

`server/Dockerfile`, root build-context allowlist updates, locked uv builder use, runtime user, read-only-compatible filesystem, and server image health command.

## Out of Scope

Caddy image, web build, production Compose, topology verifier, application changes, and new endpoints.

## Expected Files/Directories

`.dockerignore`, `server/Dockerfile`, and image-specific tests or verification fixtures.

## Implementation Tasks

1. Define exact root-context allowlist for server inputs only.
2. Build from locked Python/uv inputs and copy only the environment, package, and Alembic files needed at runtime.
3. Configure non-root execution, Uvicorn proxy headers, port 8000, health probe, read-only filesystem support, dropped capabilities, and `/tmp` strategy in Compose-facing metadata.
4. Build and inspect the final image for absent uv/compiler/package manager.

## Tests and Verification

Build the image, inspect user and command, run the health probe where dependencies are available, and verify no build tool is present.

## Definition of Done

- Image consumes frozen server lock data.
- Runtime user is non-root and no build toolchain remains.
- Uvicorn command matches the approved proxy trust contract.
- Image is ready for Step 13 Compose integration.

## Handoff Information

Record image tag, build command, inspected user/toolchain results, and commit ID.

## Suggested Commit Checkpoint

`build(server): add hardened production image`
