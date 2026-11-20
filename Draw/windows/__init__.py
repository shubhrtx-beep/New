"""Draw Window Subsystem Package.

Exposes window creation, lifecycle, element declaration, frame factories,
and the window registry following the same architectural patterns as the
Draw Shape subsystem.

Usage::

    from Draw import shapes, color, motion, window

    window.create(
        name="main",
        frame=window.custom(
            size=(1400, 850),
            ratio={"top_bar": 0.05, "main_display": 0.95},
            elements=["min", "max", "close", "card"],
            drag_region="top_bar",
            resize_border=6,
        ),
    )

    shapes.shape(
        name=window.element("min"),
        region="top_bar",
        type="rectangle",
        size=(46, 30),
        action="minimize",
    )
"""

from typing import Dict, List, Tuple, Optional, Union, Any

from .errors import *
from .element import (
    ElementName,
    ElementRegistry,
    GLOBAL_ELEMENT_REGISTRY,
)
from .region import (
    Region,
    RegionLayout,
    validate_ratios,
)
from .layout import (
    LayoutResolver,
    resolve_anchor_position,
    resolve_unit,
    resolve_size_pair,
    SUPPORTED_ANCHORS,
)
from .frame import (
    FrameDescription,
    DisplayFrame,
    CustomFrame,
    TitlebarFrame,
    display,
    custom,
    titlebar,
)
from .window import (
    Window,
    SUPPORTED_ACTIONS,
)
from .hittest import (
    HitTestResolver,
    HitTestResult,
)
from .events import (
    WindowEvent,
    WindowEventType,
    WindowEventDispatcher,
    GLOBAL_EVENT_DISPATCHER,
)
from .registry import (
    WindowRegistry,
    GLOBAL_WINDOW_REGISTRY,
)


# ── Public API Functions ──


def create(name: str, frame: FrameDescription) -> Window:
    """Creates, registers, and returns a new Window.

    Raises ``DuplicateWindowNameError`` if the name already exists.
    """
    return GLOBAL_WINDOW_REGISTRY.create(name, frame)


def get(name: str) -> Window:
    """Returns the Window object for the given name.

    Raises ``WindowNotFoundError`` if unknown.
    """
    return GLOBAL_WINDOW_REGISTRY.get(name)


def close(name: str) -> None:
    """Closes the SDL window but keeps its definition for reopening."""
    GLOBAL_WINDOW_REGISTRY.close(name)


def open(name: str) -> None:
    """Reopens a closed window from its stored definition."""
    GLOBAL_WINDOW_REGISTRY.open(name)


def remove(name: str) -> None:
    """Closes the window and deletes it from the registry."""
    GLOBAL_WINDOW_REGISTRY.remove(name)


def element(name: str) -> ElementName:
    """Declares an element name and returns the ``ElementName`` tag.

    Idempotent — calling with an already-declared name returns the
    same tag without error.
    """
    return GLOBAL_ELEMENT_REGISTRY.declare(name)


def focus(name: str) -> None:
    """Gives the named window input focus."""
    GLOBAL_WINDOW_REGISTRY.focus(name)


def get_all() -> Dict[str, Window]:
    """Returns all registered windows."""
    return GLOBAL_WINDOW_REGISTRY.get_all()


__all__ = [
    # Public API functions
    "create",
    "get",
    "close",
    "open",
    "remove",
    "element",
    "focus",
    "get_all",
    # Frame factories
    "display",
    "custom",
    "titlebar",
    # Core types
    "Window",
    "FrameDescription",
    "DisplayFrame",
    "CustomFrame",
    "TitlebarFrame",
    "ElementName",
    "Region",
    "RegionLayout",
    "LayoutResolver",
    "HitTestResolver",
    "HitTestResult",
    "WindowEvent",
    "WindowEventType",
    "WindowEventDispatcher",
    # Registries
    "WindowRegistry",
    "GLOBAL_WINDOW_REGISTRY",
    "ElementRegistry",
    "GLOBAL_ELEMENT_REGISTRY",
    "GLOBAL_EVENT_DISPATCHER",
    # Constants
    "SUPPORTED_ACTIONS",
    "SUPPORTED_ANCHORS",
    # Helpers
    "validate_ratios",
    "resolve_anchor_position",
    "resolve_unit",
    "resolve_size_pair",
    # Errors
    "DrawWindowError",
    "DuplicateWindowNameError",
    "WindowNotFoundError",
    "InvalidRegionRatioError",
    "DuplicateElementNameError",
    "InvalidFrameConfigError",
    "WindowLifecycleError",
    "InvalidAnchorError",
    "InvalidActionError",
]
