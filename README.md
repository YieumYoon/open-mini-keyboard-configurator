# Open MINI Keyboard Configurator

Experimental, unofficial CLI-first configurator for the vendor
`MINI_KEYBOARD.app`.

## Status and disclaimer

This is an unofficial community reverse-engineering project. It is not
affiliated with, endorsed by, or supported by the keyboard vendor.

This project is based on static analysis of the local vendor app. It does not
install, bundle, or run the vendor app, and this repository should not contain
vendor binaries, installers, images, or firmware.

Use it at your own risk. Keep a read-only snapshot of your device configuration
before writing changes, and treat untested hardware variants as experimental.

The implemented write paths cover the tested basic keys, media keys,
mouse/wheel actions, simple modifier chords, timed token-list macros, static
Procreate presets, and RGB LED layer colors. See `VENDOR_COVERAGE.md` for a
vendor UI-to-replacement coverage map.

Released under the MIT License; see `LICENSE`.

## Supported device

Default target:

- VID: `0x514c`
- wired/config PID: `0x8850`
- Preferred HID interface: usage page `0xff00`, usage `0x0001`

The tested wireless dongle appears as VID:PID `0x514c:0x4155` and exposes only
standard keyboard, mouse, and Consumer Control HID interfaces. It does not
expose the vendor `0xff00` configuration interface on macOS, so configuration
and RGB LED writes should be done over wired USB.

## Hardware variants and validation scope

The original vendor software appears to be built for a family of small macro
keyboards, not only the board tested here. Public model strings observed in the
app include:

```text
2KEY, 3KEY, 3+1KEY, 4KEY, 4+1KEY, 4+1_2KEY, 5KEY,
6KEY, 6+1KEY, 6+2KEY, 9+2KEY, 9+3KEY, 11+3KEY,
12+2KEY, 12+3KEY, 15+3KEY
```

Only the `12+2KEY` board has been physically tested by this project so far.
Other model names and layout handlers are documented as static compatibility
clues from the vendor app; they should be treated as unverified until someone
with that hardware tests them.

Use `vendor-models` and `vendor-models --handlers` to print the catalog known
to this tool. Hardware photos and layout notes can be collected under
`docs/hardware/`; use only photos you took yourself or images that are clearly
licensed for redistribution.

## Safety model

- `remap` is dry-run by default and only prints the HID reports.
- A real write requires both `--write` and `--yes`.
- Media, mouse, macro, and RGB commands are also dry-run by default.
- `restore-snapshot` is also dry-run by default; use filters such as `--key`
  or `--layer` before writing broad restores.
- Physical key numbers are the app/device slots. On the tested 12-key board,
  visible keys appear to start at `1`; slot `0` can be written but did not map
  to an obvious physical key.

## Tested 12-key + 2-knob layout

With the keyboard facing you and the knobs on the right:

```text
[ 1 ] [ 2 ] [ 3 ] [ 4 ]      top-left=16  top-click=17  top-right=18
[ 5 ] [ 6 ] [ 7 ] [ 8 ]
[ 9 ] [10 ] [11 ] [12 ]      bottom-left=19 bottom-click=20 bottom-right=21
```

The knob names describe the action:

- `top-left` / `top-ccw`: top knob turned left
- `top-click`: top knob pressed
- `top-right` / `top-cw`: top knob turned right
- `bottom-left` / `bottom-ccw`: bottom knob turned left
- `bottom-click`: bottom knob pressed
- `bottom-right` / `bottom-cw`: bottom knob turned right

You can also print this from the CLI:

```sh
uv run python -m mini_keyboard_tool slots
```

## Run

From this directory:

```sh
uv run python -m mini_keyboard_tool --help
uv run python -m mini_keyboard_tool remap --key 0 --to a
```

This project is CLI-first. There is a rough experimental Tk GUI prototype:

```sh
uv run python -m mini_keyboard_tool gui
```

