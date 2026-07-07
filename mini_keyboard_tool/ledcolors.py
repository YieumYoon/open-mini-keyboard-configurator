from __future__ import annotations

import re


RGB = tuple[int, int, int]


VENDOR_LED_SWATCHES: dict[int, RGB] = {
    1: (255, 0, 0),
    2: (255, 128, 60),
    3: (255, 255, 60),
    4: (0, 255, 0),
    5: (0, 255, 255),
    6: (0, 0, 255),
    7: (128, 0, 128),
    8: (139, 0, 0),
    9: (255, 165, 0),
    10: (255, 255, 150),
    11: (125, 255, 0),
    12: (0, 139, 139),
    13: (0, 0, 139),
    14: (255, 0, 255),
    15: (128, 0, 0),
    16: (255, 140, 0),
    17: (255, 215, 0),
    18: (0, 255, 128),
    19: (224, 255, 255),
    20: (135, 206, 235),
    21: (75, 0, 130),
    22: (255, 102, 102),
    23: (255, 200, 100),
    24: (255, 250, 100),
    25: (0, 128, 0),
    26: (0, 127, 150),
    27: (0, 128, 128),
    28: (230, 230, 250),
    29: (255, 192, 203),
    30: (255, 200, 0),
    31: (205, 170, 0),
    32: (128, 128, 0),
    33: (0, 255, 127),
    35: (143, 0, 255),
    36: (255, 69, 0),
    37: (255, 85, 0),
    38: (200, 255, 0),
    39: (128, 255, 128),
    40: (128, 192, 192),
    41: (173, 216, 230),
    42: (128, 128, 192),
    44: (255, 120, 0),
    45: (150, 150, 100),
    46: (34, 139, 34),
    47: (0, 100, 255),
    48: (0, 127, 255),
    49: (224, 176, 255),
    50: (255, 0, 255),
    51: (255, 102, 0),
    52: (150, 190, 100),
    53: (57, 255, 20),
    54: (0, 200, 100),
    56: (200, 200, 150),
}

NAMED_COLORS: dict[str, RGB] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "cyan": (0, 255, 255),
    "purple": (128, 0, 128),
    "magenta": (255, 0, 255),
    "orange": (255, 165, 0),
    "yellow": (255, 255, 60),
}


def rgb_hex(color: RGB) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


def canonical_led_swatches() -> list[tuple[str, RGB]]:
    return [(f"swatch-{index}", color) for index, color in sorted(VENDOR_LED_SWATCHES.items())]


def _parse_swatch_alias(text: str) -> RGB | None:
    normalized = text.strip().lower().replace("_", "-")
    match = re.fullmatch(r"(?:swatch|vendor|led-color)-?(\d+)", normalized)
    if match is None:
        match = re.fullmatch(r"led-?color-?(\d+)", normalized)
    if match is None:
        return None
    index = int(match.group(1))
    if index not in VENDOR_LED_SWATCHES:
        raise ValueError(f"unknown vendor LED swatch: {text!r}")
    return VENDOR_LED_SWATCHES[index]


def parse_led_color(value: str) -> RGB:
    text = value.strip()
    normalized = text.lower().replace("_", "-")
    if normalized in NAMED_COLORS:
        return NAMED_COLORS[normalized]

    swatch = _parse_swatch_alias(text)
    if swatch is not None:
        return swatch

    hex_text = text[1:] if text.startswith("#") else text
    if len(hex_text) == 6:
        try:
            return int(hex_text[0:2], 16), int(hex_text[2:4], 16), int(hex_text[4:6], 16)
        except ValueError as exc:
            raise ValueError(f"invalid RGB color: {value!r}") from exc

    parts = [part.strip() for part in text.replace("/", ",").split(",")]
    if len(parts) != 3:
        raise ValueError(
            "RGB color must be a name, vendor swatch, #rrggbb, or r,g,b"
        )
    try:
        red, green, blue = (int(part, 0) for part in parts)
    except ValueError as exc:
        raise ValueError(f"invalid RGB color: {value!r}") from exc
    for channel_name, channel in (("red", red), ("green", green), ("blue", blue)):
        if not 0 <= channel <= 0xFF:
            raise ValueError(f"{channel_name} channel out of range")
    return red, green, blue
