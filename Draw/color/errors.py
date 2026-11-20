"""Draw Color API — Custom Exception Hierarchy.

All exceptions raised by the color subsystem inherit from DrawColorError.
"""


class DrawColorError(Exception):
    """Base exception for all Draw Color API errors."""


class InvalidColorValueError(DrawColorError):
    """Raised when a color channel, opacity, or coordinate value is out of valid bounds."""


class UnknownColorNameError(DrawColorError):
    """Raised when a named color or referenced token cannot be resolved."""


class InvalidHexColorError(DrawColorError):
    """Raised when a hexadecimal color string contains invalid formatting or characters."""


class ColorTokenCycleError(DrawColorError):
    """Raised when design tokens or themes form a circular dependency."""


class InvalidMotionError(DrawColorError):
    """Raised when an animation driver or motion parameter is invalid or unsupported."""


class DuplicateColorNameError(DrawColorError):
    """Raised when registering a color with a name that is already registered."""


class ColorNotFoundError(DrawColorError):
    """Raised when querying a color name that is not registered."""
