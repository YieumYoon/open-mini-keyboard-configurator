# MINI Keyboard Feature Matrix

This is the current replacement status for the local vendor `MINI_KEYBOARD.app`.
The app binary was inspected statically; it was not run.
For a vendor UI-to-replacement map, see `VENDOR_COVERAGE.md`.
For physical behavior observed on the connected board, see `PHYSICAL_TESTS.md`.

## Confirmed On The Device

- Device discovery and model probe for VID `0x514c`, PID `0x8850`.
- Read-back of key records from the configuration interface.
- Human-readable decoding for key, media, and mouse read-back records.
- Multi-slot read-back filters through repeated `--key` and ranged `--keys`.
- Physical slots `1` through `12`.
- Knob slots `16` through `21`.
- Basic key writes on layer 0.
- Layer 1 and layer 2 key assignments through each command's `--layer` option;
  physically confirmed with visible outputs on slots 1 through 3.
- Basic-mode modifier chords, confirmed with `shift+a` on slot `12` producing
  uppercase `A`.
- Consumer media writes for volume down, mute, and volume up.
- Raw Consumer HID usage `0x0192` / `calculator`, confirmed on Ubuntu; no
  visible macOS response was observed in the tested context.
- Consumer transport and system usages: play/pause, previous track, next track,
  stop, eject, rewind, fast-forward, and display brightness up/down.
- Browser/app-launch Consumer HID usages: back, forward, refresh,
  media-select, email, my-computer, internet-browser, browser-search, and
  browser-home, with visible behavior varying by OS.
- Mouse wheel and button records: left-click, right-click, and middle-click.
- Per-token macro delays on layer 0.
- Wheel sign behavior using Ubuntu/Linux as the practical baseline:
  `wheel-negative` scrolls down there, while macOS may present the opposite
  direction because of natural scrolling or app focus.
- Modifier wheel records: Ctrl-wheel confirmed for browser zoom/Ubuntu zoom
  behavior, Shift-wheel observed as horizontal movement, and Alt-wheel observed
  as image-viewer zoom.
- RGB LED color writes for layers 0, 1, and 2.
- LED modes `mode0` through `mode5` on wired USB: off, static color,
  key-press fade, key-press orthogonal ripple, diagonal rainbow wave, and
  left-to-right rainbow wave.
- LED color entry mapping: entries `1` through `12` map to keys `1` through
  `12`; entries `13` through `16` are writable/readable but not visible on the
  tested board.
- Extracted vendor LED color swatch aliases.
- Read-only snapshots of key records and LED layers.
- Snapshot-to-report restore generation for key config and LED layers.
- Snapshot diffing for before/after experiments.
- Built-in restore profile generation for verified controls and the tested
  12-key baseline.
- Bulk clear report generation for one or more selected slots, the tested
  visible 12-key layout, and tested knob slots.
- Vendor-style basic key aliases for symbols, arrow keys, system keys, numpad
  keys, and `NULL`, exposed through `vendor-key-aliases`.
- Vendor model catalog, `Set_Keyboard_*` handler catalog, and Procreate tab
  static token catalog extracted from the binary.
- Regression tests for critical HID report byte layouts.
- Current-device verification for the tested baseline profile.
- Tk GUI report generation for basic, media, mouse, macro, Procreate, LED,
  bulk clear, and read-back flows.
- Focused experiment presets for macro delay, raw media, modified wheel, swipe,
  and LED mode tests.
- Generated `test-plan` command sequences for the remaining physical test
  queue. The command prints steps only; it does not access the HID device.

## Implemented, Needs Focused Physical Testing

- Snapshot writes back to the device through `restore-snapshot --write --yes`,
  and `diff-snapshot --semantic` verifies decoded behavior after restore.
- Built-in profile writes through `profile --name ... --write --yes`.
- Macro delay behavior on layers/modes beyond the tested layer-0 basic-mode
  token-list path.
- Raw 16-bit Consumer HID usages through `media --to 0xNNNN` beyond the tested
  named usages and `0x0192` / `calculator`.
