"""Draw Color API — Color Values, Formats, and Color Space Representations.

Provides pure Python color representations: color.rgb, color.rgba, color.hsv, and color.hex,
with strict range validation, CSS color names lookup, and deterministic conversion.
"""

import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from .errors import (
    InvalidColorValueError,
    InvalidHexColorError,
    UnknownColorNameError,
)
from .motion import is_dynamic_value

# Standard CSS / SVG color names mapped to canonical RGBA [0.0, 1.0]
CSS_COLOR_NAMES: Dict[str, Tuple[float, float, float, float]] = {
    "transparent": (0.0, 0.0, 0.0, 0.0),
    "black": (0.0, 0.0, 0.0, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0, 1.0),
    "green": (0.0, 0.50196, 0.0, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "yellow": (1.0, 1.0, 0.0, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0, 1.0),
    "gray": (0.50196, 0.50196, 0.50196, 1.0),
    "grey": (0.50196, 0.50196, 0.50196, 1.0),
    "darkgray": (0.66275, 0.66275, 0.66275, 1.0),
    "darkgrey": (0.66275, 0.66275, 0.66275, 1.0),
    "lightgray": (0.82745, 0.82745, 0.82745, 1.0),
    "lightgrey": (0.82745, 0.82745, 0.82745, 1.0),
    "orange": (1.0, 0.64706, 0.0, 1.0),
    "purple": (0.50196, 0.0, 0.50196, 1.0),
    "pink": (1.0, 0.75294, 0.79608, 1.0),
    "gold": (1.0, 0.84314, 0.0, 1.0),
    "silver": (0.75294, 0.75294, 0.75294, 1.0),
    "navy": (0.0, 0.0, 0.50196, 1.0),
    "teal": (0.0, 0.50196, 0.50196, 1.0),
    "lime": (0.0, 1.0, 0.0, 1.0),
    "maroon": (0.50196, 0.0, 0.0, 1.0),
    "olive": (0.50196, 0.50196, 0.0, 1.0),
    "aqua": (0.0, 1.0, 1.0, 1.0),
    "fuchsia": (1.0, 0.0, 1.0, 1.0),
    "crimson": (0.86275, 0.07843, 0.23529, 1.0),
    "indigo": (0.29412, 0.0, 0.50980, 1.0),
    "violet": (0.93333, 0.50980, 0.93333, 1.0),
    "coral": (1.0, 0.49804, 0.31373, 1.0),
    "salmon": (0.98039, 0.50196, 0.44706, 1.0),
    "khaki": (0.94118, 0.90196, 0.54902, 1.0),
    "plum": (0.86667, 0.62745, 0.86667, 1.0),
    "azure": (0.94118, 1.0, 1.0, 1.0),
    "beige": (0.96078, 0.96078, 0.86275, 1.0),
    "darkblue": (0.0, 0.0, 0.54510, 1.0),
    "darkgreen": (0.0, 0.39216, 0.0, 1.0),
    "darkred": (0.54510, 0.0, 0.0, 1.0),
}


def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[float, float, float]:
    """Converts H (0..360), S (0..100), V (0..100) to normalized RGB [0.0, 1.0]."""
    h_norm = (h % 360.0) / 60.0
    s_norm = max(0.0, min(100.0, s)) / 100.0
    v_norm = max(0.0, min(100.0, v)) / 100.0

    c = v_norm * s_norm
    x = c * (1.0 - abs((h_norm % 2.0) - 1.0))
    m = v_norm - c

    if 0.0 <= h_norm < 1.0:
        r, g, b = c, x, 0.0
    elif 1.0 <= h_norm < 2.0:
        r, g, b = x, c, 0.0
    elif 2.0 <= h_norm < 3.0:
        r, g, b = 0.0, c, x
    elif 3.0 <= h_norm < 4.0:
        r, g, b = 0.0, x, c
    elif 4.0 <= h_norm < 5.0:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x

    return (r + m, g + m, b + m)


def rgb_to_hsv(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """Converts normalized RGB [0.0, 1.0] to H (0..360), S (0..100), V (0..100)."""
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    delta = max_c - min_c

    v = max_c * 100.0

    if max_c == 0.0:
        s = 0.0
    else:
        s = (delta / max_c) * 100.0

    if delta == 0.0:
        h = 0.0
    elif max_c == r:
        h = (60.0 * ((g - b) / delta)) % 360.0
    elif max_c == g:
        h = (60.0 * ((b - r) / delta) + 120.0) % 360.0
    else:
        h = (60.0 * ((r - g) / delta) + 240.0) % 360.0

    return (h, s, v)


def parse_hex_color(hex_str: str) -> Tuple[float, float, float, float]:
    """Parses #RGB, #RGBA, #RRGGBB, #RRGGBBAA to canonical RGBA floats in [0.0, 1.0]."""
    s = hex_str.strip()
    if not s.startswith("#"):
        raise InvalidHexColorError(f"Hex color string must start with '#', got '{hex_str}'.")

    content = s[1:]
    if not re.fullmatch(r"[0-9a-fA-F]+", content):
        raise InvalidHexColorError(f"Invalid hexadecimal color string '{hex_str}'.")

    length = len(content)
    if length == 3:  # #RGB
        r = int(content[0] * 2, 16) / 255.0
        g = int(content[1] * 2, 16) / 255.0
        b = int(content[2] * 2, 16) / 255.0
        a = 1.0
    elif length == 4:  # #RGBA
        r = int(content[0] * 2, 16) / 255.0
        g = int(content[1] * 2, 16) / 255.0
        b = int(content[2] * 2, 16) / 255.0
        a = int(content[3] * 2, 16) / 255.0
    elif length == 6:  # #RRGGBB
        r = int(content[0:2], 16) / 255.0
        g = int(content[2:4], 16) / 255.0
        b = int(content[4:6], 16) / 255.0
        a = 1.0
    elif length == 8:  # #RRGGBBAA
        r = int(content[0:2], 16) / 255.0
        g = int(content[2:4], 16) / 255.0
        b = int(content[4:6], 16) / 255.0
        a = int(content[6:8], 16) / 255.0
    else:
        raise InvalidHexColorError(
            f"Invalid hex string length for '{hex_str}'. Expected 3, 4, 6, or 8 characters after '#'."
        )

    return (r, g, b, a)


def _validate_channel(val: Any, channel_name: str, is_alpha: bool = False) -> float:
    """Validates and normalizes a single color channel value (int or float)."""
    if isinstance(val, int) and not isinstance(val, bool):
        if is_alpha:
            if val == 0 or val == 1:
                return float(val)
            if 0 <= val <= 255:
                return val / 255.0
            raise InvalidColorValueError(f"Alpha channel '{channel_name}' value {val} out of bounds [0, 255].")
        if 0 <= val <= 255:
            return val / 255.0
        raise InvalidColorValueError(f"Channel '{channel_name}' value {val} exceeds integer bounds [0, 255].")

    if isinstance(val, float):
        if 0.0 <= val <= 1.0:
            return val
        raise InvalidColorValueError(f"Float channel '{channel_name}' value {val} exceeds unit bounds [0.0, 1.0].")

    raise InvalidColorValueError(f"Invalid type {type(val).__name__} for channel '{channel_name}'.")


class ColorValue:
    """Represents a validated, normalized color in RGBA or dynamic HSV/RGB space."""

    def __init__(
        self,
        mode: str = "rgba",
        rgba: Optional[Tuple[float, float, float, float]] = None,
        hsv_channels: Optional[Dict[str, Any]] = None,
        rgb_channels: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.mode = mode
        self._rgba: Optional[Tuple[float, float, float, float]] = rgba
        self._hsv_channels: Optional[Dict[str, Any]] = hsv_channels
        self._rgb_channels: Optional[Dict[str, Any]] = rgb_channels

    @property
    def is_dynamic(self) -> bool:
        """Returns True if any channel is driven dynamically."""
        if self._hsv_channels:
            return any(is_dynamic_value(v) for v in self._hsv_channels.values())
        if self._rgb_channels:
            return any(is_dynamic_value(v) for v in self._rgb_channels.values())
        return False

    def to_rgba_tuple(self) -> Tuple[float, float, float, float]:
        """Returns static RGBA tuple in [0.0, 1.0]. Evaluates static HSV if necessary."""
        if self._rgba is not None:
            return self._rgba
        if self._hsv_channels is not None:
            h = float(self._hsv_channels["h"])
            s = float(self._hsv_channels["s"])
            v = float(self._hsv_channels["v"])
            a = float(self._hsv_channels["a"])
            r, g, b = hsv_to_rgb(h, s, v)
            return (r, g, b, a)
        if self._rgb_channels is not None:
            r = float(self._rgb_channels["r"])
            g = float(self._rgb_channels["g"])
            b = float(self._rgb_channels["b"])
            a = float(self._rgb_channels["a"])
            return (r, g, b, a)
        return (0.0, 0.0, 0.0, 1.0)

    def to_dict(self) -> Any:
        """Serializes into standard transfer format for renderer."""
        if not self.is_dynamic:
            r, g, b, a = self.to_rgba_tuple()
            return [round(r, 4), round(g, 4), round(b, 4), round(a, 4)]

        if self.mode == "hsv" and self._hsv_channels:
            out: Dict[str, Any] = {"type": "hsv"}
            for k, val in self._hsv_channels.items():
                if hasattr(val, "to_dict"):
                    out[k] = val.to_dict()
                else:
                    out[k] = val
            return out

        if self.mode == "rgb" and self._rgb_channels:
            out = {"type": "rgb"}
            for k, val in self._rgb_channels.items():
                if hasattr(val, "to_dict"):
                    out[k] = val.to_dict()
                else:
                    out[k] = val
            return out

        r, g, b, a = self.to_rgba_tuple()
        return [round(r, 4), round(g, 4), round(b, 4), round(a, 4)]


def rgb(
    r: Union[int, float, Any],
    g: Union[int, float, Any],
    b: Union[int, float, Any],
    a: Union[int, float, Any] = 1.0,
) -> ColorValue:
    """Constructs a ColorValue using Red, Green, Blue, and optional Alpha channels."""
    if any(is_dynamic_value(ch) for ch in (r, g, b, a)):
        return ColorValue(
            mode="rgb",
            rgb_channels={"r": r, "g": g, "b": b, "a": a},
        )

    r_f = _validate_channel(r, "r")
    g_f = _validate_channel(g, "g")
    b_f = _validate_channel(b, "b")
    a_f = _validate_channel(a, "a", is_alpha=True)

    return ColorValue(mode="rgba", rgba=(r_f, g_f, b_f, a_f))


def rgba(
    r: Union[int, float, Any],
    g: Union[int, float, Any],
    b: Union[int, float, Any],
    a: Union[int, float, Any] = 1.0,
) -> ColorValue:
    """Alias for color.rgb with explicit alpha parameter."""
    return rgb(r, g, b, a)


def hsv(
    h: Union[float, int, Any],
    s: Union[float, int, Any] = 100.0,
    v: Union[float, int, Any] = 100.0,
    a: Union[float, int, Any] = 1.0,
) -> ColorValue:
    """Constructs a ColorValue using Hue (0..360), Saturation (0..100%), and Value (0..100%)."""
    if any(is_dynamic_value(ch) for ch in (h, s, v, a)):
        return ColorValue(
            mode="hsv",
            hsv_channels={"h": h, "s": s, "v": v, "a": a},
        )

    h_f = float(h)
    s_f = float(s)
    v_f = float(v)
    a_f = _validate_channel(a, "a", is_alpha=True)

    if not (0.0 <= s_f <= 100.0):
        raise InvalidColorValueError(f"HSV saturation {s_f} out of bounds [0, 100].")
    if not (0.0 <= v_f <= 100.0):
        raise InvalidColorValueError(f"HSV value {v_f} out of bounds [0, 100].")

    r, g, b = hsv_to_rgb(h_f, s_f, v_f)
    return ColorValue(mode="rgba", rgba=(r, g, b, a_f))


def hex(value: str) -> ColorValue:
    """Constructs a ColorValue by parsing a hexadecimal string (#RGB, #RGBA, #RRGGBB, #RRGGBBAA)."""
    rgba_tuple = parse_hex_color(value)
    return ColorValue(mode="rgba", rgba=rgba_tuple)


def parse_color(val: Any) -> ColorValue:
    """Converts any supported color representation into a normalized ColorValue."""
    if isinstance(val, ColorValue):
        return val

    if isinstance(val, str):
        val_clean = val.strip()
        if val_clean.startswith("#"):
            return hex(val_clean)
        lower_name = val_clean.lower()
        if lower_name in CSS_COLOR_NAMES:
            return ColorValue(mode="rgba", rgba=CSS_COLOR_NAMES[lower_name])
        raise UnknownColorNameError(f"Unknown color name '{val}'.")

    if isinstance(val, (tuple, list)):
        length = len(val)
        if length == 3:
            return rgb(val[0], val[1], val[2], 1.0)
        elif length == 4:
            return rgb(val[0], val[1], val[2], val[3])
        raise InvalidColorValueError(f"Color tuple must have 3 or 4 channels, got {length}.")

    raise InvalidColorValueError(f"Unsupported color input value '{val}' of type {type(val).__name__}.")
