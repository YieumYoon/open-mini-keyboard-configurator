from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .catalog import PROCREATE_PRESET_BY_SLUG, PROCREATE_PRESETS
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
from .ledcolors import parse_led_color
from .protocol import (
    DEFAULT_PRODUCT_ID,
    DEFAULT_USAGE_PAGE,
    DEFAULT_VENDOR_ID,
    MODE_BASIC,
    MODE_FUNCTION,
    MODE_MACRO,
    MODE_MOUSE,
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


MOUSE_ACTIONS: dict[str, dict[str, int]] = {
    "left-click": {"page": 1, "button": 1},
    "right-click": {"page": 1, "button": 2},
    "middle-click": {"page": 1, "button": 4},
    "wheel-positive": {"page": 1, "wheel": 1},
    "wheel-negative": {"page": 1, "wheel": -1},
    "ctrl-wheel-positive": {"page": 1, "wheel_modifier": 0xF1, "wheel": 1},
    "ctrl-wheel-negative": {"page": 1, "wheel_modifier": 0xF1, "wheel": -1},
    "shift-wheel-positive": {"page": 1, "wheel_modifier": 0xF2, "wheel": 1},
    "shift-wheel-negative": {"page": 1, "wheel_modifier": 0xF2, "wheel": -1},
    "alt-wheel-positive": {"page": 1, "wheel_modifier": 0xF3, "wheel": 1},
    "alt-wheel-negative": {"page": 1, "wheel_modifier": 0xF3, "wheel": -1},
    "like": {"page": 4, "swipe": 1},
    "swipe-left": {"page": 4, "swipe": 2},
    "swipe-right": {"page": 4, "swipe": 3},
    "swipe-up": {"page": 4, "swipe": 4},
    "swipe-down": {"page": 4, "swipe": 5},
}

RECORD_MODES = {
    "basic": MODE_BASIC,
    "mode1": MODE_BASIC,
    "function": MODE_FUNCTION,
    "media": MODE_FUNCTION,
    "mode2": MODE_FUNCTION,
    "mouse": MODE_MOUSE,
    "mode3": MODE_MOUSE,
    "macro": MODE_MACRO,
    "mode5": MODE_MACRO,
}

SLOT_ALIASES = {
    "top-left": 16,
    "top-ccw": 16,
    "top-click": 17,
    "top-right": 18,
    "top-cw": 18,
    "bottom-left": 19,
    "bottom-ccw": 19,
    "bottom-click": 20,
    "bottom-right": 21,
    "bottom-cw": 21,
    "knob1-left": 16,
    "knob1-click": 17,
    "knob1-right": 18,
    "knob2-left": 19,
    "knob2-click": 20,
    "knob2-right": 21,
}

TESTED_12KEY_SLOTS = tuple(range(1, 13))
TESTED_KNOB_SLOTS = (16, 17, 18, 19, 20, 21)


def _parse_number(value: str) -> int:
    return int(value.strip(), 0)


def _parse_slot(value: str) -> int:
    normalized = value.strip().lower().replace("_", "-")
    if normalized in SLOT_ALIASES:
        return SLOT_ALIASES[normalized]
    return _parse_number(value)


def _parse_slot_list(value: str) -> tuple[int, ...]:
    slots: list[int] = []
    for chunk in value.replace(";", ",").split(","):
        text = chunk.strip()
        if not text:
            continue
        if ".." in text:
            start_text, end_text = text.split("..", 1)
            start = _parse_slot(start_text)
            end = _parse_slot(end_text)
            step = 1 if start <= end else -1
            slots.extend(range(start, end + step, step))
        else:
            slots.append(_parse_slot(text))
    return tuple(dict.fromkeys(slots))


def _parse_delay(value: str) -> int:
    delay = _parse_number(value)
    if not 0 <= delay <= 0xFFFF:
        raise ValueError("delay must be between 0 and 65535 ms")
    return delay


def _parse_delay_list(value: str) -> tuple[int, ...]:
    delays = []
    for chunk in value.replace(";", ",").split(","):
        text = chunk.strip()
        if text:
            delays.append(_parse_delay(text))
    return tuple(delays)


def _parse_record_mode(value: str) -> int:
    normalized = value.strip().lower().replace("_", "-")
    if normalized in RECORD_MODES:
        return RECORD_MODES[normalized]
    number = _parse_number(normalized)
    if not 0 <= number <= 0xFF:
        raise ValueError("record mode must fit in one byte")
    return number


def _parse_led_mode(value: str) -> int:
    normalized = value.strip().lower().replace("_", "")
    if normalized.startswith("mode") and normalized[4:].isdigit():
        return int(normalized[4:], 10)
    number = _parse_number(normalized)
    if not 0 <= number <= 0xFF:
        raise ValueError("LED mode must fit in one byte")
    return number


def _parse_rgb_color(value: str) -> tuple[int, int, int]:
    return parse_led_color(value)


def _parse_macro_tokens(value: str) -> tuple[int, ...]:
    tokens: list[int] = []
    steps = [step.strip() for step in value.replace(";", ",").split(",") if step.strip()]
    if not steps:
        raise ValueError("macro needs at least one step")
    for step in steps:
        chunks = [chunk.strip() for chunk in step.split("+") if chunk.strip()]
        for modifier in chunks[:-1]:
            tokens.append(parse_modifier_token(modifier))
        key = chunks[-1]
        if key.lower().startswith("raw:"):
            token = int(key.split(":", 1)[1], 0)
            if not 0 <= token <= 0xFF:
                raise ValueError(f"raw token out of range: {key!r}")
            tokens.append(token)
        else:
            tokens.append(parse_keycode(key))
    if len(tokens) > 18:
        raise ValueError("macro expands to more than 18 tokens")
    return tuple(tokens)


def _is_sequence_remap_text(value: str) -> bool:
    return any(separator in value for separator in ("+", ",", ";"))


def _sequence_tokens_from_response(response: bytes) -> list[int]:
    if len(response) < 10:
        return []
    tokens = []
    for index in range(min(response[6], 18)):
        offset = 9 + (index * 3)
        if offset >= len(response):
            break
        tokens.append(response[offset])
    return tokens


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
    tokens = " ".join(f"{token:02x}" for token in sequence_tokens) or "-"
    summary = (
        f"slot {slot:02d} layer {layer} mode {mode:02x} "
        f"page {page:02x} count {count:02x} tokens {tokens}"
    )
    if mode in (MODE_BASIC, MODE_MACRO):
        summary += f" keys={_format_sequence_tokens(sequence_tokens)}"
    if mode == MODE_FUNCTION and len(response) > 12 and count == 2:
        usage = response[9] | (response[12] << 8)
        summary += f" media={media_usage_name(usage)}(0x{usage:04x})"
    if mode == MODE_MOUSE and len(response) > 21:
        wheel = _decode_mouse_wheel(response[21])
        summary += f" mouse(button={response[12]}, wheel_modifier=0x{response[9]:02x}, wheel={wheel})"
        action = _mouse_action_from_response(response)
        if action is not None:
            summary += f" action={action}"
    return summary


class MiniKeyboardGUI:
    def __init__(
        self,
        root: tk.Tk,
        vid: int = DEFAULT_VENDOR_ID,
        pid: int = DEFAULT_PRODUCT_ID,
        usage_page: int = DEFAULT_USAGE_PAGE,
        hidapi_path: str | None = None,
    ):
        self.root = root
        self.hidapi_path = hidapi_path
        self.root.title("Open MINI Keyboard Configurator")
        self.root.geometry("920x680")

        self.vid = tk.StringVar(value=f"0x{vid:04x}")
        self.pid = tk.StringVar(value=f"0x{pid:04x}")
        self.usage_page = tk.StringVar(value=f"0x{usage_page:04x}")
        self.variant = tk.StringVar(value="new")
        self.commit = tk.BooleanVar(value=True)
        self.dry_run = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Dry-run mode is on.")
        self.last_reports: list[tuple[str, bytes]] = []

        self.basic_key = tk.StringVar(value="1")
        self.basic_layer = tk.IntVar(value=0)
        self.basic_to = tk.StringVar(value="a")
        self.basic_clear = tk.BooleanVar(value=False)

        self.media_key = tk.StringVar(value="top-left")
        self.media_layer = tk.IntVar(value=0)
        self.media_to = tk.StringVar(value="volume-down")

        self.mouse_key = tk.StringVar(value="bottom-left")
        self.mouse_layer = tk.IntVar(value=0)
        self.mouse_to = tk.StringVar(value="wheel-negative")

        self.macro_key = tk.StringVar(value="12")
        self.macro_layer = tk.IntVar(value=0)
        self.macro_steps = tk.StringVar(value="shift+a")
        self.macro_delay = tk.StringVar(value="0")
        self.macro_delays = tk.StringVar(value="")
        self.macro_mode = tk.StringVar(value="basic")

        self.procreate_key = tk.StringVar(value="2")
        self.procreate_layer = tk.IntVar(value=0)
        self.procreate_action = tk.StringVar(value="copy")
        self.procreate_mode = tk.StringVar(value="basic")

        self.clear_slots = tk.StringVar(value="12")
        self.clear_layer = tk.IntVar(value=0)
        self.clear_all_layers = tk.BooleanVar(value=False)
        self.clear_tested_12key = tk.BooleanVar(value=False)
        self.clear_include_knobs = tk.BooleanVar(value=False)
        self.clear_mode = tk.StringVar(value="basic")

        self.led_layer = tk.IntVar(value=0)
        self.led_mode = tk.StringVar(value="mode1")
        self.led_color = tk.StringVar(value="#ff0000")

        self.read_page = tk.StringVar(value="1")
        self.read_count = tk.StringVar(value="0x19")
        self.read_key = tk.StringVar(value="")
        self.read_led_layer = tk.StringVar(value="0")

        self._build()
        self.generate()

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        device = ttk.LabelFrame(outer, text="Device", padding=10)
        device.pack(fill=tk.X)
        for col in range(8):
            device.columnconfigure(col, weight=1)
        self._entry(device, "VID", self.vid, 0, 0)
        self._entry(device, "PID", self.pid, 0, 2)
        self._entry(device, "Usage page", self.usage_page, 0, 4)
        ttk.Checkbutton(device, text="Commit", variable=self.commit).grid(row=0, column=6, sticky="w")
        ttk.Checkbutton(device, text="Dry run", variable=self.dry_run).grid(row=0, column=7, sticky="w")
        ttk.Label(device, text="Variant").grid(row=1, column=0, sticky="w", pady=6)
        ttk.OptionMenu(device, self.variant, "new", "new", "old").grid(
            row=1, column=1, sticky="ew", padx=(0, 12), pady=6
        )

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.X, pady=(10, 8))
        self._build_basic_tab()
        self._build_media_tab()
        self._build_mouse_tab()
        self._build_macro_tab()
        self._build_procreate_tab()
        self._build_led_tab()
        self._build_clear_tab()
        self._build_read_tab()

        buttons = ttk.Frame(outer)
        buttons.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(buttons, text="Generate", command=self.generate).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="Write", command=self.write).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons, text="List Devices", command=self.list_devices).pack(side=tk.LEFT)

        self.output = scrolledtext.ScrolledText(outer, height=24, wrap=tk.NONE)
        self.output.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, textvariable=self.status, anchor="w").pack(fill=tk.X, pady=(8, 0))

    def _build_basic_tab(self) -> None:
        tab = self._tab("Basic")
        self._key_layer_fields(tab, self.basic_key, self.basic_layer)
        ttk.Label(tab, text="To key").grid(row=1, column=0, sticky="w", pady=6)
        key_values = [
            *[name for name, _ in canonical_keycodes()],
            *[label for label, _, _ in vendor_basic_key_aliases()],
        ]
        ttk.Combobox(tab, textvariable=self.basic_to, values=key_values).grid(
            row=1, column=1, sticky="ew", padx=(0, 12), pady=6
        )
        ttk.Checkbutton(tab, text="Clear", variable=self.basic_clear).grid(row=1, column=2, sticky="w")

    def _build_media_tab(self) -> None:
        tab = self._tab("Media")
        self._key_layer_fields(tab, self.media_key, self.media_layer)
        ttk.Label(tab, text="Usage").grid(row=1, column=0, sticky="w", pady=6)
        values = [name for name, _ in canonical_media_usages()]
        ttk.Combobox(tab, textvariable=self.media_to, values=values).grid(
            row=1, column=1, sticky="ew", padx=(0, 12), pady=6
        )

    def _build_mouse_tab(self) -> None:
        tab = self._tab("Mouse")
        self._key_layer_fields(tab, self.mouse_key, self.mouse_layer)
        ttk.Label(tab, text="Action").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(tab, textvariable=self.mouse_to, values=sorted(MOUSE_ACTIONS)).grid(
            row=1, column=1, sticky="ew", padx=(0, 12), pady=6
        )

    def _build_macro_tab(self) -> None:
        tab = self._tab("Macro")
        self._key_layer_fields(tab, self.macro_key, self.macro_layer)
        self._entry(tab, "Steps", self.macro_steps, 1, 0)
        self._entry(tab, "Delay", self.macro_delay, 1, 2)
        self._entry(tab, "Delays", self.macro_delays, 2, 0)
        ttk.Label(tab, text="Record mode").grid(row=2, column=2, sticky="w", pady=6)
        ttk.Combobox(tab, textvariable=self.macro_mode, values=sorted(RECORD_MODES)).grid(
            row=2, column=3, sticky="ew", padx=(0, 12), pady=6
        )

    def _build_procreate_tab(self) -> None:
        tab = self._tab("Procreate")
        self._key_layer_fields(tab, self.procreate_key, self.procreate_layer)
        ttk.Label(tab, text="Action").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            tab,
            textvariable=self.procreate_action,
            values=[slug for slug, _, _ in PROCREATE_PRESETS],
        ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)
        ttk.Label(tab, text="Record mode").grid(row=1, column=2, sticky="w", pady=6)
        ttk.Combobox(tab, textvariable=self.procreate_mode, values=sorted(RECORD_MODES)).grid(
            row=1, column=3, sticky="ew", padx=(0, 12), pady=6
        )

    def _build_led_tab(self) -> None:
        tab = self._tab("LED")
        ttk.Label(tab, text="Layer").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Spinbox(tab, from_=0, to=2, textvariable=self.led_layer, width=8).grid(
            row=0, column=1, sticky="ew", padx=(0, 12), pady=6
        )
        ttk.Label(tab, text="Mode").grid(row=0, column=2, sticky="w", pady=6)
        ttk.Combobox(tab, textvariable=self.led_mode, values=[f"mode{i}" for i in range(6)]).grid(
            row=0, column=3, sticky="ew", padx=(0, 12), pady=6
        )
        self._entry(tab, "Fill color", self.led_color, 1, 0)

    def _build_clear_tab(self) -> None:
        tab = self._tab("Clear")
        self._entry(tab, "Slots", self.clear_slots, 0, 0)
        ttk.Label(tab, text="Layer").grid(row=0, column=2, sticky="w", pady=6)
        ttk.Spinbox(tab, from_=0, to=2, textvariable=self.clear_layer, width=8).grid(
            row=0, column=3, sticky="ew", padx=(0, 12), pady=6
        )
        ttk.Checkbutton(tab, text="All layers", variable=self.clear_all_layers).grid(
            row=1, column=0, sticky="w", pady=6
        )
        ttk.Checkbutton(tab, text="Tested 12 keys", variable=self.clear_tested_12key).grid(
            row=1, column=1, sticky="w", pady=6
        )
        ttk.Checkbutton(tab, text="Include knobs", variable=self.clear_include_knobs).grid(
            row=1, column=2, sticky="w", pady=6
        )
        ttk.Label(tab, text="Record mode").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Combobox(tab, textvariable=self.clear_mode, values=sorted(RECORD_MODES)).grid(
            row=2, column=1, sticky="ew", padx=(0, 12), pady=6
        )

    def _build_read_tab(self) -> None:
        tab = self._tab("Read")
        self._entry(tab, "Page", self.read_page, 0, 0)
        self._entry(tab, "Count", self.read_count, 0, 2)
        self._entry(tab, "Only key", self.read_key, 1, 0)
        self._entry(tab, "LED layer", self.read_led_layer, 1, 2)
        ttk.Button(tab, text="Info", command=self.info).grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=6)
        ttk.Button(tab, text="Read Config", command=self.read_config).grid(
            row=2, column=1, sticky="ew", padx=(0, 8), pady=6
        )
        ttk.Button(tab, text="Read LED", command=self.read_led).grid(row=2, column=2, sticky="ew", pady=6)

    def _tab(self, name: str) -> ttk.Frame:
        tab = ttk.Frame(self.notebook, padding=10)
        for col in range(4):
            tab.columnconfigure(col, weight=1)
        self.notebook.add(tab, text=name)
        return tab

    def _entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, column: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row,
            column=column + 1,
            sticky="ew",
            padx=(0, 12),
            pady=6,
        )

    def _key_layer_fields(self, parent: ttk.Frame, key_var: tk.StringVar, layer_var: tk.IntVar) -> None:
        self._entry(parent, "Key slot", key_var, 0, 0)
        ttk.Label(parent, text="Layer").grid(row=0, column=2, sticky="w", pady=6)
        ttk.Spinbox(parent, from_=0, to=2, textvariable=layer_var, width=8).grid(
            row=0, column=3, sticky="ew", padx=(0, 12), pady=6
        )

    def _device_ids(self) -> tuple[int, int, int]:
        return _parse_number(self.vid.get()), _parse_number(self.pid.get()), _parse_number(self.usage_page.get())

    def _append_commit(self, reports: list[tuple[str, bytes]]) -> None:
        if self.commit.get():
            reports.append(("commit", build_commit_report()))

    def _set_reports(self, reports: list[tuple[str, bytes]], header: str) -> None:
        self.last_reports = reports
        lines = [header, ""]
        for index, (label, report) in enumerate(reports, start=1):
            lines.append(f"Report {index} ({label}, {len(report)} bytes)")
            lines.append(hex_dump(report))
            lines.append("")
        self._set_output("\n".join(lines))
        self.status.set("Report generated. Dry-run mode is on." if self.dry_run.get() else "Report generated.")

    def generate(self) -> None:
        selected = self.notebook.tab(self.notebook.select(), "text")
        try:
            if selected == "Basic":
                self._generate_basic()
            elif selected == "Media":
                self._generate_media()
            elif selected == "Mouse":
                self._generate_mouse()
            elif selected == "Macro":
                self._generate_macro()
            elif selected == "Procreate":
                self._generate_procreate()
            elif selected == "LED":
                self._generate_led()
            elif selected == "Clear":
                self._generate_clear()
            else:
                self.status.set("Use the buttons in the Read tab.")
        except Exception as exc:
            self.last_reports = []
            self._set_output(f"Error: {exc}\n")
            self.status.set("Could not generate report.")

    def _generate_basic(self) -> None:
        key = _parse_slot(self.basic_key.get())
        layer = int(self.basic_layer.get())
        variant = self.variant.get()
        if self.basic_clear.get() or not _is_sequence_remap_text(self.basic_to.get()):
            keycode = None if self.basic_clear.get() else parse_keycode(self.basic_to.get())
            remap = BasicRemap(
                physical_key=key,
                layer=layer,
                keycode=keycode,
                variant=variant,
            )
            reports = [("basic", build_basic_report(remap))]
            title = f"Basic key {remap.physical_key} layer {remap.layer}"
        else:
            tokens = _parse_macro_tokens(self.basic_to.get())
            report = build_sequence_report(
                SequenceRemap(
                    physical_key=key,
                    layer=layer,
                    mode=MODE_BASIC,
                    tokens=tokens,
                    variant=variant,
                )
            )
            reports = [("basic token-list", report)]
            title = f"Basic key {key} layer {layer}: {_format_sequence_tokens(list(tokens))}"
        self._append_commit(reports)
        self._set_reports(reports, title)

    def _generate_media(self) -> None:
        usage = parse_media_usage(self.media_to.get())
        key = _parse_slot(self.media_key.get())
        layer = int(self.media_layer.get())
        reports = [("media", build_media_report(key, layer, usage, variant=self.variant.get()))]
        self._append_commit(reports)
        self._set_reports(reports, f"Media key {key} layer {layer} usage 0x{usage:04x}")

    def _generate_mouse(self) -> None:
        action = MOUSE_ACTIONS[self.mouse_to.get()]
        key = _parse_slot(self.mouse_key.get())
        layer = int(self.mouse_layer.get())
        report = build_mouse_report(MouseRemap(physical_key=key, layer=layer, variant=self.variant.get(), **action))
        reports = [("mouse", report)]
        self._append_commit(reports)
        self._set_reports(reports, f"Mouse key {key} layer {layer} action {self.mouse_to.get()}")

    def _generate_macro(self) -> None:
        tokens = _parse_macro_tokens(self.macro_steps.get())
        if self.macro_delays.get().strip():
            delays = _parse_delay_list(self.macro_delays.get())
            if len(delays) != len(tokens):
                raise ValueError("per-token delays must match expanded token count")
        else:
            delays = (_parse_delay(self.macro_delay.get()),) * len(tokens)
        key = _parse_slot(self.macro_key.get())
        layer = int(self.macro_layer.get())
        mode = _parse_record_mode(self.macro_mode.get())
        report = build_sequence_report(
            SequenceRemap(
                physical_key=key,
                layer=layer,
                mode=mode,
                tokens=tokens,
                delays=delays,
                variant=self.variant.get(),
            )
        )
        reports = [("macro", report)]
        self._append_commit(reports)
        self._set_reports(reports, f"Macro key {key} layer {layer} tokens {tokens} delays {delays}")

    def _generate_procreate(self) -> None:
        action = self.procreate_action.get().strip().lower().replace("_", "-")
        if action not in PROCREATE_PRESET_BY_SLUG:
            raise ValueError(f"unknown Procreate action: {self.procreate_action.get()!r}")
        label, tokens = PROCREATE_PRESET_BY_SLUG[action]
        key = _parse_slot(self.procreate_key.get())
        layer = int(self.procreate_layer.get())
        mode = _parse_record_mode(self.procreate_mode.get())
        report = build_sequence_report(
            SequenceRemap(
                physical_key=key,
                layer=layer,
                mode=mode,
                tokens=tokens,
                variant=self.variant.get(),
            )
        )
        reports = [("procreate", report)]
        self._append_commit(reports)
        self._set_reports(reports, f"Procreate key {key} layer {layer} action {action} ({label}) tokens {tokens}")

    def _generate_led(self) -> None:
        layer = int(self.led_layer.get())
        mode = _parse_led_mode(self.led_mode.get())
        color = _parse_rgb_color(self.led_color.get())
        report = build_led_report(LedConfig(layer=layer, mode=mode, colors=(color,) * 16))
        reports = [("led", report)]
        self._append_commit(reports)
        self._set_reports(reports, f"LED layer {layer} mode {mode} color #{color[0]:02x}{color[1]:02x}{color[2]:02x}")

    def _generate_clear(self) -> None:
        slots = list(_parse_slot_list(self.clear_slots.get()))
        if self.clear_tested_12key.get():
            slots.extend(TESTED_12KEY_SLOTS)
        if self.clear_include_knobs.get():
            slots.extend(TESTED_KNOB_SLOTS)
        slots = list(dict.fromkeys(slots))
        if not slots:
            raise ValueError("clear needs at least one slot or preset checkbox")

        layers = (0, 1, 2) if self.clear_all_layers.get() else (int(self.clear_layer.get()),)
        mode = _parse_record_mode(self.clear_mode.get())
        reports: list[tuple[str, bytes]] = []
        for layer in layers:
            for slot in slots:
                report = build_basic_report(
                    BasicRemap(
                        physical_key=slot,
                        layer=layer,
                        keycode=None,
                        variant=self.variant.get(),
                        mode=mode,
                    )
                )
                reports.append((f"clear slot {slot} layer {layer}", report))
        self._append_commit(reports)
        slot_text = ", ".join(str(slot) for slot in slots)
        layer_text = ", ".join(str(layer) for layer in layers)
        self._set_reports(reports, f"Clear slots {slot_text} on layer(s) {layer_text}")

    def list_devices(self) -> None:
        try:
            api = HidAPI(self.hidapi_path)
            devices = api.enumerate(_parse_number(self.vid.get()), _parse_number(self.pid.get()))
        except Exception as exc:
            self._set_output(f"Error: {exc}\n")
            self.status.set("Device list failed.")
            return

        if not devices:
            self._set_output("No matching HID devices found.\n")
            self.status.set("No devices found.")
            return

        lines = [f"Loaded hidapi: {api.path}", ""]
        for index, device in enumerate(devices):
            lines.append(
                f"[{index}] VID:PID=0x{device.vendor_id:04x}:0x{device.product_id:04x} "
                f"usage=0x{device.usage_page:04x}:0x{device.usage:04x} "
                f"product={device.product_string!r} serial={device.serial_number!r}"
            )
            lines.append(f"    path={device.path_text}")
        self._set_output("\n".join(lines))
        self.status.set("Device list complete.")

    def info(self) -> None:
        try:
            response = self._write_then_read(build_info_request())
            model = parse_info_response(response)
        except Exception as exc:
            self._set_output(f"Error: {exc}\n")
            self.status.set("Info failed.")
            return
        self.last_reports = []
        self._set_output(f"Keyboard model bytes: {model[0]}, {model[1]}, {model[2]}\n\n{hex_dump(response)}")
        self.status.set("Info read complete.")

    def read_config(self) -> None:
        try:
            _, _, usage_page = self._device_ids()
            api = HidAPI(self.hidapi_path)
            page = _parse_number(self.read_page.get())
            count = _parse_number(self.read_count.get())
            only_key = self.read_key.get().strip()
            only_slot = _parse_slot(only_key) if only_key else None
            request = build_read_config_request(page, count)
            lines = ["Config records:", ""]
            with api.open_device(_parse_number(self.vid.get()), _parse_number(self.pid.get()), usage_page) as device:
                device.write(request)
                for index in range(1, count + 1):
                    response = device.read_timeout(64, 1000)
                    if not response:
                        lines.append(f"No response for record {index}.")
                        break
                    if only_slot is not None and len(response) > 2 and response[2] != only_slot:
                        continue
                    lines.append(_summarize_config_response(response))
            self.last_reports = []
            self._set_output("\n".join(lines))
            self.status.set("Config read complete.")
        except Exception as exc:
            self._set_output(f"Error: {exc}\n")
            self.status.set("Config read failed.")

    def read_led(self) -> None:
        try:
            layer = _parse_number(self.read_led_layer.get())
            response = self._write_then_read(build_read_led_request(layer))
            mode, colors = parse_led_response(response)
        except Exception as exc:
            self._set_output(f"Error: {exc}\n")
            self.status.set("LED read failed.")
            return
        lines = [f"LED layer {layer} mode {mode}", ""]
        for index, (red, green, blue) in enumerate(colors, start=1):
            lines.append(f"{index:2d}: #{red:02x}{green:02x}{blue:02x}")
        self.last_reports = []
        self._set_output("\n".join(lines))
        self.status.set("LED read complete.")

    def _write_then_read(self, report: bytes) -> bytes:
        vid, pid, usage_page = self._device_ids()
        api = HidAPI(self.hidapi_path)
        with api.open_device(vid, pid, usage_page) as device:
            device.write(report)
            response = device.read_timeout(64, 1000)
        if not response:
            raise HIDAPIError("No response before timeout.")
        return response

    def write(self) -> None:
        self.generate()
        if not self.last_reports:
            return
        if self.dry_run.get():
            messagebox.showinfo("Dry run", "Dry run is on. Uncheck it before writing.")
            return
        if not messagebox.askyesno("Write to keyboard", "Send these HID reports to the keyboard?"):
            return
        try:
            vid, pid, usage_page = self._device_ids()
            api = HidAPI(self.hidapi_path)
            with api.open_device(vid, pid, usage_page) as device:
                for _, report in self.last_reports:
                    written = device.write(report)
                    if written != len(report):
                        raise HIDAPIError(f"hid_write returned {written}, expected {len(report)}")
        except HIDAPIError as exc:
            messagebox.showerror("hidapi error", str(exc))
            self.status.set("Write failed.")
            return
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.status.set("Write failed.")
            return
        self.status.set("Reports written.")
        messagebox.showinfo("Done", "Reports written.")

    def _set_output(self, value: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, value)


def run(
    vid: int = DEFAULT_VENDOR_ID,
    pid: int = DEFAULT_PRODUCT_ID,
    usage_page: int = DEFAULT_USAGE_PAGE,
    hidapi_path: str | None = None,
) -> None:
    root = tk.Tk()
    MiniKeyboardGUI(root, vid=vid, pid=pid, usage_page=usage_page, hidapi_path=hidapi_path)
    root.mainloop()
