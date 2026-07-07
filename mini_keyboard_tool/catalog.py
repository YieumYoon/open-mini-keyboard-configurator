from __future__ import annotations

from dataclasses import dataclass


VENDOR_MODELS: tuple[str, ...] = (
    "2KEY",
    "3KEY",
    "3+1KEY",
    "4KEY",
    "4+1KEY",
    "4+1_2KEY",
    "5KEY",
    "6KEY",
    "6+1KEY",
    "6+2KEY",
    "9+2KEY",
    "9+3KEY",
    "11+3KEY",
    "12+2KEY",
    "12+3KEY",
    "15+3KEY",
)

VENDOR_MODEL_HANDLERS: tuple[dict[str, object], ...] = (
    {
        "model": "0+1KEY",
        "handler": "Widget::Set_Keyboard_0add1()",
        "keys": 0,
        "extras": 1,
        "public": False,
        "note": "internal handler symbol; no matching public model string observed",
    },
    {
        "model": "0+1_2KEY",
        "handler": "Widget::Set_Keyboard_0add1_2()",
        "keys": 0,
        "extras": 1,
        "public": False,
        "note": "internal alternate 0+1 handler",
    },
    {
        "model": "0+2KEY",
        "handler": "Widget::Set_Keyboard_0add2()",
        "keys": 0,
        "extras": 2,
        "public": False,
        "note": "internal handler symbol; no matching public model string observed",
    },
    {
        "model": "0+3KEY",
        "handler": "Widget::Set_Keyboard_0add3()",
        "keys": 0,
        "extras": 3,
        "public": False,
        "note": "internal handler symbol; no matching public model string observed",
    },
    {"model": "1KEY", "handler": "Widget::Set_Keyboard_1add0()", "keys": 1, "extras": 0, "public": False, "note": "internal handler symbol"},
    {"model": "2KEY", "handler": "Widget::Set_Keyboard_2add0()", "keys": 2, "extras": 0, "public": True, "note": "public model string observed"},
    {"model": "3KEY", "handler": "Widget::Set_Keyboard_3add0()", "keys": 3, "extras": 0, "public": True, "note": "public model string observed"},
    {"model": "3+1KEY", "handler": "Widget::Set_Keyboard_3add1()", "keys": 3, "extras": 1, "public": True, "note": "public model string observed"},
    {"model": "4KEY", "handler": "Widget::Set_Keyboard_4Key()", "keys": 4, "extras": 0, "public": True, "note": "public model string observed"},
    {"model": "4+1KEY", "handler": "Widget::Set_Keyboard_4add1()", "keys": 4, "extras": 1, "public": True, "note": "public model string observed"},
    {"model": "4+1_2KEY", "handler": "Widget::Set_Keyboard_4add2()", "keys": 4, "extras": 2, "public": True, "note": "public string naming is vendor-specific"},
    {"model": "4+3KEY", "handler": "Widget::Set_Keyboard_4add3()", "keys": 4, "extras": 3, "public": False, "note": "internal handler symbol; no matching public model string observed"},
    {"model": "5KEY", "handler": "Widget::Set_Keyboard_5Key_Mute()", "keys": 5, "extras": 0, "public": True, "note": "mute-specific handler/image strings observed"},
    {"model": "6KEY", "handler": "Widget::Set_Keyboard_6Key()", "keys": 6, "extras": 0, "public": True, "note": "public model string observed"},
    {"model": "6+1KEY", "handler": "Widget::Set_Keyboard_6add1()", "keys": 6, "extras": 1, "public": True, "note": "public model string observed"},
    {"model": "6+2KEY", "handler": "Widget::Set_Keyboard_6add2()", "keys": 6, "extras": 2, "public": True, "note": "public model string observed"},
    {"model": "6+2KEY-LAN-KD", "handler": "Widget::Set_Keyboard_6add2_Lan_KD()", "keys": 6, "extras": 2, "public": False, "note": "LAN/KD special handler and QR image strings observed"},
    {"model": "9KEY", "handler": "Widget::Set_Keyboard_9add0()", "keys": 9, "extras": 0, "public": False, "note": "internal handler symbol"},
    {"model": "9+2KEY", "handler": "Widget::Set_Keyboard_9add2()", "keys": 9, "extras": 2, "public": True, "note": "public model string observed"},
    {"model": "9+3KEY", "handler": "Widget::Set_Keyboard_9add3()", "keys": 9, "extras": 3, "public": True, "note": "public model string observed"},
    {"model": "11+3KEY", "handler": "Widget::Set_Keyboard_11add3()", "keys": 11, "extras": 3, "public": True, "note": "public model string observed"},
    {"model": "12KEY", "handler": "Widget::Set_Keyboard_12add0()", "keys": 12, "extras": 0, "public": False, "note": "internal handler symbol"},
    {"model": "12+2KEY", "handler": "Widget::Set_Keyboard_12add2()", "keys": 12, "extras": 2, "public": True, "note": "connected board handler; physically tested"},
    {"model": "12+3KEY", "handler": "Widget::Set_Keyboard_12add3()", "keys": 12, "extras": 3, "public": True, "note": "public model string observed"},
    {"model": "12+4KEY", "handler": "Widget::Set_Keyboard_12add4()", "keys": 12, "extras": 4, "public": False, "note": "internal handler symbol; no matching public model string observed"},
    {"model": "12+4KEY-LAN", "handler": "Widget::Set_Keyboard_12add4_Lan()", "keys": 12, "extras": 4, "public": False, "note": "LAN special handler observed"},
    {"model": "15+3KEY", "handler": "Widget::Set_Keyboard_15add3()", "keys": 15, "extras": 3, "public": True, "note": "public model string observed"},
    {"model": "16KEY", "handler": "Widget::Set_Keyboard_16add0()", "keys": 16, "extras": 0, "public": False, "note": "internal handler symbol"},
    {"model": "16+3KEY", "handler": "Widget::Set_Keyboard_16add3()", "keys": 16, "extras": 3, "public": False, "note": "internal handler symbol"},
    {"model": "21+1KEY", "handler": "Widget::Set_Keyboard_21add1()", "keys": 21, "extras": 1, "public": False, "note": "internal handler symbol"},
)


