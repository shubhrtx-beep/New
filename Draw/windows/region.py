"""Draw Window API — Region Ratio Validation and Region Lookup.

Regions are named areas created by a window's ``ratio`` dict. This module
validates ratio constraints, computes pixel dimensions from fractional
shares, and provides lookup for nested coordinate resolution.
"""

import warnings
from typing import Dict, Tuple, Optional, List

from .errors import InvalidRegionRatioError

# Floating-point tolerance for ratio sum validation
_RATIO_TOLERANCE = 1e-6


def validate_ratios(ratio: Dict[str, float]) -> None:
    """Validates that all ratio values are in [0, 1] and sum to 1.0 within tolerance.

    Raises ``InvalidRegionRatioError`` with detailed diagnostics on failure.
    Ratios are never silently normalised.
    """
    if not ratio:
        return

    # Check individual range first
    for region_name, value in ratio.items():
        if value < 0.0 or value > 1.0:
            raise InvalidRegionRatioError(
                f"Invalid ratio for region '{region_name}'.\n\n"
                f"Received: {value}\n"
                f"Allowed range: 0.0 to 1.0"
            )

    # Check total sum
    total = sum(ratio.values())
    if abs(total - 1.0) > _RATIO_TOLERANCE:
        lines = [f"Region ratios must sum to 1.0.\n\nReceived:"]
        max_name_len = max(len(n) for n in ratio)
        for name, val in ratio.items():
            lines.append(f"    {name:<{max_name_len}} = {val}")
        lines.append(f"\nTotal = {total}")
        lines.append(f"Expected = 1.0")
        lines.append(f"\nDifference = {round(abs(total - 1.0), 10)}")
        raise InvalidRegionRatioError("\n".join(lines))


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
    """

    def __init__(self, ratio: Dict[str, float], window_size: Tuple[float, float]) -> None:
        validate_ratios(ratio)
        self._ratio: Dict[str, float] = dict(ratio)
        self._window_size: Tuple[float, float] = window_size
        self._regions: Dict[str, Region] = {}
        self._order: List[str] = list(ratio.keys())
        self._compute()

    def _compute(self) -> None:
        """Recomputes region pixel bounds from ratios and window size."""
        w, h = self._window_size
        y_offset = 0.0
        self._regions.clear()
        for name in self._order:
            r = self._ratio[name]
            region_height = r * h
            self._regions[name] = Region(
                name=name,
                ratio=r,
                origin=(0.0, y_offset),
                size=(w, region_height),
            )
            y_offset += region_height

    def recalculate(self, window_size: Tuple[float, float]) -> None:
        """Recomputes all region bounds for a new window size."""
        self._window_size = window_size
        self._compute()

    def update_ratio(self, name: str, new_ratio: float) -> None:
        """Updates a single region's ratio. Caller must revalidate totals."""
        if name in self._ratio:
            self._ratio[name] = new_ratio
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
