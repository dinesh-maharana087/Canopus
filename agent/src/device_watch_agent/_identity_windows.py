"""Protected Windows files, with native owner/DACL and handle validation.

This adapter requires a local drive path on a filesystem supporting Windows
security descriptors. The protected directory and its files have one explicit
full-control ACE for the process user, a matching owner, and a protected DACL.
Privileged administrators and processes running as that same user are outside
the file-permission boundary. Windows chmod is deliberately not used.
"""

from __future__ import annotations

import ctypes as ct
import os
from collections.abc import Iterator
from contextlib import contextmanager
from ctypes import wintypes as wt
from pathlib import Path
from typing import Any

_MESSAGE = "Identity storage access failed"
_READ_CONTROL = 0x00020000
_DIRECTORY = 0x10
_REPARSE = 0x400
_FULL_CONTROL = 0x001F01FF
_INVALID_HANDLE = ct.c_void_p(-1).value


class _SecurityAttributes(ct.Structure):
    _fields_ = [
        ("length", wt.DWORD),
        ("descriptor", ct.c_void_p),
        ("inherit", wt.BOOL),
    ]


class _FileInformation(ct.Structure):
    _fields_ = [
        ("attributes", wt.DWORD),
        ("creation", wt.FILETIME),
        ("access", wt.FILETIME),
        ("write", wt.FILETIME),
        ("volume", wt.DWORD),
        ("size_high", wt.DWORD),
        ("size_low", wt.DWORD),
        ("links", wt.DWORD),
        ("index_high", wt.DWORD),
        ("index_low", wt.DWORD),
    ]


class _Acl(ct.Structure):
    _fields_ = [
        ("revision", wt.BYTE),
        ("reserved", wt.BYTE),
        ("size", wt.WORD),
        ("count", wt.WORD),
        ("reserved2", wt.WORD),
    ]


class _Ace(ct.Structure):
    _fields_ = [
        ("kind", wt.BYTE),
        ("flags", wt.BYTE),
        ("size", wt.WORD),
        ("mask", wt.DWORD),
    ]


def _bind(library: Any, name: str, result: Any, arguments: list[Any]) -> None:
    function = getattr(library, name)
    function.restype = result
    function.argtypes = arguments


