from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from . import __version__
from .catalog import (
    PROCREATE_PRESET_BY_SLUG,
    PROCREATE_PRESETS,
    VENDOR_MODELS,
    vendor_model_handlers,
)
from .hidapi import HIDAPIError, HidAPI
from .keycodes import (
    canonical_keycodes,
    canonical_media_usages,
    media_usage_name,
    modifier_token_name,
    parse_keycode,
    parse_media_usage,
    parse_modifier_token,
    token_name,
    vendor_basic_key_aliases,
)
from .ledcolors import canonical_led_swatches, parse_led_color, rgb_hex
from .protocol import (
    DEFAULT_PRODUCT_ID,
    DEFAULT_USAGE_PAGE,
    DEFAULT_VENDOR_ID,
    MODE_BASIC,
    MODE_FUNCTION,
    MODE_MOUSE,
    MODE_MACRO,
    REPORT_ID,
    REPORT_LEN,
    BasicRemap,
    LedConfig,
    MouseRemap,
    SequenceRemap,
    build_basic_report,
    build_commit_report,
    build_info_request,
    build_led_report,
    build_media_report,
    build_mouse_report,
    build_read_config_request,
    build_read_led_request,
    build_sequence_report,
    hex_dump,
    parse_info_response,
    parse_led_response,
)


