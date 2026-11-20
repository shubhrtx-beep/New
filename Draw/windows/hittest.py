"""Draw Window API — SDL2 Hit-Test Callback Logic.

Builds the hit-test decision function for ``SDL_SetWindowHitTest``.

The callback classifies each mouse position as one of:
* **Draggable area** — inside a drag_region, not over an interactive element.
* **Resize edge** — within ``resize_border`` pixels of a window edge.
* **Normal content** — everything else (clickable shapes, background).

Interactive shapes (those with ``action`` or ``callback``) inside a
drag region are automatically excluded from dragging so they remain
clickable.
"""

from typing import Tuple, Optional, Union, List, Set, Dict
from enum import Enum

from .region import RegionLayout


class HitTestResult(Enum):
    """SDL hit-test result classification."""
    NORMAL = "normal"
    DRAGGABLE = "draggable"
    RESIZE_TOP_LEFT = "resize_top_left"
    RESIZE_TOP = "resize_top"
    RESIZE_TOP_RIGHT = "resize_top_right"
    RESIZE_LEFT = "resize_left"
    RESIZE_RIGHT = "resize_right"
    RESIZE_BOTTOM_LEFT = "resize_bottom_left"
    RESIZE_BOTTOM = "resize_bottom"
    RESIZE_BOTTOM_RIGHT = "resize_bottom_right"


class HitTestResolver:
    """Resolves hit-test classification for a point in window coordinates.

    Decisions are built from:
    * ``drag_regions`` — region/element names where dragging is allowed.
    * ``resize_border`` — pixel width of the invisible resize edge.
    * ``interactive_exclusions`` — element names that have ``action``
      or ``callback`` and must remain clickable inside drag regions.
    """

    def __init__(
        self,
        window_size: Tuple[int, int],
        region_layout: Optional[RegionLayout],
        drag_regions: Optional[Union[str, List[str]]],
        resize_border: int = 0,
        interactive_exclusions: Optional[Set[str]] = None,
        element_bounds: Optional[Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]] = None,
    ) -> None:
        self._window_size = window_size
        self._region_layout = region_layout
        self._resize_border = max(0, resize_border)
        self._interactive_exclusions: Set[str] = interactive_exclusions or set()
        self._element_bounds: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = element_bounds or {}

        # Normalise drag_regions to a list
        if drag_regions is None:
            self._drag_regions: List[str] = []
        elif isinstance(drag_regions, str):
            self._drag_regions = [drag_regions]
        else:
            self._drag_regions = list(drag_regions)

    def update_window_size(self, size: Tuple[int, int]) -> None:
        self._window_size = size

    def update_element_bounds(
        self,
        bounds: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]],
    ) -> None:
        self._element_bounds = bounds

    def classify(self, px: float, py: float) -> HitTestResult:
        """Classifies a point (px, py) in window-local coordinates."""
        w, h = self._window_size
        b = self._resize_border

        # 1. Check resize edges first (highest priority)
        if b > 0:
            on_left = px < b
            on_right = px >= w - b
            on_top = py < b
            on_bottom = py >= h - b

            if on_top and on_left:
                return HitTestResult.RESIZE_TOP_LEFT
            if on_top and on_right:
                return HitTestResult.RESIZE_TOP_RIGHT
            if on_bottom and on_left:
                return HitTestResult.RESIZE_BOTTOM_LEFT
            if on_bottom and on_right:
                return HitTestResult.RESIZE_BOTTOM_RIGHT
            if on_top:
                return HitTestResult.RESIZE_TOP
            if on_bottom:
                return HitTestResult.RESIZE_BOTTOM
            if on_left:
                return HitTestResult.RESIZE_LEFT
            if on_right:
                return HitTestResult.RESIZE_RIGHT

        # 2. Check if inside any interactive exclusion element
        for elem_name in self._interactive_exclusions:
            if elem_name in self._element_bounds:
                origin, size = self._element_bounds[elem_name]
                ex, ey = origin
                ew, eh = size
                if ex <= px <= ex + ew and ey <= py <= ey + eh:
                    return HitTestResult.NORMAL

        # 3. Check if inside a drag region
        if self._drag_regions:
            for region_name in self._drag_regions:
                # Check ratio-defined regions
                if self._region_layout and self._region_layout.exists(region_name):
                    region = self._region_layout.get(region_name)
                    if region and region.contains(px, py):
                        return HitTestResult.DRAGGABLE

                # Check element-as-region
                if region_name in self._element_bounds:
                    origin, size = self._element_bounds[region_name]
                    ex, ey = origin
                    ew, eh = size
                    if ex <= px <= ex + ew and ey <= py <= ey + eh:
                        return HitTestResult.DRAGGABLE

        # 4. Default: normal content
        return HitTestResult.NORMAL