class _WindowsApi:
    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError(_MESSAGE)
        self.kernel = ct.WinDLL("kernel32", use_last_error=True)
        self.security = ct.WinDLL("advapi32", use_last_error=True)
        pointer = ct.c_void_p
        for name, result, arguments in (
            ("GetCurrentProcess", wt.HANDLE, []),
            ("CloseHandle", wt.BOOL, [wt.HANDLE]),
            ("LocalFree", pointer, [pointer]),
            ("CreateDirectoryW", wt.BOOL, [wt.LPCWSTR, pointer]),
            (
                "CreateFileW",
                wt.HANDLE,
                [wt.LPCWSTR, wt.DWORD, wt.DWORD, pointer, wt.DWORD, wt.DWORD, pointer],
            ),
            ("GetFileInformationByHandle", wt.BOOL, [wt.HANDLE, pointer]),
            ("GetFileType", wt.DWORD, [wt.HANDLE]),
            ("MoveFileExW", wt.BOOL, [wt.LPCWSTR, wt.LPCWSTR, wt.DWORD]),
            ("DeleteFileW", wt.BOOL, [wt.LPCWSTR]),
        ):
            _bind(self.kernel, name, result, arguments)
        for name, result, arguments in (
            ("OpenProcessToken", wt.BOOL, [wt.HANDLE, wt.DWORD, pointer]),
            (
                "GetTokenInformation",
                wt.BOOL,
                [wt.HANDLE, wt.DWORD, pointer, wt.DWORD, pointer],
            ),
            ("ConvertSidToStringSidW", wt.BOOL, [pointer, pointer]),
            (
                "ConvertStringSecurityDescriptorToSecurityDescriptorW",
                wt.BOOL,
                [wt.LPCWSTR, wt.DWORD, pointer, pointer],
            ),
            (
                "GetSecurityInfo",
                wt.DWORD,
                [
                    wt.HANDLE,
                    wt.DWORD,
                    wt.DWORD,
                    pointer,
                    pointer,
                    pointer,
                    pointer,
                    pointer,
                ],
            ),
            ("GetSecurityDescriptorControl", wt.BOOL, [pointer, pointer, pointer]),
            ("EqualSid", wt.BOOL, [pointer, pointer]),
            ("GetAce", wt.BOOL, [pointer, wt.DWORD, pointer]),
        ):
            _bind(self.security, name, result, arguments)
        token = wt.HANDLE()
        if not self.security.OpenProcessToken(
            self.kernel.GetCurrentProcess(), 0x0008, ct.byref(token)
        ):
            raise OSError(_MESSAGE)
        try:
            needed = wt.DWORD()
            self.security.GetTokenInformation(token, 1, None, 0, ct.byref(needed))
            if not needed.value:
                raise OSError(_MESSAGE)
            self._token = ct.create_string_buffer(needed.value)
            if not self.security.GetTokenInformation(
                token, 1, self._token, needed.value, ct.byref(needed)
            ):
                raise OSError(_MESSAGE)
        finally:
            self.kernel.CloseHandle(token)
        self.sid = ct.cast(self._token, ct.POINTER(pointer)).contents
        text = wt.LPWSTR()
        if not self.security.ConvertSidToStringSidW(self.sid, ct.byref(text)):
            raise OSError(_MESSAGE)
        try:
            descriptor_text = f"O:{text.value}D:P(A;;FA;;;{text.value})"
        finally:
            self.kernel.LocalFree(text)
        self.descriptor = pointer()
        if not self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            descriptor_text, 1, ct.byref(self.descriptor), None
        ):
            raise OSError(_MESSAGE)
        self.attributes = _SecurityAttributes(
            ct.sizeof(_SecurityAttributes), self.descriptor, False
        )

    def close(self) -> None:
        self.kernel.LocalFree(self.descriptor)

    def open(self, path: Path, *, directory: bool, create: bool = False) -> int:
        # FILE_LIST_DIRECTORY makes share-mode protection effective; a handle
        # requesting metadata alone does not prevent directory rename.
        access = _READ_CONTROL | (0x81 if directory else 0x80000000)
        if create:
            access |= 0x40000000
        handle = self.kernel.CreateFileW(
            str(path),
            access,
            3 if directory else (0 if create else 1),  # Never share DELETE.
            ct.byref(self.attributes) if create else None,
            1 if create else 3,  # CREATE_NEW / OPEN_EXISTING.
            0x00200000 | (0x02000000 if directory else 0),
            None,
        )
        if handle == _INVALID_HANDLE:
            if ct.get_last_error() in (2, 3):
                raise FileNotFoundError(_MESSAGE)
            raise OSError(_MESSAGE)
        return int(handle)

    def validate(self, handle: int, *, directory: bool, private: bool = True) -> None:
        information = _FileInformation()
        if not self.kernel.GetFileInformationByHandle(handle, ct.byref(information)):
            raise OSError(_MESSAGE)
        if (
            information.attributes & _REPARSE
            or bool(information.attributes & _DIRECTORY) != directory
            or self.kernel.GetFileType(handle) != 1
            or (not directory and information.links != 1)
        ):
            raise OSError(_MESSAGE)
        if not private:
            return
        owner = ct.c_void_p()
        dacl = ct.c_void_p()
        descriptor = ct.c_void_p()
        result = self.security.GetSecurityInfo(
            handle,
            1,
            5,
            ct.byref(owner),
            None,
            ct.byref(dacl),
            None,
            ct.byref(descriptor),
        )
        if result:
            raise OSError(_MESSAGE)
        try:
            control = wt.WORD()
            revision = wt.DWORD()
            if (
                not owner.value
                or not dacl.value
                or not self.security.EqualSid(owner, self.sid)
                or not self.security.GetSecurityDescriptorControl(
                    descriptor, ct.byref(control), ct.byref(revision)
                )
                or not control.value & 0x1000  # SE_DACL_PROTECTED.
                or ct.cast(dacl, ct.POINTER(_Acl)).contents.count != 1
            ):
                raise OSError(_MESSAGE)
            ace_pointer = ct.c_void_p()
            if not self.security.GetAce(dacl, 0, ct.byref(ace_pointer)):
                raise OSError(_MESSAGE)
            ace = ct.cast(ace_pointer, ct.POINTER(_Ace)).contents
            if (
                ace.kind != 0  # ACCESS_ALLOWED_ACE_TYPE; reject callback/object ACEs.
                or ace.flags != 0
                or ace.mask != _FULL_CONTROL
                or not ace_pointer.value
                or not self.security.EqualSid(ace_pointer.value + 8, self.sid)
            ):
                raise OSError(_MESSAGE)
        finally:
            self.kernel.LocalFree(descriptor)


