"""Step 08 enrollment contract, retry traces, and protected storage handoff."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from device_watch_agent.config import AgentSettings, AgentSettingsError, load_settings
from device_watch_agent.identity import IdentityError, IdentityStore
from device_watch_agent.transport.enrollment import (
    EnrollmentClient,
    EnrollmentError,
    EnrollmentState,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        pytest.fail(message, pytrace=False)


def bootstrap() -> str:
    return "dwb_v1_" + base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")


def credential() -> str:
    return "dwc_v1_" + "1" * 32 + "_" + bootstrap()[7:]


def response_body() -> dict[str, object]:
    return {
        "protocol_version": 1,
        "device_id": "12345678-1234-4234-8234-123456789abc",
        "display_name": "Lab device",
        "credential": credential(),
        "created_at": "2026-09-14T12:00:00Z",
    }


@pytest.fixture
def settings(tmp_path: Path) -> AgentSettings:
    return load_settings(
        {
            "DEVICE_WATCH_AGENT_MODE": "service",
            "DEVICE_WATCH_AGENT_IDENTITY_PATH": str(
                tmp_path / "private" / "identity.json"
            ),
            "DEVICE_WATCH_AGENT_SERVER_URL": "https://portal.example/",
            "DEVICE_WATCH_AGENT_BOOTSTRAP_SECRET": bootstrap(),
            "DEVICE_WATCH_AGENT_DISPLAY_NAME": " Lab device ",
        }
    )


async def test_enrolls_with_exact_contract_and_restart_does_not_send(
    settings: AgentSettings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    requests: list[httpx.Request] = []

    def server(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        require(
            json.loads(request.content)
            == {
                "protocol_version": 1,
                "bootstrap_secret": bootstrap(),
                "display_name": "Lab device",
                "agent_version": "0.1.0",
            },
            "Enrollment request did not match the approved wire contract",
        )
        assert request.method == "POST"
        assert str(request.url) == "https://portal.example/api/v1/enrollment"
        assert request.headers["content-type"] == "application/json"
        assert "authorization" not in request.headers
        assert request.extensions["timeout"] == {
            "connect": 5.0,
            "read": 10.0,
            "write": 10.0,
            "pool": 5.0,
        }
        return httpx.Response(201, json=response_body())

    client = EnrollmentClient(settings, transport=httpx.MockTransport(server))
    identity = await client.ensure_enrolled()
    assert client.state is EnrollmentState.ENROLLED
    require(identity.credential == credential(), "Issued credential was not retained")
    require(
        IdentityStore(settings.identity_path).load() == identity, "Identity not saved"
    )
    restarted = EnrollmentClient(
        AgentSettings(mode="service", identity_path=settings.identity_path),
        transport=httpx.MockTransport(server),
    )
    require(await restarted.ensure_enrolled() == identity, "Restart lost identity")
    assert len(requests) == 1
    require(
        bootstrap() not in caplog.text + repr(settings) + repr(client)
        and credential() not in caplog.text + repr(identity),
        "Enrollment exposed secret material",
    )


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ConnectTimeout])
async def test_only_connection_failures_retry_then_persist(
    settings: AgentSettings, error_type: type[httpx.RequestError]
) -> None:
    attempts = 0

    def server(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise error_type("synthetic connection failure", request=request)
        return httpx.Response(201, json=response_body())

    client = EnrollmentClient(settings, transport=httpx.MockTransport(server))
    await client.ensure_enrolled()
    assert attempts == 3
    assert client.state is EnrollmentState.ENROLLED


async def test_connection_retry_exhaustion_is_bounded(settings: AgentSettings) -> None:
    attempts = 0

    def server(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectTimeout("synthetic timeout", request=request)

    client = EnrollmentClient(settings, transport=httpx.MockTransport(server))
    with pytest.raises(EnrollmentError):
        await client.ensure_enrolled()
    assert attempts == 3
    assert client.state is EnrollmentState.UNENROLLED
    assert not settings.identity_path.exists()


@pytest.mark.parametrize(
    "error_type",
    [
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.ReadError,
        httpx.WriteError,
        httpx.RemoteProtocolError,
    ],
)
async def test_uncertain_request_never_replays_and_errors_are_sanitized(
    settings: AgentSettings,
    error_type: type[httpx.RequestError],
    caplog: pytest.LogCaptureFixture,
) -> None:
    attempts = 0
    caplog.set_level(logging.DEBUG)

    def server(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise error_type(bootstrap() + credential(), request=request)

    client = EnrollmentClient(settings, transport=httpx.MockTransport(server))
    for _ in range(2):
        with pytest.raises(EnrollmentError) as caught:
            await client.ensure_enrolled()
        require(
            bootstrap() not in str(caught.value) + caplog.text
            and credential() not in str(caught.value) + caplog.text,
            "Transport exception exposed secret material",
        )
    assert attempts == 1
    assert client.state is EnrollmentState.REENROLLMENT_REQUIRED
    assert not settings.identity_path.exists()


@pytest.mark.parametrize("status", [200, 301, 307, 400, 401, 403, 429, 500, 503])
async def test_non_201_never_retries_or_follows_redirect(
    settings: AgentSettings, status: int
) -> None:
    attempts = 0

    def server(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            status,
            headers={"location": "https://other.example/"},
            text=bootstrap() + credential(),
        )

    client = EnrollmentClient(settings, transport=httpx.MockTransport(server))
    with pytest.raises(EnrollmentError):
        await client.ensure_enrolled()
    assert attempts == 1
    assert client.state is EnrollmentState.REENROLLMENT_REQUIRED
    assert not settings.identity_path.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol_version", True),
        ("protocol_version", 1.0),
        ("protocol_version", 2),
        ("device_id", "invalid"),
        ("device_id", "12345678-1234-1234-8234-123456789abc"),
        ("credential", "invalid"),
        ("created_at", "2026-09-14T12:00:00"),
        ("created_at", "invalid"),
        ("created_at", "2026-09-14T12:00:00+00:60"),
        ("display_name", ""),
        ("display_name", "Other device"),
        ("unexpected", "extra"),
    ],
    ids=[
        "boolean-version",
        "float-version",
        "wrong-version",
        "bad-uuid",
        "non-v4",
        "bad-credential",
        "naive-time",
        "bad-time",
        "bad-offset",
        "blank-name",
        "different-name",
        "extra-field",
    ],
)
async def test_malformed_response_never_reaches_storage(
    settings: AgentSettings, field: str, value: object
) -> None:
    payload = response_body()
    payload[field] = value
    client = EnrollmentClient(
        settings,
        transport=httpx.MockTransport(lambda _: httpx.Response(201, json=payload)),
    )
    with pytest.raises(EnrollmentError):
        await client.ensure_enrolled()
    assert client.state is EnrollmentState.REENROLLMENT_REQUIRED
    assert not settings.identity_path.exists()


@pytest.mark.parametrize("content", [b"{", b"[]", b"{}", b"\xff"])
async def test_invalid_json_response_fails_closed(
    settings: AgentSettings, content: bytes
) -> None:
    client = EnrollmentClient(
        settings,
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                201, content=content, headers={"content-type": "application/json"}
            )
        ),
    )
    with pytest.raises(EnrollmentError):
        await client.ensure_enrolled()
    assert not settings.identity_path.exists()


async def test_storage_failure_after_201_does_not_replay(
    settings: AgentSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts = 0

    def server(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(201, json=response_body())

    def fail_save(*args: object) -> None:
        raise IdentityError()

    monkeypatch.setattr(IdentityStore, "save", fail_save)
    client = EnrollmentClient(settings, transport=httpx.MockTransport(server))
    for _ in range(2):
        with pytest.raises(EnrollmentError):
            await client.ensure_enrolled()
    assert attempts == 1
    assert client.state is EnrollmentState.REENROLLMENT_REQUIRED


async def test_malformed_existing_storage_prevents_any_request(
    settings: AgentSettings,
) -> None:
    settings.identity_path.parent.mkdir()
    settings.identity_path.write_text("malformed")

    def unexpected(_: httpx.Request) -> httpx.Response:
        pytest.fail("Enrollment was attempted with unusable existing storage")

    client = EnrollmentClient(settings, transport=httpx.MockTransport(unexpected))
    with pytest.raises(EnrollmentError):
        await client.ensure_enrolled()
    assert client.state is EnrollmentState.REENROLLMENT_REQUIRED


async def test_cancellation_closes_transport_without_replay(
    settings: AgentSettings,
) -> None:
    entered = asyncio.Event()
    closed = False

    class WaitingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            entered.set()
            await asyncio.Event().wait()
            raise AssertionError("Unreachable")

        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    client = EnrollmentClient(settings, transport=WaitingTransport())
    task = asyncio.create_task(client.ensure_enrolled())
    await asyncio.wait_for(entered.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed
    assert client.state is EnrollmentState.REENROLLMENT_REQUIRED
    assert not settings.identity_path.exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://portal.example",
        "https://user:password@portal.example",
        "https://portal.example/?secret=x",
        "https://portal.example/#secret",
        "https://portal.example/path",
        "https://",
        "https://portal.example:bad",
        " https://portal.example",
        "https://portal.example\n",
    ],
)
def test_unsafe_server_url_rejected_without_echo(url: str) -> None:
    with pytest.raises(AgentSettingsError) as caught:
        load_settings(
            {"DEVICE_WATCH_AGENT_MODE": "service", "DEVICE_WATCH_AGENT_SERVER_URL": url}
        )
    require(url not in str(caught.value), "Invalid URL echoed")


def test_no_enrollment_defaults_and_hidden_bootstrap(settings: AgentSettings) -> None:
    defaults = load_settings({"DEVICE_WATCH_AGENT_MODE": "service"})
    assert defaults.server_url is None
    assert defaults.bootstrap_secret is None
    assert defaults.display_name is None
    require(bootstrap() not in repr(settings), "Settings repr exposed bootstrap")


@pytest.mark.parametrize("field", ["server_url", "bootstrap_secret", "display_name"])
async def test_missing_input_cannot_send(settings: AgentSettings, field: str) -> None:
    from dataclasses import replace

    settings = replace(settings, **{field: None})

    def unexpected(_: httpx.Request) -> httpx.Response:
        pytest.fail("Enrollment sent without required explicit inputs")

    client = EnrollmentClient(settings, transport=httpx.MockTransport(unexpected))
    with pytest.raises(EnrollmentError):
        await client.ensure_enrolled()
    assert client.state is EnrollmentState.UNENROLLED


@pytest.mark.parametrize("transform", [lambda _: "invalid", lambda value: value + "="])
def test_bad_bootstrap_is_rejected_without_echo(
    transform: Callable[[str], str],
) -> None:
    value = transform(bootstrap())
    with pytest.raises(AgentSettingsError) as caught:
        load_settings(
            {
                "DEVICE_WATCH_AGENT_MODE": "service",
                "DEVICE_WATCH_AGENT_BOOTSTRAP_SECRET": value,
            }
        )
    require(value not in str(caught.value), "Bootstrap input echoed")


async def test_total_attempt_timeout_does_not_replay(
    settings: AgentSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from device_watch_agent.transport import enrollment

    attempts = 0

    async def server(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        await asyncio.Event().wait()
        raise AssertionError("Unreachable")

    monkeypatch.setattr(enrollment, "_ATTEMPT_SECONDS", 0.01)
    client = EnrollmentClient(settings, transport=httpx.MockTransport(server))
    with pytest.raises(EnrollmentError):
        await asyncio.wait_for(client.ensure_enrolled(), 1)
    assert attempts == 1
    assert client.state is EnrollmentState.REENROLLMENT_REQUIRED


def test_explicit_command_persists_without_printing_secrets(
    settings: AgentSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    from device_watch_agent import main as entry

    def factory(config: AgentSettings) -> EnrollmentClient:
        return EnrollmentClient(
            config,
            transport=httpx.MockTransport(
                lambda _: httpx.Response(201, json=response_body())
            ),
        )

    monkeypatch.setattr(entry, "load_settings", lambda: settings)
    monkeypatch.setattr(entry, "EnrollmentClient", factory, raising=False)
    assert entry.main(["--enroll"]) == 0
    assert IdentityStore(settings.identity_path).load() is not None
    output = capsys.readouterr()
    require(
        bootstrap() not in output.out + output.err + caplog.text
        and credential() not in output.out + output.err + caplog.text,
        "Command exposed enrollment secrets",
    )


def test_failed_command_exits_nonzero_without_error_body(
    settings: AgentSettings,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from device_watch_agent import main as entry

    def factory(config: AgentSettings) -> EnrollmentClient:
        return EnrollmentClient(
            config,
            transport=httpx.MockTransport(
                lambda _: httpx.Response(500, text=bootstrap() + credential())
            ),
        )

    monkeypatch.setattr(entry, "load_settings", lambda: settings)
    monkeypatch.setattr(entry, "EnrollmentClient", factory, raising=False)
    assert entry.main(["--enroll"]) == 1
    require(
        bootstrap() not in caplog.text and credential() not in caplog.text,
        "Command logged a secret-bearing error body",
    )


async def test_normal_service_start_does_not_replay_enrollment(
    settings: AgentSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from device_watch_agent import main as entry

    def forbidden(*args: object, **kwargs: object) -> EnrollmentClient:
        pytest.fail("Ordinary service startup must not initiate enrollment")

    def stop_immediately(stop: asyncio.Event, loop: asyncio.AbstractEventLoop) -> None:
        stop.set()

    monkeypatch.setattr(entry, "load_settings", lambda: settings)
    monkeypatch.setattr(entry, "EnrollmentClient", forbidden, raising=False)
    monkeypatch.setattr(entry, "_install_signal_handlers", stop_immediately)
    await asyncio.wait_for(entry._run(), 1)


async def test_stop_signal_cancels_enrollment_before_returning(
    settings: AgentSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from device_watch_agent import main as entry

    stopped: asyncio.Event | None = None
    closed = False

    class SignalTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            assert stopped is not None
            stopped.set()
            await asyncio.Event().wait()
            raise AssertionError("Unreachable")

        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    def capture_stop(stop: asyncio.Event, loop: asyncio.AbstractEventLoop) -> None:
        nonlocal stopped
        stopped = stop

    def factory(config: AgentSettings) -> EnrollmentClient:
        return EnrollmentClient(config, transport=SignalTransport())

    monkeypatch.setattr(entry, "load_settings", lambda: settings)
    monkeypatch.setattr(entry, "EnrollmentClient", factory, raising=False)
    monkeypatch.setattr(entry, "_install_signal_handlers", capture_stop)
    await asyncio.wait_for(entry._run(enroll=True), 1)
    assert closed
    assert not settings.identity_path.exists()
