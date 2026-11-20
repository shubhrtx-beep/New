"""Draw Window API — SDL2 Window Events.

Handles SDL2 events for window resize, close, minimize, maximize, focus,
and maps them to Draw3 internal state updates and callbacks.

Window events are processed separately from shape drawing and normal
renderer logic. Resize events trigger region/layout recalculation and
redraw.
"""

from typing import Dict, List, Callable, Optional, Any, Tuple
from enum import Enum


class WindowEventType(Enum):
    """Types of window lifecycle events."""
    RESIZE = "resize"
    CLOSE = "close"
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    RESTORE = "restore"
    FOCUS_GAINED = "focus_gained"
    FOCUS_LOST = "focus_lost"
    MOVED = "moved"
    SHOWN = "shown"
    HIDDEN = "hidden"
    EXPOSED = "exposed"


class WindowEvent:
    """Represents a single window event with associated data."""

    def __init__(
        self,
        event_type: WindowEventType,
        window_name: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.event_type = event_type
        self.window_name = window_name
        self.data: Dict[str, Any] = data or {}

    def __repr__(self) -> str:
        return f"WindowEvent({self.event_type.value}, window='{self.window_name}', data={self.data})"


class WindowEventDispatcher:
    """Routes SDL2 window events to registered handlers and internal
    state update callbacks.

    Handlers are registered per event type, per window name. A handler
    registered with ``window_name=None`` acts as a global handler for
    all windows.
    """

    def __init__(self) -> None:
        # (event_type, window_name or None) -> list of callbacks
        self._handlers: Dict[Tuple[WindowEventType, Optional[str]], List[Callable[[WindowEvent], None]]] = {}

    def on(
        self,
        event_type: WindowEventType,
        handler: Callable[[WindowEvent], None],
        window_name: Optional[str] = None,
    ) -> None:
        """Registers a handler for a specific event type and optional window."""
        key = (event_type, window_name)
        if key not in self._handlers:
            self._handlers[key] = []
        self._handlers[key].append(handler)

    def off(
        self,
        event_type: WindowEventType,
        handler: Callable[[WindowEvent], None],
        window_name: Optional[str] = None,
    ) -> None:
        """Removes a specific handler."""
        key = (event_type, window_name)
        if key in self._handlers:
            try:
                self._handlers[key].remove(handler)
            except ValueError:
                pass

    def dispatch(self, event: WindowEvent) -> None:
        """Dispatches a window event to all matching handlers.

        First dispatches to window-specific handlers, then global handlers.
        """
        # Window-specific handlers
        specific_key = (event.event_type, event.window_name)
        for handler in self._handlers.get(specific_key, []):
            handler(event)

        # Global handlers (window_name=None)
        global_key = (event.event_type, None)
        for handler in self._handlers.get(global_key, []):
            handler(event)

    def clear(self, window_name: Optional[str] = None) -> None:
        """Removes all handlers, or all handlers for a specific window."""
        if window_name is None:
            self._handlers.clear()
        else:
            keys_to_remove = [
                k for k in self._handlers if k[1] == window_name
            ]
            for k in keys_to_remove:
                del self._handlers[k]


# Global Singleton Event Dispatcher
GLOBAL_EVENT_DISPATCHER = WindowEventDispatcher()
