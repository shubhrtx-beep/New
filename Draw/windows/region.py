"""Draw Window API — Region Ratio Validation and Region Lookup.

Regions are named areas created by a window's ``ratio`` dict. This module
validates ratio constraints, computes pixel dimensions from fractional
shares, and provides lookup for nested coordinate resolution.
"""

import warnings
from typing import Dict, Tuple, Optional, List, Any

from .errors import InvalidRegionRatioError
from ..maths import (
    validate_ratios as maths_validate_ratios,
    resolve_ratio as maths_resolve_ratio,
    resolve as maths_resolve,
)
from ..maths.errors import InvalidRatioError

# Floating-point tolerance for ratio sum validation
_RATIO_TOLERANCE = 1e-6


def validate_ratios(ratio: Dict[str, Any], total_dimension: Optional[float] = None) -> None:
    """Validates that all ratio values are well-formed and sum properly.

    Supports:
    * Standard fractional ratios (e.g. 0.05, 0.95 summing to 1.0)
    * Percentage strings (e.g. "5%", "95%" summing to 100%)
    * Absolute pixel / physical units (e.g. "40px", "2cm") mixed with ratios.

    Raises ``InvalidRegionRatioError`` with detailed diagnostics on failure.
    """
    if not ratio:
        return
    try:
        maths_validate_ratios(ratio, total_dimension=total_dimension)
    except InvalidRatioError as err:
        raise InvalidRegionRatioError(str(err)) from err


class Region:
    """Represents a named rectangular area inside a window.

    ``origin`` and ``size`` are in absolute pixel coordinates relative
    to the window's client area.
    """

    def __init__(
        self,
        name: str,
        ratio: float,
        origin: Tuple[float, float] = (0.0, 0.0),
        size: Tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self.name: str = name
        self.ratio: float = ratio
        self.origin: Tuple[float, float] = origin
        self.size: Tuple[float, float] = size

    @property
    def x(self) -> float:
        return self.origin[0]

    @property
    def y(self) -> float:
        return self.origin[1]

    @property
    def width(self) -> float:
        return self.size[0]

    @property
    def height(self) -> float:
        return self.size[1]

    def contains(self, px: float, py: float) -> bool:
        """Returns True if the point (px, py) lies inside this region."""
        return (
            self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "ratio": self.ratio,
            "origin": self.origin,
            "size": self.size,
        }


class RegionLayout:
    """Computes and caches absolute pixel regions from ratio definitions.

    Regions are stacked vertically (top-to-bottom) by default, in the
    order they appear in the ``ratio`` dict.
    Supports pure ratios (0.05, 0.95), percentages ("5%", "95%"),
    and physical / pixel units ("40px", "2cm").
    """

    def __init__(self, ratio: Dict[str, Any], window_size: Tuple[float, float]) -> None:
        self._window_size: Tuple[float, float] = (float(window_size[0]), float(window_size[1]))
        validate_ratios(ratio, total_dimension=self._window_size[1])
        self._raw_ratio: Dict[str, Any] = dict(ratio)
        self._ratio: Dict[str, float] = {}
        self._regions: Dict[str, Region] = {}
        self._order: List[str] = list(ratio.keys())
        self._compute()

    def _compute(self) -> None:
        """Recomputes region pixel bounds from ratios/units and window size."""
        w, h = self._window_size
        y_offset = 0.0
        self._regions.clear()
        heights = maths_resolve_ratio(self._raw_ratio, h)
        for name in self._order:
            region_height = heights[name]
            frac = (region_height / h) if h > 0.0 else 0.0
            self._ratio[name] = frac
            self._regions[name] = Region(
                name=name,
                ratio=frac,
                origin=(0.0, y_offset),
                size=(w, region_height),
            )
            y_offset += region_height

    def recalculate(self, window_size: Tuple[float, float]) -> None:
        """Recomputes all region bounds for a new window size."""
        self._window_size = (float(window_size[0]), float(window_size[1]))
        self._compute()

    def update_ratio(self, name: str, new_ratio: Any) -> None:
        """Updates a single region's ratio. Caller must revalidate totals."""
        if name in self._raw_ratio:
            self._raw_ratio[name] = new_ratio
            self._compute()

    def get(self, name: str) -> Optional[Region]:
        """Returns the Region by name, or None if not found."""
        return self._regions.get(name)

    def exists(self, name: str) -> bool:
        return name in self._regions

    @property
    def regions(self) -> Dict[str, Region]:
        return dict(self._regions)

    @property
    def window_size(self) -> Tuple[float, float]:
        return self._window_size

    def to_dict(self) -> Dict[str, object]:
        return {name: r.to_dict() for name, r in self._regions.items()}