@dataclass(frozen=True)
class VendorModelRoute:
    model: str
    handler: str
    key_count: int
    extra_count: int
    public: bool
    feature: int | None = None
    feature_min: int | None = None
    feature_max: int | None = None
    product_id: int | None = None
    product_id_not: int | None = None
    kd_version: int | None = None
    note: str = ""

    def feature_condition(self) -> str:
        if self.feature is not None:
            return str(self.feature)
        parts = []
        if self.feature_min is not None:
            parts.append(f">={self.feature_min}")
        if self.feature_max is not None:
            parts.append(f"<={self.feature_max}")
        return " and ".join(parts) if parts else "*"

    def condition_text(self) -> str:
        parts = [f"bytes={self.key_count},{self.extra_count},{self.feature_condition()}"]
        if self.product_id is not None:
            parts.append(f"pid=0x{self.product_id:04x}")
        if self.product_id_not is not None:
            parts.append(f"pid!=0x{self.product_id_not:04x}")
        if self.kd_version is not None:
            parts.append(f"kd_version={self.kd_version}")
        return " ".join(parts)

    def matches(
        self,
        model_bytes: tuple[int, int, int],
        product_id: int | None = None,
        kd_version: int | None = None,
    ) -> bool:
        key_count, extra_count, feature = model_bytes
        if key_count != self.key_count or extra_count != self.extra_count:
            return False
        if self.feature is not None and feature != self.feature:
            return False
        if self.feature_min is not None and feature < self.feature_min:
            return False
        if self.feature_max is not None and feature > self.feature_max:
            return False
        if self.product_id is not None and product_id != self.product_id:
            return False
        if self.product_id_not is not None:
            if product_id is None or product_id == self.product_id_not:
                return False
        if self.kd_version is not None and kd_version != self.kd_version:
            return False
        return True


