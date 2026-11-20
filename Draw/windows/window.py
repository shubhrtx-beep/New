"""Draw Window API — Window Object and SDL2 Lifecycle.

The ``Window`` class represents one SDL2 window. It owns the frame
description, region layout, element membership, hit-test resolver,
and event dispatch for that window.

The SDL2 backend is abstracted behind a thin interface so the data
model can be tested without a live display.
"""

import warnings
from typing import Tuple, Dict, List, Optional, Union, Set, Any

from .errors import (
    WindowLifecycleError,
    InvalidRegionRatioError,
    InvalidActionError,
)
from .frame import FrameDescription, DisplayFrame, CustomFrame, TitlebarFrame
from .region import RegionLayout, Region, validate_ratios
from .element import ElementName, GLOBAL_ELEMENT_REGISTRY
from .layout import LayoutResolver, resolve_unit, resolve_size_pair
from .hittest import HitTestResolver, HitTestResult
from .events import (
    WindowEvent,
    WindowEventType,
    WindowEventDispatcher,
    GLOBAL_EVENT_DISPATCHER,
)


# Supported window actions for shapes
SUPPORTED_ACTIONS = {"close", "minimize", "maximize", "restore"}


class Window:
    """Represents a single Draw3 window backed by an SDL2 window.

    State properties (``is_open``, ``is_visible``, ``is_minimized``,
    ``is_maximized``, ``size``, ``position``) reflect the actual SDL
    window state. Maximize/restore actions update state consistently.
    """

    def __init__(
        self,
        name: str,
        frame: FrameDescription,
    ) -> None:
        self.name: str = name
        self.frame: FrameDescription = frame

        # Window state
        self._is_open: bool = frame.visible
        self._is_visible: bool = frame.visible
        self._is_minimized: bool = False
        self._is_maximized: bool = False
        self._size: Tuple[int, int] = frame.size
        self._position: Tuple[int, int] = (0, 0)  # SDL default

        # Region layout (custom/titlebar frames only)
        self._region_layout: Optional[RegionLayout] = None
        self._layout_resolver: LayoutResolver = LayoutResolver()
        self._hit_test_resolver: Optional[HitTestResolver] = None

        # Element membership for this window
        self._elements: List[str] = []
        self._drag_regions: Optional[Union[str, List[str]]] = None
        self._resize_border: int = 0

        # Interactive elements (have action or callback) — excluded from drag
        self._interactive_elements: Set[str] = set()

        # Build from frame
        self._init_from_frame()

    def _init_from_frame(self) -> None:
        """Initialises internal structures from the frame description."""
        frame = self.frame

        if isinstance(frame, CustomFrame):
            # Set up ratio-based regions
            if frame.ratio:
                self._region_layout = RegionLayout(
                    ratio=frame.ratio,
                    window_size=(float(self._size[0]), float(self._size[1])),
                )
                self._layout_resolver.set_region_layout(self._region_layout)

            self._elements = list(frame.elements)
            self._drag_regions = frame.drag_region
            self._resize_border = frame.resize_border

            # Build hit-test resolver
            self._hit_test_resolver = HitTestResolver(
                window_size=self._size,
                region_layout=self._region_layout,
                drag_regions=self._drag_regions,
                resize_border=self._resize_border,
                interactive_exclusions=self._interactive_elements,
            )

        elif isinstance(frame, DisplayFrame):
            # Normal windows: no custom regions, elements, or hit-testing
            pass

    # ── Properties ──

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @property
    def is_minimized(self) -> bool:
        return self._is_minimized

    @property
    def is_maximized(self) -> bool:
        return self._is_maximized

    @property
    def size(self) -> Tuple[int, int]:
        return self._size

    @property
    def position(self) -> Tuple[int, int]:
        return self._position

    # ── Region access ──

    def region(self, name: str) -> Optional[Region]:
        """Returns a Region object by name, or None if not found."""
        if self._region_layout:
            return self._region_layout.get(name)
        return None

    @property
    def regions(self) -> Dict[str, Region]:
        """Returns all ratio-defined regions."""
        if self._region_layout:
            return self._region_layout.regions
        return {}

    # ── Element access ──

    def element(self, name: str) -> Optional[ElementName]:
        """Returns the ElementName if it belongs to this window, else None."""
        if name in self._elements:
            if GLOBAL_ELEMENT_REGISTRY.is_declared(name):
                return GLOBAL_ELEMENT_REGISTRY.declare(name)
            return ElementName(name)
        return None

    @property
    def elements(self) -> List[str]:
        return list(self._elements)

    def has_element(self, name: str) -> bool:
        return name in self._elements

    # ── Interactive element tracking ──

    def mark_interactive(self, element_name: str) -> None:
        """Marks an element as interactive (has action or callback).
        Interactive elements are excluded from drag regions."""
        self._interactive_elements.add(element_name)
        if self._hit_test_resolver:
            self._hit_test_resolver._interactive_exclusions = self._interactive_elements

    # ── Lifecycle ──

    def close(self) -> None:
        """Closes the SDL window but keeps the definition for reopening."""
        self._is_open = False
        self._is_visible = False
        GLOBAL_EVENT_DISPATCHER.dispatch(
            WindowEvent(WindowEventType.CLOSE, self.name)
        )

    def open(self) -> None:
        """Reopens a closed window from its stored definition."""
        self._is_open = True
        self._is_visible = self.frame.visible
        GLOBAL_EVENT_DISPATCHER.dispatch(
            WindowEvent(WindowEventType.SHOWN, self.name)
        )

    def minimize(self) -> None:
        self._is_minimized = True
        self._is_maximized = False
        GLOBAL_EVENT_DISPATCHER.dispatch(
            WindowEvent(WindowEventType.MINIMIZE, self.name)
        )

    def maximize(self) -> None:
        self._is_maximized = True
        self._is_minimized = False
        GLOBAL_EVENT_DISPATCHER.dispatch(
            WindowEvent(WindowEventType.MAXIMIZE, self.name)
        )

    def restore(self) -> None:
        self._is_minimized = False
        self._is_maximized = False
        GLOBAL_EVENT_DISPATCHER.dispatch(
            WindowEvent(WindowEventType.RESTORE, self.name)
        )

    # ── Resize handling ──

    def _handle_resize(self, new_size: Tuple[int, int]) -> None:
        """Updates size, recalculates regions/layout, and dispatches event."""
        self._size = new_size
        if self._region_layout:
            self._region_layout.recalculate(
                (float(new_size[0]), float(new_size[1]))
            )
        if self._hit_test_resolver:
            self._hit_test_resolver.update_window_size(new_size)
        GLOBAL_EVENT_DISPATCHER.dispatch(
            WindowEvent(
                WindowEventType.RESIZE,
                self.name,
                data={"size": new_size},
            )
        )

    # ── Hit testing ──

    def hit_test(self, px: float, py: float) -> HitTestResult:
        """Classifies a point for the SDL hit-test callback."""
        if self._hit_test_resolver:
            return self._hit_test_resolver.classify(px, py)
        return HitTestResult.NORMAL

    # ── Window actions (from shape action= parameter) ──

    def execute_action(self, action: str) -> None:
        """Executes a window action triggered by a shape click."""
        action_lower = action.lower()
        if action_lower == "close":
            self.close()
        elif action_lower == "minimize":
            self.minimize()
        elif action_lower == "maximize":
            if self._is_maximized:
                self.restore()
            else:
                self.maximize()
        elif action_lower == "restore":
            self.restore()
        else:
            raise InvalidActionError(
                f"Unknown window action '{action}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_ACTIONS))}"
            )

    # ── Validation and warnings ──

    def validate(self) -> List[str]:
        """Performs lazy validation at window open/render time.

        Returns a list of warning messages for unresolved references.
        Does not raise errors — these are warnings per spec section 4.2.
        """
        warns: List[str] = []

        # Check that declared elements are registered
        for elem_name in self._elements:
            if not GLOBAL_ELEMENT_REGISTRY.is_declared(elem_name):
                warns.append(
                    f"Window '{self.name}' lists element '{elem_name}' "
                    f"which was never declared with window.element()."
                )

        return warns

    # ── Serialisation ──

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "frame": self.frame.to_dict(),
            "is_open": self._is_open,
            "is_visible": self._is_visible,
            "is_minimized": self._is_minimized,
            "is_maximized": self._is_maximized,
            "size": self._size,
            "position": self._position,
            "elements": list(self._elements),
            "regions": self._region_layout.to_dict() if self._region_layout else {},
        }
