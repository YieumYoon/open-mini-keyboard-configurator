from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .catalog import identify_vendor_model_route, vendor_model_route_dict
from .protocol import DEFAULT_PRODUCT_ID, DEFAULT_USAGE, DEFAULT_USAGE_PAGE, DEFAULT_VENDOR_ID


STATUS_CATALOG_ONLY = "catalog-only"
STATUS_EXTERNAL_REFERENCE = "external-reference"
STATUS_FINGERPRINTED = "fingerprinted"
STATUS_READ_TESTED = "read-tested"
STATUS_WRITE_TESTED = "write-tested"
STATUS_PHYSICALLY_TESTED = "physically-tested"

PROTOCOL_FD_NEW = "fd-new"
PROTOCOL_FE_AA_TYPE1 = "fe-aa-type1"
PROTOCOL_LEGACY_8B = "legacy-8b"
PROTOCOL_STANDARD_HID_ONLY = "standard-hid-only"
PROTOCOL_UNKNOWN = "unknown"


@dataclass(frozen=True)
class DeviceProfile:
    id: str
    name: str
    layout: str
    vendor_id: int
    product_id: int
    protocol_family: str
    status: str
    write_support: str
    keys: int | None = None
    knobs: int | None = None
    layers: int | None = None
    model_bytes: tuple[int | None, int | None, int | None] | None = None
    usage_page: int | None = DEFAULT_USAGE_PAGE
    usage: int | None = None
    interface_number: int | None = None
    report_id: int | None = 0x03
    commit: str | None = None
    tested_os: tuple[str, ...] = ()
    tested_features: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    notes: str = ""

    @property
    def vid_pid(self) -> str:
        return f"{self.vendor_id:04x}:{self.product_id:04x}"

    @property
    def usb_label(self) -> str:
        usage_page = "-" if self.usage_page is None else f"{self.usage_page:04x}"
        usage = "-" if self.usage is None else f"{self.usage:04x}"
        interface = "-" if self.interface_number is None else str(self.interface_number)
        return f"{self.vid_pid} usage={usage_page}:{usage} interface={interface}"


@dataclass(frozen=True)
class ProfileMatch:
    profile: DeviceProfile
    confidence: str
    score: int
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()


