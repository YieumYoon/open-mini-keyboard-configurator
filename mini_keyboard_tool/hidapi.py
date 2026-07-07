from __future__ import annotations

import ctypes
import ctypes.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .protocol import DEFAULT_PRODUCT_ID, DEFAULT_USAGE_PAGE, DEFAULT_VENDOR_ID


class HIDAPIError(RuntimeError):
    pass


class _HidDeviceInfo(ctypes.Structure):
    pass


_HidDeviceInfoPtr = ctypes.POINTER(_HidDeviceInfo)
_HidDeviceInfo._fields_ = [
    ("path", ctypes.c_char_p),
    ("vendor_id", ctypes.c_ushort),
    ("product_id", ctypes.c_ushort),
    ("serial_number", ctypes.c_wchar_p),
    ("release_number", ctypes.c_ushort),
    ("manufacturer_string", ctypes.c_wchar_p),
    ("product_string", ctypes.c_wchar_p),
    ("usage_page", ctypes.c_ushort),
    ("usage", ctypes.c_ushort),
    ("interface_number", ctypes.c_int),
    ("next", _HidDeviceInfoPtr),
]


@dataclass(frozen=True)
class DeviceInfo:
    path: bytes
    vendor_id: int
    product_id: int
    serial_number: str | None
    release_number: int
    manufacturer_string: str | None
    product_string: str | None
    usage_page: int
    usage: int
    interface_number: int

    @property
    def path_text(self) -> str:
        return self.path.decode("utf-8", errors="replace")

    @property
    def looks_like_config_interface(self) -> bool:
        return self.usage_page == DEFAULT_USAGE_PAGE


def _candidate_library_paths(explicit: str | None = None) -> Iterable[str]:
    seen: set[str] = set()

    def add(path: str | None) -> Iterable[str]:
        if path and path not in seen:
            seen.add(path)
            yield path

    yield from add(explicit)
    yield from add(os.environ.get("MINI_KEYBOARD_HIDAPI"))

    for path in (
        "/opt/homebrew/lib/libhidapi.dylib",
        "/usr/local/lib/libhidapi.dylib",
        "/opt/homebrew/lib/libhidapi.0.dylib",
        "/usr/local/lib/libhidapi.0.dylib",
        "/usr/lib/libhidapi.dylib",
    ):
        if Path(path).exists():
            yield from add(path)

    for name in ("hidapi", "hidapi-hidraw", "hidapi-libusb"):
        found = ctypes.util.find_library(name)
        yield from add(found)


