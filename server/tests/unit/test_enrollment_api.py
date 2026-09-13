"""HTTP enrollment contract; database transaction guarantees belong to Step 05."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.engine import Engine

import device_watch_server.app as app_module
from device_watch_server.auth.credentials import CredentialValue
from device_watch_server.core.config import Environment, Settings
from device_watch_server.domain.contracts import DeviceIdentity
from device_watch_server.enrollment.bootstrap import generate_bootstrap_value
from device_watch_server.enrollment.transaction import EnrollmentError, EnrollmentResult

NOW = datetime(2026, 9, 13, 12, tzinfo=UTC)
PATH = "/api/v1/enrollment"
FAILURE = {"detail": "Enrollment failed"}
PEPPER = "api-fixture-pepper-minimum-32-bytes-not-for-deployment"


def require(condition: bool, message: str) -> None:
    if not condition:
        pytest.fail(message, pytrace=False)


def settings() -> Settings:
    return Settings(
        device_watch_env=Environment.TEST,
        database_url=SecretStr("mysql+pymysql://db/device_watch"),
        device_watch_bootstrap_hmac_pepper=SecretStr(PEPPER),
    )


def body() -> dict[str, object]:
    return {
        "protocol_version": 1,
        "bootstrap_secret": generate_bootstrap_value().to_wire(),
        "display_name": "  workstation  ",
        "agent_version": "  0.2.0  ",
    }


@pytest.fixture
def app() -> FastAPI:
    return app_module.create_app(settings(), database_check=lambda: None)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    def forbidden(*args: object, **kwargs: object) -> EnrollmentResult:
        pytest.fail("Invalid input reached the enrollment transaction", pytrace=False)

    app.state.enrollment_service = forbidden
    with TestClient(app) as value:
        yield value


def test_success_contract_then_service_rejection_never_replays_credential(
    app: FastAPI, client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    request_body = body()
    # A transient value suffices for an HTTP mapping test; hashing is tested separately.
    credential = CredentialValue(key_id=uuid4().hex, secret=bytes(range(32)))
    result = EnrollmentResult(
        device=DeviceIdentity(
            device_id=uuid4(), display_name="workstation", created_at=NOW
        ),
        credential=credential,
    )
    delivered = False

    def enroll(bootstrap_secret: str, *, display_name: str) -> EnrollmentResult:
        nonlocal delivered
        require(
            bootstrap_secret == request_body["bootstrap_secret"],
            "Bootstrap wiring differs",
        )
        require(display_name == "workstation", "Display name was not normalized")
        if delivered:
            raise EnrollmentError()
        delivered = True
        return result

    app.state.enrollment_service = enroll
    response = client.post(
        PATH, json=request_body, headers={"Authorization": "Bearer fixture-header"}
    )
    replay = client.post(PATH, json=request_body)
    require(response.status_code == 201, "Enrollment did not return 201")
    require(
        response.json()
        == {
            "protocol_version": 1,
            "device_id": str(result.device.device_id),
            "display_name": "workstation",
            "credential": credential.to_wire(),
            "created_at": "2026-09-13T12:00:00Z",
        },
        "Success response differs from the five-field protocol",
    )
    require(
        replay.status_code == 400 and replay.json() == FAILURE,
        "Replay failure leaked details",
    )
    require(
        response.headers.get("cache-control") == "no-store",
        "Credential response can be cached",
    )
    require(
        replay.headers.get("cache-control") == "no-store",
        "Failure response can be cached",
    )
    logs = capsys.readouterr().out
    require(
        all(
            secret not in logs
            for secret in (
                str(request_body["bootstrap_secret"]),
                credential.to_wire(),
                PEPPER,
                "fixture-header",
            )
        ),
        "Request or credential material appeared in server logs",
    )
    records = [json.loads(line) for line in logs.splitlines()]
    assert [item["normalized_path"] for item in records] == [PATH, PATH]
    assert [item["status"] for item in records] == [201, 400]


@pytest.mark.parametrize(
    "field", ["protocol_version", "bootstrap_secret", "display_name", "agent_version"]
)
def test_every_request_field_is_required(client: TestClient, field: str) -> None:
    value = body()
    del value[field]
    response = client.post(PATH, json=value)
    require(
        response.status_code == 400 and response.json() == FAILURE,
        "Missing-field error is not generic",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protocol_version", True),
        ("protocol_version", 1.0),
        ("protocol_version", "1"),
        ("protocol_version", 0),
        ("protocol_version", 2),
        ("display_name", ""),
        ("display_name", " \t "),
        ("display_name", "x" * 121),
        ("display_name", 12),
        ("display_name", {"secret": "nested-private-input"}),
        ("agent_version", ""),
        ("agent_version", " \t "),
        ("agent_version", "v" * 65),
        ("agent_version", 2),
        ("agent_version", None),
        ("bootstrap_secret", ""),
        ("bootstrap_secret", "bad-secret"),
        ("bootstrap_secret", "dwb_v1_" + "A" * 42 + "B"),
        ("bootstrap_secret", 50),
        ("bootstrap_secret", None),
        ("unexpected", "private-extra-input"),
    ],
)
def test_invalid_fields_have_one_safe_error(
    client: TestClient, field: str, value: object, capsys: pytest.CaptureFixture[str]
) -> None:
    request_body = body() | {field: value}
    response = client.post(PATH, json=request_body)
    require(
        response.status_code == 400 and response.json() == FAILURE,
        "Validation response exposed input details",
    )
    logs = capsys.readouterr().out
    require(
        str(request_body["bootstrap_secret"]) not in logs
        if request_body["bootstrap_secret"]
        else True,
        "Bootstrap input appeared in logs",
    )
    require(
        "nested-private-input" not in logs and "private-extra-input" not in logs,
        "Rejected body appeared in logs",
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"null",
        b"[]",
        b'"private-body-input"',
        b"123",
        b'{"bootstrap_secret":"private-body-input",',
        b"\xff",
    ],
)
def test_malformed_json_or_wrong_body_shape_is_safe(
    client: TestClient, raw: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    response = client.post(
        PATH, content=raw, headers={"Content-Type": "application/json"}
    )
    require(
        response.status_code == 400 and response.json() == FAILURE,
        "Malformed-body error is not generic",
    )
    require(
        "private-body-input" not in capsys.readouterr().out,
        "Malformed body appeared in logs",
    )


def test_unexpected_service_failure_is_generic_without_exception_logs(
    app: FastAPI, client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    request_body = body()

    def fail(*args: object, **kwargs: object) -> EnrollmentResult:
        raise RuntimeError(str(request_body["bootstrap_secret"]) + PEPPER)

    app.state.enrollment_service = fail
    response = client.post(PATH, json=request_body)
    require(
        response.status_code == 500 and response.json() == FAILURE,
        "Unexpected error is not sanitized",
    )
    logs = capsys.readouterr().out
    require(
        str(request_body["bootstrap_secret"]) not in logs and PEPPER not in logs,
        "Exception details appeared in logs",
    )


def test_factory_shares_engine_for_readiness_and_enrollment_and_disposes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Mock(spec_set=Engine)
    created: list[Engine] = []
    checked: list[Engine] = []

    def create_engine(configuration: Settings) -> Engine:
        created.append(engine)
        return cast(Engine, engine)

    def enroll(
        owned: Engine,
        bootstrap_secret: str,
        configured_pepper: str | None,
        *,
        display_name: str,
    ) -> EnrollmentResult:
        require(
            owned is engine and configured_pepper == PEPPER,
            "Factory dependencies differ",
        )
        return EnrollmentResult(
            device=DeviceIdentity(
                device_id=uuid4(), display_name=display_name, created_at=NOW
            ),
            credential=CredentialValue(key_id=uuid4().hex, secret=bytes(range(32))),
        )

    monkeypatch.setattr(app_module, "create_database_engine", create_engine)
    monkeypatch.setattr(app_module, "check_database", checked.append)
    monkeypatch.setattr(app_module, "enroll_device", enroll, raising=False)
    application = app_module.create_app(settings())
    with TestClient(application) as connection:
        assert connection.get("/api/v1/health/live").status_code == 200
        assert checked == []
        assert connection.get("/api/v1/health/ready").status_code == 200
        response = connection.post(PATH, json=body())
        require(response.status_code == 201, "Factory enrollment service was not wired")
    assert created == [engine]
    assert checked == [engine]
    assert engine.dispose.call_count == 1


def test_openapi_describes_required_request_and_only_approved_success_fields(
    app: FastAPI,
) -> None:
    schema = app.openapi()
    operation = schema["paths"].get(PATH, {}).get("post")
    assert operation is not None
    assert "201" in operation["responses"]
    assert "400" in operation["responses"]
    assert "422" not in operation["responses"]
    definitions = schema["components"]["schemas"]
    request = definitions["EnrollmentRequest"]
    assert set(request["required"]) == {
        "protocol_version",
        "bootstrap_secret",
        "display_name",
        "agent_version",
    }
    assert request["additionalProperties"] is False
    assert set(definitions["EnrollmentResponse"]["properties"]) == {
        "protocol_version",
        "device_id",
        "display_name",
        "credential",
        "created_at",
    }


def test_response_validation_failure_does_not_expose_transient_credential(
    app: FastAPI, client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    private_output = "invalid-private-response-value"

    def invalid_output(*args: object, **kwargs: object) -> EnrollmentResult:
        invalid_credential = Mock(spec_set=CredentialValue)
        invalid_credential.to_wire.return_value = private_output
        return EnrollmentResult(
            device=DeviceIdentity(
                device_id=uuid4(), display_name="workstation", created_at=NOW
            ),
            credential=cast(CredentialValue, invalid_credential),
        )

    app.state.enrollment_service = invalid_output
    response = client.post(PATH, json=body())
    require(
        response.status_code == 500 and response.json() == FAILURE,
        "Response validation exposed private output",
    )
    require(
        private_output not in capsys.readouterr().out,
        "Response validation appeared in logs",
    )


def test_request_and_response_models_hide_secret_representations() -> None:
    from device_watch_server.api.enrollment_schemas import (
        EnrollmentRequest,
        EnrollmentResponse,
    )

    request_body = body()
    request = EnrollmentRequest.model_validate(request_body)
    credential = CredentialValue(key_id=uuid4().hex, secret=bytes(range(32)))
    response = EnrollmentResponse(
        device_id=uuid4(),
        display_name="workstation",
        credential=credential.to_wire(),
        created_at=NOW,
    )
    require(
        str(request_body["bootstrap_secret"])
        not in repr(request) + str(request) + request.model_dump_json(),
        "Request model representation reveals bootstrap material",
    )
    require(
        credential.to_wire() not in repr(response) + str(response),
        "Response model representation reveals credential material",
    )


def test_non_json_body_is_rejected_without_echo(client: TestClient) -> None:
    response = client.post(
        PATH,
        content=b"bootstrap_secret=private-form-input",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    require(
        response.status_code == 400 and response.json() == FAILURE,
        "Non-JSON input is not safe",
    )


def test_maximum_valid_text_lengths_are_accepted(
    app: FastAPI, client: TestClient
) -> None:
    def enroll(bootstrap_secret: str, *, display_name: str) -> EnrollmentResult:
        return EnrollmentResult(
            device=DeviceIdentity(
                device_id=uuid4(), display_name=display_name, created_at=NOW
            ),
            credential=CredentialValue(key_id=uuid4().hex, secret=bytes(range(32))),
        )

    app.state.enrollment_service = enroll
    response = client.post(
        PATH, json=body() | {"display_name": "d" * 120, "agent_version": "v" * 64}
    )
    require(response.status_code == 201, "Valid maximum field lengths were rejected")
