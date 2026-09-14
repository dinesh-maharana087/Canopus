"""Descriptor-relative POSIX storage under a private, agent-owned directory."""

from __future__ import annotations

import os
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

assert sys.platform != "win32", "POSIX identity adapter requires POSIX"


def _unsafe() -> OSError:
    return OSError("Unsafe identity storage")


def _file_check(fd: int) -> None:
    info = os.fstat(fd)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise _unsafe()


class PosixDirectory:
    def __init__(self, fd: int) -> None:
        self.fd = fd

    def read(self, name: str, limit: int) -> bytes | None:
        try:
            fd = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd
            )
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as stream:
            _file_check(stream.fileno())
            return stream.read(limit)

    def create(self, name: str) -> int:
        fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=self.fd,
        )
        try:
            os.fchmod(fd, 0o600)
            _file_check(fd)
        except OSError:
            os.close(fd)
            os.unlink(name, dir_fd=self.fd)
            raise
        return fd

    def replace(self, source: str, target: str) -> None:
        os.replace(source, target, src_dir_fd=self.fd, dst_dir_fd=self.fd)

    def unlink(self, name: str) -> None:
        try:
            os.unlink(name, dir_fd=self.fd)
        except FileNotFoundError:
            pass

    def sync(self) -> None:
        os.fsync(self.fd)


@contextmanager
def open_directory(path: Path, *, create: bool = False) -> Iterator[PosixDirectory]:
    """Reject links and untrusted ancestors, then anchor all file operations by FD."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        parts = path.parts[1:]
        for index, part in enumerate(parts):
            parent = os.fstat(fd)
            # A root-owned sticky /tmp is safe to traverse. The final private
            # directory is checked separately; no group/other write is allowed there.
            sticky_root = parent.st_uid == 0 and bool(parent.st_mode & stat.S_ISVTX)
            if parent.st_uid not in (0, os.geteuid()) or (
                parent.st_mode & 0o022 and not sticky_root
            ):
                raise _unsafe()
            try:
                child = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create or index != len(parts) - 1:
                    raise
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise _unsafe()
        yield PosixDirectory(fd)
    finally:
        os.close(fd)
