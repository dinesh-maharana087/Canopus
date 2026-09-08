# Step 12: Caddy Image and Path-Preserving Configuration

## Objective

Package the web build into a final Caddy image with automatic HTTPS, SPA fallback, and unchanged `/api/*` forwarding.

## Why This Step Exists

Caddy is the sole production ingress and must serve static web output while privately proxying FastAPI.

## Prerequisites

Step 10.

## In Scope

`deploy/caddy/Caddyfile`, multi-stage Caddy Dockerfile, static build copy, persistent state paths, and Caddy validation.

## Out of Scope

Production Compose network/security assertions, FastAPI image, API changes, certificates in the repository, and development deployment.

## Expected Files/Directories

`deploy/caddy/Caddyfile`, `deploy/caddy/Dockerfile`, and related Caddy fixtures.

## Implementation Tasks

1. Build web with locked npm install in a Node stage.
2. Copy only `web/dist` and Caddyfile into `caddy:2.11.4-alpine`.
3. Use `handle /api/*` with exact `reverse_proxy server:8000`, then SPA fallback/static serving.
4. Validate the packaged Caddyfile and prove Node is absent from the final image.

## Tests and Verification

Run web build prerequisite, image build, `caddy validate`, and a text assertion rejecting rewrite/handle_path directives.

## Definition of Done

- Final image contains no Node runtime.
- Domain comes from `DEVICE_WATCH_DOMAIN`.
- `/api` is preserved and targets exactly `server:8000`.
- Caddy data/config paths are ready for named volumes.

## Handoff Information

Record image tag, Caddy validation output, route assertions, and commit ID for Step 13.

## Suggested Commit Checkpoint

`build(deploy): package the Caddy ingress image`
