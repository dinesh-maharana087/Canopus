"""Live Windows checks for protected identity storage objects."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from device_watch_agent._identity_windows import open_directory

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows ACL checks")


def _write(path: Path, name: str, value: bytes) -> None:
    with (
        open_directory(path, create=True) as directory,
        os.fdopen(directory.create(name), "wb") as stream,
    ):
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def _acl(path: Path, *arguments: str) -> None:
    result = subprocess.run(
        ["icacls.exe", str(path), *arguments], capture_output=True, check=False
    )
    if result.returncode:
        pytest.fail("Could not prepare Windows ACL fixture", pytrace=False)


def test_protected_storage_survives_restart_and_replacement(tmp_path: Path) -> None:
    parent = tmp_path / "identity"
    _write(parent, "first.tmp", b"old document")
    with open_directory(parent) as directory:
        directory.replace("first.tmp", "identity.json")
        directory.sync()
    _write(parent, "next.tmp", b"new document")
    with open_directory(parent) as directory:
        assert directory.read("identity.json", 100) == b"old document"
        directory.replace("next.tmp", "identity.json")
    with open_directory(parent) as directory:
        assert directory.read("identity.json", 100) == b"new document"
        directory.unlink("identity.json")
        directory.unlink("identity.json")
        assert directory.read("identity.json", 100) is None
    assert list(parent.iterdir()) == []


def test_missing_directory_is_not_created_by_read(tmp_path: Path) -> None:
    parent = tmp_path / "missing"
    with pytest.raises(FileNotFoundError), open_directory(parent):
        pytest.fail("Missing identity directory was opened")
    assert not parent.exists()


@pytest.mark.parametrize("target", ["directory", "file"])
@pytest.mark.parametrize("unsafe", ["world_read", "inherited"])
def test_unsafe_acl_fails_closed_without_repair(
    tmp_path: Path, target: str, unsafe: str
) -> None:
    parent = tmp_path / "identity"
    _write(parent, "identity.json", b"protected fixture")
    changed = parent if target == "directory" else parent / "identity.json"
    arguments = (
        ("/grant", "*S-1-1-0:(R)") if unsafe == "world_read" else ("/inheritance:e",)
    )
    _acl(changed, *arguments)
    with pytest.raises(OSError), open_directory(parent) as directory:
        directory.read("identity.json", 100)
    # Repeated rejection also proves that opening did not repair the unsafe ACL.
    with pytest.raises(OSError), open_directory(parent) as directory:
        directory.read("identity.json", 100)


def test_hardlink_is_rejected_before_read(tmp_path: Path) -> None:
    parent = tmp_path / "identity"
    _write(parent, "identity.json", b"protected fixture")
    os.link(parent / "identity.json", parent / "other.json")
    with open_directory(parent) as directory, pytest.raises(OSError):
        directory.read("identity.json", 100)


def test_directory_junction_cannot_redirect_storage(tmp_path: Path) -> None:
    target = tmp_path / "actual"
    _write(target, "identity.json", b"protected fixture")
    junction = tmp_path / "redirect"
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        pytest.fail("Could not prepare Windows junction fixture", pytrace=False)
    try:
        with pytest.raises(OSError), open_directory(junction) as directory:
            directory.read("identity.json", 100)
        with (
            pytest.raises(OSError),
            open_directory(junction / "child", create=True),
        ):
            pytest.fail("Ancestor junction was followed")
        assert not (target / "child").exists()
    finally:
        junction.rmdir()


def test_open_directory_cannot_be_renamed_under_operation(tmp_path: Path) -> None:
    parent = tmp_path / "identity"
    with open_directory(parent, create=True), pytest.raises(OSError):
        parent.rename(tmp_path / "moved")


def test_open_directory_pins_ancestors_against_rename(tmp_path: Path) -> None:
    ancestor = tmp_path / "ancestor"
    ancestor.mkdir()
    with open_directory(ancestor / "identity", create=True), pytest.raises(OSError):
        ancestor.rename(tmp_path / "moved")


def test_exclusive_creation_and_bounded_read(tmp_path: Path) -> None:
    parent = tmp_path / "identity"
    _write(parent, "identity.json", b"a" * 200)
    with open_directory(parent) as directory:
        with pytest.raises(OSError):
            directory.create("identity.json")
        assert directory.read("identity.json", 100) == b"a" * 100
