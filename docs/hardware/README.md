# Hardware Variants

The original vendor software appears to support a family of small macro
keyboards. This project currently has physical validation for only the
`12+2KEY` board.

## Validation status

| Model | Status | Notes |
| --- | --- | --- |
| `12+2KEY` | Physically tested | 12 visible keys, two rotary encoders, wired RGB LED control verified. |
| Other public vendor model strings | Static only | Listed by `vendor-models`; needs hardware-owner testing. |
| Internal handler-only layouts | Static only | Listed by `vendor-models --handlers`; may represent unreleased, regional, or alternate boards. |

Public model strings currently known to the tool:

```text
2KEY, 3KEY, 3+1KEY, 4KEY, 4+1KEY, 4+1_2KEY, 5KEY,
6KEY, 6+1KEY, 6+2KEY, 9+2KEY, 9+3KEY, 11+3KEY,
12+2KEY, 12+3KEY, 15+3KEY
```

## Adding photos

Photos are welcome when they make the layout clearer, but do not copy product
photos from the vendor app, shopping pages, or marketplaces unless the image is
explicitly licensed for redistribution.

Acceptable image sources:

- Your own photo of hardware you own.
- A contributor-submitted photo with permission to publish under the repository
  license or a compatible license.
- A third-party image with a clear redistributable license and attribution.

Suggested file names:

```text
docs/hardware/12-plus-2key-front.jpg
docs/hardware/6-plus-2key-front.jpg
docs/hardware/15-plus-3key-front.jpg
```

For each photo, add a short note with:

- Model name, if known.
- Connection mode tested: wired USB, wireless dongle, or both.
- What was physically verified.
- Photo author or source/license.
