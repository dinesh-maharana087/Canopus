# Staged and Future Contracts

This document records the ordered cross-stage contract. The current repository partially implements the early Stage 2 foundation: typed device/bootstrap contracts, the server-owned `devices` table, one-time bootstrap cryptography and lifecycle services, and secret-safe `enrollment_bootstraps` persistence. It does not yet implement the public enrollment exchange, device credential issuance, heartbeat transport, connectivity state, monitoring, evaluation, or alerts. At Stage 1 completion, every item in the sequence below was future work.

```text
device enrollment
-> credentials/token
-> heartbeat submission
-> current health update
-> historical metric storage
-> health evaluation
-> alert generation
```

## Boundaries

- **Device enrollment:** the current server foundation defines server-owned UUID identity, persists the identity table, and implements one-time bootstrap generation, hashing, storage, validation, consumption, and revocation services. The public enrollment endpoint and the atomic exchange that creates a device and credential are still future work.
- **Credentials/token:** current bootstrap persistence stores only a lookup fingerprint and versioned HMAC digest, never the plaintext bootstrap secret. Stable device credential issuance, server-side credential hashing, and protected agent credential-file storage are still future work.
- **Heartbeat submission:** a future versioned HTTPS submission envelope would carry device identity, observation time, agent version, idempotency identity, and independent collector results. No sender or submission route exists here.
- **Current health update:** future persistence would update current state independently from history. No health table or current-state workflow exists here.
- **Historical metric storage:** the historical Stage 1 Alembic revision remains schema-empty, while the current migration head adds only device identity and enrollment-bootstrap tables. Metrics and historical-observation migrations remain future work requiring a reviewed contract.
- **Health evaluation:** future evaluation would run after persistence and use server receipt time for online/offline decisions rather than trusting the device clock. No evaluator exists here.
- **Alert generation:** future alerts would be emitted from evaluation results, not coupled directly to collection or transport. No alert route, table, or event exists here.

Future collection orchestration should isolate independent collector failures. Future delivery should use bounded timeouts, bounded retries, and backoff. Those are design boundaries only; the Stage 1 agent has an empty registry, waits for stop, and performs no collection or communication.
