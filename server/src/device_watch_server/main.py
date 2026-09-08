"""Production ASGI entry point for the Device Watch server."""

from device_watch_server.app import create_app

app = create_app()

__all__ = ["app"]