class HidAPI:
    def __init__(self, library_path: str | None = None):
        errors: list[str] = []
        self.path: str | None = None
        self.lib: ctypes.CDLL | None = None
        for candidate in _candidate_library_paths(library_path):
            try:
                self.lib = ctypes.CDLL(candidate)
                self.path = candidate
                break
            except OSError as exc:
                errors.append(f"{candidate}: {exc}")
        if self.lib is None:
            detail = "\n".join(errors) if errors else "no candidate libraries found"
            raise HIDAPIError(
                "Could not load libhidapi. Install hidapi or pass --hidapi.\n"
                f"{detail}"
            )
        self._setup_prototypes()
        if hasattr(self.lib, "hid_init"):
            result = self.lib.hid_init()
            if result != 0:
                raise HIDAPIError("hid_init failed")

    def _setup_prototypes(self) -> None:
        assert self.lib is not None
        self.lib.hid_enumerate.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
        self.lib.hid_enumerate.restype = _HidDeviceInfoPtr
        self.lib.hid_free_enumeration.argtypes = [_HidDeviceInfoPtr]
        self.lib.hid_free_enumeration.restype = None
        self.lib.hid_open_path.argtypes = [ctypes.c_char_p]
        self.lib.hid_open_path.restype = ctypes.c_void_p
        self.lib.hid_write.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_size_t,
        ]
        self.lib.hid_write.restype = ctypes.c_int
        self.lib.hid_read_timeout.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_size_t,
            ctypes.c_int,
        ]
        self.lib.hid_read_timeout.restype = ctypes.c_int
        self.lib.hid_close.argtypes = [ctypes.c_void_p]
        self.lib.hid_close.restype = None
        self.lib.hid_error.argtypes = [ctypes.c_void_p]
        self.lib.hid_error.restype = ctypes.c_wchar_p
        if hasattr(self.lib, "hid_darwin_set_open_exclusive"):
            self.lib.hid_darwin_set_open_exclusive.argtypes = [ctypes.c_int]
            self.lib.hid_darwin_set_open_exclusive.restype = None
            self.lib.hid_darwin_set_open_exclusive(0)

    def enumerate(self, vendor_id: int = 0, product_id: int = 0) -> list[DeviceInfo]:
        assert self.lib is not None
        head = self.lib.hid_enumerate(vendor_id, product_id)
        devices: list[DeviceInfo] = []
        try:
            current = head
            while current:
                item = current.contents
                devices.append(
                    DeviceInfo(
                        path=item.path or b"",
                        vendor_id=item.vendor_id,
                        product_id=item.product_id,
                        serial_number=item.serial_number,
                        release_number=item.release_number,
                        manufacturer_string=item.manufacturer_string,
                        product_string=item.product_string,
                        usage_page=item.usage_page,
                        usage=item.usage,
                        interface_number=item.interface_number,
                    )
                )
                current = item.next
        finally:
            if head:
                self.lib.hid_free_enumeration(head)
        return devices

    def open_device(
        self,
        vendor_id: int = DEFAULT_VENDOR_ID,
        product_id: int = DEFAULT_PRODUCT_ID,
        usage_page: int | None = DEFAULT_USAGE_PAGE,
        path: str | bytes | None = None,
    ) -> "HidDevice":
        assert self.lib is not None
        if path is None:
            devices = self.enumerate(vendor_id, product_id)
            candidates = [
                device
                for device in devices
                if usage_page is None or device.usage_page == usage_page
            ]
            if not candidates and usage_page is not None:
                candidates = devices
            if not candidates:
                raise HIDAPIError(
                    f"No HID device found for VID 0x{vendor_id:04x} PID 0x{product_id:04x}"
                )
            chosen = candidates[0]
            path_bytes = chosen.path
        elif isinstance(path, bytes):
            path_bytes = path
        else:
            path_bytes = path.encode("utf-8")

        handle = self.lib.hid_open_path(path_bytes)
        if not handle:
            message = self.lib.hid_error(None) or "unknown hidapi error"
            raise HIDAPIError(f"Could not open HID path {path_bytes!r}: {message}")
        return HidDevice(self, handle)


class HidDevice:
    def __init__(self, api: HidAPI, handle: int):
        self.api = api
        self.handle = handle
        self.closed = False

    def __enter__(self) -> "HidDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if not self.closed:
            assert self.api.lib is not None
            self.api.lib.hid_close(self.handle)
            self.closed = True

    def _error_text(self) -> str:
        assert self.api.lib is not None
        message = self.api.lib.hid_error(self.handle)
        return message or "unknown hidapi error"

    def write(self, data: bytes) -> int:
        assert self.api.lib is not None
        buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        written = self.api.lib.hid_write(self.handle, buffer, len(data))
        if written < 0:
            raise HIDAPIError(f"hid_write failed: {self._error_text()}")
        return written

    def read_timeout(self, length: int = 64, timeout_ms: int = 1000) -> bytes:
        assert self.api.lib is not None
        buffer = (ctypes.c_ubyte * length)()
        received = self.api.lib.hid_read_timeout(
            self.handle, buffer, length, timeout_ms
        )
        if received < 0:
            raise HIDAPIError(f"hid_read_timeout failed: {self._error_text()}")
        return bytes(buffer[:received])
