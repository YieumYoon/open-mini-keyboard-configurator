# Vendor UI Coverage Map

This document maps visible/static vendor app behavior to the replacement tool.
The vendor app was inspected statically and was not run. "Confirmed" means the
behavior was physically tested on the connected `12+2KEY` board. "Static"
means the report shape or token data was extracted from the vendor binary and
covered by dry-runs/tests, but still needs focused physical testing.

## Status Legend

- Confirmed: physically tested on the connected board.
- Static: extracted from the vendor binary or report format and covered by
  dry-run/test generation.
- Needs physical test: implemented report writer exists, but behavior has not
  been validated on the board or target app yet.
- Not implemented intentionally: outside the HID remapping replacement scope.

## Coverage

| Vendor app area / action | Static evidence | Replacement CLI | GUI | Status / notes |
| --- | --- | --- | --- | --- |
| Device discovery and connect display | HID VID/PID/interface usage | `list` | List Devices | Confirmed read-only. |
| Model probe / key count | `read_Hidkey_Data(...)`, `Set_Keyboard_12add2()` | `info`, `vendor-models`, `slots` | Info | Confirmed for VID `0x514c`, PID `0x8850`, model `12+2KEY`. |
| Read configuration | `Read_configuration_clicked`, read prefix `03 fa ...` | `read-config`, `snapshot`, `verify-current` | Read Config | Confirmed key/media/mouse/LED summaries. Multi-slot `--key` / `--keys` filters are implemented for physical test loops. |
| Download / write changes | `HID_write()`, modified-record flags, commit `03 fd fe ff ...`; `on_download_clicked()` is an empty stub in this binary | all write-capable commands with `--write --yes` | Write Report | Confirmed for tested key, media, mouse, and LED writes. |
| Basic key page | key token-list records, mode `0x01`, vendor button names such as `PrtScSysRq`, `ArrowsUp`, `M_NUM1` | `remap`, `keycodes`, `vendor-key-aliases` | Basic | Confirmed layer 0 visible keys, including slot 12 `Shift+A`. Static vendor-style aliases are implemented for symbols, arrows, system keys, numpad keys, and `NULL`. |
| Modifier chords | token modifiers such as `f2` for Shift | `remap --to shift+a`, `macro --steps shift+a` | Basic, Macro | Confirmed slot 12 outputs uppercase `A`. |
| Layer selector buttons | `SendLayer(int)` updates selected app/editor layer | `--layer` on writers/readers | layer fields | Per-layer assignments are physically confirmed for layers 0, 1, and 2. No standalone hardware layer-switch HID write has been found. |
| Media/function page | `SetFunKey`, Consumer HID labels | `media`, `media-codes` | Media | Confirmed volume down, mute, volume up, play/pause, previous, next, stop, eject usage, rewind/fast-forward on macOS, display brightness up/down, and OS-mapped browser/app-launch usages on Ubuntu. Keyboard-backlight brightness and bass/treble write/read back but lacked visible confirmation on available hardware/apps. |
| Raw Consumer HID values | 16-bit Consumer HID record shape | `media --to 0xNNNN` | Media by named list only | Write/read-back confirmed for `0x0192` as `calculator`; Ubuntu showed the calculator action, while macOS showed no visible response in the tested context. Additional raw usages still need testing. |
| Mouse page | `SetMousePage(int)`, page `1` mouse/wheel records | `mouse`, `mouse-actions` | Mouse | Confirmed left/right/middle click, bottom knob wheel records, Ctrl-wheel zoom behavior, Shift-wheel horizontal movement, and Alt-wheel image-viewer zoom. Use Ubuntu/Linux as the wheel direction baseline; macOS can invert perceived scroll direction. |
| Swipe / Like gestures | page `4`, codes `1` through `5` | `mouse --to like`, `swipe-left`, `swipe-right`, `swipe-up`, `swipe-down` | Mouse | Write/read-back confirmed for all page-4 codes `1` through `5`; no visible target-app behavior was observed in the tested contexts, so cause remains unknown. |
| Macro / delay page | `Delay_Page_Init`, `Key_Delay_Page_Opt`, `SetMulKey`, `delay_spinBox_1..18`, delay cells at record offsets `0x06`, `0x09`, ... | `macro --delay`, `macro --delays` | Macro | Confirmed on layer 0: `a,b,c` with 500 ms per-token delays typed slowly as expected. Other layers/modes still need testing. |
| Procreate tab | `Procreate_Page()` creates 31 preset buttons | `procreate-actions`, `procreate --action ...` | Procreate | Static. All extracted presets are listed and writable; app-level Procreate behavior still needs testing. |
| RGB LED colors | `SetRgb_Led_Key`, `Set_Rgb_KeyColor`, `Read_RgbLed_DataDsp` | `led`, `led-read`, `led-colors`, `led-modes` | LED, Read LED | Confirmed layer 0 red, layer 1 green, layer 2 blue. LED entries `1`-`12` map to keys `1`-`12`; entries `13`-`16` write/read back but are not visible on this board. LED modes are physically identified on wired USB: `mode0` off, `mode1` static, `mode2` key-press fade, `mode3` key-press orthogonal ripple, `mode4` upper-left diagonal rainbow wave, and `mode5` left-to-right rainbow wave. |
| Vendor LED swatches | `LED_color_N` object/style strings | `led-colors`, `led --color swatch-N` | LED color entry | Static palette extracted for swatches with confirmed RGB styles. |
| Clean selected key | `on_CleanButton_clicked()` clears selected in-memory record | `remap --clear`, `clear --key ...` | Basic Clear, Clear tab | Implemented as explicit empty HID reports. Dry-run-first. |
| Clean all visible keys | `on_CleanALLButton_clicked()` clears active-layer UI records | `clear --keys ...`, `clear --tested-12key` | Clear tab | Implemented as explicit empty HID reports for selected slots/layers. Dry-run-first. |
| Model picker / related boards | model strings `2KEY` through `15+3KEY`, `Widget::Set_Keyboard_*` handlers | `vendor-models`, `vendor-models --handlers` | not shown | Static catalog. Current layout helpers target the tested `12+2KEY` board; handler list also shows internal layouts without public model strings. |
| Snapshot / restore safety | replacement-only safety workflow | `snapshot`, `diff-snapshot`, `restore-snapshot`, `profiles`, `profile`, `test-plan` | Read tab plus CLI | Replacement addition, not a vendor UI feature. Used for safe experiments and recovery. |
| Software update | `KB_UpData_SoftWare` strings | none | none | Not implemented intentionally; outside open HID remapping scope. |
| Exact Qt visual parity | Qt 5 UI resources/styles | none | rough Tk prototype | Not implemented intentionally. The replacement focuses on transparent, dry-run-first CLI HID control. |

## Current Completion Boundary

For the connected board, the core replacement path now covers the vendor app's
known HID programming areas: basic keys, media keys, mouse/wheel actions,
macro-style token lists, Procreate presets, RGB LEDs, read-back, clear, and
write/commit reports.

The remaining work is focused validation rather than finding a missing main
writer path: restore writes, raw Consumer HID visible behavior beyond tested
`0x0192`, page-4 swipe/Like target behavior, cross-variant meaning of LED
entries `13`-`16`, wireless-dongle LED behavior, standalone layer switching,
and Procreate behavior inside the target app.
