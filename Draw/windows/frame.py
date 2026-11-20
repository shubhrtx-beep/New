"""Draw Window API — Frame Descriptions.

Factory functions that describe how a window should be configured:

* ``display(...)`` — normal SDL2 window with native OS title bar.
* ``custom(...)``  — borderless SDL2 window, fully developer-controlled.
* ``titlebar(...)`` — convenience preset built on top of ``custom()``.

A frame is a pure data description; it does not create an SDL2 window
itself.  ``window.create(name, frame)`` consumes a frame to build the
actual window.
"""

from typing import Dict, List, Tuple, Optional, Union, Any

from .errors import InvalidFrameConfigError, InvalidRegionRatioError
from .region import validate_ratios
from .element import ElementName, GLOBAL_ELEMENT_REGISTRY


class FrameDescription:
    """Base class for window frame descriptions.

    Not instantiated directly — use ``display()``, ``custom()``,
    or ``titlebar()``.
    """

    def __init__(
        self,
        *,
        frame_type: str,
        size: Tuple[int, int],
        min_size: Optional[Tuple[int, int]] = None,
        max_size: Optional[Tuple[int, int]] = None,
        visible: bool = True,
        resizable: bool = True,
    ) -> None:
        self.frame_type: str = frame_type
        self.size: Tuple[int, int] = size
        self.min_size: Optional[Tuple[int, int]] = min_size
        self.max_size: Optional[Tuple[int, int]] = max_size
        self.visible: bool = visible
        self.resizable: bool = resizable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_type": self.frame_type,
            "size": self.size,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "visible": self.visible,
            "resizable": self.resizable,
        }


class DisplayFrame(FrameDescription):
    """Normal SDL2 window with native OS title bar and controls."""

    def __init__(
        self,
        *,
        title: str = "Draw3",
        size: Tuple[int, int] = (800, 600),
        min_size: Optional[Tuple[int, int]] = None,
        max_size: Optional[Tuple[int, int]] = None,
        resizable: bool = True,
        visible: bool = True,
        icon: Optional[str] = None,
    ) -> None:
        super().__init__(
            frame_type="display",
            size=size,
            min_size=min_size,
            max_size=max_size,
            visible=visible,
            resizable=resizable,
        )
        self.title: str = title
        self.icon: Optional[str] = icon

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["title"] = self.title
        d["icon"] = self.icon
        return d


class CustomFrame(FrameDescription):
    """Borderless SDL2 window (``SDL_WINDOW_BORDERLESS``).

    The developer provides ratio-based regions, element membership,
    drag/resize settings, and draws any title bar, menus, or controls
    using Draw shapes.
    """

    def __init__(
        self,
        *,
        size: Tuple[int, int] = (800, 600),
        ratio: Optional[Dict[str, float]] = None,
        elements: Optional[List[str]] = None,
        drag_region: Optional[Union[str, List[str]]] = None,
        resize_border: int = 0,
        min_size: Optional[Tuple[int, int]] = None,
        max_size: Optional[Tuple[int, int]] = None,
        visible: bool = True,
    ) -> None:
        super().__init__(
            frame_type="custom",
            size=size,
            min_size=min_size,
            max_size=max_size,
            visible=visible,
            resizable=resize_border > 0,
        )

        # Validate ratios eagerly (they describe the frame, not a live
        # window, so early validation is appropriate)
        if ratio:
            validate_ratios(ratio)

        self.ratio: Dict[str, float] = dict(ratio or {})
        self.elements: List[str] = list(elements or [])
        self.drag_region: Optional[Union[str, List[str]]] = drag_region
        self.resize_border: int = max(0, int(resize_border))

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["ratio"] = self.ratio
        d["elements"] = self.elements
        d["drag_region"] = self.drag_region
        d["resize_border"] = self.resize_border
        return d


