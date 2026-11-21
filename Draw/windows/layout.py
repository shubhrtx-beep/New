"""Draw Window API — Layout Engine: Region Sizing, Nested Coordinates, Anchors, and Margins.

Resolves absolute positions for elements inside regions, handles nested
element-as-region coordinate chains, and applies anchor/margin placement.
All size, position, and ratio values pass through the future
``units.resolve(value, axis_length_px)`` hook.
"""

from typing import Tuple, Optional, Dict, List, Any
import warnings

from .region import Region, RegionLayout


# Supported anchor values for element placement inside a region
SUPPORTED_ANCHORS = {
    "left",
    "right",
    "top",
    "bottom",
    "center",
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
}


def resolve_anchor_position(
    anchor: Optional[str],
    element_size: Tuple[float, float],
    container_origin: Tuple[float, float],
    container_size: Tuple[float, float],
    margin: Tuple[float, float] = (0.0, 0.0),
) -> Tuple[float, float]:
    """Computes the top-left position of an element inside a container
    given an anchor keyword, element size, container bounds, and margin.

    Container coordinates use screen convention: origin is top-left,
    +X right, +Y down.
    """
    cx, cy = container_origin
    cw, ch = container_size
    ew, eh = element_size
    mx = float(maths_resolve(margin[0], reference=cw)) if margin else 0.0
    my = float(maths_resolve(margin[1], reference=ch)) if margin else 0.0

    if anchor is None or anchor == "top_left":
        return (cx + mx, cy + my)
    elif anchor == "top_right":
        return (cx + cw - ew - mx, cy + my)
    elif anchor == "bottom_left":
        return (cx + mx, cy + ch - eh - my)
    elif anchor == "bottom_right":
        return (cx + cw - ew - mx, cy + ch - eh - my)
    elif anchor == "top":
        return (cx + (cw - ew) / 2.0, cy + my)
    elif anchor == "bottom":
        return (cx + (cw - ew) / 2.0, cy + ch - eh - my)
    elif anchor == "left":
        return (cx + mx, cy + (ch - eh) / 2.0)
    elif anchor == "right":
        return (cx + cw - ew - mx, cy + (ch - eh) / 2.0)
    elif anchor == "center":
        return (cx + (cw - ew) / 2.0, cy + (ch - eh) / 2.0)
    else:
        warnings.warn(f"Unknown anchor '{anchor}', defaulting to top_left.", stacklevel=2)
        return (cx + mx, cy + my)


from ..maths import (
    resolve as maths_resolve,
    resolve_size as maths_resolve_size,
)


def resolve_unit(value: object, axis_length_px: float) -> float:
    """Universal unit resolver hook for windows layout.
    Accepts numbers, px, cm, mm, in, pt, %, vw, vh.
    """
    return maths_resolve(value, reference=axis_length_px)


def resolve_size_pair(
    size: Tuple[object, object],
    ref_width: float,
    ref_height: float,
) -> Tuple[float, float]:
    """Resolves a (width, height) pair through the universal maths units hook."""
    return maths_resolve_size(size, ref_width=ref_width, ref_height=ref_height)


class LayoutResolver:
    """Resolves nested region/element coordinate chains.

    Given a ``RegionLayout`` and a mapping of element names to their
    resolved bounding boxes, computes the absolute position for any
    child element, walking up the parent chain:

        absolute_position = parent_absolute_position + child_local_position
    """

    def __init__(self, region_layout: Optional[RegionLayout] = None) -> None:
        self._region_layout: Optional[RegionLayout] = region_layout
        # element_name -> (abs_origin, size)
        self._element_bounds: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = {}

    def set_region_layout(self, layout: RegionLayout) -> None:
        self._region_layout = layout

    def register_element_bounds(
        self,
        name: str,
        origin: Tuple[float, float],
        size: Tuple[float, float],
    ) -> None:
        """Records the resolved absolute bounds for an element so it can
        serve as a container/region for child elements."""
        self._element_bounds[name] = (origin, size)

    def get_container(
        self, region_name: Optional[str], window_size: Tuple[float, float]
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Returns ``(origin, size)`` for a named region or element.

        Falls back to the whole window area if the region is unknown,
        logging a warning.
        """
        if region_name is None:
            return ((0.0, 0.0), window_size)

        # Try ratio-defined regions first
        if self._region_layout and self._region_layout.exists(region_name):
            r = self._region_layout.get(region_name)
            if r is not None:
                return (r.origin, r.size)

        # Then try element-as-region
        if region_name in self._element_bounds:
            return self._element_bounds[region_name]

        # Unresolved — fill whole window and warn
        warnings.warn(
            f"Region '{region_name}' not found in this window. "
            f"Element will fill the whole window area.",
            stacklevel=3,
        )
        return ((0.0, 0.0), window_size)

    def resolve_element_position(
        self,
        region_name: Optional[str],
        element_size: Tuple[float, float],
        anchor: Optional[str],
        margin: Tuple[float, float],
        window_size: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Full resolution pipeline: container lookup → anchor placement → margin offset."""
        container_origin, container_size = self.get_container(region_name, window_size)
        return resolve_anchor_position(
            anchor=anchor,
            element_size=element_size,
            container_origin=container_origin,
            container_size=container_size,
            margin=margin,
        )

    def clear(self) -> None:
        self._element_bounds.clear()
