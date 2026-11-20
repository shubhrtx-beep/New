"""Draw Shape API — Exceptions and Error Hierarchy.

Defines all custom exceptions specified in conditions_and_errors.md.
All exceptions inherit from DrawShapeError for unified catching.
"""

class DrawShapeError(Exception):
    """Base exception for all Draw3 Shape module errors."""
    pass


class ClosedShapeTopologyError(DrawShapeError):
    """Raised when open-path operations (side_length, side_angle) are illegally applied to closed polygons."""
    pass


class OverConstrainedTopologyError(DrawShapeError):
    """Raised when conflicting constraints (e.g. both side_length and side_angle) are applied."""
    pass


class ConflictingGeometryDefinitionError(DrawShapeError):
    """Raised when multiple mutually exclusive geometry modes (type, vertices, coordinates) are provided."""
    pass


class MissingGeometryDefinitionError(DrawShapeError):
    """Raised when no geometry definition mode is provided."""
    pass


class UndefinedGeometryBoundsError(DrawShapeError):
    """Raised when vertices=N is specified without non-zero size."""
    pass


class SideIndexOutOfBoundsError(DrawShapeError, IndexError):
    """Raised when side or vertex index is out of 0-based range."""
    pass


class DuplicateShapeNameError(DrawShapeError, KeyError):
    """Raised when attempting to register a shape with an existing name."""
    pass


class ShapeNotFoundError(DrawShapeError, KeyError):
    """Raised when querying, updating, or deleting a non-existent shape."""
    pass


class DegenerateGeometryError(DrawShapeError):
    """Raised when geometry collapses into zero area, collinear points on closed shapes, or zero edges."""
    pass


class InvalidCoordinateValueError(DrawShapeError, ValueError):
    """Raised when coordinates contain NaN, Inf, or invalid numeric representations."""
    pass


class InvalidPolygonVertexCountError(DrawShapeError, ValueError):
    """Raised when a closed polygon has fewer than 3 vertices."""
    pass


class InvalidLineVertexCountError(DrawShapeError, ValueError):
    """Raised when an open path/line has fewer than 2 vertices."""
    pass


class UnknownShapeTypeError(DrawShapeError, ValueError):
    """Raised when an unknown primitive type string is passed."""
    pass


class InvalidWarpGridError(DrawShapeError, ValueError):
    """Raised when warp grid is not a uniform rectangular matrix of at least 2x2 control points."""
    pass


class HoleOutsideBoundaryError(DrawShapeError, ValueError):
    """Raised when an exclude cutout hole lies outside or intersects the outer polygon boundary."""
    pass