class WindowsDirectory:
    def __init__(self, path: Path, api: _WindowsApi) -> None:
        self._path = path
        self._api = api

    def _file(self, name: str) -> Path:
        if (
            not name
            or name in (".", "..")
            or any(character in name for character in '/\\:<>"|?*')
            or name.endswith((".", " "))
        ):
            raise OSError(_MESSAGE)
        return self._path / name

    def read(self, name: str, limit: int) -> bytes | None:
        import msvcrt

        if limit < 0:
            raise OSError(_MESSAGE)
        try:
            handle = self._api.open(self._file(name), directory=False)
        except FileNotFoundError:
            return None
        try:
            self._api.validate(handle, directory=False)
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        except BaseException:
            self._api.kernel.CloseHandle(handle)
            raise
        with os.fdopen(descriptor, "rb") as stream:
            return stream.read(limit)

    def create(self, name: str) -> int:
        import msvcrt

        handle = self._api.open(self._file(name), directory=False, create=True)
        try:
            self._api.validate(handle, directory=False)
            return msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY)
        except BaseException:
            self._api.kernel.CloseHandle(handle)
            raise

    def _check_file(self, name: str, *, missing: bool = False) -> None:
        try:
            handle = self._api.open(self._file(name), directory=False)
        except FileNotFoundError:
            if missing:
                return
            raise
        try:
            self._api.validate(handle, directory=False)
        finally:
            self._api.kernel.CloseHandle(handle)

    def replace(self, source: str, target: str) -> None:
        self._check_file(source)
        self._check_file(target, missing=True)
        if not self._api.kernel.MoveFileExW(
            str(self._file(source)), str(self._file(target)), 0x1 | 0x8
        ):
            raise OSError(_MESSAGE)

    def unlink(self, name: str) -> None:
        self._check_file(name, missing=True)
        if not self._api.kernel.DeleteFileW(
            str(self._file(name))
        ) and ct.get_last_error() not in (2, 3):
            raise OSError(_MESSAGE)

    def sync(self) -> None:
        """File fsync plus WRITE_THROUGH rename is the available durability bound.

        Windows has no portable directory-fsync equivalent. Deletion durability
        across power loss is not promised by this adapter.
        """


@contextmanager
def open_directory(path: Path, *, create: bool = False) -> Iterator[WindowsDirectory]:
    """Pin each ancestor without sharing DELETE; reject reparse-point redirects.

    Existing ancestors need not be private. The final dedicated directory must
    already be private, or be created with its restrictive descriptor atomically.
    Never modify the permissions of an existing object.
    """
    if (
        not path.is_absolute()
        or len(path.drive) != 2
        or path.drive[1] != ":"
        or any(
            part in (".", "..") or part.endswith((".", " ")) for part in path.parts[1:]
        )
        or len(path.parts) < 2
    ):
        raise OSError(_MESSAGE)
    api = _WindowsApi()
    handles: list[int] = []
    try:
        current = Path(path.anchor)
        parts = [current, *[Path(part) for part in path.parts[1:]]]
        for index, part in enumerate(parts):
            if index:
                current /= part
            final = index == len(parts) - 1
            try:
                handle = api.open(current, directory=True)
            except FileNotFoundError:
                if not (create and final):
                    raise
                if (
                    not api.kernel.CreateDirectoryW(
                        str(current), ct.byref(api.attributes)
                    )
                    and ct.get_last_error() != 183
                ):
                    raise OSError(_MESSAGE) from None
                # A concurrent creator must also pass handle/ACL validation.
                handle = api.open(current, directory=True)
            handles.append(handle)
            api.validate(handle, directory=True, private=final)
        yield WindowsDirectory(path, api)
    finally:
        for handle in reversed(handles):
            api.kernel.CloseHandle(handle)
        api.close()
