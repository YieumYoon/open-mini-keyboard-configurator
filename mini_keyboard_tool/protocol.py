from __future__ import annotations

from dataclasses import dataclass


DEFAULT_VENDOR_ID = 0x514C
DEFAULT_PRODUCT_ID = 0x8850
DEFAULT_USAGE_PAGE = 0xFF00
DEFAULT_USAGE = 0x0001

REPORT_ID = 0x03
REPORT_LEN = 65
RECORD_LEN = 64
MODE_BASIC = 0x01
MODE_FUNCTION = 0x02
MODE_MOUSE = 0x03
MODE_MACRO = 0x05
MODE_LED = 0x08

TOKEN_LEFT_CTRL = 0xF1
TOKEN_LEFT_SHIFT = 0xF2
TOKEN_LEFT_ALT = 0xF3
TOKEN_LEFT_GUI = 0xF4
TOKEN_RIGHT_CTRL = 0xF5
TOKEN_RIGHT_SHIFT = 0xF6
TOKEN_RIGHT_ALT = 0xF7
TOKEN_RIGHT_GUI = 0xF8

VARIANT_NEW = "new"
VARIANT_OLD = "old"
VARIANTS = (VARIANT_NEW, VARIANT_OLD)


@dataclass(frozen=True)
class BasicRemap:
    physical_key: int
    layer: int
    keycode: int | None
    variant: str = VARIANT_NEW
    mode: int = MODE_BASIC


@dataclass(frozen=True)
class SequenceRemap:
    physical_key: int
    layer: int
    tokens: tuple[int, ...]
    mode: int
    delays: tuple[int, ...] = ()
    variant: str = VARIANT_NEW


@dataclass(frozen=True)
class MouseRemap:
    physical_key: int
    layer: int
    page: int
    button: int = 0
    wheel: int = 0
    wheel_modifier: int = 0
    swipe: int = 0
    variant: str = VARIANT_NEW


@dataclass(frozen=True)
class LedConfig:
    layer: int
    mode: int
    colors: tuple[tuple[int, int, int], ...]


def _byte(value: int, name: str) -> int:
    if not 0 <= value <= 0xFF:
        raise ValueError(f"{name} must fit in one byte")
    return value


def _word(value: int, name: str) -> int:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"{name} must fit in two bytes")
    return value


def _validate_slot_layer(physical_key: int, layer: int) -> None:
    if not 0 <= physical_key <= 59:
        raise ValueError("physical key slot must be between 0 and 59")
    if not 0 <= layer <= 2:
        raise ValueError("layer must be 0, 1, or 2")


def _validate_remap(remap: BasicRemap) -> None:
    if remap.variant not in VARIANTS:
        raise ValueError(f"variant must be one of: {', '.join(VARIANTS)}")
    _validate_slot_layer(remap.physical_key, remap.layer)
    _byte(remap.mode, "mode")
    if remap.keycode is not None:
        _byte(remap.keycode, "keycode")


def _build_new_header(physical_key: int, layer: int, mode: int) -> bytearray:
    _validate_slot_layer(physical_key, layer)
    record = bytearray(RECORD_LEN)
    record[0] = 0xFD
    record[1] = physical_key
    record[2] = layer + 1
    record[3] = _byte(mode, "mode")
    return record


def build_basic_record(remap: BasicRemap) -> bytes:
    _validate_remap(remap)
    record = _build_new_header(remap.physical_key, remap.layer, remap.mode)

    if remap.keycode is None:
        return bytes(record)

    if remap.variant == VARIANT_NEW:
        record[5] = 1
        record[8] = remap.keycode
    else:
        record[9] = 1
        record[0x0B] = remap.keycode
    return bytes(record)


def _validate_new_sequence(remap: SequenceRemap) -> None:
    if remap.variant != VARIANT_NEW:
        raise ValueError("sequence/media/macro records are currently supported for new variant only")
    _validate_slot_layer(remap.physical_key, remap.layer)
    _byte(remap.mode, "mode")
    if len(remap.tokens) > 18:
        raise ValueError("at most 18 tokens fit in one sequence record")
    if remap.delays and len(remap.delays) != len(remap.tokens):
        raise ValueError("delay count must match token count")
    for token in remap.tokens:
        _byte(token, "token")
    for delay in remap.delays:
        _word(delay, "delay")


def build_sequence_record(remap: SequenceRemap) -> bytes:
    _validate_new_sequence(remap)
    record = _build_new_header(remap.physical_key, remap.layer, remap.mode)
    record[5] = len(remap.tokens)
    for index, token in enumerate(remap.tokens):
        delay = remap.delays[index] if remap.delays else 0
        record[6 + (index * 3)] = (delay >> 8) & 0xFF
        record[7 + (index * 3)] = delay & 0xFF
        record[8 + (index * 3)] = token
    return bytes(record)


def build_sequence_report(remap: SequenceRemap) -> bytes:
    return report_from_record(build_sequence_record(remap))