Treat the GUI as a convenience/debugging surface, not as a polished vendor-app
replacement. The physically verified and best-documented path is the CLI.

Write a key only after checking the dry-run report:

```sh
uv run python -m mini_keyboard_tool remap --key 1 --to 9 --write --yes
uv run python -m mini_keyboard_tool remap --key top-click --to enter --write --yes
uv run python -m mini_keyboard_tool remap --key 12 --to shift+a
uv run python -m mini_keyboard_tool remap --key 2 --to PrtScSysRq
uv run python -m mini_keyboard_tool remap --key 2 --to M_NUM1
```

`remap --to` accepts standard HID names plus vendor-style button aliases from
the app's basic key page. Chords such as `shift+a` are written as the same
basic token-list record used by the vendor app. Supported aliases include
`PrtScSysRq`, `ScrLock`, `ArrowsUp`, `NUM1` for the normal number row, `M_NUM1`
for keypad numbers, `ADD`, `SubUnd`, and `NULL`. Use `keycodes` to list the
canonical names, or `vendor-key-aliases` to list the vendor button labels.

Clear one or more slots by writing empty records:

```sh
uv run python -m mini_keyboard_tool remap --key 12 --clear
uv run python -m mini_keyboard_tool clear --keys 1..12
uv run python -m mini_keyboard_tool clear --tested-12key --include-knobs
uv run python -m mini_keyboard_tool clear --tested-12key --include-knobs --all-layers --write --yes
```

The `clear` command mirrors the vendor app's Clean/Clean All workflow as
explicit HID reports. It is dry-run by default.

Map media controls:

```sh
uv run python -m mini_keyboard_tool media --key top-left --to volume-down
uv run python -m mini_keyboard_tool media --key top-right --to volume-up --write --yes
uv run python -m mini_keyboard_tool media --key 1 --to 0x0194
uv run python -m mini_keyboard_tool media-codes
```

`media --to` accepts named aliases and raw 16-bit Consumer HID usage values.

Map mouse controls:

```sh
uv run python -m mini_keyboard_tool mouse --key bottom-left --to wheel-down
uv run python -m mini_keyboard_tool mouse --key bottom-right --to wheel-up --write --yes
uv run python -m mini_keyboard_tool mouse --key 2 --to like
uv run python -m mini_keyboard_tool mouse-actions
```

`wheel-positive` and `wheel-negative` aliases are also available when macOS
natural scrolling makes the perceived up/down direction ambiguous.
The vendor app's Procreate-style `Like` gesture is available as `like`
(`page=4`, code `1`); swipes use codes `2` through `5`.

Map a simple multi-key/macro record:

```sh
uv run python -m mini_keyboard_tool macro --key 1 --steps ctrl+c
uv run python -m mini_keyboard_tool macro --key 12 --steps shift+a
uv run python -m mini_keyboard_tool macro --key 2 --steps a,b,c --delay 100
uv run python -m mini_keyboard_tool macro --key 2 --steps shift+a --delays 0,250
uv run python -m mini_keyboard_tool macro --key 2 --steps cmd+tab,a,b,c --write --yes
```

The macro command writes the vendor app's token-list style record. It is useful
for simple modifier chords and short key sequences. On the tested board,
modifier chords such as `shift+a` work with the default `basic` record mode.
`--delay` applies the same delay to every expanded token; `--delays` applies
per-token delays after expansion. Use `--record-mode function` or `macro` only
when probing firmware behavior.

Build or write one static Procreate preset extracted from the vendor app:

```sh
uv run python -m mini_keyboard_tool procreate-actions
uv run python -m mini_keyboard_tool procreate-actions --filter copy
uv run python -m mini_keyboard_tool procreate --key 2 --action copy
uv run python -m mini_keyboard_tool procreate --key 2 --action redo --write --yes
```

`procreate` uses the same token-list record as simple modifier chords. The
tokens are statically extracted from the vendor binary; app-level behavior still
needs focused physical testing in Procreate or the target app.

