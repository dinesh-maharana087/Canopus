"""Shared SQLAlchemy declarative metadata for server migrations."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Empty declarative metadata base for the schema-empty Stage 1 baseline."""


__all__ = ["Base"]
