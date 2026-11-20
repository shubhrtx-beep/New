"""Draw Color Subsystem Package.

Exposes visual style definitions, color space representations (rgb, rgba, hsv, hex),
channel sub-constructors (body, border, shadow, glow), gradients, motion drivers,
harmonies, palette tokens, and the canonical callable ColorAPI namespace.
"""

from .errors import (
    DrawColorError,
    InvalidColorValueError,
    UnknownColorNameError,
    InvalidHexColorError,
    ColorTokenCycleError,
    InvalidMotionError,
    DuplicateColorNameError,
    ColorNotFoundError,
)
from .motion import (
    MotionDriver,
    CycleDriver,
    PulseDriver,
    OscillateDriver,
    KeyframesDriver,
    TransitionDriver,
    ExpressionNode,
    time,
    expr,
    sin,
    cos,
    expr_abs,
    expr_min,
    expr_max,
    clamp,
    lerp,
    map_range,
    cycle,
    pulse,
    oscillate,
    keyframes,
    transition,
    is_dynamic_value,
)
from .color_value import (
    ColorValue,
    rgb,
    rgba,
    hsv,
    hex,
    parse_color,
    rgb_to_hsv,
    hsv_to_rgb,
    parse_hex_color,
    CSS_COLOR_NAMES,
)
from .gradient import (
    ColorGradient,
    gradient,
)
from .channels import (
    ColorFilter,
    ColorBody,
    ColorBorder,
    ColorShadow,
    ColorGlow,
    body,
    border,
    shadow,
    glow,
    color_filter,
)
from .harmonies import (
    complement,
    analogous,
    triadic,
    split_complementary,
    tetradic,
    monochromatic,
    mix,
    lighten,
    darken,
    with_alpha,
)
from .binding import (
    ColorBinding,
    IN_SHAPE,
)
from .palette import (
    PaletteRegistry,
    palette,
)
from .registry import (
    ColorRegistry,
    ColorAPI,
    GLOBAL_COLOR_REGISTRY,
)

# Instantiate the canonical callable namespace
color = ColorAPI(GLOBAL_COLOR_REGISTRY)

# Attach sub-constructors, color representations, and helpers directly onto color namespace
color.rgb = rgb  # type: ignore[attr-defined]
color.rgba = rgba  # type: ignore[attr-defined]
color.hsv = hsv  # type: ignore[attr-defined]
color.hex = hex  # type: ignore[attr-defined]
color.body = body  # type: ignore[attr-defined]
color.border = border  # type: ignore[attr-defined]
color.shadow = shadow  # type: ignore[attr-defined]
color.glow = glow  # type: ignore[attr-defined]
color.filter = color_filter  # type: ignore[attr-defined]
color.gradient = gradient  # type: ignore[attr-defined]
color.cycle = cycle  # type: ignore[attr-defined]
color.pulse = pulse  # type: ignore[attr-defined]
color.oscillate = oscillate  # type: ignore[attr-defined]
color.keyframes = keyframes  # type: ignore[attr-defined]
color.transition = transition  # type: ignore[attr-defined]
color.time = time  # type: ignore[attr-defined]
color.expr = expr  # type: ignore[attr-defined]
color.sin = sin  # type: ignore[attr-defined]
color.cos = cos  # type: ignore[attr-defined]
color.abs = expr_abs  # type: ignore[attr-defined]
color.min = expr_min  # type: ignore[attr-defined]
color.max = expr_max  # type: ignore[attr-defined]
color.clamp = clamp  # type: ignore[attr-defined]
color.lerp = lerp  # type: ignore[attr-defined]
color.map = map_range  # type: ignore[attr-defined]
color.complement = complement  # type: ignore[attr-defined]
color.analogous = analogous  # type: ignore[attr-defined]
color.triadic = triadic  # type: ignore[attr-defined]
color.split_complementary = split_complementary  # type: ignore[attr-defined]
color.tetradic = tetradic  # type: ignore[attr-defined]
color.monochromatic = monochromatic  # type: ignore[attr-defined]
color.mix = mix  # type: ignore[attr-defined]
color.lighten = lighten  # type: ignore[attr-defined]
color.darken = darken  # type: ignore[attr-defined]
color.with_alpha = with_alpha  # type: ignore[attr-defined]
color.IN_SHAPE = IN_SHAPE  # type: ignore[attr-defined]

__all__ = [
    "color",
    "palette",
    "ColorAPI",
    "ColorBinding",
    "ColorValue",
    "ColorGradient",
    "ColorBody",
    "ColorBorder",
    "ColorShadow",
    "ColorGlow",
    "ColorFilter",
    "ColorRegistry",
    "GLOBAL_COLOR_REGISTRY",
    "PaletteRegistry",
    "IN_SHAPE",
    "rgb",
    "rgba",
    "hsv",
    "hex",
    "body",
    "border",
    "shadow",
    "glow",
    "color_filter",
    "gradient",
    "cycle",
    "pulse",
    "oscillate",
    "keyframes",
    "transition",
    "time",
    "expr",
    "sin",
    "cos",
    "clamp",
    "lerp",
    "map_range",
    "complement",
    "analogous",
    "triadic",
    "split_complementary",
    "tetradic",
    "monochromatic",
    "mix",
    "lighten",
    "darken",
    "with_alpha",
    "DrawColorError",
    "InvalidColorValueError",
    "UnknownColorNameError",
    "InvalidHexColorError",
    "ColorTokenCycleError",
    "InvalidMotionError",
    "DuplicateColorNameError",
    "ColorNotFoundError",
]
