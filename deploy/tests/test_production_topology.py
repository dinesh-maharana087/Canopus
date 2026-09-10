from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from device_watch_server.core.config import Settings
from verify_topology import validate_topology

CADDYFILE = """{$DEVICE_WATCH_DOMAIN} {
    encode zstd gzip
    handle /api/* {
        reverse_proxy server:8000
    }
    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }
}
"""


def valid_topology() -> dict[str, object]:
    service = {
        "build": {"context": "..", "dockerfile": "deploy/caddy/Dockerfile"},
        "image": "device-watch-caddy:stage1",
        "ports": ["80:80", "443:443"],
        "read_only": True,
        "security_opt": ["no-new-privileges:true"],
        "cap_drop": ["ALL"],
        "cap_add": ["NET_BIND_SERVICE"],
        "tmpfs": ["/tmp"],
        "volumes": [
            {"type": "volume", "source": "caddy_data", "target": "/data"},
            {"type": "volume", "source": "caddy_config", "target": "/config"},
        ],
        "networks": ["device_watch_prod"],
    }
    server = {
        "build": {"context": "..", "dockerfile": "server/Dockerfile"},
        "image": "device-watch-server:stage1",
        "read_only": True,
        "security_opt": ["no-new-privileges:true"],
        "cap_drop": ["ALL"],
        "tmpfs": ["/tmp"],
        "extra_hosts": ["host.docker.internal:host-gateway"],
        "secrets": [
            {"source": "mysql_ca", "target": "mysql-ca.pem", "mode": "0444"}
        ],
        "environment": {"DEVICE_WATCH_ENV": "production"},
        "networks": ["device_watch_prod"],
    }
    return {
        "services": {"caddy": service, "server": server},
        "networks": {"device_watch_prod": {"driver": "bridge"}},
        "secrets": {"mysql_ca": {"file": "./mysql-ca.pem"}},
    }


def test_production_environment_example_satisfies_server_tls_policy() -> None:
    env_file = Path(__file__).parents[1] / ".env.prod.example"
    database_url = next(
        line.removeprefix("DATABASE_URL=")
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if line.startswith("DATABASE_URL=")
    )

    Settings(device_watch_env="production", database_url=database_url)


def test_rendered_exact_two_service_topology_passes() -> None:
    assert validate_topology(valid_topology(), CADDYFILE) == []


def test_extra_caddy_volume_fails() -> None:
    topology = valid_topology()
    topology["services"]["caddy"]["volumes"].append(  # type: ignore[index, union-attr]
        {"type": "bind", "source": "/host", "target": "/host"}
    )

    assert any(
        "Caddy state volumes" in error
        for error in validate_topology(topology, CADDYFILE)
    )


def test_read_only_caddy_state_volume_fails() -> None:
    topology = valid_topology()
    topology["services"]["caddy"]["volumes"][0]["read_only"] = True  # type: ignore[index]

    assert any(
        "Caddy state volumes" in error
        for error in validate_topology(topology, CADDYFILE)
    )


def test_forbidden_server_port_fails() -> None:
    topology = valid_topology()
    topology["services"]["server"]["ports"] = ["8000:8000"]  # type: ignore[index]
    assert any("server must not publish" in error for error in validate_topology(topology, CADDYFILE))


def test_extra_service_and_network_peer_fail() -> None:
    topology = valid_topology()
    topology["services"]["worker"] = {}
    assert validate_topology(topology, CADDYFILE)

    topology = valid_topology()
    topology["services"]["server"]["networks"] = ["device_watch_prod", "other"]  # type: ignore[index]
    assert any("one production network" in error for error in validate_topology(topology, CADDYFILE))


def test_caddy_path_rewriting_and_wrong_upstream_fail() -> None:
    topology = deepcopy(valid_topology())
    assert validate_topology(topology, CADDYFILE.replace("server:8000", "server:9000"))
    assert validate_topology(topology, CADDYFILE + "\nhandle_path /api/* {}\n")


def test_wrong_ca_secret_source_fails() -> None:
    topology = valid_topology()
    topology["services"]["server"]["secrets"][0]["source"] = "wrong_ca"  # type: ignore[index]

    assert any(
        "read-only CA secret mount" in error
        for error in validate_topology(topology, CADDYFILE)
    )


def test_writable_ca_secret_mode_fails() -> None:
    topology = valid_topology()
    topology["services"]["server"]["secrets"][0]["mode"] = 444  # type: ignore[index]

    assert any(
        "read-only CA secret mount" in error
        for error in validate_topology(topology, CADDYFILE)
    )


def test_caddy_rewrite_directive_fails() -> None:
    topology = valid_topology()
    rewritten_caddyfile = CADDYFILE.replace(
        "reverse_proxy server:8000",
        "rewrite * /internal{uri}\n        reverse_proxy server:8000",
    )

    assert any(
        "rewrite" in error for error in validate_topology(topology, rewritten_caddyfile)
    )
