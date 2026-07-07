# Submit a MINI_KEYBOARD-compatible Device

Use this checklist when reporting a keyboard that may belong to the same vendor
app family. Sales names are often reused across different boards, so USB/HID
evidence matters more than the listing title.

## 1. Basic identity

- Seller or listing name:
- Purchase link, if still available:
- Physical layout, for example `3+1KEY`, `6+2KEY`, `12+2KEY`:
- Keys:
- Knobs:
- Layers shown by the vendor app, if known:
- Operating system used for testing:

## 2. Photos

Attach photos you took yourself:

- Front of the keyboard.
- Back label or PCB markings, if visible.
- Vendor app screen showing the selected model, if available.

Do not submit seller images unless their license clearly allows redistribution.

## 3. USB/HID fingerprint

Run:

```sh
uv run python -m mini_keyboard_tool fingerprint --all --json
```

Paste the relevant JSON entry or attach the full output. The important fields
are:

- VID/PID.
- Product and manufacturer strings.
- Usage page and usage.
- Interface number.
- Whether a vendor-defined `0xff00` configuration interface exists.
- Matched built-in profile and confidence, if any.
- Vendor model route, if `fingerprint --probe-info` can decode the model bytes.

## 4. Read-only probes

Run these before any write tests:

```sh
uv run python -m mini_keyboard_tool fingerprint --probe-info
uv run python -m mini_keyboard_tool info
uv run python -m mini_keyboard_tool snapshot --json snapshots/your-device.json --no-led
```

If LED read is expected to work, also run:

```sh
uv run python -m mini_keyboard_tool snapshot --json snapshots/your-device-with-led.json
```

Record whether each command succeeded, timed out, or returned unexpected data.
For `fingerprint --probe-info` and `info`, keep the three model bytes and the
decoded vendor model route together; that route is often more reliable than the
seller's product name.

## 5. Write validation

Only run writes after you have a snapshot and understand how to restore it.
Start with one sacrificial slot and dry-run first:

```sh
uv run python -m mini_keyboard_tool remap --key 1 --to a
uv run python -m mini_keyboard_tool remap --key 1 --to a --write --yes
uv run python -m mini_keyboard_tool read-config --page 1 --key 1
```

For each write test, record:

- Command used.
- Expected physical behavior.
- Actual physical behavior.
- Read-back summary.
- Whether restore from the snapshot worked.

## 6. Suggested status

Pick the most conservative status that matches the evidence:

- `fingerprinted`: fingerprint output only.
- `read-tested`: read-only commands succeeded.
- `write-tested`: at least one write and read-back succeeded.
- `physically-tested`: the relevant feature set has been tested on real
  hardware.

Leave unknowns explicit. A careful "not tested" is more useful than a guess.
