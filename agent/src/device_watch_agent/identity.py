"""Protected identity-file storage. This module performs no network operations."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import secrets
import sys
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID

_MAX_FILE_BYTES = 4096
_CREDENTIAL = re.compile(r"dwc_v1_[0-9a-f]{32}_([A-Za-z0-9_-]{43})\Z")
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z"
)


class IdentityError(ValueError):
    def __init__(self) -> None:
        super().__init__("Identity storage unavailable")


class IdentityState(StrEnum):
    REENROLLMENT_REQUIRED = "reenrollment_required"


@dataclass(frozen=True, slots=True, repr=False)
class AgentIdentity:
    device_id: UUID
    credential: str
    created_at: datetime

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.device_id, UUID) or self.device_id.version != 4:
                raise IdentityError()
            if not isinstance(self.credential, str):
                raise IdentityError()
            matched = _CREDENTIAL.fullmatch(self.credential)
            if matched is None:
                raise IdentityError()
            secret = base64.b64decode(matched[1] + "=", altchars=b"-_", validate=True)
            if (
                len(secret) != 32
                or base64.urlsafe_b64encode(secret).decode().rstrip("=") != matched[1]
            ):
                raise IdentityError()
            if (
                not isinstance(self.created_at, datetime)
                or self.created_at.tzinfo is None
                or self.created_at.utcoffset() is None
            ):
                raise IdentityError()
            object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
        except (ValueError, TypeError, OverflowError, binascii.Error):
            raise IdentityError() from None

    def __repr__(self) -> str:
        return "AgentIdentity(<redacted>)"

    __str__ = __repr__


def validate_identity_path(path: Path) -> Path:
    """Require an absolute local path without traversal, device names, or streams."""
    if not isinstance(path, Path) or not path.is_absolute() or not path.name:
        raise IdentityError()
    if ".." in path.parts or "\x00" in str(path):
        raise IdentityError()
    if os.name == "nt":
        if path.drive.startswith("\\"):
            raise IdentityError()
        reserved = {"CON", "PRN", "AUX", "NUL"} | {
            f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
        }
        for part in path.parts[1:]:
            if (
                ":" in part
                or part.endswith((" ", "."))
                or part.split(".")[0].upper() in reserved
            ):
                raise IdentityError()
    return path


def default_identity_path(environ: Mapping[str, str] | None = None) -> Path:
    values = os.environ if environ is None else environ
    if os.name == "nt":
        root = Path(values.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        return validate_identity_path(root / "DeviceWatch" / "identity.json")
    return Path("/var/lib/device-watch-agent/identity.json")


class _Directory(Protocol):
    def read(self, name: str, limit: int) -> bytes | None: ...
    def create(self, name: str) -> int: ...
    def replace(self, source: str, target: str) -> None: ...
    def unlink(self, name: str) -> None: ...
    def sync(self) -> None: ...


def _open_directory(
    path: Path, *, create: bool = False
) -> AbstractContextManager[_Directory]:
    if sys.platform == "win32":
        from device_watch_agent._identity_windows import open_directory

        return open_directory(path, create=create)
    else:
        if os.name != "posix":
            raise IdentityError()
        from device_watch_agent._identity_posix import open_directory as posix_directory

        return posix_directory(path, create=create)


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise IdentityError()
        result[key] = value
    return result


def _read(directory: _Directory, name: str) -> bytes | None:
    # Read one sentinel byte so a valid JSON prefix cannot hide oversized input.
    content = directory.read(name, _MAX_FILE_BYTES + 1)
    if content is not None and len(content) > _MAX_FILE_BYTES:
        raise IdentityError()
    return content


def _decode(content: bytes) -> AgentIdentity:
    value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields)
    if not isinstance(value, dict) or set(value) != {
        "version",
        "device_id",
        "credential",
        "created_at",
    }:
        raise IdentityError()
    if type(value["version"]) is not int or value["version"] != 1:
        raise IdentityError()
    if not all(
        isinstance(value[name], str)
        for name in ("device_id", "credential", "created_at")
    ):
        raise IdentityError()
    device_id = UUID(value["device_id"])
    if str(device_id) != value["device_id"] or not _TIMESTAMP.fullmatch(
        value["created_at"]
    ):
        raise IdentityError()
    return AgentIdentity(
        device_id, value["credential"], datetime.fromisoformat(value["created_at"])
    )


class IdentityStore:
    """Single-writer storage. Errors return no identity; callers must fail closed.

    The immediate private parent can be created; its ancestors must already exist.
    No cached identity, backup, plaintext fallback, automatic repair, or replay is kept.
    """

    def __init__(self, path: Path) -> None:
        self.path = validate_identity_path(path)

    def load(self) -> AgentIdentity | None:
        try:
            with _open_directory(self.path.parent) as directory:
                content = _read(directory, self.path.name)
                return None if content is None else _decode(content)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError, RecursionError):
            raise IdentityError() from None

    def save(self, value: AgentIdentity) -> None:
        temporary: str | None = None
        try:
            if not isinstance(value, AgentIdentity):
                raise IdentityError()
            content = json.dumps(
                {
                    "version": 1,
                    "device_id": str(value.device_id),
                    "credential": value.credential,
                    "created_at": value.created_at.isoformat().replace("+00:00", "Z"),
                },
                separators=(",", ":"),
            ).encode("utf-8")
            with _open_directory(self.path.parent, create=True) as directory:
                existing = _read(directory, self.path.name)
                if existing is not None:
                    _decode(existing)
                temporary = ".identity-" + secrets.token_hex(16) + ".tmp"
                created = False
                try:
                    fd = directory.create(temporary)
                    created = True
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    directory.replace(temporary, self.path.name)
                    temporary = None
                    directory.sync()
                finally:
                    if created and temporary is not None:
                        directory.unlink(temporary)
        except (OSError, ValueError, TypeError, RecursionError):
            raise IdentityError() from None

    def invalidate(self) -> IdentityState:
        """Delete protected storage; caller must discard memory and require enrollment."""
        try:
            with _open_directory(self.path.parent) as directory:
                if _read(directory, self.path.name) is not None:
                    directory.unlink(self.path.name)
                    directory.sync()
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            raise IdentityError() from None
        return IdentityState.REENROLLMENT_REQUIRED
