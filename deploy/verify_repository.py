"""Audit repository security and Stage 1 executable boundaries."""

from __future__ import annotations

import argparse
import ast
import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Finding:
    """Sanitized audit finding with no source-value echo."""

    path: str
    rule: str
    message: str


class AuditScope(str, Enum):
    """Repository boundary selected for executable-feature checks."""

    CURRENT = "current"
    STAGE_ONE = "stage-one"


_EXCLUDED_PARTS = {
    ".git",
    ".git.codex-generated",
    ".tmp",
    ".worktrees",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
_TEXT_SUFFIXES = {
    ".c",
    ".cfg",
    ".css",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".key",
    ".md",
    ".pem",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}
_CREDENTIAL_SUFFIXES = {".cfg", ".env", ".ini", ".json", ".toml", ".yml", ".yaml"}
_PRIVATE_KEY_FILE_SUFFIXES = {".key", ".p12", ".pfx"}
_PRIVATE_KEY_FILE_NAMES = {"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"}
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:[A-Z0-9][A-Z0-9 -]* )?PRIVATE KEY-----",
    re.IGNORECASE,
)
_URL_SCHEME = re.compile(r"\b([a-z][a-z0-9+.-]*)://", re.IGNORECASE)
_DATABASE_URL_CONTEXT = re.compile(
    r"\b(?:database|db)(?:[_-][a-z0-9]+)*[_-]?url\b|\bsqlalchemy\.url\b",
    re.IGNORECASE,
)
_ALLOWED_DATABASE_SCHEMES = {"mysql+pymysql"}
_STAGE_ONE_MIGRATION = "server/alembic/versions/20260831_0001_baseline.py"
_STAGE_ONE_SERVER_SOURCES = {
    "server/src/device_watch_server/__init__.py",
    "server/src/device_watch_server/api/__init__.py",
    "server/src/device_watch_server/api/health.py",
    "server/src/device_watch_server/api/router.py",
    "server/src/device_watch_server/app.py",
    "server/src/device_watch_server/cli.py",
    "server/src/device_watch_server/core/__init__.py",
    "server/src/device_watch_server/core/config.py",
    "server/src/device_watch_server/core/logging.py",
    "server/src/device_watch_server/core/middleware.py",
    "server/src/device_watch_server/db/__init__.py",
    "server/src/device_watch_server/db/base.py",
    "server/src/device_watch_server/db/engine.py",
    "server/src/device_watch_server/db/health.py",
    "server/src/device_watch_server/main.py",
}
_ALEMBIC_TABLE = re.compile(r"\bop\.create_table\s*\(")
_LIVE_SECRET = re.compile(
    r"""(?<![A-Za-z0-9_-])["']?
        (?:password|passwd|secret|token|api[_-]?key)["']?\s*[:=]\s*(?:
        "(?![$<{\[])[^"\r\n]+"
        |
        '(?![$<{\[])[^'\r\n]+'
        |
        (?![$<{\["'])[^\s,;#]+
    )""",
    re.IGNORECASE | re.VERBOSE,
)
_ROUTE = re.compile(r"(?:add_api_route|@?(?:app|router)\.(?:get|post|put|patch|delete))\s*\(\s*[\"']([^\"']+)")


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _excluded(path: Path) -> bool:
    return any(part in _EXCLUDED_PARTS for part in path.parts)


def _project_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or _excluded(path.relative_to(root)):
            continue
        yield path


def _files(paths: Iterable[Path]) -> Iterable[tuple[Path, str]]:
    for path in paths:
        if path.suffix.lower() not in _TEXT_SUFFIXES and path.name not in {".env", "Dockerfile", "Caddyfile"}:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def _is_example(path: Path) -> bool:
    return path.name == ".env.example" or path.name.endswith(".example")


def _is_production_surface(relative: str) -> bool:
    return relative.startswith(("server/src/", "agent/src/", "web/src/", "deploy/"))


def _is_credential_surface(path: Path, relative: str) -> bool:
    return _is_production_surface(relative) or path.suffix.lower() in _CREDENTIAL_SUFFIXES


def _is_private_key_file(path: Path) -> bool:
    return (
        path.suffix.lower() in _PRIVATE_KEY_FILE_SUFFIXES
        or path.name.lower() in _PRIVATE_KEY_FILE_NAMES
    )