Build or read RGB LED reports:

```sh
uv run python -m mini_keyboard_tool led --layer 0 --mode mode0 --color '#ff0000'
uv run python -m mini_keyboard_tool led --layer 0 --mode mode1 --color swatch-1
uv run python -m mini_keyboard_tool led-read --layer 0
uv run python -m mini_keyboard_tool led-modes
uv run python -m mini_keyboard_tool led-colors
```

List matching HID devices:

```sh
uv run python -m mini_keyboard_tool list
```

List vendor app catalog data extracted from the binary:

```sh
uv run python -m mini_keyboard_tool vendor-models
uv run python -m mini_keyboard_tool vendor-models --handlers
uv run python -m mini_keyboard_tool vendor-key-aliases
uv run python -m mini_keyboard_tool procreate-actions
uv run python -m mini_keyboard_tool procreate-actions --filter brush
```

`vendor-models --handlers` lists the static `Widget::Set_Keyboard_*` layout
handlers found in the binary, including internal handlers that do not have a
matching public model string. `procreate-actions` lists labels and static token
mappings from the vendor app's Procreate tab, for example `copy` as `cmd+c` and
`redo` as `shift+cmd+z`.

Read the keyboard's model bytes using the vendor app's probe command:

```sh
uv run python -m mini_keyboard_tool info
```

Read back saved key records:

```sh
uv run python -m mini_keyboard_tool read-config --page 1 --key 12
uv run python -m mini_keyboard_tool read-config --page 1 --keys 2..5
uv run python -m mini_keyboard_tool read-config --page 1 --key 2 --key top-click
uv run python -m mini_keyboard_tool read-config --page 1 --key bottom-left --verbose
```

Read-back summaries decode common records into names such as `keys=shift+a`,
`media=volume-down`, and `action=wheel-negative` while preserving raw bytes in
verbose output and snapshots. `--key` is repeatable, and `--keys` accepts
comma-separated slots, aliases, and `..` ranges.

Verify the currently tested baseline:

```sh
uv run python -m mini_keyboard_tool verify-current
uv run python -m mini_keyboard_tool verify-current --json snapshots/verified.json
```

Capture a read-only snapshot before/after experiments:

```sh
uv run python -m mini_keyboard_tool snapshot
uv run python -m mini_keyboard_tool snapshot --json snapshots/current.json
uv run python -m mini_keyboard_tool snapshot --pages 1 --no-led
```

Compare two snapshots:

```sh
uv run python -m mini_keyboard_tool diff-snapshot snapshots/before.json snapshots/after.json
uv run python -m mini_keyboard_tool diff-snapshot snapshots/before.json snapshots/after.json --key 12 --no-led
uv run python -m mini_keyboard_tool diff-snapshot snapshots/before.json snapshots/after.json --semantic
```

Use the default raw diff when byte-level changes matter. Use `--semantic` after
restore tests to compare decoded behavior; the device may normalize derived
fields such as the media record page byte while keeping the same Consumer HID
usage.

Build or write restore reports from a snapshot:

```sh
uv run python -m mini_keyboard_tool restore-snapshot --json snapshots/current.json --key 12
uv run python -m mini_keyboard_tool restore-snapshot --json snapshots/current.json --layer 0 --write --yes
uv run python -m mini_keyboard_tool restore-snapshot --json snapshots/current.json --no-config --include-led --led-layers 0
```

List or build built-in tested restore profiles:

```sh
uv run python -m mini_keyboard_tool profiles
uv run python -m mini_keyboard_tool profile --name verified-controls
uv run python -m mini_keyboard_tool profile --name tested-12key-baseline --no-led
uv run python -m mini_keyboard_tool profile --name tested-12key-baseline --write --yes
```

`verified-controls` rebuilds the physically verified slot 12, knob controls, and
RGB LED layers. `tested-12key-baseline` also restores the tested layer-0
number/symbol mapping for slots 1 through 11, useful after using one of those
keys as a sacrificial experiment slot.

