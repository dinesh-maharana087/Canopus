from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from verify_topology import validate_topology  # noqa: I001


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
        "volumes": ["caddy_data:/data", "caddy_config:/config"],
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
        "secrets": [{"target": "mysql-ca.pem", "mode": "0444"}],
        "environment": {"DEVICE_WATCH_ENV": "production"},
        "networks": ["device_watch_prod"],
    }
    return {
        "services": {"caddy": service, "server": server},
        "networks": {"device_watch_prod": {"driver": "bridge"}},
        "secrets": {"mysql_ca": {"file": "./mysql-ca.pem"}},
    }


def test_exact_two_service_topology_passes() -> None:
    assert validate_topology(valid_topology(), CADDYFILE) == []


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