- Bass and treble Consumer HID usages write/read back, but visible behavior is
  still unconfirmed in the tested contexts.
- Keyboard-backlight brightness usages write/read back, but visible behavior is
  still unconfirmed on available hardware.
- `Like` gesture and swipe records.
- `like`, `swipe-left`, `swipe-right`, `swipe-up`, and `swipe-down` page-4
  codes are writable/readable, but all had no visible target-app response in
  the tested contexts.
- Whether LED entries `13` through `16` are used on another hardware variant.
- LED behavior over the wireless dongle. Wired USB shows `mode2`; the observed
  dongle setup did not light the LEDs, and the cause is not yet known.
- GUI writes for the expanded tabs beyond basic key remaps, including bulk
  clear.
- Procreate preset writes through `procreate --action ...`; the token mappings
  are static-vendor extractions and still need app-level physical testing.

## Not Yet Identified

- A standalone hardware key action that switches the keyboard's active layer.
  `Widget::SendLayer(int)` appears to update app/editor state
  (`Select_PHY_Key_Layer`, button styles, selected key text, optional LED read)
  and does not call the HID write path. Per-layer assignment/output is
  confirmed; standalone layer switching from the replacement tool is separate
  and still unidentified.
- Exact vendor-app visual parity. The replacement GUI now covers the main
  protocol flows, but it is intentionally simpler than the Qt vendor UI.

## Useful Test Queue

Capture the current state before a test:

```sh
uv run python -m mini_keyboard_tool snapshot --json snapshots/before.json
```

Verify the tested baseline:

```sh
uv run python -m mini_keyboard_tool verify-current
```

Use one sacrificial slot for focused tests, then use the snapshot as a reference
while writing a known mapping back.

List focused test presets:

```sh
uv run python -m mini_keyboard_tool experiments
```

Print the safe command sequence for the remaining focused tests:

```sh
uv run python -m mini_keyboard_tool test-plan --key 2
uv run python -m mini_keyboard_tool test-plan --key 2 --no-led
```

Build a focused experiment report:

```sh
uv run python -m mini_keyboard_tool experiment --name macro-delay --key 2
```

Build bulk clear reports:

```sh
uv run python -m mini_keyboard_tool clear --key 12
uv run python -m mini_keyboard_tool clear --keys 1..12
uv run python -m mini_keyboard_tool clear --tested-12key --include-knobs
```

Build a restore report for one slot:

```sh
uv run python -m mini_keyboard_tool restore-snapshot --json snapshots/before.json --key 2
```

Build a built-in baseline profile:

```sh
uv run python -m mini_keyboard_tool profile --name tested-12key-baseline --no-led
```

Compare before/after:

```sh
uv run python -m mini_keyboard_tool diff-snapshot snapshots/before.json snapshots/after.json --key 2
```

Macro delay:

```sh
uv run python -m mini_keyboard_tool macro --key 2 --steps a,b,c --delay 250 --write --yes
```

Raw Consumer HID value:

```sh
uv run python -m mini_keyboard_tool media --key 2 --to 0x0192 --write --yes
```

Modified wheel:

```sh
uv run python -m mini_keyboard_tool mouse --key 2 --to ctrl-wheel-negative --write --yes
```

Swipe:

```sh
uv run python -m mini_keyboard_tool mouse --key 2 --to swipe-left --write --yes
```

Like gesture:

```sh
uv run python -m mini_keyboard_tool mouse --key 2 --to like --write --yes
```

LED mode:

```sh
uv run python -m mini_keyboard_tool led --layer 0 --mode mode1 --color '#ff0000' --write --yes
```

Vendor LED swatches:

```sh
uv run python -m mini_keyboard_tool led-colors
uv run python -m mini_keyboard_tool led --layer 0 --mode mode1 --color swatch-1 --write --yes
```

Vendor catalog:

```sh
uv run python -m mini_keyboard_tool vendor-models
uv run python -m mini_keyboard_tool procreate-actions
uv run python -m mini_keyboard_tool procreate --key 2 --action copy
```

Regression tests:

```sh
uv run python -m unittest discover -v
```