class TitlebarFrame(CustomFrame):
    """Convenience preset frame built on top of ``CustomFrame``.

    Automatically generates and registers elements for menus, search,
    and window controls (minimize, maximize, close).
    """

    # Supported control actions
    SUPPORTED_CONTROLS = {"minimize", "maximize", "close"}

    def __init__(
        self,
        *,
        size: Tuple[int, int] = (1400, 850),
        ratio: Optional[Dict[str, float]] = None,
        menus: Optional[List[str]] = None,
        search: bool = False,
        controls: Optional[List[str]] = None,
        drag_region: Optional[Union[str, List[str]]] = None,
        resize_border: int = 6,
        min_size: Optional[Tuple[int, int]] = None,
        max_size: Optional[Tuple[int, int]] = None,
        visible: bool = True,
    ) -> None:
        # Build generated element names
        generated_elements: List[str] = ["titlebar"]
        self.menu_elements: List[str] = []
        self.search_enabled: bool = search
        self.control_elements: List[str] = []

        if menus:
            for menu_label in menus:
                elem_name = f"menu_{menu_label.lower().replace(' ', '_')}"
                self.menu_elements.append(elem_name)
                generated_elements.append(elem_name)

        if search:
            generated_elements.append("search")

        if controls:
            for ctrl in controls:
                ctrl_lower = ctrl.lower()
                if ctrl_lower not in self.SUPPORTED_CONTROLS:
                    raise InvalidFrameConfigError(
                        f"Unsupported titlebar control '{ctrl}'. "
                        f"Supported: {', '.join(sorted(self.SUPPORTED_CONTROLS))}"
                    )
                self.control_elements.append(ctrl_lower)
                generated_elements.append(ctrl_lower)

        # Declare all generated elements in the global element registry
        for elem_name in generated_elements:
            GLOBAL_ELEMENT_REGISTRY.declare(elem_name)

        self.generated_elements: List[str] = generated_elements

        super().__init__(
            size=size,
            ratio=ratio,
            elements=generated_elements,
            drag_region=drag_region,
            resize_border=resize_border,
            min_size=min_size,
            max_size=max_size,
            visible=visible,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["menus"] = self.menu_elements
        d["search"] = self.search_enabled
        d["controls"] = self.control_elements
        d["generated_elements"] = self.generated_elements
        return d


# ── Public Frame Factory Functions ──


def display(
    title: str = "Draw3",
    size: Tuple[int, int] = (800, 600),
    min_size: Optional[Tuple[int, int]] = None,
    max_size: Optional[Tuple[int, int]] = None,
    resizable: bool = True,
    visible: bool = True,
    icon: Optional[str] = None,
) -> DisplayFrame:
    """Creates a normal SDL2 window frame with the native OS title bar."""
    return DisplayFrame(
        title=title,
        size=size,
        min_size=min_size,
        max_size=max_size,
        resizable=resizable,
        visible=visible,
        icon=icon,
    )


def custom(
    size: Tuple[int, int] = (800, 600),
    ratio: Optional[Dict[str, float]] = None,
    elements: Optional[List[str]] = None,
    drag_region: Optional[Union[str, List[str]]] = None,
    resize_border: int = 0,
    min_size: Optional[Tuple[int, int]] = None,
    max_size: Optional[Tuple[int, int]] = None,
    visible: bool = True,
) -> CustomFrame:
    """Creates a borderless SDL2 window frame (custom chrome)."""
    return CustomFrame(
        size=size,
        ratio=ratio,
        elements=elements,
        drag_region=drag_region,
        resize_border=resize_border,
        min_size=min_size,
        max_size=max_size,
        visible=visible,
    )


def titlebar(
    size: Tuple[int, int] = (1400, 850),
    ratio: Optional[Dict[str, float]] = None,
    menus: Optional[List[str]] = None,
    search: bool = False,
    controls: Optional[List[str]] = None,
    drag_region: Optional[Union[str, List[str]]] = None,
    resize_border: int = 6,
    min_size: Optional[Tuple[int, int]] = None,
    max_size: Optional[Tuple[int, int]] = None,
    visible: bool = True,
) -> TitlebarFrame:
    """Creates a convenience title-bar preset frame (borderless + generated elements)."""
    return TitlebarFrame(
        size=size,
        ratio=ratio,
        menus=menus,
        search=search,
        controls=controls,
        drag_region=drag_region,
        resize_border=resize_border,
        min_size=min_size,
        max_size=max_size,
        visible=visible,
    )