def parse_number(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid number: {value!r}") from exc


def parse_number_list(value: str) -> tuple[int, ...]:
    numbers = []
    for chunk in value.replace(";", ",").split(","):
        text = chunk.strip()
        if not text:
            continue
        numbers.append(parse_number(text))
    if not numbers:
        raise argparse.ArgumentTypeError("list needs at least one number")
    return tuple(numbers)


SLOT_ALIASES = {
    "top-left": 16,
    "top-ccw": 16,
    "top-click": 17,
    "top-press": 17,
    "top-right": 18,
    "top-cw": 18,
    "upper-left": 16,
    "upper-ccw": 16,
    "upper-click": 17,
    "upper-press": 17,
    "upper-right": 18,
    "upper-cw": 18,
    "knob1-left": 16,
    "knob1-ccw": 16,
    "knob1-click": 17,
    "knob1-press": 17,
    "knob1-right": 18,
    "knob1-cw": 18,
    "bottom-left": 19,
    "bottom-ccw": 19,
    "bottom-click": 20,
    "bottom-press": 20,
    "bottom-right": 21,
    "bottom-cw": 21,
    "lower-left": 19,
    "lower-ccw": 19,
    "lower-click": 20,
    "lower-press": 20,
    "lower-right": 21,
    "lower-cw": 21,
    "knob2-left": 19,
    "knob2-ccw": 19,
    "knob2-click": 20,
    "knob2-press": 20,
    "knob2-right": 21,
    "knob2-cw": 21,
}

SLOT_LABELS = {
    1: "row1-col1",
    2: "row1-col2",
    3: "row1-col3",
    4: "row1-col4",
    5: "row2-col1",
    6: "row2-col2",
    7: "row2-col3",
    8: "row2-col4",
    9: "row3-col1",
    10: "row3-col2",
    11: "row3-col3",
    12: "row3-col4",
    16: "top-left/top-ccw",
    17: "top-click",
    18: "top-right/top-cw",
    19: "bottom-left/bottom-ccw",
    20: "bottom-click",
    21: "bottom-right/bottom-cw",
}

TESTED_12KEY_SLOTS = tuple(range(1, 13))
TESTED_KNOB_SLOTS = (16, 17, 18, 19, 20, 21)

MOUSE_ACTIONS: dict[str, dict[str, int]] = {
    "left-click": {"page": 1, "button": 1},
    "mouse-left": {"page": 1, "button": 1},
    "right-click": {"page": 1, "button": 2},
    "mouse-right": {"page": 1, "button": 2},
    "middle-click": {"page": 1, "button": 4},
    "mouse-middle": {"page": 1, "button": 4},
    "wheel-up": {"page": 1, "wheel": 1},
    "scroll-up": {"page": 1, "wheel": 1},
    "wheel-positive": {"page": 1, "wheel": 1},
    "wheel+": {"page": 1, "wheel": 1},
    "wheel-down": {"page": 1, "wheel": -1},
    "scroll-down": {"page": 1, "wheel": -1},
    "wheel-negative": {"page": 1, "wheel": -1},
    "wheel-": {"page": 1, "wheel": -1},
    "ctrl-wheel-up": {"page": 1, "wheel_modifier": 0xF1, "wheel": 1},
    "ctrl-scroll-up": {"page": 1, "wheel_modifier": 0xF1, "wheel": 1},
    "ctrl-wheel-positive": {"page": 1, "wheel_modifier": 0xF1, "wheel": 1},
    "ctrl-wheel-down": {"page": 1, "wheel_modifier": 0xF1, "wheel": -1},
    "ctrl-scroll-down": {"page": 1, "wheel_modifier": 0xF1, "wheel": -1},
    "ctrl-wheel-negative": {"page": 1, "wheel_modifier": 0xF1, "wheel": -1},
    "shift-wheel-up": {"page": 1, "wheel_modifier": 0xF2, "wheel": 1},
    "shift-scroll-up": {"page": 1, "wheel_modifier": 0xF2, "wheel": 1},
    "shift-wheel-positive": {"page": 1, "wheel_modifier": 0xF2, "wheel": 1},
    "shift-wheel-down": {"page": 1, "wheel_modifier": 0xF2, "wheel": -1},
    "shift-scroll-down": {"page": 1, "wheel_modifier": 0xF2, "wheel": -1},
    "shift-wheel-negative": {"page": 1, "wheel_modifier": 0xF2, "wheel": -1},
    "alt-wheel-up": {"page": 1, "wheel_modifier": 0xF3, "wheel": 1},
    "alt-scroll-up": {"page": 1, "wheel_modifier": 0xF3, "wheel": 1},
    "alt-wheel-positive": {"page": 1, "wheel_modifier": 0xF3, "wheel": 1},
    "alt-wheel-down": {"page": 1, "wheel_modifier": 0xF3, "wheel": -1},
    "alt-scroll-down": {"page": 1, "wheel_modifier": 0xF3, "wheel": -1},
    "alt-wheel-negative": {"page": 1, "wheel_modifier": 0xF3, "wheel": -1},
    "like": {"page": 4, "swipe": 1},
    "procreate-like": {"page": 4, "swipe": 1},
    "swipe-left": {"page": 4, "swipe": 2},
    "left-swipe": {"page": 4, "swipe": 2},
    "swipe-right": {"page": 4, "swipe": 3},
    "right-swipe": {"page": 4, "swipe": 3},
    "swipe-up": {"page": 4, "swipe": 4},
    "up-swipe": {"page": 4, "swipe": 4},
    "swipe-down": {"page": 4, "swipe": 5},
    "down-swipe": {"page": 4, "swipe": 5},
}

LED_MODE_ALIASES = {
    "mode0": 0,
    "mode1": 1,
    "mode2": 2,
    "mode3": 3,
    "mode4": 4,
    "mode5": 5,
}

RECORD_MODE_ALIASES = {
    "basic": MODE_BASIC,
    "mode1": MODE_BASIC,
    "function": MODE_FUNCTION,
    "media": MODE_FUNCTION,
    "mode2": MODE_FUNCTION,
    "macro": MODE_MACRO,
    "delay": MODE_MACRO,
    "mode5": MODE_MACRO,
}


def parse_key_slot(value: str) -> int:
    normalized = value.strip().lower().replace("_", "-")
    if normalized in SLOT_ALIASES:
        return SLOT_ALIASES[normalized]
    return parse_number(value)


def parse_key_slots(value: str) -> tuple[int, ...]:
    slots: list[int] = []
    for chunk in value.replace(";", ",").split(","):
        text = chunk.strip()
        if not text:
            continue
        if ".." in text:
            start_text, end_text = text.split("..", 1)
            start = parse_key_slot(start_text)
            end = parse_key_slot(end_text)
            step = 1 if start <= end else -1
            slots.extend(range(start, end + step, step))
        else:
            slots.append(parse_key_slot(text))
    if not slots:
        raise argparse.ArgumentTypeError("slot list needs at least one slot")
    return tuple(dict.fromkeys(slots))


def parse_mouse_action(value: str) -> dict[str, int]:
    normalized = value.strip().lower().replace("_", "-")
    if normalized in MOUSE_ACTIONS:
        return MOUSE_ACTIONS[normalized]
    raise argparse.ArgumentTypeError(f"unknown mouse action: {value!r}")


def parse_led_mode(value: str) -> int:
    normalized = value.strip().lower().replace("_", "")
    if normalized in LED_MODE_ALIASES:
        return LED_MODE_ALIASES[normalized]
    number = parse_number(value)
    if not 0 <= number <= 0xFF:
        raise argparse.ArgumentTypeError("LED mode must fit in one byte")
    return number


def parse_record_mode(value: str) -> int:
    normalized = value.strip().lower().replace("_", "-")
    if normalized in RECORD_MODE_ALIASES:
        return RECORD_MODE_ALIASES[normalized]
    number = parse_number(value)
    if not 0 <= number <= 0xFF:
        raise argparse.ArgumentTypeError("record mode must fit in one byte")
    return number


def parse_delay_ms(value: str) -> int:
    number = parse_number(value)
    if not 0 <= number <= 0xFFFF:
        raise argparse.ArgumentTypeError("delay must be between 0 and 65535 ms")
    return number


def parse_rgb_color(value: str) -> tuple[int, int, int]:
    try:
        return parse_led_color(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_macro_tokens(value: str) -> tuple[int, ...]:
    tokens: list[int] = []
    steps = [step.strip() for step in value.replace(";", ",").split(",") if step.strip()]
    if not steps:
        raise argparse.ArgumentTypeError("macro needs at least one step")
    for step in steps:
        chunks = [chunk.strip() for chunk in step.split("+") if chunk.strip()]
        if not chunks:
            continue
        for modifier in chunks[:-1]:
            try:
                tokens.append(parse_modifier_token(modifier))
            except ValueError as exc:
                raise argparse.ArgumentTypeError(str(exc)) from exc
        key = chunks[-1]
        if key.lower().startswith("raw:"):
            token_text = key.split(":", 1)[1]
            try:
                token = int(token_text, 0)
            except ValueError as exc:
                raise argparse.ArgumentTypeError(f"invalid raw token: {key!r}") from exc
            if not 0 <= token <= 0xFF:
                raise argparse.ArgumentTypeError(f"raw token out of range: {key!r}")
            tokens.append(token)
        else:
            try:
                tokens.append(parse_keycode(key))
            except ValueError as exc:
                raise argparse.ArgumentTypeError(str(exc)) from exc
    if len(tokens) > 18:
        raise argparse.ArgumentTypeError("macro expands to more than 18 tokens")
    return tuple(tokens)


def parse_delay_list(value: str) -> tuple[int, ...]:
    delays = []
    for chunk in value.replace(";", ",").split(","):
        text = chunk.strip()
        if not text:
            continue
        delays.append(parse_delay_ms(text))
    if not delays:
        raise argparse.ArgumentTypeError("delay list needs at least one value")
    if len(delays) > 18:
        raise argparse.ArgumentTypeError("delay list has more than 18 values")
    return tuple(delays)


def _snapshot_int(item: dict[str, object], key: str) -> int:
    value = item.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"snapshot item missing integer {key!r}")


def macro_delays_from_args(args: argparse.Namespace, tokens: tuple[int, ...]) -> tuple[int, ...]:
    if args.delays is not None:
        if args.delay:
            raise argparse.ArgumentTypeError("--delay cannot be combined with --delays")
        delays = args.delays
        if len(delays) != len(tokens):
            raise argparse.ArgumentTypeError(
                f"--delays has {len(delays)} values but macro expands to {len(tokens)} tokens"
            )
        return delays
    return (args.delay,) * len(tokens)


def write_labeled_reports(
    args: argparse.Namespace,
    labeled_reports: list[tuple[str, bytes]],
    success: str = "Reports written.",
) -> int:
    for index, (label, report) in enumerate(labeled_reports):
        print(f"\nReport {index + 1} ({label}, {len(report)} bytes):")
        print(hex_dump(report))

    if not args.write:
        print("\nDry run only. Add --write --yes to send these reports.")
        return 0
    if not args.yes:
        print("Refusing to write without --yes.", file=sys.stderr)
        return 2

    api = HidAPI(args.hidapi)
    with api.open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        for _, report in labeled_reports:
            written = device.write(report)
            if written != len(report):
                print(
                    f"Warning: hid_write returned {written}, expected {len(report)}",
                    file=sys.stderr,
                )
    print(success)
    return 0


def add_hid_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--vid", type=parse_number, default=DEFAULT_VENDOR_ID)
    parser.add_argument("--pid", type=parse_number, default=DEFAULT_PRODUCT_ID)
    parser.add_argument("--usage-page", type=parse_number, default=DEFAULT_USAGE_PAGE)
    parser.add_argument("--path", help="Open an exact HID path instead of auto-picking")
    parser.add_argument("--hidapi", help="Path to libhidapi.dylib")


def cmd_list(args: argparse.Namespace) -> int:
    api = HidAPI(args.hidapi)
    vendor_id = 0 if args.all else args.vid
    product_id = 0 if args.all else args.pid
    devices = api.enumerate(vendor_id, product_id)
    if not devices:
        print("No HID devices found.")
        return 1
    for index, device in enumerate(devices):
        marker = "*" if device.usage_page == args.usage_page else " "
        print(
            f"{marker} [{index}] "
            f"VID:PID=0x{device.vendor_id:04x}:0x{device.product_id:04x} "
            f"usage=0x{device.usage_page:04x}:0x{device.usage:04x} "
            f"interface={device.interface_number} "
            f"product={device.product_string!r} "
            f"serial={device.serial_number!r}"
        )
        print(f"    path={device.path_text}")
    print(f"Loaded hidapi: {api.path}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    api = HidAPI(args.hidapi)
    request = build_info_request()
    print("Info request:")
    print(hex_dump(request))
    with api.open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        written = device.write(request)
        print(f"Wrote {written} bytes.")
        response = device.read_timeout(64, args.timeout)
    if not response:
        print("No response before timeout.")
        return 1
    print("Info response:")
    print(hex_dump(response))
    try:
        model = parse_info_response(response)
    except ValueError as exc:
        print(f"Could not parse response: {exc}")
        return 1
    print(f"Keyboard model bytes: {model[0]}, {model[1]}, {model[2]}")
    return 0


def _build_remap_from_args(args: argparse.Namespace) -> BasicRemap:
    if args.clear:
        if args.to:
            raise argparse.ArgumentTypeError("--clear cannot be combined with --to")
        keycode = None
    else:
        if not args.to:
            raise argparse.ArgumentTypeError("remap requires --to unless --clear is used")
        keycode = parse_keycode(args.to)
    return BasicRemap(
        physical_key=args.key,
        layer=args.layer,
        keycode=keycode,
        variant=args.variant,
        mode=args.mode,
    )


def _is_sequence_remap_text(value: str) -> bool:
    return any(separator in value for separator in ("+", ",", ";"))


def _build_remap_labeled_reports(args: argparse.Namespace) -> tuple[str, list[tuple[str, bytes]]]:
    if args.clear or not args.to or not _is_sequence_remap_text(args.to):
        remap = _build_remap_from_args(args)
        reports = [("remap", build_basic_report(remap))]
        if not args.no_commit:
            reports.append(("commit", build_commit_report()))
        action = "clear" if remap.keycode is None else f"set to 0x{remap.keycode:02x}"
        title = (
            f"Physical key {remap.physical_key}, layer {remap.layer}, "
            f"variant {remap.variant}: {action}"
        )
        return title, reports

    tokens = parse_macro_tokens(args.to)
    report = build_sequence_report(
        SequenceRemap(
            physical_key=args.key,
            layer=args.layer,
            mode=args.mode,
            tokens=tokens,
            variant=args.variant,
        )
    )
    reports = [("remap token-list", report)]
    if not args.no_commit:
        reports.append(("commit", build_commit_report()))
    title = (
        f"Physical key {args.key}, layer {args.layer}, variant {args.variant}: "
        f"set to keys {_format_sequence_tokens(list(tokens))}, record mode {args.mode}"
    )
    return title, reports


def cmd_remap(args: argparse.Namespace) -> int:
    try:
        title, labeled_reports = _build_remap_labeled_reports(args)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    print(title)
    for index, (label, report) in enumerate(labeled_reports):
        print(f"\nReport {index + 1} ({label}, {len(report)} bytes):")
        print(hex_dump(report))

    if not args.write:
        print("\nDry run only. Add --write --yes to send these reports.")
        return 0
    if not args.yes:
        print("Refusing to write without --yes.", file=sys.stderr)
        return 2

    api = HidAPI(args.hidapi)
    with api.open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        for _, report in labeled_reports:
            written = device.write(report)
            if written != len(report):
                print(
                    f"Warning: hid_write returned {written}, expected {len(report)}",
                    file=sys.stderr,
                )
    print("Reports written.")
    return 0


def _clear_slots_from_args(args: argparse.Namespace) -> tuple[int, ...]:
    slots: list[int] = []
    for slot in args.key or ():
        slots.append(slot)
    if args.keys:
        slots.extend(args.keys)
    if args.tested_12key:
        slots.extend(TESTED_12KEY_SLOTS)
    if args.include_knobs:
        slots.extend(TESTED_KNOB_SLOTS)
    if not slots:
        raise argparse.ArgumentTypeError(
            "clear requires --key, --keys, --tested-12key, or --include-knobs"
        )
    return tuple(dict.fromkeys(slots))


def _clear_layers_from_args(args: argparse.Namespace) -> tuple[int, ...]:
    return (0, 1, 2) if args.all_layers else (args.layer,)


def _build_clear_reports(args: argparse.Namespace) -> list[tuple[str, bytes]]:
    labeled_reports: list[tuple[str, bytes]] = []
    for layer in _clear_layers_from_args(args):
        for slot in _clear_slots_from_args(args):
            report = build_basic_report(
                BasicRemap(
                    physical_key=slot,
                    layer=layer,
                    keycode=None,
                    variant=args.variant,
                    mode=args.mode,
                )
            )
            labeled_reports.append((f"clear slot {slot} layer {layer}", report))
    if not args.no_commit:
        labeled_reports.append(("commit", build_commit_report()))
    return labeled_reports


def cmd_clear(args: argparse.Namespace) -> int:
    try:
        slots = _clear_slots_from_args(args)
        layers = _clear_layers_from_args(args)
        labeled_reports = _build_clear_reports(args)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    print(
        f"Clear slots {', '.join(str(slot) for slot in slots)} "
        f"on layer(s) {', '.join(str(layer) for layer in layers)}, "
        f"variant {args.variant}, mode {args.mode}"
    )
    return write_labeled_reports(args, labeled_reports, success="Clear reports written.")


def cmd_keycodes(args: argparse.Namespace) -> int:
    needle = args.filter.lower() if args.filter else None
    rows = canonical_keycodes()
    if needle:
        rows = [(name, code) for name, code in rows if needle in name.lower()]
    for name, code in rows:
        print(f"{name:16s} 0x{code:02x}")
    return 0


def cmd_vendor_key_aliases(args: argparse.Namespace) -> int:
    needle = args.filter.lower().replace("_", "-") if args.filter else None
    rows = [
        {
            "vendor_label": label,
            "alias": alias,
            "code": code,
            "hex": f"0x{code:02x}",
        }
        for label, alias, code in vendor_basic_key_aliases()
        if needle is None
        or needle in label.lower().replace("_", "-")
        or needle in alias.lower().replace("_", "-")
    ]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print(f"{row['vendor_label']:14s} {row['alias']:16s} {row['hex']}")
    return 0


def cmd_media_codes(args: argparse.Namespace) -> int:
    needle = args.filter.lower() if args.filter else None
    rows = canonical_media_usages()
    if needle:
        rows = [(name, code) for name, code in rows if needle in name.lower()]
    for name, code in rows:
        print(f"{name:24s} 0x{code:04x}")
    return 0


def cmd_mouse_actions(args: argparse.Namespace) -> int:
    needle = args.filter.lower().replace("_", "-") if args.filter else None
    rows = sorted(MOUSE_ACTIONS)
    if needle:
        rows = [name for name in rows if needle in name]
    for name in rows:
        print(name)
    return 0


def cmd_vendor_models(args: argparse.Namespace) -> int:
    needle = args.filter.lower() if args.filter else None
    if getattr(args, "handlers", False):
        rows = [
            row
            for row in vendor_model_handlers()
            if needle is None
            or needle in str(row["model"]).lower()
            or needle in str(row["handler"]).lower()
            or needle in str(row["note"]).lower()
        ]
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        print(f"{'model':16s} {'keys':>4s} {'extra':>5s} {'public':>6s} handler")
        for row in rows:
            public = "yes" if row["public"] else "no"
            print(
                f"{str(row['model']):16s} {int(row['keys']):4d} "
                f"{int(row['extras']):5d} {public:>6s} {row['handler']}"
            )
            print(f"{'':16s} {'':4s} {'':5s} {'':6s} {row['note']}")
        return 0

    models = [model for model in VENDOR_MODELS if needle is None or needle in model.lower()]
    if args.json:
        print(json.dumps(models, indent=2))
        return 0
    for model in models:
        print(model)
    return 0


def cmd_procreate_actions(args: argparse.Namespace) -> int:
    needle = args.filter.lower().replace("_", "-") if args.filter else None
    actions = [
        {
            "slug": slug,
            "label": label,
            "tokens": [f"0x{token:02x}" for token in tokens],
            "keys": _format_sequence_tokens(list(tokens)),
            "status": "static-vendor",
        }
        for slug, label, tokens in PROCREATE_PRESETS
        if needle is None or needle in slug or needle in label.lower().replace("_", "-")
    ]
    if args.json:
        print(json.dumps(actions, indent=2))
        return 0
    for action in actions:
        print(f"{action['slug']:32s} {action['keys']:18s} {action['label']}")
    if actions:
        print()
        print("Status: static-vendor. Tokens were extracted from the vendor app binary; physical app-level behavior is not exhaustively tested.")
    return 0


def cmd_procreate(args: argparse.Namespace) -> int:
    action = args.action.lower().replace("_", "-")
    if action not in PROCREATE_PRESET_BY_SLUG:
        raise argparse.ArgumentTypeError(f"unknown Procreate action: {args.action!r}")
    label, tokens = PROCREATE_PRESET_BY_SLUG[action]
    try:
        report = build_sequence_report(
            SequenceRemap(
                physical_key=args.key,
                layer=args.layer,
                mode=args.record_mode,
                tokens=tokens,
                variant=args.variant,
            )
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    rendered_tokens = " ".join(f"0x{token:02x}" for token in tokens)
    print(
        f"Physical key {args.key}, layer {args.layer}, variant {args.variant}: "
        f"Procreate {action} ({label}), record mode {args.record_mode}"
    )
    print(f"Expanded tokens: {rendered_tokens}")
    print(f"Keys: {_format_sequence_tokens(list(tokens))}")
    labeled_reports = [("procreate", report)]
    if not args.no_commit:
        labeled_reports.append(("commit", build_commit_report()))
    return write_labeled_reports(args, labeled_reports)


def cmd_led_modes(args: argparse.Namespace) -> int:
    for name, code in sorted(LED_MODE_ALIASES.items(), key=lambda item: item[1]):
        print(f"{name:8s} 0x{code:02x}")
    return 0


def cmd_led_colors(args: argparse.Namespace) -> int:
    needle = args.filter.lower().replace("_", "-") if args.filter else None
    rows = canonical_led_swatches()
    if needle:
        rows = [(name, color) for name, color in rows if needle in name or needle in rgb_hex(color)]
    for name, color in rows:
        print(f"{name:10s} {rgb_hex(color)} {color[0]:3d},{color[1]:3d},{color[2]:3d}")
    return 0


def cmd_slots(args: argparse.Namespace) -> int:
    print("12-key + 2-knob tested layout:")
    print()
    print("  [ 1 ] [ 2 ] [ 3 ] [ 4 ]      top-left=16  top-click=17  top-right=18")
    print("  [ 5 ] [ 6 ] [ 7 ] [ 8 ]")
    print("  [ 9 ] [10 ] [11 ] [12 ]      bottom-left=19 bottom-click=20 bottom-right=21")
    print()
    print("Aliases:")
    for slot in (16, 17, 18, 19, 20, 21):
        names = sorted(name for name, mapped in SLOT_ALIASES.items() if mapped == slot)
        print(f"  {slot:2d}: {', '.join(names)}")
    return 0


def cmd_media(args: argparse.Namespace) -> int:
    try:
        usage = parse_media_usage(args.to)
        report = build_media_report(args.key, args.layer, usage, variant=args.variant)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    print(
        f"Physical key {args.key}, layer {args.layer}, variant {args.variant}: "
        f"media {args.to} (0x{usage:04x})"
    )
    labeled_reports = [("media", report)]
    if not args.no_commit:
        labeled_reports.append(("commit", build_commit_report()))
    return write_labeled_reports(args, labeled_reports)


def cmd_mouse(args: argparse.Namespace) -> int:
    action = parse_mouse_action(args.to)
    try:
        report = build_mouse_report(
            MouseRemap(
                physical_key=args.key,
                layer=args.layer,
                variant=args.variant,
                **action,
            )
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    print(
        f"Physical key {args.key}, layer {args.layer}, variant {args.variant}: "
        f"mouse {args.to}"
    )
    labeled_reports = [("mouse", report)]
    if not args.no_commit:
        labeled_reports.append(("commit", build_commit_report()))
    return write_labeled_reports(args, labeled_reports)


def cmd_macro(args: argparse.Namespace) -> int:
    tokens = parse_macro_tokens(args.steps)
    delays = macro_delays_from_args(args, tokens)
    try:
        report = build_sequence_report(
            SequenceRemap(
                physical_key=args.key,
                layer=args.layer,
                mode=args.record_mode,
                tokens=tokens,
                delays=delays,
                variant=args.variant,
            )
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    rendered_tokens = " ".join(f"0x{token:02x}" for token in tokens)
    rendered_delays = " ".join(str(delay) for delay in delays)
    print(
        f"Physical key {args.key}, layer {args.layer}, variant {args.variant}: "
        f"macro {args.steps!r}, record mode {args.record_mode}"
    )
    print(f"Expanded tokens: {rendered_tokens}")
    print(f"Token delays: {rendered_delays} ms")
    labeled_reports = [("macro", report)]
    if not args.no_commit:
        labeled_reports.append(("commit", build_commit_report()))
    return write_labeled_reports(args, labeled_reports)


EXPERIMENTS = {
    "macro-delay": "Slot macro with per-token delay; expected text is a b c with a visible pause.",
    "raw-media": "Raw 16-bit Consumer HID usage; default is calculator/app-launch usage 0x0192.",
    "modified-wheel": "Ctrl/Shift/Alt modified wheel record; default is ctrl-wheel-negative.",
    "swipe": "Mouse swipe page record; default is swipe-left.",
    "led-mode": "LED mode/color probe for one LED layer.",
}

TEST_PLAN_EXPERIMENTS = (
    {
        "id": "macro-delay",
        "title": "Per-token macro delay",
        "experiment": "macro-delay",
        "target": "config",
        "options": (("--steps", "a,b,c"), ("--delay", "250")),
        "check": (
            "Put the cursor in a text field and press the slot. Expected: a, b, c "
            "with a visible pause between tokens."
        ),
    },
    {
        "id": "raw-media",
        "title": "Raw Consumer HID usage",
        "experiment": "raw-media",
        "target": "config",
        "dynamic_options": "raw-media",
        "check": (
            "Press the slot and watch for the OS/app action from the raw Consumer HID value."
        ),
    },
    {
        "id": "modified-wheel",
        "title": "Modified wheel",
        "experiment": "modified-wheel",
        "target": "config",
        "dynamic_options": "modified-wheel",
        "check": (
            "Turn or press the selected control in an app where modified wheel input "
            "is visible, such as zoom or horizontal scroll."
        ),
    },
    {
        "id": "like-gesture",
        "title": "Vendor Like gesture",
        "experiment": "swipe",
        "target": "config",
        "options": (("--action", "like"),),
        "check": (
            "Press the slot in a target app that can react to the vendor page-4 code-1 gesture."
        ),
    },
    {
        "id": "swipe",
        "title": "Swipe gesture",
        "experiment": "swipe",
        "target": "config",
        "dynamic_options": "swipe",
        "check": "Press the slot on a screen that can react to swipe gestures.",
    },
    {
        "id": "led-mode",
        "title": "LED mode byte",
        "experiment": "led-mode",
        "target": "led",
        "dynamic_options": "led-mode",
        "check": "Visually inspect the selected LED layer for the requested mode and color.",
    },
)


def _command(args: argparse.Namespace, *parts: object) -> str:
    quoted_parts = [shlex.quote(str(part)) for part in parts]
    return " ".join([args.command_prefix, *quoted_parts])


def _after_snapshot_path(snapshot: Path, experiment_id: str) -> Path:
    return snapshot.with_name(f"after-{experiment_id}.json")


def _experiment_plan_options(
    experiment: dict[str, object],
    args: argparse.Namespace,
) -> tuple[object, ...]:
    dynamic = experiment.get("dynamic_options")
    if dynamic == "raw-media":
        parse_media_usage(args.usage)
        return ("--usage", args.usage)
    if dynamic == "modified-wheel":
        action = parse_mouse_action(args.modified_wheel_action)
        if action.get("page") != 1 or "wheel_modifier" not in action:
            raise argparse.ArgumentTypeError("--modified-wheel-action must be a modified wheel action")
        return ("--action", args.modified_wheel_action)
    if dynamic == "swipe":
        action = parse_mouse_action(args.swipe_action)
        if action.get("page") != 4:
            raise argparse.ArgumentTypeError("--swipe-action must be a page-4 swipe/gesture action")
        return ("--action", args.swipe_action)
    if dynamic == "led-mode":
        parse_led_mode(args.led_mode)
        parse_rgb_color(args.led_color)
        return ("--led-layer", args.led_layer, "--mode", args.led_mode, "--color", args.led_color)

    options = []
    for flag, value in experiment.get("options", ()):
        options.extend((flag, value))
    return tuple(options)


def _build_test_plan(args: argparse.Namespace) -> dict[str, object]:
    experiments = [
        experiment
        for experiment in TEST_PLAN_EXPERIMENTS
        if not (args.no_led and experiment.get("target") == "led")
    ]

    steps: list[dict[str, object]] = [
        {
            "type": "setup",
            "title": "Capture baseline snapshot",
            "command": _command(args, "snapshot", "--json", args.snapshot),
            "note": "Run this before the first write so each experiment can restore one slot/layer.",
        },
        {
            "type": "setup",
            "title": "Verify current tested profile",
            "command": _command(args, "verify-current", "--no-led"),
            "note": "This is read-only and checks the mappings already confirmed on the device.",
        },
    ]

    config_page = args.layer + 1
    for experiment in experiments:
        experiment_id = str(experiment["id"])
        experiment_name = str(experiment["experiment"])
        target = str(experiment["target"])
        options = _experiment_plan_options(experiment, args)

        command_parts: list[object] = ["experiment", "--name", experiment_name]
        if target == "config":
            command_parts.extend(("--key", args.key, "--layer", args.layer))
        command_parts.extend(options)

        after_snapshot = _after_snapshot_path(args.snapshot, experiment_id)
        dry_run = _command(args, *command_parts)
        write = _command(args, *command_parts, "--write", "--yes")
        if target == "led":
            after_command = _command(
                args,
                "snapshot",
                "--json",
                after_snapshot,
                "--pages",
                config_page,
                "--led-layers",
                args.led_layer,
            )
            diff_command = _command(
                args,
                "diff-snapshot",
                args.snapshot,
                after_snapshot,
                "--no-config",
                "--led-layers",
                args.led_layer,
            )
            restore_command = _command(
                args,
                "restore-snapshot",
                "--json",
                args.snapshot,
                "--no-config",
                "--include-led",
                "--led-layers",
                args.led_layer,
                "--write",
                "--yes",
            )
        else:
            after_command = _command(
                args,
                "snapshot",
                "--json",
                after_snapshot,
                "--pages",
                config_page,
                "--no-led",
            )
            diff_command = _command(
                args,
                "diff-snapshot",
                args.snapshot,
                after_snapshot,
                "--key",
                args.key,
                "--layer",
                args.layer,
                "--no-led",
            )
            restore_command = _command(
                args,
                "restore-snapshot",
                "--json",
                args.snapshot,
                "--key",
                args.key,
                "--layer",
                args.layer,
                "--write",
                "--yes",
            )

        steps.append(
            {
                "type": "experiment",
                "id": experiment_id,
                "title": experiment["title"],
                "dry_run": dry_run,
                "write": write,
                "physical_check": experiment["check"],
                "after_snapshot": after_command,
                "diff": diff_command,
                "restore": restore_command,
            }
        )

    final_verify = _command(args, "verify-current", "--no-led")
    if not args.no_led:
        final_verify = _command(args, "verify-current")
    steps.append(
        {
            "type": "finish",
            "title": "Verify restored baseline",
            "command": final_verify,
            "note": "Run after the last restore to confirm the known-good profile is back.",
        }
    )

    return {
        "key": args.key,
        "key_label": SLOT_LABELS.get(args.key, f"slot-{args.key}"),
        "layer": args.layer,
        "snapshot": str(args.snapshot),
        "steps": steps,
    }


def _print_test_plan(plan: dict[str, object]) -> None:
    print("Physical test plan (no HID commands were executed).")
    print(f"Sacrificial slot: {plan['key']} ({plan['key_label']}), layer {plan['layer']}")
    print(f"Baseline snapshot: {plan['snapshot']}")

    step_number = 1
    for step in plan["steps"]:
        assert isinstance(step, dict)
        print()
        print(f"{step_number}. {step['title']}")
        step_number += 1

        if step["type"] == "experiment":
            print(f"   Dry run:  {step['dry_run']}")
            print(f"   Write:    {step['write']}")
            print(f"   Check:    {step['physical_check']}")
            print(f"   Snapshot: {step['after_snapshot']}")
            print(f"   Diff:     {step['diff']}")
            print(f"   Restore:  {step['restore']}")
            continue

        print(f"   Command:  {step['command']}")
        note = step.get("note")
        if note:
            print(f"   Note:     {note}")


def cmd_test_plan(args: argparse.Namespace) -> int:
    plan = _build_test_plan(args)
    if args.json:
        print(json.dumps(plan, indent=2))
        return 0
    _print_test_plan(plan)
    return 0


def cmd_experiments(args: argparse.Namespace) -> int:
    for name, description in EXPERIMENTS.items():
        print(f"{name:15s} {description}")
    return 0


def _experiment_instruction(name: str, args: argparse.Namespace) -> str:
    if name == "macro-delay":
        return (
            "After writing, press the selected key in a text field. "
            "The default probe should type a, b, c with delay between tokens."
        )
    if name == "raw-media":
        return (
            "After writing, press the selected key and watch for the OS/app action "
            f"from Consumer HID usage {args.usage}."
        )
    if name == "modified-wheel":
        action = _experiment_action(name, args)
        return (
            "After writing, turn/press the selected control in an app where modified "
            f"wheel input is visible. Probe action: {action}."
        )
    if name == "swipe":
        action = _experiment_action(name, args)
        return (
            "After writing, press the selected key/control on a screen that can react "
            f"to swipe gestures. Probe action: {action}."
        )
    if name == "led-mode":
        return (
            f"After writing, visually inspect LED layer {args.led_layer} for mode "
            f"{args.mode} and color {args.color}."
        )
    return "After writing, physically test the selected feature."


def _experiment_action(name: str, args: argparse.Namespace) -> str:
    if name == "swipe" and args.action == "ctrl-wheel-negative":
        return "swipe-left"
    return args.action


def _experiment_restore_hint(name: str, args: argparse.Namespace) -> str:
    if name == "led-mode":
        return (
            "restore-snapshot --json snapshots/before.json "
            f"--no-config --include-led --led-layers {args.led_layer} --write --yes"
        )
    return f"restore-snapshot --json snapshots/before.json --key {args.key} --write --yes"


def _build_experiment_reports(args: argparse.Namespace) -> tuple[list[tuple[str, bytes]], str]:
    name = args.name
    if name not in EXPERIMENTS:
        raise argparse.ArgumentTypeError(f"unknown experiment: {name}")

    labeled_reports: list[tuple[str, bytes]] = []
    if name == "macro-delay":
        tokens = parse_macro_tokens(args.steps)
        delays = (args.delay,) * len(tokens)
        report = build_sequence_report(
            SequenceRemap(
                physical_key=args.key,
                layer=args.layer,
                mode=MODE_BASIC,
                tokens=tokens,
                delays=delays,
                variant=args.variant,
            )
        )
        labeled_reports.append((f"experiment macro-delay key {args.key}", report))
        if not args.no_commit:
            labeled_reports.append(("commit", build_commit_report()))
    elif name == "raw-media":
        usage = parse_media_usage(args.usage)
        report = build_media_report(args.key, args.layer, usage, variant=args.variant)
        labeled_reports.append((f"experiment raw-media key {args.key} usage 0x{usage:04x}", report))
        if not args.no_commit:
            labeled_reports.append(("commit", build_commit_report()))
    elif name == "modified-wheel":
        action_name = _experiment_action(name, args)
        action = parse_mouse_action(action_name)
        report = build_mouse_report(
            MouseRemap(
                physical_key=args.key,
                layer=args.layer,
                variant=args.variant,
                **action,
            )
        )
        labeled_reports.append((f"experiment modified-wheel key {args.key} {action_name}", report))
        if not args.no_commit:
            labeled_reports.append(("commit", build_commit_report()))
    elif name == "swipe":
        action_name = _experiment_action(name, args)
        action = parse_mouse_action(action_name)
        if action.get("page") != 4:
            raise argparse.ArgumentTypeError("swipe experiment action must be a swipe action")
        report = build_mouse_report(
            MouseRemap(
                physical_key=args.key,
                layer=args.layer,
                variant=args.variant,
                **action,
            )
        )
        labeled_reports.append((f"experiment swipe key {args.key} {action_name}", report))
        if not args.no_commit:
            labeled_reports.append(("commit", build_commit_report()))
    elif name == "led-mode":
        color = parse_rgb_color(args.color)
        report = build_led_report(
            LedConfig(
                layer=args.led_layer,
                mode=args.mode,
                colors=(color,) * 16,
            )
        )
        labeled_reports.append((f"experiment led-mode layer {args.led_layer}", report))
        if args.commit_led:
            labeled_reports.append(("commit", build_commit_report()))
    return labeled_reports, _experiment_instruction(name, args)


def cmd_experiment(args: argparse.Namespace) -> int:
    labeled_reports, instruction = _build_experiment_reports(args)
    print(f"Experiment: {args.name}")
    print(f"Purpose: {EXPERIMENTS[args.name]}")
    print(f"Physical check: {instruction}")
    print("Suggested safety loop:")
    print("  1. snapshot --json snapshots/before.json")
    print("  2. run this experiment with --write --yes")
    print("  3. snapshot --json snapshots/after.json")
    print("  4. diff-snapshot snapshots/before.json snapshots/after.json")
    print(f"  5. {_experiment_restore_hint(args.name, args)}")
    return write_labeled_reports(args, labeled_reports, success="Experiment reports written.")


def _sequence_tokens_from_response(response: bytes) -> list[int]:
    if len(response) < 10:
        return []
    count = response[6]
    tokens = []
    for index in range(min(count, 18)):
        offset = 9 + (index * 3)
        if offset >= len(response):
            break
        tokens.append(response[offset])
    return tokens


def _sequence_delays_from_response(response: bytes) -> list[int]:
    if len(response) < 10:
        return []
    count = response[6]
    delays = []
    for index in range(min(count, 18)):
        offset = 7 + (index * 3)
        if offset + 1 >= len(response):
            break
        delays.append((response[offset] << 8) | response[offset + 1])
    return delays


def _token_names_from_response(response: bytes) -> list[str]:
    return [token_name(token) for token in _sequence_tokens_from_response(response)]


def _format_sequence_tokens(tokens: list[int]) -> str:
    if not tokens:
        return "-"

    steps: list[str] = []
    pending_modifiers: list[str] = []
    for token in tokens:
        name = token_name(token)
        if modifier_token_name(token) is not None:
            pending_modifiers.append(name)
            continue
        if pending_modifiers:
            steps.append("+".join([*pending_modifiers, name]))
            pending_modifiers = []
        else:
            steps.append(name)

    steps.extend(pending_modifiers)
    return ", ".join(steps)


def _canonical_media_name(usage: int) -> str:
    return media_usage_name(usage)


def _decode_mouse_wheel(value: int) -> int:
    return -1 if value == 0xFF else value


def _mouse_button_name(button: int) -> str:
    names = {
        1: "left-click",
        2: "right-click",
        4: "middle-click",
    }
    return names.get(button, f"button-0x{button:02x}")


def _wheel_action_name(wheel: int) -> str:
    if wheel == -1:
        return "wheel-negative"
    if wheel == 1:
        return "wheel-positive"
    return f"wheel-{wheel:+d}"


def _swipe_action_name(swipe: int) -> str:
    names = {
        1: "like",
        2: "swipe-left",
        3: "swipe-right",
        4: "swipe-up",
        5: "swipe-down",
    }
    return names.get(swipe, f"swipe-0x{swipe:02x}")


def _mouse_action_from_response(response: bytes) -> str | None:
    if len(response) <= 21:
        return None

    page = response[5]
    if page == 1:
        button = response[12]
        wheel_modifier = response[9]
        wheel = _decode_mouse_wheel(response[21])
        actions: list[str] = []
        if button:
            actions.append(_mouse_button_name(button))
        if wheel:
            wheel_action = _wheel_action_name(wheel)
            modifier = modifier_token_name(wheel_modifier)
            if modifier is not None:
                wheel_action = f"{modifier}-{wheel_action}"
            elif wheel_modifier:
                wheel_action = f"mod-0x{wheel_modifier:02x}-{wheel_action}"
            actions.append(wheel_action)
        return ", ".join(actions) if actions else "none"

    if page == 4:
        return _swipe_action_name(response[9])

    return None


def _summarize_config_response(response: bytes) -> str:
    if len(response) < 10:
        return f"short response ({len(response)} bytes)"
    slot = response[2]
    layer = response[3] - 1 if 1 <= response[3] <= 3 else response[3]
    mode = response[4]
    page = response[5]
    count = response[6]
    sequence_tokens = _sequence_tokens_from_response(response)
    tokens = " ".join(f"{token:02x}" for token in sequence_tokens)
    delays = _sequence_delays_from_response(response)
    if not tokens:
        tokens = "-"
    summary = (
        f"slot {slot:02d} layer {layer} mode {mode:02x} "
        f"page {page:02x} count {count:02x} tokens {tokens}"
    )
    if mode in (MODE_BASIC, MODE_MACRO):
        summary += f" keys={_format_sequence_tokens(sequence_tokens)}"
    if any(delays):
        summary += " delays=" + ",".join(str(delay) for delay in delays)
    if mode == MODE_FUNCTION and len(response) > 12 and count == 2:
        usage = response[9] | (response[12] << 8)
        summary += f" media={_canonical_media_name(usage)}(0x{usage:04x})"
    if mode == MODE_MOUSE and len(response) > 21:
        wheel = _decode_mouse_wheel(response[21])
        if page == 1:
            summary += (
                f" mouse(button={response[12]}, "
                f"wheel_modifier=0x{response[9]:02x}, wheel={wheel})"
            )
        elif page == 4:
            summary += f" swipe={response[9]}"
        action = _mouse_action_from_response(response)
        if action is not None:
            summary += f" action={action}"
    return summary


def _config_response_to_dict(response: bytes) -> dict[str, object]:
    item: dict[str, object] = {
        "raw": response.hex(" "),
        "length": len(response),
        "summary": _summarize_config_response(response),
    }
    if len(response) < 10:
        item["error"] = "short response"
        return item

    slot = response[2]
    layer = response[3] - 1 if 1 <= response[3] <= 3 else response[3]
    mode = response[4]
    page = response[5]
    count = response[6]
    tokens = _sequence_tokens_from_response(response)
    delays = _sequence_delays_from_response(response)
    item.update(
        {
            "slot": slot,
            "slot_label": SLOT_LABELS.get(slot, f"slot-{slot}"),
            "layer": layer,
            "mode": mode,
            "page": page,
            "count": count,
            "tokens": tokens,
            "token_hex": [f"0x{token:02x}" for token in tokens],
            "token_names": _token_names_from_response(response),
            "keys": _format_sequence_tokens(tokens),
            "delays_ms": delays,
        }
    )

    if mode == MODE_FUNCTION and len(response) > 12 and count == 2:
        usage = response[9] | (response[12] << 8)
        item["media"] = {
            "usage": usage,
            "usage_hex": f"0x{usage:04x}",
            "name": _canonical_media_name(usage),
        }
    elif mode == MODE_MOUSE and len(response) > 21:
        mouse: dict[str, object] = {"page": page}
        action = _mouse_action_from_response(response)
        if action is not None:
            mouse["action"] = action
        if page == 1:
            mouse.update(
                {
                    "button": response[12],
                    "wheel_modifier": response[9],
                    "wheel_modifier_hex": f"0x{response[9]:02x}",
                    "wheel": _decode_mouse_wheel(response[21]),
                }
            )
        elif page == 4:
            mouse["swipe"] = response[9]
        item["mouse"] = mouse
    return item


def _led_response_to_dict(layer: int, response: bytes) -> dict[str, object]:
    item: dict[str, object] = {
        "layer": layer,
        "raw": response.hex(" "),
        "length": len(response),
    }
    try:
        mode, colors = parse_led_response(response)
    except ValueError as exc:
        item["error"] = str(exc)
        return item

    item["mode"] = mode
    item["colors"] = [f"#{red:02x}{green:02x}{blue:02x}" for red, green, blue in colors]
    item["summary"] = f"LED layer {layer} mode {mode}: {', '.join(item['colors'])}"
    return item


def _print_snapshot_summary(result: dict[str, object]) -> None:
    print("Configuration records:")
    records = result["config"]
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        print(record.get("summary", "unparsed record"))

    leds = result.get("led")
    if not leds:
        return
    print()
    print("LED layers:")
    assert isinstance(leds, list)
    for led in leds:
        assert isinstance(led, dict)
        colors = led.get("colors")
        if isinstance(colors, list) and colors:
            preview = ", ".join(str(color) for color in colors[:4])
            if len(colors) > 4:
                preview += ", ..."
            print(f"layer {led.get('layer')} mode {led.get('mode')}: {preview}")
        else:
            print(f"layer {led.get('layer')}: {led.get('error', 'unparsed LED response')}")


def _read_device_snapshot(
    args: argparse.Namespace,
    pages: tuple[int, ...] = (1,),
    count: int = 0x19,
    bank: int = 0,
    led_layers: tuple[int, ...] = (0, 1, 2),
    include_led: bool = True,
) -> dict[str, object]:
    result: dict[str, object] = {
        "device": {
            "vid": f"0x{args.vid:04x}",
            "pid": f"0x{args.pid:04x}",
            "usage_page": f"0x{args.usage_page:04x}",
        },
        "config": [],
        "led": [],
    }
    config_records = result["config"]
    led_records = result["led"]
    assert isinstance(config_records, list)
    assert isinstance(led_records, list)

    with HidAPI(args.hidapi).open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        for page in pages:
            device.write(build_read_config_request(page, count, bank))
            for _ in range(1, count + 1):
                response = device.read_timeout(64, args.timeout)
                if not response:
                    break
                config_records.append(_config_response_to_dict(response))

        if include_led:
            for layer in led_layers:
                device.write(build_read_led_request(layer))
                response = device.read_timeout(64, args.timeout)
                if not response:
                    led_records.append(
                        {
                            "layer": layer,
                            "error": "no response before timeout",
                            "length": 0,
                            "raw": "",
                        }
                    )
                    continue
                led_records.append(_led_response_to_dict(layer, response))
    return result


TESTED_CONFIG_EXPECTATIONS = (
    {
        "label": "slot 12 layer 0 Shift+A",
        "slot": 12,
        "layer": 0,
        "mode": MODE_BASIC,
        "tokens": [0xF2, 0x04],
    },
    {
        "label": "top-left volume-down",
        "slot": 16,
        "layer": 0,
        "mode": MODE_FUNCTION,
        "media_usage": 0x00EA,
    },
    {
        "label": "top-click mute",
        "slot": 17,
        "layer": 0,
        "mode": MODE_FUNCTION,
        "media_usage": 0x00E2,
    },
    {
        "label": "top-right volume-up",
        "slot": 18,
        "layer": 0,
        "mode": MODE_FUNCTION,
        "media_usage": 0x00E9,
    },
    {
        "label": "bottom-left wheel-negative",
        "slot": 19,
        "layer": 0,
        "mode": MODE_MOUSE,
        "page": 1,
        "mouse": {"button": 0, "wheel_modifier": 0, "wheel": -1},
    },
    {
        "label": "bottom-click left-click",
        "slot": 20,
        "layer": 0,
        "mode": MODE_MOUSE,
        "page": 1,
        "mouse": {"button": 1, "wheel_modifier": 0, "wheel": 0},
    },
    {
        "label": "bottom-right wheel-positive",
        "slot": 21,
        "layer": 0,
        "mode": MODE_MOUSE,
        "page": 1,
        "mouse": {"button": 0, "wheel_modifier": 0, "wheel": 1},
    },
)

TESTED_LED_EXPECTATIONS = (
    {"label": "LED layer 0 red", "layer": 0, "mode": 1, "color": "#ff0000"},
    {"label": "LED layer 1 green", "layer": 1, "mode": 1, "color": "#00ff00"},
    {"label": "LED layer 2 blue", "layer": 2, "mode": 1, "color": "#0000ff"},
)


def _find_config_record(snapshot: dict[str, object], layer: int, slot: int) -> dict[str, object] | None:
    for item in _snapshot_records(snapshot, "config"):
        if item.get("layer") == layer and item.get("slot") == slot:
            return item
    return None


def _find_led_record(snapshot: dict[str, object], layer: int) -> dict[str, object] | None:
    for item in _snapshot_records(snapshot, "led"):
        if item.get("layer") == layer:
            return item
    return None


def _verify_config_expectation(
    snapshot: dict[str, object],
    expected: dict[str, object],
) -> tuple[bool, str, str]:
    label = str(expected["label"])
    item = _find_config_record(snapshot, int(expected["layer"]), int(expected["slot"]))
    if item is None:
        return False, label, "missing record"

    mismatches = []
    if item.get("mode") != expected.get("mode"):
        mismatches.append(f"mode expected {expected.get('mode')} got {item.get('mode')}")
    if "page" in expected and item.get("page") != expected["page"]:
        mismatches.append(f"page expected {expected['page']} got {item.get('page')}")
    if "tokens" in expected and item.get("tokens") != expected["tokens"]:
        mismatches.append(f"tokens expected {expected['tokens']} got {item.get('tokens')}")
    if "media_usage" in expected:
        media = item.get("media")
        usage = media.get("usage") if isinstance(media, dict) else None
        if usage != expected["media_usage"]:
            mismatches.append(f"media expected 0x{int(expected['media_usage']):04x} got {usage}")
    if "mouse" in expected:
        mouse = item.get("mouse")
        for key, value in expected["mouse"].items():
            actual = mouse.get(key) if isinstance(mouse, dict) else None
            if actual != value:
                mismatches.append(f"mouse.{key} expected {value} got {actual}")

    if mismatches:
        return False, label, "; ".join(mismatches)
    return True, label, str(item.get("summary", "ok"))


def _verify_led_expectation(
    snapshot: dict[str, object],
    expected: dict[str, object],
) -> tuple[bool, str, str]:
    label = str(expected["label"])
    item = _find_led_record(snapshot, int(expected["layer"]))
    if item is None:
        return False, label, "missing LED record"
    colors = item.get("colors")
    expected_colors = [expected["color"]] * 16
    mismatches = []
    if item.get("mode") != expected["mode"]:
        mismatches.append(f"mode expected {expected['mode']} got {item.get('mode')}")
    if colors != expected_colors:
        mismatches.append(f"colors expected all {expected['color']} got {colors}")
    if mismatches:
        return False, label, "; ".join(mismatches)
    return True, label, str(item.get("summary", "ok"))


def _verify_tested_profile(
    snapshot: dict[str, object],
    include_led: bool = True,
) -> list[tuple[bool, str, str]]:
    results = [
        _verify_config_expectation(snapshot, expected)
        for expected in TESTED_CONFIG_EXPECTATIONS
    ]
    if include_led:
        results.extend(
            _verify_led_expectation(snapshot, expected)
            for expected in TESTED_LED_EXPECTATIONS
        )
    return results


def cmd_verify_current(args: argparse.Namespace) -> int:
    snapshot = _read_device_snapshot(args, include_led=not args.no_led)
    results = _verify_tested_profile(snapshot, include_led=not args.no_led)
    failures = 0
    for ok, label, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"{status:4s} {label}: {detail}")
        if not ok:
            failures += 1
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        print(f"Snapshot JSON written: {args.json}")
    if failures:
        print(f"{failures} check(s) failed.")
        return 1
    print("All tested-profile checks passed.")
    return 0


def _read_config_requested_keys(args: argparse.Namespace) -> tuple[int, ...] | None:
    slots: list[int] = []
    key_value = getattr(args, "key", None)
    if isinstance(key_value, int):
        slots.append(key_value)
    elif key_value:
        slots.extend(key_value)
    keys_value = getattr(args, "keys", None)
    if keys_value:
        slots.extend(keys_value)
    if not slots:
        return None
    return tuple(dict.fromkeys(slots))


def cmd_read_config(args: argparse.Namespace) -> int:
    request = build_read_config_request(args.page, args.count, args.bank)
    requested_keys = _read_config_requested_keys(args)
    print("Config read request:")
    print(hex_dump(request))

    printed = 0
    matched_slots: set[int] = set()
    with HidAPI(args.hidapi).open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        written = device.write(request)
        print(f"Wrote {written} bytes.")
        for index in range(1, args.count + 1):
            response = device.read_timeout(64, args.timeout)
            if not response:
                print(f"No response for record {index} before timeout.")
                break
            slot = response[2] if len(response) > 2 else index
            if requested_keys is not None and slot not in requested_keys:
                continue
            printed += 1
            matched_slots.add(slot)
            print(_summarize_config_response(response))
            if args.verbose:
                print(hex_dump(response))
    if requested_keys is not None and printed == 0:
        requested = ", ".join(str(slot) for slot in requested_keys)
        print(f"No matching slot(s) {requested} in page {args.page}.")
        return 1
    if requested_keys is not None:
        missing = [slot for slot in requested_keys if slot not in matched_slots]
        if missing:
            print(
                f"Missing slot(s) in page {args.page}: "
                f"{', '.join(str(slot) for slot in missing)}"
            )
            return 1
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    result: dict[str, object] = {
        "device": {
            "vid": f"0x{args.vid:04x}",
            "pid": f"0x{args.pid:04x}",
            "usage_page": f"0x{args.usage_page:04x}",
        },
        "config": [],
        "led": [],
    }
    config_records = result["config"]
    led_records = result["led"]
    assert isinstance(config_records, list)
    assert isinstance(led_records, list)

    with HidAPI(args.hidapi).open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        for page in args.pages:
            request = build_read_config_request(page, args.count, args.bank)
            written = device.write(request)
            if args.verbose:
                print(f"Config page {page}: wrote {written} bytes.")
            for index in range(1, args.count + 1):
                response = device.read_timeout(64, args.timeout)
                if not response:
                    print(f"No response for page {page} record {index} before timeout.")
                    break
                config_records.append(_config_response_to_dict(response))

        if not args.no_led:
            for layer in args.led_layers:
                request = build_read_led_request(layer)
                written = device.write(request)
                if args.verbose:
                    print(f"LED layer {layer}: wrote {written} bytes.")
                response = device.read_timeout(64, args.timeout)
                if not response:
                    led_records.append(
                        {
                            "layer": layer,
                            "error": "no response before timeout",
                            "length": 0,
                            "raw": "",
                        }
                    )
                    continue
                led_records.append(_led_response_to_dict(layer, response))

    _print_snapshot_summary(result)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print()
        print(f"Snapshot JSON written: {args.json}")
    return 0


def _load_snapshot(path: Path) -> dict[str, object]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise argparse.ArgumentTypeError(f"could not read snapshot: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid snapshot JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise argparse.ArgumentTypeError("snapshot JSON must be an object")
    return loaded


def _snapshot_records(snapshot: dict[str, object], key: str) -> list[dict[str, object]]:
    value = snapshot.get(key)
    if not isinstance(value, list):
        raise argparse.ArgumentTypeError(f"snapshot JSON is missing a {key} list")
    return [item for item in value if isinstance(item, dict)]


def _snapshot_config_key(item: dict[str, object]) -> tuple[int, int]:
    return _snapshot_int(item, "layer"), _snapshot_int(item, "slot")


def _snapshot_led_key(item: dict[str, object]) -> int:
    return _snapshot_int(item, "layer")


def _config_report_from_snapshot_item(item: dict[str, object]) -> bytes:
    raw = item.get("raw")
    if not isinstance(raw, str):
        raise ValueError("config snapshot item is missing raw bytes")
    try:
        response = bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError("config snapshot raw bytes are not valid hex") from exc
    if len(response) < 10:
        raise ValueError("config snapshot response is too short")
    if response[0] != REPORT_ID:
        raise ValueError("config snapshot response has an unexpected report ID")

    report = bytearray(REPORT_LEN)
    report[0] = REPORT_ID
    report[1] = 0xFD
    payload = response[2:]
    report[2 : 2 + min(len(payload), REPORT_LEN - 2)] = payload[: REPORT_LEN - 2]
    return bytes(report)


def _led_report_from_snapshot_item(item: dict[str, object]) -> bytes:
    layer = _snapshot_int(item, "layer")
    mode = _snapshot_int(item, "mode")
    colors_value = item.get("colors")
    if not isinstance(colors_value, list):
        raise ValueError("LED snapshot item is missing colors")
    colors = tuple(parse_rgb_color(str(color)) for color in colors_value)
    return build_led_report(LedConfig(layer=layer, mode=mode, colors=colors))


def _snapshot_config_matches(item: dict[str, object], args: argparse.Namespace) -> bool:
    if args.key is not None and item.get("slot") != args.key:
        return False
    if args.layer is not None and item.get("layer") != args.layer:
        return False
    return True


def _snapshot_led_matches(item: dict[str, object], args: argparse.Namespace) -> bool:
    if args.led_layers is None:
        return True
    return item.get("layer") in args.led_layers


def _snapshot_label(item: dict[str, object]) -> str:
    summary = item.get("summary")
    if isinstance(summary, str):
        return summary
    slot = item.get("slot", "?")
    layer = item.get("layer", "?")
    mode = item.get("mode", "?")
    return f"slot {slot} layer {layer} mode {mode}"


def _write_snapshot_reports(
    args: argparse.Namespace,
    labeled_reports: list[tuple[str, bytes]],
    config_count: int,
    title: str = "Snapshot reports selected",
    success_subject: str = "Snapshot reports written",
) -> int:
    print(f"{title}: {len(labeled_reports)}")
    for index, (label, report) in enumerate(labeled_reports, start=1):
        print(f"{index:3d}. {label} ({len(report)} bytes)")
        if args.verbose:
            print(hex_dump(report))

    if not args.write:
        print("\nDry run only. Add --write --yes to send these reports.")
        return 0
    if not args.yes:
        print("Refusing to write without --yes.", file=sys.stderr)
        return 2

    api = HidAPI(args.hidapi)
    with api.open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        for _, report in labeled_reports:
            written = device.write(report)
            if written != len(report):
                print(
                    f"Warning: hid_write returned {written}, expected {len(report)}",
                    file=sys.stderr,
                )
    restored = f"{config_count} config record(s)"
    led_count = len(labeled_reports) - config_count - (0 if args.no_commit else 1 if config_count else 0)
    if led_count:
        restored += f" and {led_count} LED layer(s)"
    print(f"{success_subject}: {restored}.")
    return 0


def cmd_restore_snapshot(args: argparse.Namespace) -> int:
    snapshot = _load_snapshot(args.json)
    labeled_reports: list[tuple[str, bytes]] = []
    config_count = 0

    if not args.no_config:
        config = snapshot.get("config")
        if not isinstance(config, list):
            raise argparse.ArgumentTypeError("snapshot JSON is missing a config list")
        for item in config:
            if not isinstance(item, dict):
                continue
            if not _snapshot_config_matches(item, args):
                continue
            try:
                report = _config_report_from_snapshot_item(item)
            except ValueError as exc:
                raise argparse.ArgumentTypeError(str(exc)) from exc
            labeled_reports.append((f"config: {_snapshot_label(item)}", report))
            config_count += 1

    if args.include_led:
        leds = snapshot.get("led")
        if not isinstance(leds, list):
            raise argparse.ArgumentTypeError("snapshot JSON is missing an LED list")
        for item in leds:
            if not isinstance(item, dict):
                continue
            if not _snapshot_led_matches(item, args):
                continue
            try:
                report = _led_report_from_snapshot_item(item)
            except ValueError as exc:
                raise argparse.ArgumentTypeError(str(exc)) from exc
            labeled_reports.append((f"LED layer {item.get('layer')} mode {item.get('mode')}", report))

    if config_count and not args.no_commit:
        labeled_reports.append(("commit", build_commit_report()))
    if not labeled_reports:
        raise argparse.ArgumentTypeError("snapshot filters did not select any writable records")
    return _write_snapshot_reports(args, labeled_reports, config_count)


PROFILE_DESCRIPTIONS = {
    "verified-controls": (
        "physically verified layer-0 slot 12, knob media/mouse mappings, and "
        "RGB LED layers"
    ),
    "tested-12key-baseline": (
        "verified-controls plus the tested 12-key layer-0 number/symbol layout"
    ),
}

PROFILE_BASE_KEYS = (
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
    (5, "5"),
    (6, "6"),
    (7, "7"),
    (8, "8"),
    (9, "9"),
    (10, "0"),
    (11, "-"),
)


def _build_profile_reports(args: argparse.Namespace) -> tuple[list[tuple[str, bytes]], int]:
    name = args.name
    if name not in PROFILE_DESCRIPTIONS:
        raise argparse.ArgumentTypeError(f"unknown profile: {name}")

    labeled_reports: list[tuple[str, bytes]] = []
    config_count = 0

    if not args.no_config:
        if name == "tested-12key-baseline":
            for slot, key_name in PROFILE_BASE_KEYS:
                keycode = parse_keycode(key_name)
                labeled_reports.append(
                    (
                        f"profile {name}: slot {slot:02d} -> {key_name}",
                        build_basic_report(BasicRemap(slot, 0, keycode)),
                    )
                )
                config_count += 1

        labeled_reports.extend(
            [
                (
                    f"profile {name}: slot 12 -> shift+a",
                    build_sequence_report(
                        SequenceRemap(
                            physical_key=12,
                            layer=0,
                            mode=MODE_BASIC,
                            tokens=(0xF2, 0x04),
                        )
                    ),
                ),
                (
                    f"profile {name}: top-left -> volume-down",
                    build_media_report(16, 0, 0x00EA),
                ),
                (
                    f"profile {name}: top-click -> mute",
                    build_media_report(17, 0, 0x00E2),
                ),
                (
                    f"profile {name}: top-right -> volume-up",
                    build_media_report(18, 0, 0x00E9),
                ),
                (
                    f"profile {name}: bottom-left -> wheel-negative",
                    build_mouse_report(MouseRemap(physical_key=19, layer=0, page=1, wheel=-1)),
                ),
                (
                    f"profile {name}: bottom-click -> left-click",
                    build_mouse_report(MouseRemap(physical_key=20, layer=0, page=1, button=1)),
                ),
                (
                    f"profile {name}: bottom-right -> wheel-positive",
                    build_mouse_report(MouseRemap(physical_key=21, layer=0, page=1, wheel=1)),
                ),
            ]
        )
        config_count += 7

    if not args.no_led:
        led_colors = (
            (0, 1, (0xFF, 0x00, 0x00), "red"),
            (1, 1, (0x00, 0xFF, 0x00), "green"),
            (2, 1, (0x00, 0x00, 0xFF), "blue"),
        )
        for layer, mode, color, color_name in led_colors:
            labeled_reports.append(
                (
                    f"profile {name}: LED layer {layer} -> {color_name}",
                    build_led_report(LedConfig(layer=layer, mode=mode, colors=(color,) * 16)),
                )
            )

    if config_count and not args.no_commit:
        labeled_reports.append(("commit", build_commit_report()))
    if not labeled_reports:
        raise argparse.ArgumentTypeError("profile filters did not select any writable records")
    return labeled_reports, config_count


def cmd_profiles(args: argparse.Namespace) -> int:
    for name, description in PROFILE_DESCRIPTIONS.items():
        print(f"{name:22s} {description}")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    labeled_reports, config_count = _build_profile_reports(args)
    print(f"Profile: {args.name}")
    print(f"Purpose: {PROFILE_DESCRIPTIONS[args.name]}")
    return _write_snapshot_reports(
        args,
        labeled_reports,
        config_count,
        title="Profile reports selected",
        success_subject="Profile reports written",
    )


def _snapshot_raw(item: dict[str, object]) -> str:
    raw = item.get("raw")
    return raw if isinstance(raw, str) else ""


def _snapshot_media_usage(item: dict[str, object]) -> int | None:
    media = item.get("media")
    if not isinstance(media, dict):
        return None
    usage = media.get("usage")
    return usage if isinstance(usage, int) else None


def _snapshot_mouse_signature(item: dict[str, object]) -> tuple[object, ...] | None:
    mouse = item.get("mouse")
    if not isinstance(mouse, dict):
        return None
    page = item.get("page")
    if page == 1:
        return (
            page,
            mouse.get("button"),
            mouse.get("wheel_modifier"),
            mouse.get("wheel"),
        )
    if page == 4:
        return (page, mouse.get("swipe"))
    return (page, tuple(sorted(mouse.items())))


def _config_semantic_signature(item: dict[str, object]) -> tuple[object, ...]:
    mode = item.get("mode")
    base = (item.get("slot"), item.get("layer"), mode)
    if mode == MODE_FUNCTION:
        usage = _snapshot_media_usage(item)
        if usage is not None:
            return base + ("media", usage)
    if mode == MODE_MOUSE:
        return base + ("mouse", _snapshot_mouse_signature(item))
    if mode in (MODE_BASIC, MODE_MACRO):
        return base + (
            "sequence",
            tuple(item.get("tokens", ())),
            tuple(item.get("delays_ms", ())),
        )
    return base + (
        "raw-fields",
        item.get("page"),
        item.get("count"),
        tuple(item.get("tokens", ())),
        tuple(item.get("delays_ms", ())),
    )


def _diff_snapshot_config(
    before: dict[str, object],
    after: dict[str, object],
    args: argparse.Namespace,
) -> list[str]:
    before_items = {
        _snapshot_config_key(item): item
        for item in _snapshot_records(before, "config")
        if _snapshot_config_matches(item, args)
    }
    after_items = {
        _snapshot_config_key(item): item
        for item in _snapshot_records(after, "config")
        if _snapshot_config_matches(item, args)
    }

    lines: list[str] = []
    for layer, slot in sorted(set(before_items) | set(after_items)):
        before_item = before_items.get((layer, slot))
        after_item = after_items.get((layer, slot))
        label = f"slot {slot:02d} layer {layer}"
        if before_item is None:
            lines.append(f"+ config {label}: {after_item.get('summary', 'added')}")
        elif after_item is None:
            lines.append(f"- config {label}: {before_item.get('summary', 'removed')}")
        elif _snapshot_raw(before_item) != _snapshot_raw(after_item):
            if getattr(args, "semantic", False) and (
                _config_semantic_signature(before_item)
                == _config_semantic_signature(after_item)
            ):
                continue
            lines.append(f"~ config {label}:")
            lines.append(f"  before: {before_item.get('summary', _snapshot_raw(before_item))}")
            lines.append(f"  after:  {after_item.get('summary', _snapshot_raw(after_item))}")
    return lines


def _diff_snapshot_led(
    before: dict[str, object],
    after: dict[str, object],
    args: argparse.Namespace,
) -> list[str]:
    before_items = {
        _snapshot_led_key(item): item
        for item in _snapshot_records(before, "led")
        if _snapshot_led_matches(item, args)
    }
    after_items = {
        _snapshot_led_key(item): item
        for item in _snapshot_records(after, "led")
        if _snapshot_led_matches(item, args)
    }

    lines: list[str] = []
    for layer in sorted(set(before_items) | set(after_items)):
        before_item = before_items.get(layer)
        after_item = after_items.get(layer)
        label = f"LED layer {layer}"
        if before_item is None:
            lines.append(f"+ {label}: {after_item.get('summary', 'added')}")
        elif after_item is None:
            lines.append(f"- {label}: {before_item.get('summary', 'removed')}")
        elif (
            before_item.get("mode") != after_item.get("mode")
            or before_item.get("colors") != after_item.get("colors")
        ):
            lines.append(f"~ {label}:")
            lines.append(
                f"  before: mode {before_item.get('mode')} colors {before_item.get('colors')}"
            )
            lines.append(
                f"  after:  mode {after_item.get('mode')} colors {after_item.get('colors')}"
            )
    return lines


def cmd_diff_snapshot(args: argparse.Namespace) -> int:
    before = _load_snapshot(args.before)
    after = _load_snapshot(args.after)
    lines: list[str] = []
    if not args.no_config:
        lines.extend(_diff_snapshot_config(before, after, args))
    if not args.no_led:
        lines.extend(_diff_snapshot_led(before, after, args))

    if lines:
        print("\n".join(lines))
        return 1 if args.exit_code else 0
    print("No differences.")
    return 0


def _led_colors(args: argparse.Namespace) -> tuple[tuple[int, int, int], ...]:
    if args.colors:
        colors = tuple(parse_rgb_color(color) for color in args.colors)
        if len(colors) != 16:
            raise argparse.ArgumentTypeError("--colors must contain exactly 16 RGB colors")
        return colors
    color = parse_rgb_color(args.color)
    return (color,) * 16


def cmd_led(args: argparse.Namespace) -> int:
    try:
        colors = _led_colors(args)
        report = build_led_report(
            LedConfig(
                layer=args.layer,
                mode=args.mode,
                colors=colors,
            )
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    print(
        f"LED layer {args.layer}: mode {args.mode}, "
        f"{'16 custom colors' if args.colors else f'fill {args.color}'}"
    )
    labeled_reports = [("led", report)]
    if args.commit:
        labeled_reports.append(("commit", build_commit_report()))
    return write_labeled_reports(args, labeled_reports)


def cmd_led_read(args: argparse.Namespace) -> int:
    request = build_read_led_request(args.layer)
    print("LED read request:")
    print(hex_dump(request))
    with HidAPI(args.hidapi).open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        written = device.write(request)
        print(f"Wrote {written} bytes.")
        response = device.read_timeout(64, args.timeout)
    if not response:
        print("No response before timeout.")
        return 1
    print("LED response:")
    print(hex_dump(response))
    try:
        mode, colors = parse_led_response(response)
    except ValueError as exc:
        print(f"Could not parse LED response: {exc}")
        return 1
    print(f"LED mode: {mode}")
    for index, (red, green, blue) in enumerate(colors, start=1):
        print(f"{index:2d}: #{red:02x}{green:02x}{blue:02x}")
    return 0


TEST_PATTERN = (
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
    (5, "5"),
    (6, "6"),
    (7, "7"),
    (8, "8"),
    (9, "9"),
    (10, "0"),
    (11, "-"),
    (12, "="),
)

EXTRA_PATTERN = (
    (16, "0"),
    (17, "1"),
    (18, "2"),
    (19, "3"),
    (20, "4"),
    (21, "5"),
)


def _write_pattern(args: argparse.Namespace, pattern: tuple[tuple[int, str], ...], title: str) -> int:
    reports: list[tuple[str, bytes]] = []
    for slot, key_name in pattern:
        slot_label = SLOT_LABELS.get(slot, f"slot {slot}")
        remap = BasicRemap(
            physical_key=slot,
            layer=args.layer,
            keycode=parse_keycode(key_name),
            variant=args.variant,
            mode=args.mode,
        )
        reports.append((f"{slot_label} ({slot}) -> {key_name}", build_basic_report(remap)))
    if not args.no_commit:
        reports.append(("commit", build_commit_report()))

    print(f"{title} for layer {args.layer}, variant {args.variant}:")
    for label, report in reports:
        print(f"\n{label} ({len(report)} bytes):")
        print(hex_dump(report))

    if not args.write:
        print("\nDry run only. Add --write --yes to send these reports.")
        return 0
    if not args.yes:
        print("Refusing to write without --yes.", file=sys.stderr)
        return 2

    api = HidAPI(args.hidapi)
    with api.open_device(args.vid, args.pid, args.usage_page, args.path) as device:
        for _, report in reports:
            written = device.write(report)
            if written != len(report):
                print(
                    f"Warning: hid_write returned {written}, expected {len(report)}",
                    file=sys.stderr,
                )
    print("Test pattern written.")
    return 0


def cmd_test_pattern(args: argparse.Namespace) -> int:
    return _write_pattern(
        args,
        TEST_PATTERN,
        "Test pattern",
    )


def cmd_extra_pattern(args: argparse.Namespace) -> int:
    return _write_pattern(
        args,
        EXTRA_PATTERN,
        "Extra-control probe pattern",
    )


def cmd_gui(args: argparse.Namespace) -> int:
    from .gui import run

    run(
        vid=args.vid,
        pid=args.pid,
        usage_page=args.usage_page,
        hidapi_path=args.hidapi,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mini-keyboard-tool",
        description="Experimental CLI-first configurator for the MINI_KEYBOARD HID protocol.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List HID devices")
    add_hid_args(list_parser)
    list_parser.add_argument("--all", action="store_true", help="List every HID device")
    list_parser.set_defaults(func=cmd_list)

    info_parser = subparsers.add_parser("info", help="Send the app's model probe")
    add_hid_args(info_parser)
    info_parser.add_argument("--timeout", type=int, default=1000, help="Read timeout ms")
    info_parser.set_defaults(func=cmd_info)

    read_config_parser = subparsers.add_parser(
        "read-config", help="Read raw key configuration records"
    )
    add_hid_args(read_config_parser)
    read_config_parser.add_argument("--page", type=parse_number, default=1)
    read_config_parser.add_argument("--count", type=parse_number, default=0x19)
    read_config_parser.add_argument("--bank", type=parse_number, default=0)
    read_config_parser.add_argument(
        "--key",
        type=parse_key_slot,
        action="append",
        help="filter to one slot or alias; repeatable, e.g. --key 2 --key top-click",
    )
    read_config_parser.add_argument(
        "--keys",
        type=parse_key_slots,
        help="comma-separated slots or .. ranges, e.g. 2..5,top-left",
    )
    read_config_parser.add_argument("--timeout", type=int, default=1000, help="Read timeout ms")
    read_config_parser.add_argument("--verbose", action="store_true")
    read_config_parser.set_defaults(func=cmd_read_config)

    verify_parser = subparsers.add_parser(
        "verify-current",
        help="Read the device and verify the known tested profile",
    )
    add_hid_args(verify_parser)
    verify_parser.add_argument("--timeout", type=int, default=1000, help="Read timeout ms")
    verify_parser.add_argument("--no-led", action="store_true")
    verify_parser.add_argument("--json", type=Path, help="Write the verification snapshot")
    verify_parser.set_defaults(func=cmd_verify_current)

    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help="Read key records and LED layers into a comparable snapshot",
    )
    add_hid_args(snapshot_parser)
    snapshot_parser.add_argument(
        "--pages",
        type=parse_number_list,
        default=(1, 2, 3),
        help="comma-separated config pages/layers to read, default: 1,2,3",
    )
    snapshot_parser.add_argument("--count", type=parse_number, default=0x19)
    snapshot_parser.add_argument("--bank", type=parse_number, default=0)
    snapshot_parser.add_argument(
        "--led-layers",
        type=parse_number_list,
        default=(0, 1, 2),
        help="comma-separated LED layers to read, default: 0,1,2",
    )
    snapshot_parser.add_argument("--no-led", action="store_true")
    snapshot_parser.add_argument("--timeout", type=int, default=1000, help="Read timeout ms")
    snapshot_parser.add_argument("--json", type=Path, help="Write JSON snapshot to this path")
    snapshot_parser.add_argument("--verbose", action="store_true")
    snapshot_parser.set_defaults(func=cmd_snapshot)

    diff_snapshot_parser = subparsers.add_parser(
        "diff-snapshot",
        help="Compare two snapshot JSON files",
    )
    diff_snapshot_parser.add_argument("before", type=Path)
    diff_snapshot_parser.add_argument("after", type=Path)
    diff_snapshot_parser.add_argument(
        "--key",
        type=parse_key_slot,
        help="compare only one config slot, e.g. 12 or top-click",
    )
    diff_snapshot_parser.add_argument(
        "--layer",
        type=parse_number,
        help="compare only one config layer, e.g. 0",
    )
    diff_snapshot_parser.add_argument("--no-config", action="store_true")
    diff_snapshot_parser.add_argument("--no-led", action="store_true")
    diff_snapshot_parser.add_argument(
        "--led-layers",
        type=parse_number_list,
        help="comma-separated LED layers to compare",
    )
    diff_snapshot_parser.add_argument(
        "--semantic",
        action="store_true",
        help=(
            "compare decoded behavior instead of raw config bytes; useful after "
            "restore when the device normalizes derived record fields"
        ),
    )
    diff_snapshot_parser.add_argument(
        "--exit-code",
        action="store_true",
        help="return exit code 1 when differences are found",
    )
    diff_snapshot_parser.set_defaults(func=cmd_diff_snapshot)

    restore_snapshot_parser = subparsers.add_parser(
        "restore-snapshot",
        help="Build or write config/LED reports from a snapshot JSON file",
    )
    add_hid_args(restore_snapshot_parser)
    restore_snapshot_parser.add_argument("--json", type=Path, required=True)
    restore_snapshot_parser.add_argument(
        "--key",
        type=parse_key_slot,
        help="restore only one config slot, e.g. 12 or top-click",
    )
    restore_snapshot_parser.add_argument(
        "--layer",
        type=parse_number,
        help="restore only one config layer, e.g. 0",
    )
    restore_snapshot_parser.add_argument(
        "--no-config",
        action="store_true",
        help="skip key config records",
    )
    restore_snapshot_parser.add_argument(
        "--include-led",
        action="store_true",
        help="also restore LED layers from the snapshot",
    )
    restore_snapshot_parser.add_argument(
        "--led-layers",
        type=parse_number_list,
        help="comma-separated LED layers to restore when --include-led is set",
    )
    restore_snapshot_parser.add_argument("--no-commit", action="store_true")
    restore_snapshot_parser.add_argument("--write", action="store_true", help="Send reports")
    restore_snapshot_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    restore_snapshot_parser.add_argument("--verbose", action="store_true")
    restore_snapshot_parser.set_defaults(func=cmd_restore_snapshot)

    profiles_parser = subparsers.add_parser(
        "profiles", help="List built-in tested restore profiles"
    )
    profiles_parser.set_defaults(func=cmd_profiles)

    profile_parser = subparsers.add_parser(
        "profile", help="Build or write one built-in tested restore profile"
    )
    add_hid_args(profile_parser)
    profile_parser.add_argument("--name", choices=tuple(PROFILE_DESCRIPTIONS), required=True)
    profile_parser.add_argument("--no-config", action="store_true", help="skip key config records")
    profile_parser.add_argument("--no-led", action="store_true", help="skip LED layer records")
    profile_parser.add_argument("--no-commit", action="store_true")
    profile_parser.add_argument("--write", action="store_true", help="Send reports")
    profile_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    profile_parser.add_argument("--verbose", action="store_true")
    profile_parser.set_defaults(func=cmd_profile)

    remap_parser = subparsers.add_parser(
        "remap", help="Build or write one basic key remap report"
    )
    add_hid_args(remap_parser)
    remap_parser.add_argument(
        "--key",
        type=parse_key_slot,
        required=True,
        help="device key slot or alias, e.g. 1, top-click, bottom-right",
    )
    remap_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    remap_parser.add_argument(
        "--to",
        help="Key name, chord, or numeric HID usage, e.g. a, shift+a, PrtScSysRq, or 0x04",
    )
    remap_parser.add_argument("--clear", action="store_true", help="Clear this key record")
    remap_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    remap_parser.add_argument("--mode", type=parse_number, default=1)
    remap_parser.add_argument("--no-commit", action="store_true")
    remap_parser.add_argument("--write", action="store_true", help="Send reports")
    remap_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    remap_parser.set_defaults(func=cmd_remap)

    clear_parser = subparsers.add_parser(
        "clear", help="Build or write empty records for one or more slots"
    )
    add_hid_args(clear_parser)
    clear_parser.add_argument(
        "--key",
        type=parse_key_slot,
        action="append",
        help="device key slot or alias; repeatable, e.g. --key 12 --key top-click",
    )
    clear_parser.add_argument(
        "--keys",
        type=parse_key_slots,
        help="comma-separated slots or .. ranges, e.g. 1..12,top-left,bottom-click",
    )
    clear_parser.add_argument(
        "--tested-12key",
        action="store_true",
        help="clear tested visible slots 1 through 12",
    )
    clear_parser.add_argument(
        "--include-knobs",
        action="store_true",
        help="also clear tested knob slots 16 through 21",
    )
    clear_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    clear_parser.add_argument("--all-layers", action="store_true", help="clear layers 0, 1, and 2")
    clear_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    clear_parser.add_argument("--mode", type=parse_number, default=1)
    clear_parser.add_argument("--no-commit", action="store_true")
    clear_parser.add_argument("--write", action="store_true", help="Send reports")
    clear_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    clear_parser.set_defaults(func=cmd_clear)

    keycodes_parser = subparsers.add_parser("keycodes", help="List known keycodes")
    keycodes_parser.add_argument("--filter")
    keycodes_parser.set_defaults(func=cmd_keycodes)

    vendor_key_aliases_parser = subparsers.add_parser(
        "vendor-key-aliases",
        help="List vendor basic-key button labels accepted by remap --to",
    )
    vendor_key_aliases_parser.add_argument("--filter")
    vendor_key_aliases_parser.add_argument("--json", action="store_true")
    vendor_key_aliases_parser.set_defaults(func=cmd_vendor_key_aliases)

    media_codes_parser = subparsers.add_parser(
        "media-codes", help="List known media/consumer usages"
    )
    media_codes_parser.add_argument("--filter")
    media_codes_parser.set_defaults(func=cmd_media_codes)

    mouse_actions_parser = subparsers.add_parser(
        "mouse-actions", help="List known mouse and swipe action names"
    )
    mouse_actions_parser.add_argument("--filter")
    mouse_actions_parser.set_defaults(func=cmd_mouse_actions)

    vendor_models_parser = subparsers.add_parser(
        "vendor-models", help="List keyboard model strings found in the vendor app"
    )
    vendor_models_parser.add_argument("--filter")
    vendor_models_parser.add_argument(
        "--handlers",
        action="store_true",
        help="include static Widget::Set_Keyboard_* handler metadata",
    )
    vendor_models_parser.add_argument("--json", action="store_true")
    vendor_models_parser.set_defaults(func=cmd_vendor_models)

    procreate_actions_parser = subparsers.add_parser(
        "procreate-actions", help="List Procreate tab labels and static vendor tokens"
    )
    procreate_actions_parser.add_argument("--filter")
    procreate_actions_parser.add_argument("--json", action="store_true")
    procreate_actions_parser.set_defaults(func=cmd_procreate_actions)

    procreate_parser = subparsers.add_parser(
        "procreate", help="Build or write one static vendor Procreate preset"
    )
    add_hid_args(procreate_parser)
    procreate_parser.add_argument(
        "--key",
        type=parse_key_slot,
        required=True,
        help="device key slot or alias, e.g. 2, top-click, bottom-right",
    )
    procreate_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    procreate_parser.add_argument(
        "--action",
        choices=[slug for slug, _, _ in PROCREATE_PRESETS],
        required=True,
        help="Procreate preset slug from procreate-actions",
    )
    procreate_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    procreate_parser.add_argument(
        "--record-mode",
        type=parse_record_mode,
        default=MODE_BASIC,
        help="record mode: basic/mode1 (default), macro/delay/mode5, or a byte",
    )
    procreate_parser.add_argument("--no-commit", action="store_true")
    procreate_parser.add_argument("--write", action="store_true", help="Send reports")
    procreate_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    procreate_parser.set_defaults(func=cmd_procreate)

    experiments_parser = subparsers.add_parser(
        "experiments", help="List focused physical experiment presets"
    )
    experiments_parser.set_defaults(func=cmd_experiments)

    test_plan_parser = subparsers.add_parser(
        "test-plan", help="Print a safe command sequence for remaining physical tests"
    )
    test_plan_parser.add_argument(
        "--key",
        type=parse_key_slot,
        default=2,
        help="sacrificial device key slot or alias, default: 2",
    )
    test_plan_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    test_plan_parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("snapshots/before.json"),
        help="baseline snapshot path used by restore commands",
    )
    test_plan_parser.add_argument(
        "--command-prefix",
        default="uv run python -m mini_keyboard_tool",
        help="command prefix to print before each CLI invocation",
    )
    test_plan_parser.add_argument(
        "--usage",
        default="0x0192",
        help="raw-media Consumer HID usage to probe, default: 0x0192",
    )
    test_plan_parser.add_argument(
        "--modified-wheel-action",
        default="ctrl-wheel-negative",
        help="modified-wheel action to probe, default: ctrl-wheel-negative",
    )
    test_plan_parser.add_argument(
        "--swipe-action",
        default="swipe-left",
        help="page-4 swipe action to probe, default: swipe-left",
    )
    test_plan_parser.add_argument("--led-layer", type=int, default=0)
    test_plan_parser.add_argument("--led-mode", default="mode2")
    test_plan_parser.add_argument("--led-color", default="swatch-1")
    test_plan_parser.add_argument("--no-led", action="store_true", help="omit LED mode probe")
    test_plan_parser.add_argument("--json", action="store_true")
    test_plan_parser.set_defaults(func=cmd_test_plan)

    led_modes_parser = subparsers.add_parser("led-modes", help="List LED mode names")
    led_modes_parser.set_defaults(func=cmd_led_modes)

    led_colors_parser = subparsers.add_parser(
        "led-colors", help="List extracted vendor LED color swatches"
    )
    led_colors_parser.add_argument("--filter")
    led_colors_parser.set_defaults(func=cmd_led_colors)

    slots_parser = subparsers.add_parser("slots", help="Show tested physical slot names")
    slots_parser.set_defaults(func=cmd_slots)

    media_parser = subparsers.add_parser(
        "media", help="Build or write one media key remap report"
    )
    add_hid_args(media_parser)
    media_parser.add_argument(
        "--key",
        type=parse_key_slot,
        required=True,
        help="device key slot or alias, e.g. top-left",
    )
    media_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    media_parser.add_argument(
        "--to",
        required=True,
        help="media usage name, e.g. volume-up, volume-down, mute, play-pause",
    )
    media_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    media_parser.add_argument("--no-commit", action="store_true")
    media_parser.add_argument("--write", action="store_true", help="Send reports")
    media_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    media_parser.set_defaults(func=cmd_media)

    mouse_parser = subparsers.add_parser(
        "mouse", help="Build or write one mouse/wheel/swipe remap report"
    )
    add_hid_args(mouse_parser)
    mouse_parser.add_argument(
        "--key",
        type=parse_key_slot,
        required=True,
        help="device key slot or alias, e.g. bottom-click",
    )
    mouse_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    mouse_parser.add_argument(
        "--to",
        required=True,
        help="mouse action name, e.g. left-click, wheel-up, ctrl-wheel-down, swipe-left",
    )
    mouse_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    mouse_parser.add_argument("--no-commit", action="store_true")
    mouse_parser.add_argument("--write", action="store_true", help="Send reports")
    mouse_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    mouse_parser.set_defaults(func=cmd_mouse)

    macro_parser = subparsers.add_parser(
        "macro", help="Build or write one multi-key/macro remap report"
    )
    add_hid_args(macro_parser)
    macro_parser.add_argument(
        "--key",
        type=parse_key_slot,
        required=True,
        help="device key slot or alias, e.g. top-click",
    )
    macro_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    macro_parser.add_argument(
        "--steps",
        required=True,
        help="comma-separated steps, e.g. ctrl+c or cmd+tab,a,b,c",
    )
    macro_parser.add_argument(
        "--delay",
        type=parse_delay_ms,
        default=0,
        help="same delay in milliseconds before each expanded token",
    )
    macro_parser.add_argument(
        "--delays",
        type=parse_delay_list,
        help="comma-separated per-token delays in milliseconds",
    )
    macro_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    macro_parser.add_argument(
        "--record-mode",
        type=parse_record_mode,
        default=MODE_BASIC,
        help="record mode: basic/mode1 (default), function/mode2, macro/delay/mode5, or a byte",
    )
    macro_parser.add_argument("--no-commit", action="store_true")
    macro_parser.add_argument("--write", action="store_true", help="Send reports")
    macro_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    macro_parser.set_defaults(func=cmd_macro)

    experiment_parser = subparsers.add_parser(
        "experiment", help="Build or write one focused physical experiment preset"
    )
    add_hid_args(experiment_parser)
    experiment_parser.add_argument("--name", choices=tuple(EXPERIMENTS), required=True)
    experiment_parser.add_argument(
        "--key",
        type=parse_key_slot,
        default=2,
        help="device key slot or alias for key/control experiments, default: 2",
    )
    experiment_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    experiment_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    experiment_parser.add_argument(
        "--steps",
        default="a,b,c",
        help="macro-delay steps, default: a,b,c",
    )
    experiment_parser.add_argument(
        "--delay",
        type=parse_delay_ms,
        default=250,
        help="macro-delay per-token delay in ms, default: 250",
    )
    experiment_parser.add_argument(
        "--usage",
        default="0x0192",
        help="raw-media Consumer HID usage, default: 0x0192",
    )
    experiment_parser.add_argument(
        "--action",
        default="ctrl-wheel-negative",
        help="modified-wheel or swipe action, e.g. ctrl-wheel-negative or swipe-left",
    )
    experiment_parser.add_argument("--led-layer", type=int, default=0, help="LED layer 0, 1, or 2")
    experiment_parser.add_argument(
        "--mode",
        type=parse_led_mode,
        default=2,
        help="led-mode byte, e.g. mode0..mode5 or a number",
    )
    experiment_parser.add_argument("--color", default="#ff0000")
    experiment_parser.add_argument("--commit-led", action="store_true")
    experiment_parser.add_argument("--no-commit", action="store_true")
    experiment_parser.add_argument("--write", action="store_true", help="Send reports")
    experiment_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    experiment_parser.set_defaults(func=cmd_experiment)

    led_parser = subparsers.add_parser(
        "led", help="Build or write one RGB LED layer report"
    )
    add_hid_args(led_parser)
    led_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    led_parser.add_argument(
        "--mode",
        type=parse_led_mode,
        default=0,
        help="LED mode byte, e.g. mode0..mode5 or a number",
    )
    led_parser.add_argument(
        "--color",
        default="#ffffff",
        help="fill color as name, swatch-N, #rrggbb, or r,g,b",
    )
    led_parser.add_argument(
        "--colors",
        nargs=16,
        help="exactly 16 colors as names, swatches, #rrggbb, or r,g,b values",
    )
    led_parser.add_argument(
        "--commit",
        action="store_true",
        help="also send the normal commit report after the LED report",
    )
    led_parser.add_argument("--write", action="store_true", help="Send reports")
    led_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    led_parser.set_defaults(func=cmd_led)

    led_read_parser = subparsers.add_parser(
        "led-read", help="Read one RGB LED layer using the vendor read command"
    )
    add_hid_args(led_read_parser)
    led_read_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    led_read_parser.add_argument("--timeout", type=int, default=1000, help="Read timeout ms")
    led_read_parser.set_defaults(func=cmd_led_read)

    pattern_parser = subparsers.add_parser(
        "test-pattern",
        help="Write slots 1-12 as 1 2 3 4 5 6 7 8 9 0 - =",
    )
    add_hid_args(pattern_parser)
    pattern_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    pattern_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    pattern_parser.add_argument("--mode", type=parse_number, default=1)
    pattern_parser.add_argument("--no-commit", action="store_true")
    pattern_parser.add_argument("--write", action="store_true", help="Send reports")
    pattern_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    pattern_parser.set_defaults(func=cmd_test_pattern)

    extra_pattern_parser = subparsers.add_parser(
        "extra-pattern",
        help="Write knob slots 16-21 as 0 1 2 3 4 5 for extra-control probing",
    )
    add_hid_args(extra_pattern_parser)
    extra_pattern_parser.add_argument("--layer", type=int, default=0, help="0, 1, or 2")
    extra_pattern_parser.add_argument(
        "--variant",
        choices=("new", "old"),
        default="new",
        help="Record layout inferred from the vendor app",
    )
    extra_pattern_parser.add_argument("--mode", type=parse_number, default=1)
    extra_pattern_parser.add_argument("--no-commit", action="store_true")
    extra_pattern_parser.add_argument("--write", action="store_true", help="Send reports")
    extra_pattern_parser.add_argument("--yes", action="store_true", help="Confirm device write")
    extra_pattern_parser.set_defaults(func=cmd_extra_pattern)

    gui_parser = subparsers.add_parser("gui", help="Open a rough experimental Tkinter GUI")
    add_hid_args(gui_parser)
    gui_parser.set_defaults(func=cmd_gui)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    except HIDAPIError as exc:
        print(f"hidapi error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
