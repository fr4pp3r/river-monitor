"""
Minimal GPIO control via the system libgpiod (C library) using ctypes.

Rationale: RPi.GPIO does not support the Raspberry Pi 5 SoC (RP1),
and the gpiozero pin-factory backends (lgpio/gpiod python bindings)
fail to build on this system. libgpiod itself ships preinstalled on
Pi OS, so no Python package needs to be compiled.

Only the two operations the LoRa receiver needs are exposed:
output lines (chip-select/reset) and one input line (DIO0).

Pin numbers are interpreted as the standard 40-pin header BCM/offset
numbers, which match gpiochip0 offsets on both older Pi models and
the Pi 5 (RP1).
"""

import ctypes
import ctypes.util
import os
from typing import List, Optional

_LIB_NAME = "libgpiod.so.1"

# libgpiod v1 gpiod_line_request flags (gpiod.h)
_GPIOD_LINE_REQUEST_DIRECTION_AS_IS = 0
_GPIOD_LINE_REQUEST_DIRECTION_INPUT = 1
_GPIOD_LINE_REQUEST_DIRECTION_OUTPUT = 2
_GPIOD_LINE_REQUEST_FLAG_ACTIVE_LOW = 1 << 2

# libgpiod v1 gpiod_line_value
_GPIOD_LINE_VALUE_ACTIVE = 1
_GPIOD_LINE_VALUE_INACTIVE = 0


class _LineHandle:
    """Thin ctypes handle to one requested GPIO line."""

    __slots__ = ("lib", "chip", "line", "offset", "read", "set_value", "req_value")

    def __init__(self, lib, chip, line, offset, read, set_value, req_value):
        self.lib = lib
        self.chip = chip
        self.line = line
        self.offset = offset
        self.read = read
        self.set_value = set_value
        self.req_value = req_value

    def write(self, value: int) -> None:
        if self.req_value:
            self.req_value(self.chip, self.offset, value)
        else:
            self.set_value(self.line, value)

    def is_active(self) -> bool:
        if self.read:
            return bool(self.read(self.chip, self.offset))
        return bool(self.set_value(self.line, _GPIOD_LINE_VALUE_INACTIVE) == _GPIOD_LINE_VALUE_ACTIVE)

    def close(self) -> None:
        self.lib.gpiod_line_release(self.line)
        self.lib.gpiod_chip_close(self.chip)


class OutputPin:
    """libgpiod output line. value=True means the BCM pin is HIGH."""

    def __init__(self, offset: int, initial: bool, chip_name: Optional[str] = None):
        self._handle = _get_line(offset, "output", initial, chip_name=chip_name)
        self.offset = offset

    def on(self) -> None:
        self._handle.write(_GPIOD_LINE_VALUE_ACTIVE)

    def off(self) -> None:
        self._handle.write(_GPIOD_LINE_VALUE_INACTIVE)

    def close(self) -> None:
        self._handle.close()


class InputPin:
    """libgpiod input line. is_active() is True when the pin is HIGH."""

    def __init__(self, offset: int, chip_name: Optional[str] = None):
        self._handle = _get_line(offset, "input", False, chip_name=chip_name)
        self.offset = offset

    def is_active(self) -> bool:
        return self._handle.is_active()

    def close(self) -> None:
        self._handle.close()


_LIBGPIDOD_CACHE = None


def _load_lib() -> ctypes.CDLL:
    """Load libgpiod once and cache it."""
    global _LIBGPIDOD_CACHE
    if _LIBGPIDOD_CACHE is not None:
        return _LIBGPIDOD_CACHE

    path = ctypes.util.find_library("gpiod") or ctypes.util.find_library(_LIB_NAME)
    if path is None:
        for candidate in ("/usr/lib/aarch64-linux-gnu/libgpiod.so.1",
                          "/usr/lib/arm-linux-gnueabihf/libgpiod.so.1",
                          "/usr/lib/libgpiod.so.1"):
            if os.path.exists(candidate):
                path = candidate
                break
    if path is None:
        raise OSError(
            "libgpiod not found. Install it with `sudo apt install libgpiod2`."
        )

    lib = ctypes.CDLL(path)

    lib.gpiod_chip_open_by_name.restype = ctypes.c_void_p
    lib.gpiod_chip_open_by_name.argtypes = [ctypes.c_char_p]

    lib.gpiod_chip_get_line.restype = ctypes.c_void_p
    lib.gpiod_chip_get_line.argtypes = [ctypes.c_void_p, ctypes.c_uint]

    lib.gpiod_line_request_output.restype = ctypes.c_int
    lib.gpiod_line_request_output.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]

    lib.gpiod_line_request_input.restype = ctypes.c_int
    lib.gpiod_line_request_input.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p]

    lib.gpiod_line_set_value.restype = ctypes.c_int
    lib.gpiod_line_set_value.argtypes = [ctypes.c_void_p, ctypes.c_int]

    lib.gpiod_line_get_value.restype = ctypes.c_int
    lib.gpiod_line_get_value.argtypes = [ctypes.c_void_p]

    lib.gpiod_line_release.restype = None
    lib.gpiod_line_release.argtypes = [ctypes.c_void_p]

    lib.gpiod_chip_close.restype = None
    lib.gpiod_chip_close.argtypes = [ctypes.c_void_p]

    _LIBGPIDOD_CACHE = lib
    return lib


def _chip_names() -> List[str]:
    names = []
    if os.path.exists("/dev/gpiochip0"):
        names.append("/dev/gpiochip0")
    for i in range(1, 8):
        if os.path.exists(f"/dev/gpiochip{i}"):
            names.append(f"/dev/gpiochip{i}")
    return names


def _get_line(offset: int, direction: str, initial: bool,
              chip_name: Optional[str] = None) -> _LineHandle:
    lib = _load_lib()

    chips = [chip_name] if chip_name else _chip_names()
    last_err = None
    for dev in chips:
        chip = lib.gpiod_chip_open_by_name(dev.encode())
        if not chip:
            last_err = f"cannot open {dev} (permission denied? try root)"
            continue
        try:
            line = lib.gpiod_chip_get_line(chip, offset)
            if not line:
                last_err = f"{dev} has no line {offset}"
                lib.gpiod_chip_close(chip)
                continue
            if direction == "output":
                rc = lib.gpiod_line_request_output(
                    line, b"river-monitor", _GPIOD_LINE_VALUE_ACTIVE if initial else _GPIOD_LINE_VALUE_INACTIVE)
            else:
                rc = lib.gpiod_line_request_input(line, b"river-monitor")
            if rc != 0:
                last_err = f"cannot request line {offset} on {dev}"
                lib.gpiod_chip_close(chip)
                continue
            return _LineHandle(
                lib=lib,
                chip=chip,
                line=line,
                offset=offset,
                read=lib.gpiod_line_get_value if direction == "input" else None,
                set_value=lib.gpiod_line_set_value if direction == "output" else None,
                req_value=lib.gpiod_line_set_value if direction == "output" else None,
            )
        except Exception as e:  # bridge ctypes errors to the last_err context
            last_err = f"{dev}: {e}"
            lib.gpiod_chip_close(chip)
            continue

    raise OSError(f"GPIO init failed: {last_err or 'no gpiochip available'}")