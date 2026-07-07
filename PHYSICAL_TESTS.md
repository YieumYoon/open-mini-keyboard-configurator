# MINI Keyboard Physical Test Results

These notes record behavior observed on the connected `12+2KEY` board. Static
protocol support and physical/app-visible behavior are intentionally separated.

## 2026-07-06 Focused Probe

Backup snapshot before overwriting test slots:

```text
snapshots/physical-before-20260706.json
```

This first probe was observed primarily on macOS before the later Ubuntu
cross-checks below.

Written and read back:

| Slot | Report | Read-back | Physical result |
| --- | --- | --- | --- |
| 2 | `macro --steps a,b,c --delay 500` | `keys=a, b, c delays=500,500,500` | Confirmed. Types `a`, `b`, `c` slowly with visible delay. |
| 3 | `media --to 0x0192` | `media=calculator(0x0192)` | Stored and decoded. No visible macOS action was observed in this initial probe; the later full-matrix test confirmed the action on Ubuntu. |
| 4 | `mouse --to ctrl-wheel-negative` | `action=ctrl-wheel-negative` | Confirmed visible scroll-like movement. Observed as upward scroll on this macOS setup; perceived direction may depend on natural scrolling/app context. |
| 5 | `mouse --to swipe-left` | `action=swipe-left` | Stored and decoded. Visible target-app behavior stayed inconclusive in the tested contexts; cause is not yet known. |
| LED layer 0 | `led --mode mode2 --color #ff00ff` | `mode=2`, all LEDs `#ff00ff` | Confirmed. LEDs are off while idle; pressing a key lights purple, then slowly fades out. |

## Current Interpretation

- Per-token macro delay is physically confirmed for basic-mode token-list
  records on layer 0.
- Raw Consumer HID values are writable and readable. Usage `0x0192` decodes as
  calculator and was visible on Ubuntu; macOS showed no visible response in the
  tested context.
- Wheel records are writable, readable, and visible. Direction labels should be
  treated as raw wheel sign labels; use Ubuntu/Linux observed behavior as the
  practical baseline because macOS natural scrolling and focused app behavior
  can invert perceived motion.
- `ctrl-wheel-negative` is writable/readable and was visible on Ubuntu as
  zoom-out.
- Swipe/page-4 records are writable and readable, but the current tests did not
  prove whether the lack of visible target-app action is due to OS/app context,
  focus, unsupported gesture handling, or device behavior.
- LED `mode2` is a key-press reactive fade mode on the connected board over
  wired USB. The observed wireless-dongle LED behavior is still unknown.

## 2026-07-06 Wireless Dongle LED / Interface Check

The board was switched from wired USB to its wireless dongle while layer LEDs
were set to static red on all three layers.

Observed HID interfaces on macOS:

```text
Wired/config:   VID:PID 0x514c:0x8850 usage 0xff00:0x0001
Wireless dongle VID:PID 0x514c:0x4155 usages 0x0001:0x0006,
                0x000c:0x0001, 0x0001:0x0002, 0x0001:0x0001
```

Result:

- Wired USB exposes the vendor configuration interface and RGB LED output is
  visible.
- Wireless dongle does not expose the vendor `0xff00` configuration interface
  on macOS.
- Static red LED settings written over wired USB were not visible after
  switching to the wireless dongle.

Current interpretation:

- Keyboard, mouse, and Consumer Control input reports work through the wireless
  dongle.
- RGB LED control appears wired-only on the tested board/dongle path, or the
  dongle/firmware disables LED output for wireless power saving.
- Configuration and LED writes should be performed over wired USB.

## Verification Evidence

The current test state was read back into:

```text
snapshots/verification-current.json
```

Diffing `snapshots/physical-before-20260706.json` against that snapshot showed
only the intended physical-test changes:

- config slot 2: default `2` -> delayed `a,b,c`
- config slot 3: default `3` -> Consumer HID `calculator(0x0192)`
- config slot 4: default `4` -> `ctrl-wheel-negative`
- config slot 5: default `5` -> `swipe-left`
- LED layer 0: red `mode1` -> purple `mode2`

