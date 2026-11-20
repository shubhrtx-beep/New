"""Draw Color API — Color Theory, Harmonies, and Procedural Transforms.

Provides color.complement, analogous, triadic, split_complementary, tetradic,
monochromatic, mix, lighten, darken, and with_alpha helpers.
"""

from typing import (
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    Union,
)
from .errors import (
    UnknownColorNameError,
    InvalidColorValueError,
)
from .color_value import (
    ColorValue,
    parse_color,
    rgb_to_hsv,
    hsv_to_rgb,
    hsv,
    rgb,
)
from .motion import is_dynamic_value

# Global hook to resolve string references like "panel.body"
_REGISTRY_RESOLVER: Optional[Callable[[str], Any]] = None


def set_registry_resolver(resolver: Callable[[str], Any]) -> None:
    global _REGISTRY_RESOLVER
    _REGISTRY_RESOLVER = resolver


def _resolve_source_color(source: Any) -> ColorValue:
    """Resolves a ColorValue from an instance, string name, or dot reference ('panel.body')."""
    if isinstance(source, ColorValue):
        return source

    if isinstance(source, str):
        s = source.strip()
        if "." in s and _REGISTRY_RESOLVER is not None:
            resolved = _REGISTRY_RESOLVER(s)
            if resolved is not None:
                if isinstance(resolved, ColorValue):
                    return resolved
                return parse_color(resolved)
            raise UnknownColorNameError(f"Could not resolve color reference '{source}'.")

        # Try direct color parse
        try:
            return parse_color(s)
        except UnknownColorNameError:
            if _REGISTRY_RESOLVER is not None:
                resolved = _REGISTRY_RESOLVER(s)
                if resolved is not None:
                    if isinstance(resolved, ColorValue):
                        return resolved
                    return parse_color(resolved)
            raise

    return parse_color(source)


def complement(source: Any, angle: float = 180.0) -> ColorValue:
    """Calculates the complementary color by rotating hue by `angle` degrees (default 180°)."""
    c = _resolve_source_color(source)
    if c._hsv_channels is not None:
        h_orig = c._hsv_channels["h"]
        if is_dynamic_value(h_orig):
            return hsv(
                h=(h_orig + angle) % 360.0 if hasattr(h_orig, "__add__") else h_orig,
                s=c._hsv_channels["s"],
                v=c._hsv_channels["v"],
                a=c._hsv_channels["a"],
            )

    r, g, b, a = c.to_rgba_tuple()
    h_deg, s_pct, v_pct = rgb_to_hsv(r, g, b)
    new_h = (h_deg + angle) % 360.0
    return hsv(h=new_h, s=s_pct, v=v_pct, a=a)


def analogous(source: Any, angle: float = 30.0, count: int = 3) -> List[ColorValue]:
    """Generates a list of analogous colors shifted around the color wheel."""
    c = _resolve_source_color(source)
    r, g, b, a = c.to_rgba_tuple()
    h_deg, s_pct, v_pct = rgb_to_hsv(r, g, b)

    results: List[ColorValue] = []
    start_offset = -((count - 1) / 2.0) * angle
    for i in range(count):
        cur_h = (h_deg + start_offset + (i * angle)) % 360.0
        results.append(hsv(h=cur_h, s=s_pct, v=v_pct, a=a))
    return results


def triadic(source: Any) -> Tuple[ColorValue, ColorValue, ColorValue]:
    """Generates a 3-color equidistant triadic palette (0°, +120°, +240°)."""
    c = _resolve_source_color(source)
    r, g, b, a = c.to_rgba_tuple()
    h_deg, s_pct, v_pct = rgb_to_hsv(r, g, b)

    c1 = hsv(h=h_deg, s=s_pct, v=v_pct, a=a)
    c2 = hsv(h=(h_deg + 120.0) % 360.0, s=s_pct, v=v_pct, a=a)
    c3 = hsv(h=(h_deg + 240.0) % 360.0, s=s_pct, v=v_pct, a=a)
    return (c1, c2, c3)


def split_complementary(source: Any, angle: float = 150.0) -> Tuple[ColorValue, ColorValue, ColorValue]:
    """Generates a 3-color split complementary palette."""
    c = _resolve_source_color(source)
    r, g, b, a = c.to_rgba_tuple()
    h_deg, s_pct, v_pct = rgb_to_hsv(r, g, b)

    base = hsv(h=h_deg, s=s_pct, v=v_pct, a=a)
    split1 = hsv(h=(h_deg + angle) % 360.0, s=s_pct, v=v_pct, a=a)
    split2 = hsv(h=(h_deg - angle) % 360.0, s=s_pct, v=v_pct, a=a)
    return (base, split1, split2)


def tetradic(source: Any, angle: float = 90.0) -> Tuple[ColorValue, ColorValue, ColorValue, ColorValue]:
    """Generates a 4-color square or rectangular tetradic palette."""
    c = _resolve_source_color(source)
    r, g, b, a = c.to_rgba_tuple()
    h_deg, s_pct, v_pct = rgb_to_hsv(r, g, b)

    c1 = hsv(h=h_deg, s=s_pct, v=v_pct, a=a)
    c2 = hsv(h=(h_deg + angle) % 360.0, s=s_pct, v=v_pct, a=a)
    c3 = hsv(h=(h_deg + 180.0) % 360.0, s=s_pct, v=v_pct, a=a)
    c4 = hsv(h=(h_deg + 180.0 + angle) % 360.0, s=s_pct, v=v_pct, a=a)
    return (c1, c2, c3, c4)


def monochromatic(source: Any, count: int = 5) -> List[ColorValue]:
    """Generates shades and tints with varying lightness/value."""
    c = _resolve_source_color(source)
    r, g, b, a = c.to_rgba_tuple()
    h_deg, s_pct, _ = rgb_to_hsv(r, g, b)

    results: List[ColorValue] = []
    step = 80.0 / max(1, count - 1)
    for i in range(count):
        v = 20.0 + (i * step)
        results.append(hsv(h=h_deg, s=s_pct, v=v, a=a))
    return results


def mix(first: Any, second: Any, amount: float = 0.5, space: str = "srgb") -> ColorValue:
    """Linearly interpolates between two colors."""
    c1 = _resolve_source_color(first)
    c2 = _resolve_source_color(second)

    t = max(0.0, min(1.0, float(amount)))
    r1, g1, b1, a1 = c1.to_rgba_tuple()
    r2, g2, b2, a2 = c2.to_rgba_tuple()

    r = r1 * (1.0 - t) + r2 * t
    g = g1 * (1.0 - t) + g2 * t
    b = b1 * (1.0 - t) + b2 * t
    a = a1 * (1.0 - t) + a2 * t

    return rgb(r, g, b, a)


def lighten(source: Any, amount: float = 0.1) -> ColorValue:
    """Increases color lightness by blending toward pure white."""
    return mix(source, (1.0, 1.0, 1.0, 1.0), amount=amount)


def darken(source: Any, amount: float = 0.1) -> ColorValue:
    """Decreases color lightness by blending toward pure black."""
    return mix(source, (0.0, 0.0, 0.0, 1.0), amount=amount)


def with_alpha(source: Any, alpha: float = 1.0) -> ColorValue:
    """Returns the same color with a replaced alpha value."""
    c = _resolve_source_color(source)
    r, g, b, _ = c.to_rgba_tuple()
    a_f = max(0.0, min(1.0, float(alpha)))
    return rgb(r, g, b, a_f)