def _literal_text(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            value.value
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _literal_text(node.left)
        right = _literal_text(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _literal_url_scheme(node: ast.expr) -> str | None:
    text = _literal_text(node)
    if text is None:
        return None
    match = _URL_SCHEME.search(text)
    return match.group(1).lower() if match else None


def _database_engine_schemes(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()

    assigned: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if value is None:
                continue
            scheme = _literal_url_scheme(value)
            if scheme is None:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = scheme

    schemes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function_name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            if isinstance(node.func, ast.Attribute)
            else ""
        )
        if function_name not in {"create_async_engine", "create_engine"}:
            continue
        argument = node.args[0]
        scheme = (
            assigned.get(argument.id)
            if isinstance(argument, ast.Name)
            else _literal_url_scheme(argument)
        )
        if scheme is not None:
            schemes.add(scheme)
    return schemes


def _has_unsupported_database_url(path: Path, text: str, *, is_test: bool) -> bool:
    if path.suffix.lower() == ".py":
        if any(
            scheme not in _ALLOWED_DATABASE_SCHEMES
            for scheme in _database_engine_schemes(text)
        ):
            return True
        if is_test:
            return False

    for line in text.splitlines():
        if not _DATABASE_URL_CONTEXT.search(line):
            continue
        if any(
            match.group(1).lower() not in _ALLOWED_DATABASE_SCHEMES
            for match in _URL_SCHEME.finditer(line)
        ):
            return True
    return False


def _finding(root: Path, path: Path, rule: str, message: str) -> Finding:
    return Finding(_relative(root, path), rule, message)


def audit_repository(
    root: Path,
    *,
    scope: AuditScope = AuditScope.STAGE_ONE,
) -> list[Finding]:
    """Return sanitized findings for security and Stage 1 boundary violations."""

    findings: list[Finding] = []
    project_files = sorted(_project_files(root))
    private_key_files = {path for path in project_files if _is_private_key_file(path)}
    contents = list(_files(project_files))

    for path in sorted(private_key_files):
        findings.append(
            _finding(root, path, "private-key", "private-key file is present")
        )

    for path, text in contents:
        relative = _relative(root, path)
        is_test = "/tests/" in f"/{relative}"
        if path not in private_key_files and _PRIVATE_KEY.search(text):
            findings.append(_finding(root, path, "private-key", "private-key material is present"))

        if path.name == ".env" or (path.name.startswith(".env.") and not _is_example(path)):
            findings.append(_finding(root, path, "live-environment", "live environment files must not be committed"))

        scans_for_literals = _is_credential_surface(path, relative)
        if not is_test and not _is_example(path) and scans_for_literals and _LIVE_SECRET.search(text):
            findings.append(_finding(root, path, "live-credential", "credential-like literal found outside an example file"))

        if _has_unsupported_database_url(path, text, is_test=is_test):
            findings.append(_finding(root, path, "database-allowlist", "unsupported database URL scheme"))

        if scope is AuditScope.STAGE_ONE and relative.startswith("server/src/"):
            for match in _ROUTE.finditer(text):
                if match.group(1) not in {"/api/v1/health/live", "/api/v1/health/ready"}:
                    findings.append(_finding(root, path, "business-route", "non-health API route is present"))
            if re.search(r"class\s+\w+\s*\(\s*Base\s*\)|__tablename__\s*=", text):
                findings.append(_finding(root, path, "domain-table", "mapped domain table is present"))

        if (
            scope is AuditScope.STAGE_ONE
            and relative.startswith("server/src/device_watch_server/")
            and path.suffix.lower() == ".py"
            and relative not in _STAGE_ONE_SERVER_SOURCES
        ):
            findings.append(
                _finding(
                    root,
                    path,
                    "stage-one-source",
                    "server source is outside the Stage 1 boundary",
                )
            )

        if (
            scope is AuditScope.STAGE_ONE
            and relative.startswith("server/alembic/versions/")
            and path.suffix.lower() == ".py"
        ):
            if relative != _STAGE_ONE_MIGRATION:
                findings.append(
                    _finding(
                        root,
                        path,
                        "stage-one-migration",
                        "migration is outside the Stage 1 baseline",
                    )
                )
            if _ALEMBIC_TABLE.search(text):
                findings.append(
                    _finding(root, path, "domain-table", "domain table migration is present")
                )

        if scope is AuditScope.STAGE_ONE and relative.startswith("agent/src/"):
            if path.name.lower() in {"sender.py", "transport.py"} or "sender" in path.stem.lower():
                findings.append(_finding(root, path, "sender", "production sender module is present"))
            if path.name != "contracts.py" and re.search(r"async\s+def\s+collect\s*\(", text):
                findings.append(_finding(root, path, "concrete-collector", "production collector implementation is present"))

        if scope is AuditScope.STAGE_ONE and relative.startswith("web/src/"):
            if re.search(r"\bfetch\s*\(|XMLHttpRequest|\.open\s*\(\s*[\"'](?:GET|POST|PUT|PATCH|DELETE)", text):
                findings.append(_finding(root, path, "frontend-api", "frontend network API call is present"))
            if re.search(r"(?:device_id|heartbeat|observed_at|monitoring_records?)\s*[:=]", text, re.IGNORECASE):
                findings.append(_finding(root, path, "monitoring-fixture", "monitoring data fixture is present"))

    production_compose = root / "deploy" / "compose.prod.yml"
    if production_compose.exists():
        text = production_compose.read_text(encoding="utf-8")
        service_block = re.search(r"^services:\s*\n(?P<body>.*?)(?=^networks:|^volumes:|^secrets:|\Z)", text, re.MULTILINE | re.DOTALL)
        if service_block:
            service_names = set(re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", service_block.group("body"), re.MULTILINE))
            if service_names != {"caddy", "server"}:
                findings.append(_finding(root, production_compose, "production-services", "production Compose must contain only caddy and server"))
        server_block = re.search(r"^  server:\s*\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\s*$|^networks:|\Z)", text, re.MULTILINE | re.DOTALL)
        if server_block and re.search(r"^\s+ports:\s*$", server_block.group("body"), re.MULTILINE):
            findings.append(_finding(root, production_compose, "server-port", "production server must not publish a host port"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the Device Watch repository")
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument(
        "--scope",
        choices=tuple(scope.value for scope in AuditScope),
        default=AuditScope.STAGE_ONE.value,
        help="apply current security checks or historical Stage 1 absence boundaries",
    )
    args = parser.parse_args(argv)
    findings = audit_repository(
        args.root.resolve(),
        scope=AuditScope(args.scope),
    )
    for finding in findings:
        print(f"{finding.path}: {finding.rule}: {finding.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