No other slot or LED layer differences were reported by the snapshot diff.

## 2026-07-06 Full 12-Key Matrix

Snapshot for the written test matrix:

```text
snapshots/fulltest-12key-current.json
snapshots/fulltest-12key-post-user-validation.json
```

After the user physically tested the slots, the device was read again into the
post-user-validation snapshot. `diff-snapshot --layer 0` and
`diff-snapshot --no-config` reported no differences against the written
fulltest snapshot for the validated layer-0 mappings and LED layers.

Written and read back:

| Slot | Mapping | Physical result |
| --- | --- | --- |
| 1 | `z` | Confirmed. Types `z`. |
| 2 | `shift+a` | Confirmed. Types uppercase `A`. |
| 3 | `a,b,c` with 500 ms delay | Confirmed. Types `abc` slowly. |
| 4 | `volume-down` | Confirmed. |
| 5 | `mute` | Confirmed. |
| 6 | `volume-up` | Confirmed. |
| 7 | raw Consumer HID `0x0192` / `calculator` | Confirmed on Ubuntu. No visible change observed on macOS. |
| 8 | `left-click` | Confirmed. |
| 9 | `wheel-negative` | Confirmed. Scrolls down on Ubuntu; appears as upward scroll on macOS with the tested settings. |
| 10 | `ctrl-wheel-negative` | Confirmed on Ubuntu as zoom-out. On macOS it appeared similar to normal wheel-negative in the tested context. |
| 11 | `swipe-left` | Stored and decoded. No visible difference observed in the tested contexts; cause is not yet known. |
| 12 | `like` | Stored and decoded. No visible difference observed in the tested contexts; cause is not yet known. |

LED behavior:

- Wired USB connection: LED layer 0 `mode2` lights purple on key press and then
  slowly fades out.
- Wireless dongle connection: LED did not light in the observed setup. Cause is
  not yet known; possible causes include product design, wireless power-saving,
  dongle HID report forwarding, or a different active interface.

Direction convention:

- Use Ubuntu/Linux observed behavior as the practical direction baseline for
  wheel aliases: `wheel-negative` behaves as scroll down there.
- macOS can present the opposite visual direction depending on natural scrolling
  and focused app behavior.

## 2026-07-06 Round 2 Mouse / Gesture Matrix

Snapshots:

```text
snapshots/round2-before-mouse-gesture.json
snapshots/round2-mouse-gesture-post-user-validation.json
```

Written, read back, and physically tested:

| Slot | Stored action after decoder correction | Physical result |
| --- | --- | --- |
| 1 | `middle-click` / button `4` | Appeared as middle-click or macOS control-click-like behavior. This corrected the previous `right-click` alias. |
| 2 | `right-click` / button `2` | Confirmed right-click. This corrected the previous `middle-click` alias. |
| 3 | `ctrl-wheel-positive` | Browser zoom. In an image viewer it behaved more like an up-arrow/up movement. |
| 4 | `shift-wheel-negative` | Appeared as horizontal movement to the right. |
| 5 | `shift-wheel-positive` | Appeared as horizontal movement to the left. |
| 6 | `alt-wheel-negative` | Image viewer zoom-out. |
| 7 | `alt-wheel-positive` | Image viewer zoom-in. |
| 8 | `like` | No visible response in the tested contexts. |
| 9 | `swipe-left` | No visible response in the tested contexts. |
| 10 | `swipe-right` | No visible response in the tested contexts. |
| 11 | `swipe-up` | No visible response in the tested contexts. |
| 12 | `swipe-down` | No visible response in the tested contexts. |

Corrections from this round:

- Mouse button aliases are now corrected to standard/observed HID behavior:
  button `1` = left, button `2` = right, button `4` = middle.
- Modifier wheel records are physically confirmed, but their visible behavior
  is target-app dependent.
- Page-4 gesture records remain writable/readable, but all tested page-4
  actions had no visible target-app response in this test round.

## 2026-07-06 Round 3 Media / Consumer HID Matrix

Snapshots:

```text
snapshots/round3-before-media.json
snapshots/round3-media-current.json
snapshots/round3-media-post-user-validation.json
```

