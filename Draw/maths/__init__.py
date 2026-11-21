"""Draw Maths Module — Package Entry Point.

Universal mathematics and unit conversion utilities for Draw3.
Every subsystem (Shape, Color, Motion, Window) imports from here.
"""

from .errors import (
    DrawMathsError,
    InvalidUnitError,
    InvalidUnitValueError,
    MissingReferenceError,
    InvalidRatioError,
)
from .units import (
    resolve,
    resolve_size,
    resolve_position,
    resolve_origin,
    resolve_corner_radius,
    resolve_stop_offset,
    validate_ratios,
    resolve_ratio,
    set_canvas_size,
    get_canvas_size,
    set_dpi,
    get_dpi,
)

__all__ = [
    # Errors
    "DrawMathsError",
    "InvalidUnitError",
    "InvalidUnitValueError",
    "MissingReferenceError",
    "InvalidRatioError",
    # Core resolver
    "resolve",
    # 2D convenience resolvers
    "resolve_size",
    "resolve_position",
    "resolve_origin",
    "resolve_corner_radius",
    # Gradient stop
    "resolve_stop_offset",
    # Ratio helpers
    "validate_ratios",
    "resolve_ratio",
    # Canvas / DPI config
    "set_canvas_size",
    "get_canvas_size",
    "set_dpi",
    "get_dpi",
]
