"""Draw Motion API — Exceptions and Error Hierarchy.

Defines all custom exceptions for the motion and timeline subsystem.
All exceptions inherit from DrawMotionError for unified catching.
"""


class DrawMotionError(Exception):
    """Base exception for all Draw3 Motion module errors."""
    pass


class InvalidEasingError(DrawMotionError, ValueError):
    """Raised when an unsupported easing/graph name is provided."""
    pass


class InvalidChannelError(DrawMotionError, ValueError):
    """Raised when a motion channel name is not recognized or not supported for the target shape."""
    pass


class InvalidChannelFormatError(DrawMotionError, ValueError):
    """Raised when a channel value list has an invalid structure (wrong length, bad types)."""
    pass


class InvalidDurationError(DrawMotionError, ValueError):
    """Raised when a duration value is negative or otherwise invalid."""
    pass


class DuplicateMotionNameError(DrawMotionError, KeyError):
    """Raised when registering a motion with a name that already exists."""
    pass


class MotionNotFoundError(DrawMotionError, KeyError):
    """Raised when querying or referencing a motion name that is not registered."""
    pass


class DuplicateTimelineNameError(DrawMotionError, KeyError):
    """Raised when registering a timeline with a name that already exists."""
    pass


class TimelineNotFoundError(DrawMotionError, KeyError):
    """Raised when querying or referencing a timeline name that is not registered."""
    pass


class TimelineSectionNotFoundError(DrawMotionError, KeyError):
    """Raised when a channel references a named timeline section that does not exist."""
    pass


class TimelineSectionCountMismatchError(DrawMotionError, ValueError):
    """Raised when the time and names lists in a timeline definition have different lengths."""
    pass


class InvalidTimelineError(DrawMotionError, ValueError):
    """Raised when a timeline definition is structurally invalid."""
    pass


class InvalidPlaybackError(DrawMotionError, ValueError):
    """Raised when an invalid playback mode, directive, or parameter is provided."""
    pass

