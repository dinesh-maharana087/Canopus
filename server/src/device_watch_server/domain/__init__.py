"""Stage 2 domain contracts without persistence or transport behavior."""

from device_watch_server.domain.contracts import (
    CURRENT_PROTOCOL_VERSION,
    BootstrapState,
    ConnectivityState,
    CredentialState,
    DeviceIdentity,
    DeviceLifecycle,
    DeviceSummary,
    HeartbeatAccepted,
    HeartbeatRequest,
    HeartbeatResponse,
    HeartbeatStatus,
    PersistenceBoundary,
)

__all__ = [
    "CURRENT_PROTOCOL_VERSION",
    "BootstrapState",
    "ConnectivityState",
    "CredentialState",
    "DeviceIdentity",
    "DeviceLifecycle",
    "DeviceSummary",
    "HeartbeatAccepted",
    "HeartbeatRequest",
    "HeartbeatResponse",
    "HeartbeatStatus",
    "PersistenceBoundary",
]