Run the regression tests:

```sh
uv run python -m unittest discover -v
```

List and build focused physical test presets for remaining features:

```sh
uv run python -m mini_keyboard_tool experiments
uv run python -m mini_keyboard_tool test-plan --key 2
uv run python -m mini_keyboard_tool experiment --name macro-delay --key 2
uv run python -m mini_keyboard_tool experiment --name raw-media --key 2
uv run python -m mini_keyboard_tool experiment --name modified-wheel --key 2
uv run python -m mini_keyboard_tool experiment --name swipe --key 2
uv run python -m mini_keyboard_tool experiment --name led-mode --led-layer 0 --mode mode2
```

`test-plan` only prints a safe command sequence. It does not access the HID
device. The generated plan captures a baseline snapshot, runs one focused
experiment at a time on a sacrificial slot, diffs the result, restores that
slot or LED layer from the snapshot, and verifies the known baseline.

## Current feature status

Physically tested on the 12-key + 2-knob board:

- Basic key remaps on layer 0.
- Layer 1 and layer 2 key assignments through `--layer`, confirmed with visible
  outputs on slots 1 through 3.
- Basic-mode modifier chords such as `shift+a`.
- Consumer media keys: volume down, mute, volume up.
- Raw Consumer HID `0x0192` / `calculator`, visible on Ubuntu; no visible macOS
  response was observed in the tested context.
- Consumer transport/system usages: play/pause, previous track, next track,
  stop, eject usage, rewind, fast-forward, and display brightness up/down.
- Browser/app-launch Consumer HID usages including back, forward, refresh,
  media-select, email, my-computer, internet-browser, browser-search, and
  browser-home, with visible behavior varying by OS.
- Mouse wheel and button records: left-click, right-click, and middle-click.
- Per-token macro delays on layer 0.
- Wheel sign behavior using Ubuntu/Linux as the practical baseline:
  `wheel-negative` scrolls down there, while macOS can present the opposite
  visual direction.
- Modifier wheel records: Ctrl-wheel browser/Ubuntu zoom behavior, Shift-wheel
  horizontal movement, and Alt-wheel image-viewer zoom.
- RGB color writes for layers 0, 1, and 2.
- LED modes `mode0` through `mode5` over wired USB: off, static color,
  key-press fade, key-press orthogonal ripple, diagonal rainbow wave, and
  left-to-right rainbow wave.
- LED entries `1` through `12` map to keys `1` through `12`; LED entries `13`
  through `16` write/read back but are not visible on the tested board.
- Snapshot readback and restore report generation.
- Human-readable readback summaries for key, media, and mouse records.
- Snapshot diffing for before/after experiments.
- Extracted vendor LED swatch aliases such as `swatch-1` and `LED_color_56`.
- Built-in dry-run restore profiles for the verified controls and the tested
  12-key baseline.
- Bulk clear report generation for selected slots or the tested 12-key layout.
- Vendor-style basic key aliases for symbols, arrows, system keys, numpad keys,
  and `NULL`, with `vendor-key-aliases` for lookup.
- Vendor model strings, static `Set_Keyboard_*` handler catalog, and Procreate
  static token catalog extracted from the app binary.
- Unit tests for the critical HID report layouts.
- Current-device verification for the tested baseline profile.
- Rough Tk GUI prototype for basic, media, mouse, macro, Procreate, LED, bulk
  clear, and read-back flows. The CLI is the primary supported interface.
- Focused experiment presets for the remaining physical test queue.
- Generated physical test plans for the remaining feature queue.

Implemented from the vendor app protocol, but still needs focused physical
testing on this board:

- Full read-only configuration and LED snapshots for before/after comparison.
- Snapshot writes back to the device via `restore-snapshot --write --yes`, with
  semantic diff support for post-restore behavior checks.
- GUI write flows beyond basic smoke coverage. The Tk GUI is intentionally
  secondary to the CLI and should be treated as experimental.
