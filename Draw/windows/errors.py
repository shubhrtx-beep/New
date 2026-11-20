"""Draw Window API — Exceptions and Error Hierarchy.

Defines all custom exceptions specified in the Window API specification.
All exceptions inherit from DrawWindowError for unified catching.
"""


class DrawWindowError(Exception):
    """Base exception for all Draw3 Window module errors."""
    pass


class DuplicateWindowNameError(DrawWindowError, KeyError):
    """Raised when window.create() uses a name already registered."""
    pass


class WindowNotFoundError(DrawWindowError, KeyError):
    """Raised when window.get/close/open/remove uses an unknown name."""
    pass


class InvalidRegionRatioError(DrawWindowError, ValueError):
    """Raised when ratio values are outside 0..1 or do not sum to 1 within tolerance."""
    pass


class DuplicateElementNameError(DrawWindowError, KeyError):
    """Raised when an element name conflicts in an unexpected way."""
    pass


class InvalidFrameConfigError(DrawWindowError, ValueError):
    """Raised when a frame factory receives invalid or incomplete arguments."""
    pass


class WindowLifecycleError(DrawWindowError, RuntimeError):
    """Raised when a window operation violates lifecycle rules (e.g. opening an already open window)."""
    pass


class InvalidAnchorError(DrawWindowError, ValueError):
    """Raised when an unrecognized anchor value is provided."""
    pass


class InvalidActionError(DrawWindowError, ValueError):
    """Raised when an unrecognized window action is provided."""
    pass
