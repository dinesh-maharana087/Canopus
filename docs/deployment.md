# Production Deployment

Production requires DNS for `DEVICE_WATCH_DOMAIN` to resolve to the host running Caddy. Caddy is the only service with published ports: `80` for HTTP and `443` for HTTPS. Caddy automatically manages certificates; certificates are not stored in this repository.

## Required Values

Use `deploy/.env.prod.example` only as a checked-in template. Copy its shape into an operator-managed environment file such as `deploy/.env.prod`, which is ignored by Git, replace every placeholder, and provide:

- `DEVICE_WATCH_DOMAIN`: the public DNS name.
- `DATABASE_URL`: the complete `mysql+pymysql` URL for externally administered MySQL.
- `MYSQL_CA_CERT_PATH`: host path to the operator-provided CA certificate.

Production `DATABASE_URL` must contain exactly these query entries:

```text
ssl_ca=/run/secrets/mysql-ca.pem
ssl_verify_cert=true
ssl_verify_identity=true
```

Use placeholders only while preparing the operator file; do not run production commands until every value is real, and never commit a live URL or certificate. The commands below use the ignored `deploy/.env.prod` operator file, not the checked-in example. The Compose secret mounts the CA read-only at `/run/secrets/mysql-ca.pem`. The server runs with `DEVICE_WATCH_ENV=production`, a read-only root filesystem, dropped capabilities, `/tmp` tmpfs, and no host port. Persistent Caddy state is stored in named volumes `caddy_data` and `caddy_config`.

## External MySQL

The database is not a production Compose service. Restrict its bind address, firewall, and grants to the intended Docker host or subnet. Use a least-privilege account and configure the account to require encrypted transport. Maintain the CA and certificate lifecycle outside this repository.

On Linux, the server has `host.docker.internal:host-gateway` available when the external MySQL service runs on the Docker host. Do not use `localhost` for that connection: inside the server container it resolves to the server container itself.

## Render and Validate

Run from the repository root without echoing the database URL:

```powershell
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml config
python deploy/verify_topology.py --env-file deploy/.env.prod
```

Build both pinned images and validate the Caddy configuration:

```powershell
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml build server caddy
docker run --rm --entrypoint caddy -e DEVICE_WATCH_DOMAIN=example.invalid device-watch-caddy:stage1 validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker image inspect device-watch-server:stage1 --format '{{.Config.User}}'
```

Start and inspect the private server and public ingress:

```powershell
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml up -d

docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml ps
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml logs --tail=100 caddy server
```

The server readiness probe is `/api/v1/health/ready`; the public health path is served through Caddy without removing `/api`.

## Stop and Rollback

To stop the current release while retaining Caddy certificates and configuration:

```powershell
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml down
```

Do not add `--volumes` during a routine rollback-safe stop. Keep the prior image tags available, deploy a corrected image under a new tag, validate it, and use the Compose file to return to the previous known-good image if needed.
