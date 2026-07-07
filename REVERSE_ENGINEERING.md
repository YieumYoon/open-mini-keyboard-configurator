# MINI_KEYBOARD Reverse Engineering Notes

These notes summarize the local static analysis used by this replacement tool.
The vendor app was inspected from the extracted package and was not run.
A higher-level vendor UI coverage map lives in `VENDOR_COVERAGE.md`.

## Vendor Binary

- App: `MINI_KEYBOARD.app`
- Executable: `Contents/MacOS/MINI_KEYBOARD`
- Architecture: x86_64 Mach-O
- UI framework: Qt 5
- HID library: bundled `libhidapi.0.12.0.dylib`

Important symbols remain in the binary, including:

- `Widget::HID_write()`
- `Widget::read_Hidkey_Data(unsigned char, unsigned char, unsigned char)`
- `Widget::Read_RgbLed_DataDsp()`
- `Widget::Set_Keyboard_Ver_SLOT(int)`
- `Widget::SendLayer(int)`
- `Widget::SetMousePage(int)`
- `Widget::SetRgb_Led_Key(int)`
- `Widget::on_confirmButton_clicked()`
- model-specific writers such as `Widget::Set_Keyboard_12add2()`

`Widget::on_download_clicked()` is present as a Qt slot but is an empty stub in
this binary. The replacement therefore treats `Widget::HID_write()` as the
authoritative write path and builds the HID reports directly instead of trying
to mirror one visible button handler.

## Tested Device

The connected board reports as the vendor model handled by
`Set_Keyboard_12add2()`.

Tested physical layout:

```text
[ 1 ] [ 2 ] [ 3 ] [ 4 ]      top-left=16  top-click=17  top-right=18
[ 5 ] [ 6 ] [ 7 ] [ 8 ]
[ 9 ] [10 ] [11 ] [12 ]      bottom-left=19 bottom-click=20 bottom-right=21
```

## Vendor Model Strings

The app contains UI strings for multiple related devices:

- `2KEY`
- `3KEY`
- `3+1KEY`
- `4KEY`
- `4+1KEY`
- `4+1_2KEY`
- `5KEY`
- `6KEY`
- `6+1KEY`
- `6+2KEY`
- `9+2KEY`
- `9+3KEY`
- `11+3KEY`
- `12+2KEY`
- `12+3KEY`
- `15+3KEY`

The current replacement focuses on the tested `12+2KEY` layout but keeps slot
validation broad enough for related boards.

The model strings are exposed by `vendor-models`. Static `Widget::Set_Keyboard_*`
layout handlers are exposed by `vendor-models --handlers`; that list includes
the connected board's `Widget::Set_Keyboard_12add2()` handler plus internal
handlers such as `12+4KEY`, `16+3KEY`, and `21+1KEY` that do not have matching
public model strings in this binary.

## HID Report Shapes

All observed writes are 65 bytes with report ID `0x03`.

Config write prefix:

```text
03 fd <slot> <layer+1> <mode> ...
```

Commit:

```text
03 fd fe ff ...
```

Read config:

```text
03 fa <count> <bank> <page> ...
```

LED write:

```text
03 fe b0 <layer> <mode> <16 RGB triples> ...
```

LED read:

```text
03 fa b0 <layer> ...
```

## Write Path

`Widget::HID_write()` writes 65-byte reports with report ID `0x03`. For the
newer board path used by the connected `12+2KEY` device, it scans modified
`_PHY2_KEY_Value` records, writes each changed key record, and then sends the
commit report `03 fd fe ff ...`. When LED state is marked changed, it writes
three `fe b0` LED records, one each for layers 0, 1, and 2.

The visible `on_download_clicked()` slot is empty in this binary, so the actual
UI flow likely reaches `HID_write()` through another confirmed/download handler
and the modified-record flags. The open replacement bypasses that UI indirection
and generates the same report family directly.

## Key Record Modes

- `01`: basic/key token-list records
- `02`: Consumer HID media/function records
- `03`: mouse/wheel/swipe records
- `05`: macro/delay-style token-list records. Layer-0 delayed token-list
  behavior is physically confirmed through the replacement's macro writer;
  other layers/modes still need focused testing.

On this board, modifier chords such as `Shift+A` work in mode `01` as token
lists: `f2 04`.

The basic key page contains `pushButton_*` object names such as
`pushButton_PrtScSysRq`, `pushButton_ArrowsUp`, and `pushButton_M_NUM1`.
Accepted equivalents are exposed through `vendor-key-aliases`.

