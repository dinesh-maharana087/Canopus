"""Explicit one-shot enrollment; this module never schedules automatic enrollment."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID

import httpx

from device_watch_agent.config import AgentSettings
from device_watch_agent.identity import AgentIdentity, IdentityError, IdentityStore

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
_ATTEMPT_SECONDS = 30.0
_RETRY_DELAYS = (0.5, 1.0)
_MAX_RESPONSE_BYTES = 4096
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:[0-5]\d)\Z"
)


class EnrollmentState(StrEnum):
    UNENROLLED = "unenrolled"
    ENROLLING = "enrolling"
    ENROLLED = "enrolled"
    REENROLLMENT_REQUIRED = "reenrollment_required"


class EnrollmentError(ValueError):
    """Sanitized failure; state indicates whether operator recovery is required."""

    def __init__(self, state: EnrollmentState) -> None:
        self.state = state
        super().__init__(f"Enrollment unavailable ({state.value})")


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _identity_from_response(content: bytes, display_name: str) -> AgentIdentity:
    value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields)
    if not isinstance(value, dict) or set(value) != {
        "protocol_version",
        "device_id",
        "display_name",
        "credential",
        "created_at",
    }:
        raise ValueError
    if type(value["protocol_version"]) is not int or value["protocol_version"] != 1:
        raise ValueError
    if not all(
        isinstance(value[name], str)
        for name in ("device_id", "display_name", "credential", "created_at")
    ):
        raise ValueError
    if value["display_name"] != display_name or not _TIMESTAMP.fullmatch(
        value["created_at"]
    ):
        raise ValueError
    device_id = UUID(value["device_id"])
    if str(device_id) != value["device_id"]:
        raise ValueError
    return AgentIdentity(
        device_id=device_id,
        credential=value["credential"],
        created_at=datetime.fromisoformat(value["created_at"]),
    )


class EnrollmentClient:
    """A single explicit enrollment action with no background retry or heartbeat.

    After an uncertain send, this instance cannot enroll again. An operator must
    reconcile the server-side outcome and supply a fresh bootstrap when needed.
    The command is opt-in on every invocation; ordinary restarts never call it.
    """

    def __init__(
        self,
        settings: AgentSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._store = IdentityStore(settings.identity_path)
        self._transport = transport
        self.state = EnrollmentState.UNENROLLED

    async def ensure_enrolled(self) -> AgentIdentity:
        if self.state in {
            EnrollmentState.ENROLLING,
            EnrollmentState.REENROLLMENT_REQUIRED,
        }:
            raise EnrollmentError(self.state)
        try:
            identity = self._store.load()
        except IdentityError:
            self.state = EnrollmentState.REENROLLMENT_REQUIRED
            raise EnrollmentError(self.state) from None
        if identity is not None:
            self.state = EnrollmentState.ENROLLED
            return identity
        settings = self._settings
        if (
            settings.server_url is None
            or settings.bootstrap_secret is None
            or settings.display_name is None
        ):
            self.state = EnrollmentState.UNENROLLED
            raise EnrollmentError(self.state)

        self.state = EnrollmentState.ENROLLING
        try:
            # No transport-level retries, redirects, environment proxies or netrc.
            # Only this layer decides whether the POST is safe to retry.
            async with httpx.AsyncClient(
                verify=True,
                trust_env=False,
                follow_redirects=False,
                timeout=_TIMEOUT,
                transport=self._transport,
            ) as client:
                for attempt in range(len(_RETRY_DELAYS) + 1):
                    try:
                        async with asyncio.timeout(_ATTEMPT_SECONDS):
                            async with client.stream(
                                "POST",
                                settings.server_url + "/api/v1/enrollment",
                                json={
                                    "protocol_version": 1,
                                    "bootstrap_secret": settings.bootstrap_secret,
                                    "display_name": settings.display_name,
                                    "agent_version": "0.1.0",
                                },
                            ) as response:
                                if response.status_code != 201:
                                    raise ValueError
                                if (
                                    response.headers.get("content-type", "")
                                    .split(";")[0]
                                    .strip()
                                    .lower()
                                    != "application/json"
                                ):
                                    raise ValueError
                                content = bytearray()
                                async for chunk in response.aiter_bytes():
                                    content.extend(chunk)
                                    if len(content) > _MAX_RESPONSE_BYTES:
                                        raise ValueError
                                identity = _identity_from_response(
                                    bytes(content), settings.display_name
                                )
                        # No await between accepting the identity and atomic save.
                        self._store.save(identity)
                        self.state = EnrollmentState.ENROLLED
                        return identity
                    except (httpx.ConnectError, httpx.ConnectTimeout):
                        if attempt == len(_RETRY_DELAYS):
                            self.state = EnrollmentState.UNENROLLED
                            raise EnrollmentError(self.state) from None
                        await asyncio.sleep(_RETRY_DELAYS[attempt])
        except EnrollmentError:
            raise
        except asyncio.CancelledError:
            self.state = EnrollmentState.REENROLLMENT_REQUIRED
            raise
        except (
            httpx.HTTPError,
            TimeoutError,
            ValueError,
            TypeError,
            OverflowError,
            RecursionError,
        ):
            self.state = EnrollmentState.REENROLLMENT_REQUIRED
            raise EnrollmentError(self.state) from None
        raise AssertionError("Enrollment attempts exhausted without a result")


__all__ = ["EnrollmentClient", "EnrollmentError", "EnrollmentState"]
