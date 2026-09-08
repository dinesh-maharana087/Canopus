# Future Contracts

Everything in this document is a future contract, not an implemented route, table, credential, fixture, or workflow.

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

- **Device enrollment:** a future one-time bootstrap exchange would establish a device identity and issue a revocable credential. No enrollment endpoint exists in Stage 1.
- **Credentials/token:** the future server would store only a credential hash; a future agent would store its issued secret in a protected root-readable file. No credential is issued or stored here.
- **Heartbeat submission:** a future versioned HTTPS submission envelope would carry device identity, observation time, agent version, idempotency identity, and independent collector results. No sender or submission route exists here.
- **Current health update:** future persistence would update current state independently from history. No health table or current-state workflow exists here.
- **Historical metric storage:** future migrations would add domain tables only after a reviewed contract. The Stage 1 Alembic baseline is schema-empty.
- **Health evaluation:** future evaluation would run after persistence and use server receipt time for online/offline decisions rather than trusting the device clock. No evaluator exists here.
- **Alert generation:** future alerts would be emitted from evaluation results, not coupled directly to collection or transport. No alert route, table, or event exists here.

Future collection orchestration should isolate independent collector failures. Future delivery should use bounded timeouts, bounded retries, and backoff. Those are design boundaries only; the Stage 1 agent has an empty registry, waits for stop, and performs no collection or communication.