DEVICE_PROFILES: tuple[DeviceProfile, ...] = (
    DeviceProfile(
        id="514c-8850-12plus2-fd",
        name="MINI_KEYBOARD 12+2KEY",
        layout="12+2KEY",
        vendor_id=DEFAULT_VENDOR_ID,
        product_id=DEFAULT_PRODUCT_ID,
        usage_page=DEFAULT_USAGE_PAGE,
        usage=DEFAULT_USAGE,
        interface_number=None,
        protocol_family=PROTOCOL_FD_NEW,
        report_id=0x03,
        commit="fd-fe-ff",
        status=STATUS_PHYSICALLY_TESTED,
        write_support="enabled",
        keys=12,
        knobs=2,
        layers=3,
        model_bytes=(12, 2, None),
        tested_os=("macOS", "Ubuntu"),
        tested_features=(
            "basic",
            "media",
            "mouse",
            "macro",
            "procreate",
            "rgb-led",
            "read-back",
            "snapshot",
            "restore",
        ),
        aliases=(
            "12+2KEY",
            "Widget::Set_Keyboard_12add2()",
            "MINI_KEYBOARD.app",
        ),
        sources=("local vendor-app static analysis", "local physical validation"),
        notes=(
            "Default write-enabled target for this project. Use wired USB; the "
            "observed wireless dongle exposes only standard input HID interfaces."
        ),
    ),
    DeviceProfile(
        id="514c-4155-wireless-standard-hid",
        name="MINI_KEYBOARD wireless dongle",
        layout="12+2KEY transport",
        vendor_id=0x514C,
        product_id=0x4155,
        usage_page=None,
        usage=None,
        interface_number=None,
        protocol_family=PROTOCOL_STANDARD_HID_ONLY,
        report_id=None,
        commit=None,
        status=STATUS_FINGERPRINTED,
        write_support="disabled",
        keys=12,
        knobs=2,
        layers=None,
        tested_os=("macOS",),
        tested_features=("standard-keyboard", "standard-mouse", "consumer-control"),
        aliases=("wireless dongle",),
        sources=("local HID enumeration",),
        notes="Observed dongle has no vendor-defined configuration interface on macOS.",
    ),
    DeviceProfile(
        id="514c-8851-fe-aa-type1",
        name="MINI_KEYBOARD compatible Type 1",
        layout="unknown",
        vendor_id=0x514C,
        product_id=0x8851,
        usage_page=DEFAULT_USAGE_PAGE,
        usage=None,
        interface_number=0,
        protocol_family=PROTOCOL_FE_AA_TYPE1,
        report_id=0x03,
        commit="aa-aa",
        status=STATUS_EXTERNAL_REFERENCE,
        write_support="disabled",
        keys=None,
        knobs=None,
        layers=3,
        tested_features=("basic",),
        aliases=("mini-keyboard-spec",),
        sources=("Rockheung/mini-keyboard-spec",),
        notes="External protocol reference only; not write-enabled by this project.",
    ),
    DeviceProfile(
        id="1189-8840-3plus1-fe-aa-type1",
        name="MINI_KEYBOARD 3+1KEY",
        layout="3+1KEY",
        vendor_id=0x1189,
        product_id=0x8840,
        usage_page=DEFAULT_USAGE_PAGE,
        usage=None,
        interface_number=0,
        protocol_family=PROTOCOL_FE_AA_TYPE1,
        report_id=0x03,
        commit="aa-aa",
        status=STATUS_EXTERNAL_REFERENCE,
        write_support="disabled",
        keys=3,
        knobs=1,
        layers=3,
        tested_os=("macOS",),
        tested_features=("basic", "media", "mouse", "lighting", "read-back"),
        aliases=("Fydun 3 Keys 1 Knob", "MacroPadStudio"),
        sources=("maerki/MacroPadStudio", "Rockheung/mini-keyboard-spec"),
        notes="Same product-family name but a different protocol family from the tested 514c:8850 board.",
    ),
    DeviceProfile(
        id="1189-8890-3plus1-legacy",
        name="MINI_KEYBOARD 3+1KEY legacy",
        layout="3+1KEY",
        vendor_id=0x1189,
        product_id=0x8890,
        usage_page=DEFAULT_USAGE_PAGE,
        usage=None,
        interface_number=1,
        protocol_family=PROTOCOL_LEGACY_8B,
        report_id=None,
        commit="aa-aa",
        status=STATUS_EXTERNAL_REFERENCE,
        write_support="disabled",
        keys=3,
        knobs=1,
        layers=1,
        tested_features=("basic",),
        aliases=("CH552G mini keyboard", "hid-minikb-libusb"),
        sources=("devkev/hid-minikb-libusb", "Rockheung/mini-keyboard-spec"),
        notes="External legacy 8-byte reference only; not write-enabled by this project.",
    ),
)


def device_profile_dict(profile: DeviceProfile) -> dict[str, object]:
    return {
        "id": profile.id,
        "name": profile.name,
        "layout": profile.layout,
        "keys": profile.keys,
        "knobs": profile.knobs,
        "layers": profile.layers,
        "usb": {
            "vendor_id": f"0x{profile.vendor_id:04x}",
            "product_id": f"0x{profile.product_id:04x}",
            "usage_page": None if profile.usage_page is None else f"0x{profile.usage_page:04x}",
            "usage": None if profile.usage is None else f"0x{profile.usage:04x}",
            "interface_number": profile.interface_number,
        },
        "protocol": {
            "family": profile.protocol_family,
            "report_id": None if profile.report_id is None else f"0x{profile.report_id:02x}",
            "commit": profile.commit,
        },
        "model_bytes": None
        if profile.model_bytes is None
        else [
            None if byte is None else f"0x{byte:02x}"
            for byte in profile.model_bytes
        ],
        "status": profile.status,
        "write_support": profile.write_support,
        "tested_os": list(profile.tested_os),
        "tested_features": list(profile.tested_features),
        "aliases": list(profile.aliases),
        "sources": list(profile.sources),
        "notes": profile.notes,
    }


def device_profiles(filter_text: str | None = None) -> list[DeviceProfile]:
    if filter_text is None:
        return list(DEVICE_PROFILES)
    needle = filter_text.lower()
    return [
        profile
        for profile in DEVICE_PROFILES
        if needle in profile.id.lower()
        or needle in profile.name.lower()
        or needle in profile.layout.lower()
        or needle in profile.protocol_family.lower()
        or needle in profile.status.lower()
        or needle in profile.vid_pid.lower()
        or any(needle in alias.lower() for alias in profile.aliases)
    ]


def _device_attr(device: Any, name: str) -> Any:
    return getattr(device, name)


