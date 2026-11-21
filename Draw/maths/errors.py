"""Draw Maths Module — Exceptions and Error Hierarchy.

Defines all custom exceptions for the universal unit conversion system.
All exceptions inherit from DrawMathsError for unified catching.
"""


class DrawMathsError(Exception):
    """Base exception for all Draw3 Maths module errors."""
    pass


class InvalidUnitError(DrawMathsError, ValueError):
    """Raised when an unrecognised unit suffix is encountered."""
    pass


class InvalidUnitValueError(DrawMathsError, ValueError):
    """Raised when a unit value is NaN, Infinite, or otherwise unparseable."""
    pass


class MissingReferenceError(DrawMathsError, ValueError):
    """Raised when a relative unit (%, ratio) is used without a reference context."""
    pass


class InvalidRatioError(DrawMathsError, ValueError):
    """Raised when ratio values are outside valid range or do not sum correctly."""
    pass
