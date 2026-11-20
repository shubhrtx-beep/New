"""Draw Motion Graph API — Exceptions and Error Hierarchy.

Defines all custom exceptions for the Draw.motion_graph subsystem.
All exceptions inherit from DrawMotionGraphError for unified catching.
"""


class DrawMotionGraphError(Exception):
    """Base exception for all Draw3 Motion Graph errors."""
    pass


class InvalidMotionGraphError(DrawMotionGraphError, ValueError):
    """Raised when a motion graph definition is structurally invalid."""
    pass


class DuplicateMotionGraphNameError(DrawMotionGraphError, KeyError):
    """Raised when registering a motion graph with a name that already exists."""
    pass


class MotionGraphNotFoundError(DrawMotionGraphError, KeyError):
    """Raised when referencing or querying a motion graph name that is not registered."""
    pass


class CircularGraphReferenceError(DrawMotionGraphError, ValueError):
    """Raised when a combined graph definition contains circular/cyclic references."""
    pass


class InvalidInterpolationModeError(DrawMotionGraphError, ValueError):
    """Raised when an unsupported interpolation mode is specified."""
    pass


class InvalidGraphPointsError(DrawMotionGraphError, ValueError):
    """Raised when a point-based graph has invalid, descending, or non-finite points."""
    pass


class InvalidGraphCombineError(DrawMotionGraphError, ValueError):
    """Raised when a combined graph definition has invalid entries, negative weights, or zero sum."""
    pass


class GraphDefinitionConflictError(DrawMotionGraphError, ValueError):
    """Raised when both 'points' and 'combine' are supplied, or neither is supplied."""
    pass
