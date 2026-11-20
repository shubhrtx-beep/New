"""Draw Window API — Window Registry.

Manages registered Window instances: creation, lookup, lifecycle
(open/close/remove), focus, and enumeration. Duplicate name detection
follows the same pattern as the shape SceneRegistry.
"""

from typing import Dict, Optional, List, Any

from .errors import DuplicateWindowNameError, WindowNotFoundError
from .frame import FrameDescription
from .window import Window


class WindowRegistry:
    """Authoritative registry of all created Draw3 windows."""

    def __init__(self) -> None:
        self._windows: Dict[str, Window] = {}

    def create(self, name: str, frame: FrameDescription) -> Window:
        """Builds, registers, and returns a new Window.

        Raises ``DuplicateWindowNameError`` if the name is already in use.
        """
        if name in self._windows:
            raise DuplicateWindowNameError(
                f"Window with name '{name}' already exists. "
                f"Use window.remove('{name}') first or choose a different name."
            )
        win = Window(name=name, frame=frame)
        self._windows[name] = win
        return win

    def get(self, name: str) -> Window:
        """Returns the Window object for the given name.

        Raises ``WindowNotFoundError`` if unknown.
        """
        if name not in self._windows:
            raise WindowNotFoundError(
                f"No registered window found with name '{name}'."
            )
        return self._windows[name]

    def exists(self, name: str) -> bool:
        return name in self._windows

    def close(self, name: str) -> None:
        """Destroys the SDL window but keeps its definition for reopening."""
        win = self.get(name)
        win.close()

    def open(self, name: str) -> None:
        """Recreates the SDL window from the stored definition."""
        win = self.get(name)
        win.open()

    def remove(self, name: str) -> None:
        """Closes the window and deletes it from the registry.

        The name becomes available again for a new ``create()`` call.
        """
        if name in self._windows:
            self._windows[name].close()
            del self._windows[name]
        else:
            raise WindowNotFoundError(
                f"No registered window found with name '{name}'."
            )

    def focus(self, name: str) -> None:
        """Gives the named window input focus."""
        win = self.get(name)
        # In a real SDL2 backend this would call SDL_RaiseWindow
        # For now, dispatch a focus event
        from .events import WindowEvent, WindowEventType, GLOBAL_EVENT_DISPATCHER
        GLOBAL_EVENT_DISPATCHER.dispatch(
            WindowEvent(WindowEventType.FOCUS_GAINED, name)
        )

    def get_all(self) -> Dict[str, Window]:
        """Returns a snapshot of all registered windows."""
        return dict(self._windows)

    def clear(self) -> None:
        """Closes and removes all windows (useful for testing)."""
        for name in list(self._windows.keys()):
            self._windows[name].close()
        self._windows.clear()

    def list_names(self) -> List[str]:
        """Returns a list of all registered window names."""
        return list(self._windows.keys())


# Global Singleton Window Registry
GLOBAL_WINDOW_REGISTRY = WindowRegistry()