def build_media_report(
    physical_key: int,
    layer: int,
    consumer_usage: int,
    variant: str = VARIANT_NEW,
) -> bytes:
    if variant != VARIANT_NEW:
        raise ValueError("media records are currently supported for new variant only")
    _validate_slot_layer(physical_key, layer)
    usage = _word(consumer_usage, "consumer usage")

    record = _build_new_header(physical_key, layer, MODE_FUNCTION)
    record[5] = 2
    record[8] = usage & 0xFF
    record[11] = (usage >> 8) & 0xFF
    return report_from_record(bytes(record))


def build_mouse_record(remap: MouseRemap) -> bytes:
    if remap.variant != VARIANT_NEW:
        raise ValueError("mouse records are currently supported for new variant only")
    _validate_slot_layer(remap.physical_key, remap.layer)
    page = _byte(remap.page, "mouse page")
    button = _byte(remap.button, "mouse button")
    wheel_modifier = _byte(remap.wheel_modifier, "wheel modifier")
    swipe = _byte(remap.swipe, "swipe code")
    if remap.wheel not in (-1, 0, 1):
        raise ValueError("wheel must be -1, 0, or 1")

    record = _build_new_header(remap.physical_key, remap.layer, MODE_MOUSE)
    record[4] = page
    record[5] = 4
    if page == 1:
        record[8] = wheel_modifier
        record[11] = button
        if remap.wheel:
            record[20] = 0x01 if remap.wheel > 0 else 0xFF
    elif page == 4:
        record[8] = swipe
    else:
        raise ValueError("mouse page must be 1 for mouse buttons/wheel or 4 for swipe")
    return bytes(record)


def build_mouse_report(remap: MouseRemap) -> bytes:
    return report_from_record(build_mouse_record(remap))


def report_from_record(record: bytes) -> bytes:
    if len(record) != RECORD_LEN:
        raise ValueError(f"record must be exactly {RECORD_LEN} bytes")
    return bytes([REPORT_ID]) + record


def build_basic_report(remap: BasicRemap) -> bytes:
    return report_from_record(build_basic_record(remap))


def build_commit_report() -> bytes:
    report = bytearray(REPORT_LEN)
    report[0] = REPORT_ID
    report[1] = 0xFD
    report[2] = 0xFE
    report[3] = 0xFF
    return bytes(report)


def build_info_request() -> bytes:
    report = bytearray(REPORT_LEN)
    report[0] = REPORT_ID
    report[1] = 0xFB
    report[2] = 0xFB
    report[3] = 0xFB
    return bytes(report)


def build_read_config_request(page: int, count: int, bank: int = 0) -> bytes:
    report = bytearray(REPORT_LEN)
    report[0] = REPORT_ID
    report[1] = 0xFA
    report[2] = _byte(count, "count")
    report[3] = _byte(bank, "bank")
    report[4] = _byte(page, "page")
    return bytes(report)


def build_led_report(config: LedConfig) -> bytes:
    if not 0 <= config.layer <= 2:
        raise ValueError("layer must be 0, 1, or 2")
    _byte(config.mode, "LED mode")
    if len(config.colors) != 16:
        raise ValueError("LED report needs exactly 16 RGB colors")

    report = bytearray(REPORT_LEN)
    report[0] = REPORT_ID
    report[1] = 0xFE
    report[2] = 0xB0
    report[3] = config.layer
    report[4] = config.mode
    offset = 5
    for red, green, blue in config.colors:
        report[offset] = _byte(red, "red")
        report[offset + 1] = _byte(green, "green")
        report[offset + 2] = _byte(blue, "blue")
        offset += 3
    return bytes(report)


def build_read_led_request(layer: int) -> bytes:
    report = bytearray(REPORT_LEN)
    report[0] = REPORT_ID
    report[1] = 0xFA
    report[2] = 0xB0
    report[3] = _byte(layer, "layer")
    return bytes(report)


def parse_led_response(response: bytes) -> tuple[int, tuple[tuple[int, int, int], ...]]:
    if len(response) < 51:
        raise ValueError("LED response is shorter than 51 bytes")
    mode = response[2]
    colors = []
    for offset in range(3, 51, 3):
        colors.append((response[offset], response[offset + 1], response[offset + 2]))
    return mode, tuple(colors)


def parse_info_response(response: bytes) -> tuple[int, int, int]:
    if len(response) < 5:
        raise ValueError("info response is shorter than 5 bytes")
    return response[2], response[3], response[4]


def build_reports(remap: BasicRemap, commit: bool = True) -> list[bytes]:
    reports = [build_basic_report(remap)]
    if commit:
        reports.append(build_commit_report())
    return reports


def hex_dump(data: bytes, width: int = 16) -> str:
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        rendered = " ".join(f"{byte:02x}" for byte in chunk)
        lines.append(f"{offset:04x}: {rendered}")
    return "\n".join(lines)