- Macro delay behavior beyond the tested layer-0 basic-mode token-list path.
- Consumer HID values beyond the tested media keys and raw `0x0192` usage.
- Keyboard-backlight brightness usages write/read back, but visible behavior is
  unconfirmed on available hardware.
- Bass/treble usages write/read back, but visible behavior is unconfirmed in the
  tested contexts.
- `Like` and swipe records. Page-4 codes `1` through `5` write/readback are
  confirmed, but visible target-app behavior remains inconclusive.
- Procreate preset writes via `procreate --action ...`; the mappings are
  statically extracted and need app-level physical testing.

Known limits:

- The vendor app exposes layer selection as an editor/app state. A standalone
  hardware "switch to layer N" key has not been identified yet; static analysis
  of `SendLayer(int)` shows UI state/style updates, not a HID write. Per-layer
  assignment/output is confirmed; standalone layer switching from the
  replacement tool is separate and still unidentified.
- LED mode bytes are writable and physically identified on wired USB. The
  observed wireless-dongle setup did not light LEDs, and the cause is not yet
  known. LED entries `13` through `16` may be used by another hardware variant,
  but are not visible on the tested `12+2KEY` board.
- Procreate target-app behavior is not exhaustively tested yet, even though the
  vendor token mappings are now statically extracted.

See `FEATURES.md` for the current feature matrix and focused test queue.
See `REVERSE_ENGINEERING.md` for the static-analysis notes behind the protocol
and remaining physical tests.
See `PHYSICAL_TESTS.md` for observed behavior on the connected board.

## hidapi

The tool uses `ctypes` and does not need a Python hidapi package. It still needs
a native `libhidapi` dynamic library for device access.

Lookup order:

1. `MINI_KEYBOARD_HIDAPI`
2. `--hidapi /path/to/libhidapi.dylib`
3. common Homebrew/macOS library paths
4. `ctypes.util.find_library()` for `hidapi`, `hidapi-hidraw`, or
   `hidapi-libusb`
5. `ctypes.util.find_library("hidapi")`

If the bundled library has the wrong CPU architecture for your Python, install a
matching native library, for example:

```sh
brew install hidapi
```

## Protocol notes

All writes observed in the vendor app are 65 bytes. Byte 0 is report ID `0x03`.

Probe keyboard model:

```text
03 fb fb fb 00 ...
```

Newer/basic key remap record:

```text
03 fd <physical-key> <layer+1> 01 00 01 00 00 <hid-keycode> ...
```

Older/basic key remap record:

```text
03 fd <physical-key> <layer+1> 01 00 00 00 00 00 00 01 00 <hid-keycode> ...
```

Commit/save:

```text
03 fd fe ff 00 ...
```

Newer media remap records use mode `02` and store the 16-bit Consumer HID
usage little-endian across the vendor app's 3-byte token slots:

```text
03 fd <physical-key> <layer+1> 02 00 02 00 00 <usage-lo> 00 00 <usage-hi> ...
```

Newer token-list records store per-token delay high byte, delay low byte, and
token byte in each 3-byte slot. Static analysis of the vendor delay UI confirms
18 cells at record offsets `0x06`, `0x09`, and onward. The token count is
record byte `0x05`. Some firmware accepts these only under specific mode bytes:

```text
03 fd <physical-key> <layer+1> <mode> 00 <count> <d1-hi> <d1-lo> <token1> <d2-hi> <d2-lo> <token2> ...
```

Newer mouse remap records use mode `03`; the app stores button, wheel, or swipe
fields in the same slot record. Wheel direction is byte `0x14` in the slot
record; optional Ctrl/Shift/Alt wheel modifiers use vendor tokens
`f1`/`f2`/`f3` at byte `0x08`.

RGB LED layer write:

```text
03 fe b0 <layer> <led-mode> <16 RGB triples> ...
```

RGB LED layer read:

```text
03 fa b0 <layer> 00 ...
```
