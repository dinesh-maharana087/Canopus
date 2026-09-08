"""Validate the rendered production Compose topology without parsing YAML."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class TopologyError(ValueError):
    """Raised when a production topology violates the Stage 1 contract."""


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _service_ports(service: dict[str, Any]) -> list[str]:
    ports = []
    for item in _list(service.get("ports")):
        if isinstance(item, str):
            ports.append(item)
        elif isinstance(item, dict):
            ports.append(f"{item.get('published')}:{item.get('target')}")
    return ports


def _network_names(service: dict[str, Any]) -> set[str]:
    networks = service.get("networks", {})
    if isinstance(networks, dict):
        return set(networks)
    return set(networks) if isinstance(networks, list) else set()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise TopologyError(message)


def validate_caddyfile(caddyfile: str) -> None:
    """Reject path rewriting and require the exact private API upstream."""

    _assert("handle /api/*" in caddyfile, "Caddy must preserve /api/* with an API handler")
    _assert("reverse_proxy server:8000" in caddyfile, "Caddy upstream must be server:8000")
    _assert("handle_path" not in caddyfile, "Caddy must not strip the API path")
    _assert("strip_prefix" not in caddyfile, "Caddy must not rewrite the API path")
    _assert(caddyfile.count("{") == caddyfile.count("}"), "Caddyfile braces are unbalanced")
    _assert(caddyfile.count("reverse_proxy") == 1, "Caddy must define one API upstream")


def validate_topology(rendered: dict[str, Any], caddyfile: str) -> list[str]:
    """Return all sanitized topology violations in a rendered Compose document."""

    errors: list[str] = []
    try:
        services = rendered.get("services", {})
        _assert(set(services) == {"caddy", "server"}, "production must contain only caddy and server")
        caddy = services["caddy"]
        server = services["server"]
        _assert(caddy.get("image") == "device-watch-caddy:stage1", "caddy image is not pinned")
        _assert(server.get("image") == "device-watch-server:stage1", "server image is not pinned")
        _assert(caddy.get("build", {}).get("context") in ("..", "."), "caddy build context is incorrect")
        _assert(caddy.get("build", {}).get("dockerfile") == "deploy/caddy/Dockerfile", "caddy Dockerfile is incorrect")
        _assert(server.get("build", {}).get("context") in ("..", "."), "server build context is incorrect")
        _assert(server.get("build", {}).get("dockerfile") == "server/Dockerfile", "server Dockerfile is incorrect")
        _assert(set(_service_ports(caddy)) == {"80:80", "443:443"}, "only Caddy may publish ports 80 and 443")
        _assert(not _service_ports(server), "server must not publish a host port")
        _assert(caddy.get("read_only") is True and server.get("read_only") is True, "both filesystems must be read-only")
        _assert("/tmp" in _list(caddy.get("tmpfs")) and "/tmp" in _list(server.get("tmpfs")), "both services require /tmp tmpfs")
        _assert("no-new-privileges:true" in _list(caddy.get("security_opt")), "Caddy requires no-new-privileges")
        _assert("no-new-privileges:true" in _list(server.get("security_opt")), "server requires no-new-privileges")
        _assert(set(_list(caddy.get("cap_drop"))) == {"ALL"}, "Caddy must drop all capabilities")
        _assert(set(_list(server.get("cap_drop"))) == {"ALL"}, "server must drop all capabilities")
        _assert(_list(caddy.get("cap_add")) == ["NET_BIND_SERVICE"], "Caddy may add only NET_BIND_SERVICE")
        _assert(not _list(server.get("cap_add")), "server must not retain capabilities")
        _assert(set(caddy.get("volumes", [])) == {"caddy_data:/data", "caddy_config:/config"}, "Caddy state volumes are incorrect")
        _assert(_network_names(caddy) == {"device_watch_prod"} and _network_names(server) == {"device_watch_prod"}, "services must share one production network")
        _assert(rendered.get("networks", {}).get("device_watch_prod", {}).get("internal") is not True, "production network must reach external services")
        _assert(server.get("environment", {}).get("DEVICE_WATCH_ENV") == "production", "server must run in production mode")
        _assert(any("host.docker.internal:host-gateway" == item for item in _list(server.get("extra_hosts"))), "server requires the host gateway mapping")
        secrets = server.get("secrets", [])
        _assert(any((item.get("target") == "mysql-ca.pem" and item.get("mode") in ("0444", 444)) for item in secrets if isinstance(item, dict)), "server requires a read-only CA secret mount")
        _assert("mysql_ca" in rendered.get("secrets", {}), "production CA secret is missing")
        validate_caddyfile(caddyfile)
    except (KeyError, TypeError, AttributeError, TopologyError) as exc:
        errors.append(str(exc))
    return errors


def _render_compose(compose_file: Path, env_file: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), "-f", str(compose_file), "config", "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise TopologyError("docker compose rendering failed")
    return json.loads(result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the production Compose topology")
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--compose-file", type=Path, default=Path("deploy/compose.prod.yml"))
    parser.add_argument("--caddyfile", type=Path, default=Path("deploy/caddy/Caddyfile"))
    args = parser.parse_args(argv)
    try:
        rendered = _render_compose(args.compose_file, args.env_file)
        errors = validate_topology(rendered, args.caddyfile.read_text(encoding="utf-8"))
    except (OSError, TopologyError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"topology validation failed: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