VENDOR_MODEL_ROUTES: tuple[VendorModelRoute, ...] = (
    VendorModelRoute(
        "0+1_2KEY",
        "Widget::Set_Keyboard_0add1_2()",
        0,
        1,
        False,
        feature_min=10,
        note="third model byte selects the alternate 0+1 handler",
    ),
    VendorModelRoute(
        "0+1KEY",
        "Widget::Set_Keyboard_0add1()",
        0,
        1,
        False,
        feature_max=9,
        note="internal handler symbol; no matching public model string observed",
    ),
    VendorModelRoute(
        "0+2KEY",
        "Widget::Set_Keyboard_0add2()",
        0,
        2,
        False,
        product_id=0x8850,
        note="PID-gated route in the vendor dispatcher",
    ),
    VendorModelRoute(
        "0+1KEY",
        "Widget::Set_Keyboard_0add1()",
        0,
        2,
        False,
        product_id_not=0x8850,
        note="vendor dispatcher falls back to the 0+1 handler for non-0x8850 PID",
    ),
    VendorModelRoute("0+3KEY", "Widget::Set_Keyboard_0add3()", 0, 3, False),
    VendorModelRoute("1KEY", "Widget::Set_Keyboard_1add0()", 1, 0, False),
    VendorModelRoute("2KEY", "Widget::Set_Keyboard_2add0()", 2, 0, True),
    VendorModelRoute("3KEY", "Widget::Set_Keyboard_3add0()", 3, 0, True),
    VendorModelRoute("3+1KEY", "Widget::Set_Keyboard_3add1()", 3, 1, True),
    VendorModelRoute("4KEY", "Widget::Set_Keyboard_4Key()", 4, 0, True),
    VendorModelRoute(
        "4+1_2KEY",
        "Widget::Set_Keyboard_4add2()",
        4,
        1,
        True,
        product_id=0x8851,
        note="PID 0x8851 selects the vendor-specific alternate 4+1 handler",
    ),
    VendorModelRoute(
        "4+1_2KEY",
        "Widget::Set_Keyboard_4add2()",
        4,
        1,
        True,
        feature=1,
        note="feature byte 1 selects the vendor-specific alternate 4+1 handler",
    ),
    VendorModelRoute(
        "4+1KEY",
        "Widget::Set_Keyboard_4add1()",
        4,
        1,
        True,
        feature=0,
        product_id_not=0x8851,
    ),
    VendorModelRoute("4+3KEY", "Widget::Set_Keyboard_4add3()", 4, 3, False),
    VendorModelRoute("5KEY", "Widget::Set_Keyboard_5Key_Mute()", 5, 0, True),
    VendorModelRoute("6KEY", "Widget::Set_Keyboard_6Key()", 6, 0, True),
    VendorModelRoute("6+1KEY", "Widget::Set_Keyboard_6add1()", 6, 1, True),
    VendorModelRoute(
        "6+2KEY-LAN-KD",
        "Widget::Set_Keyboard_6add2_Lan_KD()",
        6,
        2,
        False,
        kd_version=1,
        note="KD/LAN build flag selects the special handler",
    ),
    VendorModelRoute("6+2KEY", "Widget::Set_Keyboard_6add2()", 6, 2, True),
    VendorModelRoute("11+3KEY", "Widget::Set_Keyboard_11add3()", 11, 3, True),
    VendorModelRoute("12+3KEY", "Widget::Set_Keyboard_12add3()", 12, 3, True),
    VendorModelRoute(
        "12+4KEY-LAN",
        "Widget::Set_Keyboard_12add4_Lan()",
        12,
        4,
        False,
        kd_version=1,
        note="KD/LAN build flag selects the special handler",
    ),
    VendorModelRoute("12+4KEY", "Widget::Set_Keyboard_12add4()", 12, 4, False),
    VendorModelRoute("12KEY", "Widget::Set_Keyboard_12add0()", 12, 0, False),
    VendorModelRoute(
        "12+2KEY",
        "Widget::Set_Keyboard_12add2()",
        12,
        2,
        True,
        note="connected board route; observed model bytes include 12,2,11",
    ),
    VendorModelRoute("9KEY", "Widget::Set_Keyboard_9add0()", 9, 0, False),
    VendorModelRoute("9+2KEY", "Widget::Set_Keyboard_9add2()", 9, 2, True),
    VendorModelRoute("9+3KEY", "Widget::Set_Keyboard_9add3()", 9, 3, True),
    VendorModelRoute("16KEY", "Widget::Set_Keyboard_16add0()", 16, 0, False),
    VendorModelRoute("16+3KEY", "Widget::Set_Keyboard_16add3()", 16, 3, False),
    VendorModelRoute("21+1KEY", "Widget::Set_Keyboard_21add1()", 21, 1, False),
)


def vendor_model_route_dict(route: VendorModelRoute) -> dict[str, object]:
    data: dict[str, object] = {
        "model": route.model,
        "handler": route.handler,
        "key_count": route.key_count,
        "extra_count": route.extra_count,
        "feature": route.feature_condition(),
        "condition": route.condition_text(),
        "public": route.public,
        "note": route.note,
    }
    if route.product_id is not None:
        data["product_id"] = f"0x{route.product_id:04x}"
    if route.product_id_not is not None:
        data["product_id_not"] = f"0x{route.product_id_not:04x}"
    if route.kd_version is not None:
        data["kd_version"] = route.kd_version
    return data


def vendor_model_routes() -> list[dict[str, object]]:
    return [vendor_model_route_dict(route) for route in VENDOR_MODEL_ROUTES]