Newer token-list and macro records use 18 three-byte cells at record offsets
`0x06`, `0x09`, `0x0c`, and so on. Each cell stores a 16-bit big-endian delay
followed by one token byte. `Key_Delay_Page_Opt()` and the delay UI reference
`delay_spinBox_1` through `delay_spinBox_18`, matching the replacement's
`macro --delay` / `macro --delays` report shape. The delay timing behavior
is physically confirmed for visible layer-0, layer-1, and layer-2 key outputs
on the tested board.

## Mouse And Swipe Page

`Widget::SetMousePage(int)` statically confirms:

- page `1`: mouse buttons, wheel, and Ctrl/Shift/Alt modified wheel records
- page `4`: gesture records
- page `4`, code `1`: vendor `Like`
- page `4`, code `2`: swipe left
- page `4`, code `3`: swipe right
- page `4`, code `4`: swipe up
- page `4`, code `5`: swipe down

The connected board has physically confirmed normal wheel and left-click records.
Right-click and middle-click are also physically confirmed; this corrected the
alias mapping to button `2` = right and button `4` = middle. Ctrl/Shift/Alt
modified wheel records are physically confirmed, with visible behavior depending
on the target app. Use Ubuntu/Linux as the practical wheel direction baseline;
macOS can present the opposite visual direction depending on natural scrolling
and target app focus. `Like` and swipe records are implemented and read back
correctly, but visible target-app behavior remains inconclusive in the tested
contexts.

## Built-In Restore Profiles

The replacement includes dry-run built-in profiles derived from the physically
verified readback state:

- `verified-controls`: slot 12 `Shift+A`, top knob volume down/mute/up, bottom
  knob wheel/click/wheel, and LED layers red/green/blue.
- `tested-12key-baseline`: `verified-controls` plus layer-0 slots 1 through 11
  as `1 2 3 4 5 6 7 8 9 0 -`.

These profiles are not additional reverse-engineered firmware features; they
are reproducible bundles of confirmed writes for fast recovery after physical
experiments.

## Clean And Clean All

`Widget::on_CleanButton_clicked()` clears the selected key's in-memory
configuration record for the active layer. `Widget::on_CleanALLButton_clicked()`
clears the in-memory records for the active layer and updates the Qt button text
back to blank. `Widget::on_clean_DevData()` is an empty stub in this binary.

Those UI handlers do not directly call `Widget::HID_write()`. The replacement
therefore exposes the same outcome as explicit, dry-run-first HID reports:
`remap --clear` for one slot, or `clear --keys ...` / `clear --tested-12key` for
bulk empty records.

## Media Functions

The vendor UI includes these Consumer HID names:

- Play/Pause
- Stop
- Previous track
- Next track
- My Computer
- Screen brightness up/down
- Multimedia
- Mute
- Volume up/down
- Calculator
- WWW home
- E-mail
- Bass up/down
- Treble up/down
- WWW page refresh/forward/back

The replacement supports named aliases and raw 16-bit Consumer HID values.
Volume down, mute, and volume up are physically confirmed.

## LED Swatches

The vendor UI contains `LED_color_N` button object names. Static string parsing
confirmed RGB styles for 53 swatches, now exposed as aliases such as
`swatch-1`, `vendor-1`, and `LED_color_1`.

Some object numbers appear without an adjacent `background-color: rgb(...)`
style in the extracted strings, so only confirmed RGB swatches are included in
the replacement palette.

## Procreate Tab

`Widget::Procreate_Page()` creates 31 Procreate buttons. Static disassembly
shows that each button stores the same token-list style record used by the
basic/macro path. These presets are exposed by `procreate-actions` and can be
built with `procreate --action ...`.

