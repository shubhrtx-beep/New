"""Draw Color API — Target Visual Channel Containers.

Defines ColorBody, ColorBorder, ColorShadow, ColorGlow, and ColorFilter
representing shape interior, outline stroke, drop shadows, and glow effects.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from .errors import InvalidColorValueError
from .color_value import ColorValue, parse_color
from .gradient import ColorGradient
from .motion import is_dynamic_value

SUPPORTED_BLEND_MODES = {
    "normal",
    "multiply",
    "screen",
    "overlay",
    "darken",
    "lighten",
    "add",
    "difference",
}

SUPPORTED_BORDER_STYLES = {"solid", "dashed", "dotted"}

SUPPORTED_FILTERS = {
    "brightness",
    "contrast",
    "saturate",
    "grayscale",
    "invert",
    "sepia",
    "hue_rotate",
}


def _validate_blend(mode: str) -> str:
    if mode not in SUPPORTED_BLEND_MODES:
        raise ValueError(
            f"Unsupported blend mode '{mode}'. Must be one of {sorted(SUPPORTED_BLEND_MODES)}."
        )
    return mode


class ColorFilter:
    """Represents a composable post-processing color filter."""

    def __init__(self, name: str, amount: Union[float, Any] = 1.0) -> None:
        if name not in SUPPORTED_FILTERS:
            raise ValueError(
                f"Unsupported filter '{name}'. Must be one of {sorted(SUPPORTED_FILTERS)}."
            )
        self.name = name
        self.amount = amount

    @property
    def is_dynamic(self) -> bool:
        return is_dynamic_value(self.amount)

    def to_dict(self) -> Dict[str, Any]:
        amount_val = self.amount.to_dict() if hasattr(self.amount, "to_dict") else self.amount
        return {"name": self.name, "amount": amount_val}


class ColorBody:
    """Visual channel container for shape interior fill."""

    def __init__(
        self,
        fill: Union[str, Tuple, ColorValue, ColorGradient] = "#1e293b",
        opacity: Union[float, Any] = 1.0,
        blend: str = "normal",
        filters: Optional[Sequence[ColorFilter]] = None,
    ) -> None:
        if isinstance(fill, ColorGradient):
            self.fill: Union[ColorValue, ColorGradient] = fill
        else:
            self.fill = parse_color(fill)

        self.opacity = opacity
        self.blend = _validate_blend(blend)
        self.filters = list(filters or [])

    @property
    def is_dynamic(self) -> bool:
        if self.fill.is_dynamic or is_dynamic_value(self.opacity):
            return True
        return any(f.is_dynamic for f in self.filters)

    def to_dict(self) -> Dict[str, Any]:
        opacity_val = self.opacity.to_dict() if hasattr(self.opacity, "to_dict") else self.opacity
        return {
            "fill": self.fill.to_dict(),
            "opacity": opacity_val,
            "blend": self.blend,
            "filters": [f.to_dict() for f in self.filters],
        }


class ColorBorder:
    """Visual channel container for shape outline stroke."""

    def __init__(
        self,
        fill: Union[str, Tuple, ColorValue, ColorGradient] = "#38bdf8",
        width: Union[float, Any] = 1.0,
        style: str = "solid",
        opacity: Union[float, Any] = 1.0,
        blend: str = "normal",
    ) -> None:
        if isinstance(fill, ColorGradient):
            self.fill: Union[ColorValue, ColorGradient] = fill
        else:
            self.fill = parse_color(fill)

        if style not in SUPPORTED_BORDER_STYLES:
            raise InvalidColorValueError(
                f"Unsupported border style '{style}'. Must be one of {sorted(SUPPORTED_BORDER_STYLES)}."
            )

        self.width = width
        self.style = style
        self.opacity = opacity
        self.blend = _validate_blend(blend)

    @property
    def is_dynamic(self) -> bool:
        return (
            self.fill.is_dynamic
            or is_dynamic_value(self.width)
            or is_dynamic_value(self.opacity)
        )

    def to_dict(self) -> Dict[str, Any]:
        width_val = self.width.to_dict() if hasattr(self.width, "to_dict") else self.width
        opacity_val = self.opacity.to_dict() if hasattr(self.opacity, "to_dict") else self.opacity
        return {
            "fill": self.fill.to_dict(),
            "width": width_val,
            "style": self.style,
            "opacity": opacity_val,
            "blend": self.blend,
        }


class ColorShadow:
    """Visual channel container for drop shadows."""

    def __init__(
        self,
        fill: Union[str, Tuple, ColorValue] = "black",
        blur: Union[float, Any] = 16.0,
        spread: Union[float, Any] = 0.0,
        offset: Tuple[Union[float, Any], Union[float, Any]] = (0.0, 4.0),
        opacity: Union[float, Any] = 0.5,
        inner: bool = False,
    ) -> None:
        self.fill = parse_color(fill)
        self.blur = blur
        self.spread = spread
        self.offset = offset
        self.opacity = opacity
        self.inner = bool(inner)

    @property
    def is_dynamic(self) -> bool:
        return (
            self.fill.is_dynamic
            or is_dynamic_value(self.blur)
            or is_dynamic_value(self.spread)
            or is_dynamic_value(self.offset[0])
            or is_dynamic_value(self.offset[1])
            or is_dynamic_value(self.opacity)
        )

    def to_dict(self) -> Dict[str, Any]:
        blur_val = self.blur.to_dict() if hasattr(self.blur, "to_dict") else self.blur
        spread_val = self.spread.to_dict() if hasattr(self.spread, "to_dict") else self.spread
        opacity_val = self.opacity.to_dict() if hasattr(self.opacity, "to_dict") else self.opacity
        off_x = self.offset[0].to_dict() if hasattr(self.offset[0], "to_dict") else self.offset[0]
        off_y = self.offset[1].to_dict() if hasattr(self.offset[1], "to_dict") else self.offset[1]

        return {
            "fill": self.fill.to_dict(),
            "blur": blur_val,
            "spread": spread_val,
            "offset": [off_x, off_y],
            "opacity": opacity_val,
            "inner": self.inner,
        }


class ColorGlow:
    """Visual channel container for outer neon glow."""

    def __init__(
        self,
        fill: Union[str, Tuple, ColorValue] = "cyan",
        blur: Union[float, Any] = 24.0,
        spread: Union[float, Any] = 0.0,
        opacity: Union[float, Any] = 0.8,
    ) -> None:
        self.fill = parse_color(fill)
        self.blur = blur
        self.spread = spread
        self.opacity = opacity

    @property
    def is_dynamic(self) -> bool:
        return (
            self.fill.is_dynamic
            or is_dynamic_value(self.blur)
            or is_dynamic_value(self.spread)
            or is_dynamic_value(self.opacity)
        )

    def to_dict(self) -> Dict[str, Any]:
        blur_val = self.blur.to_dict() if hasattr(self.blur, "to_dict") else self.blur
        spread_val = self.spread.to_dict() if hasattr(self.spread, "to_dict") else self.spread
        opacity_val = self.opacity.to_dict() if hasattr(self.opacity, "to_dict") else self.opacity

        return {
            "fill": self.fill.to_dict(),
            "blur": blur_val,
            "spread": spread_val,
            "opacity": opacity_val,
        }


def body(
    fill: Union[str, Tuple, ColorValue, ColorGradient] = "#1e293b",
    opacity: Union[float, Any] = 1.0,
    blend: str = "normal",
    filters: Optional[Sequence[ColorFilter]] = None,
) -> ColorBody:
    return ColorBody(fill=fill, opacity=opacity, blend=blend, filters=filters)


def border(
    fill: Union[str, Tuple, ColorValue, ColorGradient] = "#38bdf8",
    width: Union[float, Any] = 1.0,
    style: str = "solid",
    opacity: Union[float, Any] = 1.0,
    blend: str = "normal",
) -> ColorBorder:
    return ColorBorder(fill=fill, width=width, style=style, opacity=opacity, blend=blend)


def shadow(
    fill: Union[str, Tuple, ColorValue] = "black",
    blur: Union[float, Any] = 16.0,
    spread: Union[float, Any] = 0.0,
    offset: Tuple[Union[float, Any], Union[float, Any]] = (0.0, 4.0),
    opacity: Union[float, Any] = 0.5,
    inner: bool = False,
) -> ColorShadow:
    return ColorShadow(fill=fill, blur=blur, spread=spread, offset=offset, opacity=opacity, inner=inner)


def glow(
    fill: Union[str, Tuple, ColorValue] = "cyan",
    blur: Union[float, Any] = 24.0,
    spread: Union[float, Any] = 0.0,
    opacity: Union[float, Any] = 0.8,
) -> ColorGlow:
    return ColorGlow(fill=fill, blur=blur, spread=spread, opacity=opacity)


def color_filter(name: str, amount: Union[float, Any] = 1.0) -> ColorFilter:
    return ColorFilter(name=name, amount=amount)
