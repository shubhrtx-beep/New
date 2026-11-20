"""Draw Shape API — Units, Metric Resolution and System Bounds.

Implements pure-number pass-through resolution for numeric, pixel ('px'),
and percentage ('%') strings across canvas, parent, and local scopes.
"""

from typing import Union, Tuple, List, Optional
from .errors import InvalidCoordinateValueError

# Global default canvas resolution
_CANVAS_SIZE: Tuple[float, float] = (1920.0, 1080.0)


def set_canvas_size(width: float, height: float) -> None:
    """Sets the global canvas reference dimensions for resolving percentage units on root shapes."""
    global _CANVAS_SIZE
    if width <= 0.0 or height <= 0.0:
        raise ValueError(f"Canvas dimensions must be positive, got ({width}, {height})")
    _CANVAS_SIZE = (float(width), float(height))


def get_canvas_size() -> Tuple[float, float]:
    """Returns the current global canvas reference dimensions (width, height)."""
    return _CANVAS_SIZE


class UnitResolver:
    """Resolves string units ('px', '%') into pure 32-bit floats before geometry processing."""

    @staticmethod
    def to_float(val: Union[float, int, str], reference: float = 1.0) -> float:
        """Resolves raw numbers, 'px', or '%' against a reference metric."""
        if isinstance(val, (int, float)):
            f_val = float(val)
            if f_val != f_val or f_val == float("inf") or f_val == float("-inf"):
                raise InvalidCoordinateValueError(f"Coordinate value cannot be NaN or Infinite: {val}")
            return f_val

        cleaned = str(val).strip().lower()
        try:
            if cleaned.endswith("px"):
                f_val = float(cleaned[:-2].strip())
            elif cleaned.endswith("%"):
                pct = float(cleaned[:-1].strip()) / 100.0
                f_val = pct * reference
            else:
                f_val = float(cleaned)

            if f_val != f_val or f_val == float("inf") or f_val == float("-inf"):
                raise InvalidCoordinateValueError(f"Coordinate value cannot be NaN or Infinite: {val}")
            return f_val
        except (ValueError, TypeError) as err:
            raise InvalidCoordinateValueError(f"Invalid unit or coordinate string: '{val}'") from err

    @classmethod
    def resolve_size(
        cls,
        size: Tuple[Union[float, str], Union[float, str]],
        ref_width: float,
        ref_height: float,
    ) -> Tuple[float, float]:
        """Resolves (width, height) tuple with mixed unit types against reference bounds."""
        if not isinstance(size, (tuple, list)) or len(size) != 2:
            raise ValueError(f"Size must be a 2-tuple (width, height), got {size}")
        return (
            cls.to_float(size[0], ref_width),
            cls.to_float(size[1], ref_height),
        )

    @classmethod
    def resolve_position(
        cls,
        pos: Tuple[Union[float, str], Union[float, str]],
        ref_width: float,
        ref_height: float,
    ) -> Tuple[float, float]:
        """Resolves (x, y) position tuple with mixed unit types against reference bounds."""
        if not isinstance(pos, (tuple, list)) or len(pos) != 2:
            raise ValueError(f"Position must be a 2-tuple (x, y), got {pos}")
        return (
            cls.to_float(pos[0], ref_width),
            cls.to_float(pos[1], ref_height),
        )

    @classmethod
    def resolve_origin(
        cls,
        origin: Union[Tuple[float, float], str],
        width: float,
        height: float,
    ) -> Tuple[float, float]:
        """Resolves named anchors or numeric coordinates into local origin offsets.

        Local coordinates have (0, 0) at the geometric center:
        - X range: [-width/2, width/2]
        - Y range: [-height/2, height/2] (+Y is up)
        """
        if isinstance(origin, (tuple, list)) and len(origin) == 2:
            ox = cls.to_float(origin[0], width)
            oy = cls.to_float(origin[1], height)
            return (ox, oy)

        if isinstance(origin, str):
            anchor = origin.strip().lower().replace("_", "-")
            half_w = width / 2.0
            half_h = height / 2.0
            anchor_map = {
                "center": (0.0, 0.0),
                "top": (0.0, half_h),
                "bottom": (0.0, -half_h),
                "left": (-half_w, 0.0),
                "right": (half_w, 0.0),
                "top-left": (-half_w, half_h),
                "top-right": (half_w, half_h),
                "bottom-left": (-half_w, -half_h),
                "bottom-right": (half_w, -half_h),
            }
            if anchor in anchor_map:
                return anchor_map[anchor]

        return (0.0, 0.0)

    @classmethod
    def resolve_corner_radius(
        cls,
        edges: Union[float, int, str, List[Union[float, int, str]]],
        min_dimension: float,
        vertex_count: int = 4,
    ) -> List[float]:
        """Resolves corner rounding radii against maximum allowable bevel limit.

        r_max = min_dimension / 2.0
        Percentages resolve against r_max:
        - '100%' -> r_max (fully rounded pill/circle)
        - '50%'  -> 0.5 * r_max
        """
        r_max = max(0.0, min_dimension / 2.0)

        def _resolve_one(val: Union[float, int, str]) -> float:
            if isinstance(val, str) and val.strip().endswith("%"):
                pct = float(val.strip()[:-1]) / 100.0
                r = pct * r_max
            else:
                r = cls.to_float(val, reference=r_max)
            return max(0.0, min(r, r_max))

        if isinstance(edges, (list, tuple)):
            return [_resolve_one(e) for e in edges]
        else:
            r = _resolve_one(edges)
            return [r] * vertex_count