def identify_vendor_model_route(
    model_bytes: tuple[int, int, int],
    product_id: int | None = None,
    kd_version: int | None = None,
) -> VendorModelRoute | None:
    for route in VENDOR_MODEL_ROUTES:
        if route.matches(model_bytes, product_id=product_id, kd_version=kd_version):
            return route
    return None


def vendor_model_handlers() -> list[dict[str, object]]:
    return [dict(row) for row in VENDOR_MODEL_HANDLERS]


PROCREATE_PRESETS: tuple[tuple[str, str, tuple[int, ...]], ...] = (
    ("quick-menu", "QuickMenu", (0x2C,)),
    ("debug-commands", "Debug Commands", (0x35,)),
    ("brush-tool", "Activate Brush Tool", (0x05,)),
    ("color-panel", "Open Color Panel", (0x06,)),
    ("eraser-tool", "Activate Eraser Tool", (0x3E,)),
    ("layers-panel", "Open Layers Panel", (0x0F,)),
    ("selection-mode", "Enter Selection Mode", (0x16,)),
    ("transform-mode", "Enter Transform Mode", (0x19,)),
    ("swap-previous-current-color", "Switch Between Previous and Current Color", (0x1B,)),
    ("color-pick-alt", "Color Pick (Alt)", (0xF3,)),
    ("color-pick-m-ios17", "Color Pick M (iOS 17)", (0x10,)),
    ("clear-selected-layer", "Clear Selected Layer", (0xF4, 0x2A)),
    ("toggle-full-screen-mode", "Toggle Full Screen Mode", (0xF4, 0x27)),
    ("toggle-perspective-guide", "Toggle Perspective Guide", (0xF4, 0x33)),
    ("decrease-brush-size-1", "Decrease Brush Size by 1%", (0xF4, 0x2F)),
    ("increase-brush-size-1", "Increase Brush Size by 1%", (0xF4, 0x30)),
    ("decrease-brush-size-5", "Decrease Brush Size by 5%", (0x2F,)),
    ("increase-brush-size-5", "Increase Brush Size by 5%", (0x30,)),
    ("decrease-brush-size-10", "Decrease Brush Size by 10%", (0xF2, 0x2F)),
    ("increase-brush-size-10", "Increase Brush Size by 10%", (0xF2, 0x30)),
    ("copy-all", "Copy All", (0xF4, 0x04)),
    ("apply-color-balance", "Apply Color Balance Adjustment", (0xF4, 0x05)),
    ("copy", "Copy", (0xF4, 0x06)),
    ("clear-selection", "Clear Selection", (0xF4, 0x07)),
    ("duplicate-selection", "Duplicate Selection", (0xF4, 0x0D)),
    ("actions-menu", "Open Actions Menu", (0xF4, 0x0E)),
    ("apply-hsb-adjustment", "Apply HSB Adjustment", (0xF4, 0x18)),
    ("paste", "Paste", (0xF4, 0x19)),
    ("cut", "Cut", (0xF4, 0x1B)),
    ("undo", "Undo", (0xF4, 0x1D)),
    ("redo", "Redo", (0xF2, 0xF4, 0x1D)),
)

PROCREATE_ACTIONS: tuple[tuple[str, str], ...] = tuple(
    (slug, label) for slug, label, _ in PROCREATE_PRESETS
)
PROCREATE_PRESET_BY_SLUG: dict[str, tuple[str, tuple[int, ...]]] = {
    slug: (label, tokens) for slug, label, tokens in PROCREATE_PRESETS
}

VENDOR_MEDIA_LABELS: tuple[str, ...] = (
    "Play/Pause",
    "Stop",
    "Previous track",
    "Next track",
    "My Computer",
    "Screen brightness+",
    "Screen brightness-",
    "Multimedia",
    "Mute",
    "Volume+",
    "Volume-",
    "Calculator",
    "WWW home",
    "E-mail",
    "Bass+",
    "Bass-",
    "Treble+",
    "Treble-",
    "WWW Pagerefresh",
    "WWW Pageforward",
    "WWW Pageback",
)

VENDOR_MOUSE_LABELS: tuple[str, ...] = (
    "Mouse LeftKey",
    "Mouse Middle",
    "Mouse Right",
    "Mouse Wheel+",
    "Mouse Wheel-",
    "Ctrl+Mouse Up",
    "Ctrl+Mouse Down",
    "Shift+Mouse Up",
    "Shift+Mouse Down",
    "Alt+Mouse Up",
    "Alt+Mouse Down",
    "Like",
    "Swipe left",
    "Swipe right",
    "Swipe Up",
    "Swipe Down",
)
