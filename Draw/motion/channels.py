"""Draw Motion API — Supported Animation Channels.

Defines the supported channel names for motion.move(), their expected
value types, and validation utilities.
"""

from typing import Any, Dict, FrozenSet, Optional, Tuple, Union
from .errors import InvalidChannelError, InvalidChannelFormatError

# Supported channels for motion.move()
# Maps channel name -> brief description
SUPPORTED_MOVE_CHANNELS: Dict[str, str] = {
    "translate": "Position movement (x, y)",
    "rotate": "Rotation in degrees",
    "rotate_x": "Pseudo-3D rotation around X axis (degrees)",
    "rotate_y": "Pseudo-3D rotation around Y axis (degrees)",
    "rotate_3d": "Pseudo-3D rotation angles (rx, ry, rz)",
    "perspective": "Perspective depth / projection distance",
    "scale": "Scale factor (sx, sy)",
    "size": "Width/height (w, h)",
    "opacity": "Transparency 0.0–1.0",
    "blur": "Blur radius",
    "skew": "Skew angles (sx, sy)",
    "edges": "Corner rounding radius",
    "z": "Depth / z-order ranking",
    "color": "Color animation (integration with Draw Color)",
    "glow": "Glow visual animation",
}

# Channels that expect a 2-tuple value
_TUPLE_CHANNELS: FrozenSet[str] = frozenset({"translate", "scale", "size", "skew"})

# Channels that expect a 3-tuple value
_TUPLE3_CHANNELS: FrozenSet[str] = frozenset({"rotate_3d"})

# Channels that expect a single numeric value
_SCALAR_CHANNELS: FrozenSet[str] = frozenset({
    "rotate", "rotate_x", "rotate_y", "perspective",
    "opacity", "blur", "edges", "z"
})


def validate_channel_name(name: str) -> str:
    """Validates that a channel name is supported for motion.move()."""
    if name not in SUPPORTED_MOVE_CHANNELS:
        raise InvalidChannelError(
            f"Unsupported motion channel '{name}'. "
            f"Supported channels: {', '.join(sorted(SUPPORTED_MOVE_CHANNELS.keys()))}."
        )
    return name


def validate_channel_value(name: str, value: Any) -> Any:
    """Validates and normalizes a channel's target value.

    Returns the normalized value.
    """
    if name in _TUPLE_CHANNELS:
        if isinstance(value, (list, tuple)):
            if len(value) != 2:
                raise InvalidChannelFormatError(
                    f"Channel '{name}' expects a 2-element tuple (x, y), got {len(value)} elements."
                )
            return (float(value[0]), float(value[1]))
        elif isinstance(value, (int, float)):
            # Scalar provided for a tuple channel — broadcast to both axes
            v = float(value)
            return (v, v)
        else:
            raise InvalidChannelFormatError(
                f"Channel '{name}' expects a numeric tuple or scalar, got {type(value).__name__}."
            )
    elif name in _TUPLE3_CHANNELS:
        if isinstance(value, (list, tuple)):
            if len(value) != 3:
                raise InvalidChannelFormatError(
                    f"Channel '{name}' expects a 3-element tuple (rx, ry, rz), got {len(value)} elements."
                )
            return (float(value[0]), float(value[1]), float(value[2]))
        elif isinstance(value, (int, float)):
            v = float(value)
            return (v, v, v)
        else:
            raise InvalidChannelFormatError(
                f"Channel '{name}' expects a 3-element numeric tuple or scalar, got {type(value).__name__}."
            )
    elif name in _SCALAR_CHANNELS:
        if not isinstance(value, (int, float)):
            raise InvalidChannelFormatError(
                f"Channel '{name}' expects a numeric scalar, got {type(value).__name__}."
            )
        if name == "z":
            return int(round(float(value)))
        return float(value)
    else:
        # color, glow — pass through for now; their validation happens
        # at the integration layer with Draw.color
        return value