| Slug | Tokens | Label |
| --- | --- | --- |
| `quick-menu` | `space` | QuickMenu |
| `debug-commands` | `` ` `` | Debug Commands |
| `brush-tool` | `b` | Activate Brush Tool |
| `color-panel` | `c` | Open Color Panel |
| `eraser-tool` | `f5` | Activate Eraser Tool |
| `layers-panel` | `l` | Open Layers Panel |
| `selection-mode` | `s` | Enter Selection Mode |
| `transform-mode` | `v` | Enter Transform Mode |
| `swap-previous-current-color` | `x` | Switch Between Previous and Current Color |
| `color-pick-alt` | `alt` | Color Pick (Alt) |
| `color-pick-m-ios17` | `m` | Color Pick M (iOS 17) |
| `clear-selected-layer` | `cmd+backspace` | Clear Selected Layer |
| `toggle-full-screen-mode` | `cmd+0` | Toggle Full Screen Mode |
| `toggle-perspective-guide` | `cmd+;` | Toggle Perspective Guide |
| `decrease-brush-size-1` | `cmd+[` | Decrease Brush Size by 1% |
| `increase-brush-size-1` | `cmd+]` | Increase Brush Size by 1% |
| `decrease-brush-size-5` | `[` | Decrease Brush Size by 5% |
| `increase-brush-size-5` | `]` | Increase Brush Size by 5% |
| `decrease-brush-size-10` | `shift+[` | Decrease Brush Size by 10% |
| `increase-brush-size-10` | `shift+]` | Increase Brush Size by 10% |
| `copy-all` | `cmd+a` | Copy All |
| `apply-color-balance` | `cmd+b` | Apply Color Balance Adjustment |
| `copy` | `cmd+c` | Copy |
| `clear-selection` | `cmd+d` | Clear Selection |
| `duplicate-selection` | `cmd+j` | Duplicate Selection |
| `actions-menu` | `cmd+k` | Open Actions Menu |
| `apply-hsb-adjustment` | `cmd+u` | Apply HSB Adjustment |
| `paste` | `cmd+v` | Paste |
| `cut` | `cmd+x` | Cut |
| `undo` | `cmd+z` | Undo |
| `redo` | `shift+cmd+z` | Redo |

The mappings above are static-vendor extractions. The HID report format is
covered by tests, but behavior inside Procreate or another target app still
needs focused physical testing.

## Physical Test Notes

Detailed physical observations live in `PHYSICAL_TESTS.md`.

- Layer-0 per-token macro delays are confirmed: `a,b,c` with 500 ms delays typed
  slowly as expected.
- Raw Consumer HID `0x0192` is writable/readable, decodes as calculator, and was
  visible on Ubuntu. macOS showed no visible response in the tested context.
- Consumer transport/system usages are physically confirmed: play/pause,
  previous track, next track, stop, eject usage, rewind/fast-forward on macOS,
  and display brightness up/down.
- Browser/app-launch usages are physically confirmed with OS-specific behavior:
  Ubuntu handled browser back/forward/refresh, media-select, email,
  my-computer, internet-browser, browser-search, and browser-home; macOS visibly
  handled browser-search as Spotlight and did not visibly handle several other
  browser/app-launch usages in the tested contexts.
- Keyboard-backlight brightness usages write/read back, but visible behavior is
  unconfirmed on available hardware.
- Bass/treble Consumer HID usages write/read back, but visible behavior remains
  unconfirmed.
- `wheel-negative` scrolls down on Ubuntu and appeared upward on the tested
  macOS setup, so wheel aliases use raw sign plus Ubuntu/Linux as the practical
  direction baseline.
- `ctrl-wheel-negative` is writable/readable and was confirmed on Ubuntu as
  zoom-out. On macOS it looked similar to normal wheel movement in the tested
  context.
- `ctrl-wheel-positive` produced browser zoom, Shift-wheel produced horizontal
  movement, and Alt-wheel produced image-viewer zoom in the tested contexts.
- `like` plus swipe left/right/up/down are writable/readable, but the current
  tests did not determine why no visible target-app action appeared.
- LED modes are physically identified on wired USB: `mode0` off, `mode1`
  static color, `mode2` key-press fade, `mode3` key-press orthogonal ripple,
  `mode4` upper-left diagonal rainbow wave, and `mode5` left-to-right rainbow
  wave. The observed wireless-dongle setup did not light LEDs; cause is
  unknown.
- LED color entries `1` through `12` map directly to keys `1` through `12` on
  the tested board. Entries `13` through `16` write/read back but are not
  visible, likely reserved for other variants or non-populated LEDs.

## Layer Selection

`Widget::SendLayer(int)` appears to update editor/UI state:

- `Select_PHY_Key_Layer`
- button styles
- selected key text
- optional LED read/display state

No standalone hardware "switch to layer N" HID write has been identified yet.
Per-layer assignment bytes are nevertheless physically confirmed: slots 1
through 3 were written as `x/y/z` on layer 0, `1/2/3` on layer 1, and `7/8/9`
on layer 2, and each set output correctly when its layer was active.

## Remaining Physical Tests

The replacement exposes `test-plan` to print a safe sequence for these probes:
baseline snapshot, one focused experiment, after snapshot, diff, targeted
restore, and final verification. The plan command itself does not access the
HID device.

- standalone layer-switch HID write, if one exists
- snapshot restore writes
- raw Consumer HID visible behavior and usages beyond the tested named set
- `Like` and remaining swipe/page-4 target-app behavior
- cross-variant meaning of LED entries `13` through `16`
- wireless-dongle LED behavior
- app-level behavior of static Procreate presets