def _confidence_from_score(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def match_profile(device: Any, profile: DeviceProfile) -> ProfileMatch | None:
    if _device_attr(device, "vendor_id") != profile.vendor_id:
        return None
    if _device_attr(device, "product_id") != profile.product_id:
        return None

    score = 40
    reasons = [f"VID:PID matches {profile.vid_pid}"]
    warnings: list[str] = []

    usage_page = _device_attr(device, "usage_page")
    usage = _device_attr(device, "usage")
    interface_number = _device_attr(device, "interface_number")
    product_string = (_device_attr(device, "product_string") or "").lower()

    if profile.usage_page is None:
        reasons.append("profile does not require a vendor configuration interface")
        score += 10
    elif usage_page == profile.usage_page:
        reasons.append(f"usage page matches 0x{usage_page:04x}")
        score += 25
    else:
        warnings.append(
            f"usage page 0x{usage_page:04x} differs from profile 0x{profile.usage_page:04x}"
        )

    if profile.usage is None:
        if usage_page == DEFAULT_USAGE_PAGE:
            reasons.append("vendor-defined usage page is present")
            score += 5
    elif usage == profile.usage:
        reasons.append(f"usage matches 0x{usage:04x}")
        score += 15
    else:
        warnings.append(f"usage 0x{usage:04x} differs from profile 0x{profile.usage:04x}")

    if profile.interface_number is None:
        if interface_number >= 0:
            score += 3
    elif interface_number == profile.interface_number:
        reasons.append(f"interface matches {interface_number}")
        score += 10
    else:
        warnings.append(
            f"interface {interface_number} differs from profile {profile.interface_number}"
        )

    if product_string and (
        "mini" in product_string
        or "keyboard" in product_string
        or any(alias.lower() in product_string for alias in profile.aliases)
    ):
        reasons.append(f"product string looks related: {product_string!r}")
        score += 5

    return ProfileMatch(
        profile=profile,
        confidence=_confidence_from_score(score),
        score=score,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def profile_matches(device: Any) -> list[ProfileMatch]:
    matches = [
        match
        for profile in DEVICE_PROFILES
        if (match := match_profile(device, profile)) is not None
    ]
    return sorted(matches, key=lambda match: match.score, reverse=True)


def best_profile_match(device: Any) -> ProfileMatch | None:
    matches = profile_matches(device)
    return matches[0] if matches else None


def profile_match_dict(match: ProfileMatch) -> dict[str, object]:
    return {
        "profile": device_profile_dict(match.profile),
        "confidence": match.confidence,
        "score": match.score,
        "reasons": list(match.reasons),
        "warnings": list(match.warnings),
    }


def _effective_write_support(device: Any, profile: DeviceProfile) -> str:
    if profile.write_support != "enabled":
        return profile.write_support
    if profile.usage_page is not None and _device_attr(device, "usage_page") != profile.usage_page:
        return "enabled-on-config-interface-only"
    if profile.usage is not None and _device_attr(device, "usage") != profile.usage:
        return "enabled-on-config-interface-only"
    if (
        profile.interface_number is not None
        and _device_attr(device, "interface_number") != profile.interface_number
    ):
        return "enabled-on-config-interface-only"
    return "enabled"


def device_fingerprint_dict(
    device: Any,
    match: ProfileMatch | None = None,
    model_bytes: tuple[int, int, int] | None = None,
    probe_error: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "vendor_id": f"0x{_device_attr(device, 'vendor_id'):04x}",
        "product_id": f"0x{_device_attr(device, 'product_id'):04x}",
        "release_number": f"0x{_device_attr(device, 'release_number'):04x}",
        "manufacturer_string": _device_attr(device, "manufacturer_string"),
        "product_string": _device_attr(device, "product_string"),
        "serial_number": _device_attr(device, "serial_number"),
        "usage_page": f"0x{_device_attr(device, 'usage_page'):04x}",
        "usage": f"0x{_device_attr(device, 'usage'):04x}",
        "interface_number": _device_attr(device, "interface_number"),
        "looks_like_config_interface": _device_attr(device, "usage_page") == DEFAULT_USAGE_PAGE,
        "path": device.path_text if hasattr(device, "path_text") else "",
    }
    if match is not None:
        result["match"] = profile_match_dict(match)
        result["effective_write_support"] = _effective_write_support(device, match.profile)
    if model_bytes is not None:
        result["model_bytes"] = list(model_bytes)
        route = identify_vendor_model_route(
            model_bytes,
            product_id=_device_attr(device, "product_id"),
        )
        if route is not None:
            result["vendor_model_route"] = vendor_model_route_dict(route)
    if probe_error is not None:
        result["probe_error"] = probe_error
    return result