Written, read back, and physically tested:

| Slot | Stored action | Physical result |
| --- | --- | --- |
| 1 | `play-pause` | Confirmed. |
| 2 | `previous-track` | Confirmed. |
| 3 | `next-track` | Confirmed. |
| 4 | `stop` | Confirmed. |
| 5 | `eject` | Some visible OS action was observed. Exact user-facing function is environment-dependent; the HID usage is Consumer `0x00b8` / eject. |
| 6 | `brightness-down` | Confirmed. |
| 7 | `brightness-up` | Confirmed. |
| 8 | `keyboard-brightness-down` | No visible macOS response. Ubuntu setup did not have a keyboard backlight to test. |
| 9 | `keyboard-brightness-up` | No visible macOS response. Ubuntu setup did not have a keyboard backlight to test. |
| 10 | `browser-back` | Confirmed on Ubuntu. No visible macOS response in the tested context. |
| 11 | `browser-forward` | Confirmed on Ubuntu. No visible macOS response in the tested context. |
| 12 | `browser-refresh` | Confirmed on Ubuntu. No visible macOS response in the tested context. |

Interpretation:

- Consumer HID transport controls are confirmed: play/pause, previous, next,
  stop, and eject usage writes/read back and produce visible action.
- Display brightness down/up is confirmed.
- Keyboard-backlight brightness usages write/read back, but visible behavior
  remains unconfirmed because the tested Mac did not respond and the Ubuntu
  setup lacked keyboard backlight hardware.
- Browser back/forward/refresh usages are confirmed on Ubuntu. The tested macOS
  browser context did not respond to those Consumer HID usages.

## 2026-07-06 Round 4 Extra Consumer HID Matrix

Snapshots:

```text
snapshots/round4-before-consumer-extra.json
snapshots/round4-consumer-extra-current.json
snapshots/round4-consumer-extra-post-user-validation.json
```

The post-user-validation snapshot was captured after the device became visible
to macOS HID enumeration again. Read-back matched the intended matrix.

Written, read back, and physically tested:

| Slot | Stored action | Physical result |
| --- | --- | --- |
| 1 | `rewind` | Confirmed on macOS. No visible Ubuntu response in the tested context. |
| 2 | `fast-forward` | Confirmed on macOS. No visible Ubuntu response in the tested context. |
| 3 | `media-select` | No visible macOS response. Ubuntu opened a settings window. |
| 4 | `email` | No visible macOS response. Ubuntu opened Firefox in the tested setup. |
| 5 | `my-computer` | No visible macOS response. Ubuntu opened the home/files view. |
| 6 | `internet-browser` | No visible macOS response. Ubuntu opened Firefox. |
| 7 | `browser-search` | Confirmed on macOS as Spotlight search. Ubuntu opened a search UI across windows. |
| 8 | `browser-home` | No visible macOS response. Confirmed on Ubuntu. |
| 9 | `bass-down` | No visible/identifiable response in the tested contexts. |
| 10 | `bass-up` | No visible/identifiable response in the tested contexts. |
| 11 | `treble-down` | No visible/identifiable response in the tested contexts. |
| 12 | `treble-up` | No visible/identifiable response in the tested contexts. |

Interpretation:

- Rewind and fast-forward are confirmed on macOS but not Ubuntu in the tested
  context.
- App-launch/browser Consumer HID usages are heavily OS-mapped: Ubuntu handled
  media-select, email, my-computer, internet-browser, browser-search, and
  browser-home; macOS visibly handled browser-search as Spotlight only.
- Bass/treble Consumer HID usages write/read back, but visible behavior remains
  unconfirmed.

## 2026-07-06 Round 5 LED Mode Matrix

Snapshots:

```text
snapshots/round5-led-mode0-current.json
snapshots/round5-led-mode1-current.json
snapshots/round5-led-mode3-current.json
snapshots/round5-led-mode4-current.json
snapshots/round5-led-mode5-current.json
```

Mode observations:

| Mode | Stored color | Physical result |
| --- | --- | --- |
| `mode0` | `#ff0000` | Read-back confirmed mode `0` and red color. No LED output while idle, and no LED output when pressing keys. |
| `mode1` | `#00ff00` | Read-back confirmed mode `1` and green color. LEDs stay on while idle; pressing keys does not visibly change the LED behavior. |
| `mode3` | `#0000ff` | Read-back confirmed mode `3` and blue color. LEDs are off while idle. Pressing a key triggers a wave/ripple that spreads horizontally and vertically from the key area, not diagonally, then turns off. |
| `mode4` | `#ffff00` | Read-back confirmed mode `4` and yellow color bytes. LEDs stay on while idle and continuously cycle through a rainbow diagonal wave that starts from the upper-left area. Pressing keys does not visibly change the LED behavior. |
| `mode5` | `#00ffff` | Read-back confirmed mode `5` and cyan color bytes. LEDs show an always-on rainbow wave moving left-to-right. |

Current interpretation:

- `mode0` appears to be LED off/disabled on the tested wired board.
- `mode1` appears to be static always-on color on the tested wired board.
- `mode3` appears to be a key-press reactive orthogonal wave/ripple effect on
  the tested wired board.
- `mode4` appears to be an always-on animated diagonal rainbow wave from the
  upper-left area on the tested wired board.
- `mode5` appears to be an always-on animated left-to-right rainbow wave on the
  tested wired board.

## 2026-07-06 Round 6 LED Index Mapping

Snapshots:

```text
snapshots/round6-led-index-01-04-current.json
snapshots/round6-led-index-05-08-current.json
snapshots/round6-led-index-09-12-current.json
snapshots/round6-led-index-13-16-current.json
```

Index observations:

| LED entry | Test color | Physical position |
| --- | --- | --- |
| 1 | red | key 1 |
| 2 | green | key 2 |
| 3 | blue | key 3 |
| 4 | white | key 4 |
| 5 | red | key 5 |
| 6 | green | key 6 |
| 7 | blue | key 7 |
| 8 | white | key 8 |
| 9 | red | key 9 |
| 10 | green | key 10 |
| 11 | blue | key 11 |
| 12 | white | key 12 |
| 13 | red | no visible LED on the tested board |
| 14 | green | no visible LED on the tested board |
| 15 | blue | no visible LED on the tested board |
| 16 | white | no visible LED on the tested board |

Current interpretation:

- LED entries `1` through `12` map directly to physical keys `1` through `12`.
- LED entries `13` through `16` are writable/readable but do not correspond to
  a visible LED on the tested `12+2KEY` board.

## 2026-07-06 Round 7 Layer Assignment Test

Snapshots:

```text
snapshots/round7-before-layer-test.json
snapshots/round7-layer-test-current.json
snapshots/round7-layer-test-layer2-visible-current.json
snapshots/round7-layer-test-post-user-validation.json
snapshots/round7-restore-verification.json
```

Written, read back, and physically tested:

| Layer | Slot 1 | Slot 2 | Slot 3 | Physical result |
| --- | --- | --- | --- | --- |
| 0 | `x` | `y` | `z` | Confirmed. Typed `xyz`. |
| 1 | `1` | `2` | `3` | Confirmed. Typed `123`. |
| 2 | `7` | `8` | `9` | Confirmed after retesting with visible text keys. Typed `789`. |

Notes:

- The first layer-2 probe used `F1`, `F2`, and `F3`, which did not produce text
  in a text field. That was inconclusive rather than a layer failure.
- Rewriting layer 2 to `7`, `8`, and `9` confirmed that layer-2 assignments are
  stored and physically output when layer 2 is active.
- A standalone HID report that switches the active layer has still not been
  identified; the confirmed behavior here is per-layer assignment and output
  when that layer is active.

Restore verification:

- Restoring `snapshots/round7-before-layer-test.json` and reading the device
  back into `snapshots/round7-restore-verification.json` produced no semantic
  differences.
- Raw diff showed only media-record page-byte normalization on layer-0 slots
  `1` through `3` (`page 01` to `page 00`) while the Consumer HID usages stayed
  the same.
