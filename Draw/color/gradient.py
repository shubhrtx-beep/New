"""Draw Color API — Gradient Fill Representations.

Supports linear, radial, and conical gradients with normalized stops,
spread modes, and color interpolation options.
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
from .motion import is_dynamic_value

VALID_GRADIENT_TYPES = {"linear", "radial", "conical"}
VALID_SPREAD_MODES = {"pad", "repeat", "reflect"}
VALID_INTERPOLATION_MODES = {"srgb", "linear"}
VALID_SPACES = {"shape", "scene"}


def _parse_stop_offset(offset: Union[float, int, str]) -> float:
    """Parses a stop offset float in [0.0, 1.0] or percentage string '0%'..'100%'."""
    if isinstance(offset, (int, float)):
        val = float(offset)
        if not (0.0 <= val <= 1.0):
            raise InvalidColorValueError(f"Gradient stop offset {val} must be in [0.0, 1.0].")
        return val

    if isinstance(offset, str):
        s = offset.strip()
        if s.endswith("%"):
            try:
                pct = float(s[:-1])
                val = pct / 100.0
                if not (0.0 <= val <= 1.0):
                    raise InvalidColorValueError(f"Gradient stop offset {offset} out of [0%, 100%].")
                return val
            except ValueError as e:
                raise InvalidColorValueError(f"Invalid percentage stop offset '{offset}'.") from e

        try:
            val = float(s)
            if not (0.0 <= val <= 1.0):
                raise InvalidColorValueError(f"Gradient stop offset {val} must be in [0.0, 1.0].")
            return val
        except ValueError as e:
            raise InvalidColorValueError(f"Invalid stop offset '{offset}'.") from e

    raise InvalidColorValueError(f"Invalid gradient stop offset type {type(offset).__name__}.")


class ColorGradient:
    """Represents a procedural or multi-stop gradient."""

    def __init__(
        self,
        gradient_type: str = "linear",
        angle: Union[float, Any] = 0.0,
        center: Tuple[float, float] = (50.0, 50.0),
        radius: float = 50.0,
        radius_x: Optional[float] = None,
        radius_y: Optional[float] = None,
        stops: Sequence[Tuple[Union[float, str], Any]] = (),
        spread: str = "pad",
        interpolation: str = "srgb",
        space: str = "shape",
        transform: Optional[Dict[str, Any]] = None,
    ) -> None:
        if gradient_type not in VALID_GRADIENT_TYPES:
            raise InvalidColorValueError(
                f"Invalid gradient type '{gradient_type}'. Must be one of {sorted(VALID_GRADIENT_TYPES)}."
            )
        if spread not in VALID_SPREAD_MODES:
            raise InvalidColorValueError(
                f"Invalid spread mode '{spread}'. Must be one of {sorted(VALID_SPREAD_MODES)}."
            )
        if interpolation not in VALID_INTERPOLATION_MODES:
            raise InvalidColorValueError(
                f"Invalid interpolation '{interpolation}'. Must be one of {sorted(VALID_INTERPOLATION_MODES)}."
            )
        if space not in VALID_SPACES:
            raise InvalidColorValueError(
                f"Invalid coordinate space '{space}'. Must be one of {sorted(VALID_SPACES)}."
            )

        self.gradient_type = gradient_type
        self.angle = angle
        self.center = (float(center[0]), float(center[1]))
        self.radius = float(radius)
        self.radius_x = float(radius_x) if radius_x is not None else None
        self.radius_y = float(radius_y) if radius_y is not None else None
        self.spread = spread
        self.interpolation = interpolation
        self.space = space
        self.transform = transform

        # Parse & normalize stops
        parsed_stops: List[Tuple[float, ColorValue]] = []
        for stop in stops:
            if not isinstance(stop, (tuple, list)) or len(stop) != 2:
                raise InvalidColorValueError(f"Gradient stop must be a (offset, color) pair, got '{stop}'.")
            offset_val = _parse_stop_offset(stop[0])
            color_val = parse_color(stop[1])
            parsed_stops.append((offset_val, color_val))

        # Sort stops by offset
        parsed_stops.sort(key=lambda s: s[0])
        self.stops = parsed_stops

    @property
    def is_dynamic(self) -> bool:
        """Returns True if the angle or any stop is dynamic."""
        if is_dynamic_value(self.angle):
            return True
        for _, c in self.stops:
            if c.is_dynamic:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes gradient into standard dictionary representation."""
        serialized_angle = self.angle.to_dict() if hasattr(self.angle, "to_dict") else self.angle

        serialized_stops: List[Dict[str, Any]] = []
        for offset, c in self.stops:
            serialized_stops.append({
                "offset": round(offset, 4),
                "color": c.to_dict(),
            })

        data: Dict[str, Any] = {
            "type": "gradient",
            "gradient_type": self.gradient_type,
            "angle": serialized_angle,
            "center": list(self.center),
            "radius": self.radius,
            "spread": self.spread,
            "interpolation": self.interpolation,
            "space": self.space,
            "stops": serialized_stops,
        }
        if self.radius_x is not None:
            data["radius_x"] = self.radius_x
        if self.radius_y is not None:
            data["radius_y"] = self.radius_y
        if self.transform is not None:
            data["transform"] = self.transform

        return data


def gradient(
    type: str = "linear",
    angle: Union[float, Any] = 0.0,
    center: Tuple[float, float] = (50.0, 50.0),
    radius: float = 50.0,
    radius_x: Optional[float] = None,
    radius_y: Optional[float] = None,
    stops: Sequence[Tuple[Union[float, str], Any]] = (),
    spread: str = "pad",
    interpolation: str = "srgb",
    space: str = "shape",
    transform: Optional[Dict[str, Any]] = None,
) -> ColorGradient:
    """Constructs a ColorGradient instance."""
    return ColorGradient(
        gradient_type=type,
        angle=angle,
        center=center,
        radius=radius,
        radius_x=radius_x,
        radius_y=radius_y,
        stops=stops,
        spread=spread,
        interpolation=interpolation,
        space=space,
        transform=transform,
    )
