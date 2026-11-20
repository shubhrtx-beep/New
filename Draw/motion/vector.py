"""Draw Motion API — 2D Vector Mathematics.

Provides Vector2D and fundamental vector algebra for both Physical Motion
and Mathematical Motion without external dependencies.
"""

import math
from typing import Any, Dict, Iterator, Sequence, Tuple, Union

PointLike = Union["Vector2D", Sequence[Union[int, float]], Tuple[Union[int, float], Union[int, float]]]


class Vector2D:
    """Immutable/mutable 2D vector representation for physics and procedural math.

    Attributes:
        x: Horizontal coordinate / component.
        y: Vertical coordinate / component.
    """

    __slots__ = ("x", "y")

    def __init__(self, x: Union[int, float] = 0.0, y: Union[int, float] = 0.0) -> None:
        self.x: float = float(x)
        self.y: float = float(y)

    @classmethod
    def from_value(cls, val: Any) -> "Vector2D":
        """Converts tuple, list, scalar or Vector2D into a Vector2D."""
        if isinstance(val, Vector2D):
            return Vector2D(val.x, val.y)
        if isinstance(val, (list, tuple)):
            if len(val) >= 2:
                return Vector2D(val[0], val[1])
            elif len(val) == 1:
                return Vector2D(val[0], val[0])
            return Vector2D(0.0, 0.0)
        if isinstance(val, (int, float)):
            return Vector2D(val, val)
        return Vector2D(0.0, 0.0)

    # ── Arithmetic Operations ───────────────────────────────────────────

    def __add__(self, other: Any) -> "Vector2D":
        if isinstance(other, Vector2D):
            return Vector2D(self.x + other.x, self.y + other.y)
        if isinstance(other, (list, tuple)) and len(other) >= 2:
            return Vector2D(self.x + float(other[0]), self.y + float(other[1]))
        if isinstance(other, (int, float)):
            return Vector2D(self.x + float(other), self.y + float(other))
        return NotImplemented

    def __radd__(self, other: Any) -> "Vector2D":
        return self.__add__(other)

    def __sub__(self, other: Any) -> "Vector2D":
        if isinstance(other, Vector2D):
            return Vector2D(self.x - other.x, self.y - other.y)
        if isinstance(other, (list, tuple)) and len(other) >= 2:
            return Vector2D(self.x - float(other[0]), self.y - float(other[1]))
        if isinstance(other, (int, float)):
            return Vector2D(self.x - float(other), self.y - float(other))
        return NotImplemented

    def __rsub__(self, other: Any) -> "Vector2D":
        if isinstance(other, (list, tuple)) and len(other) >= 2:
            return Vector2D(float(other[0]) - self.x, float(other[1]) - self.y)
        if isinstance(other, (int, float)):
            return Vector2D(float(other) - self.x, float(other) - self.y)
        return NotImplemented

    def __mul__(self, other: Any) -> "Vector2D":
        if isinstance(other, (int, float)):
            return Vector2D(self.x * float(other), self.y * float(other))
        if isinstance(other, Vector2D):
            return Vector2D(self.x * other.x, self.y * other.y)
        if isinstance(other, (list, tuple)) and len(other) >= 2:
            return Vector2D(self.x * float(other[0]), self.y * float(other[1]))
        return NotImplemented

    def __rmul__(self, other: Any) -> "Vector2D":
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> "Vector2D":
        if isinstance(other, (int, float)):
            if abs(other) < 1e-12:
                return Vector2D(0.0, 0.0)
            inv = 1.0 / float(other)
            return Vector2D(self.x * inv, self.y * inv)
        if isinstance(other, Vector2D):
            x = self.x / other.x if abs(other.x) >= 1e-12 else 0.0
            y = self.y / other.y if abs(other.y) >= 1e-12 else 0.0
            return Vector2D(x, y)
        return NotImplemented

    def __neg__(self) -> "Vector2D":
        return Vector2D(-self.x, -self.y)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Vector2D):
            return abs(self.x - other.x) < 1e-6 and abs(self.y - other.y) < 1e-6
        if isinstance(other, (list, tuple)) and len(other) >= 2:
            return abs(self.x - float(other[0])) < 1e-6 and abs(self.y - float(other[1])) < 1e-6
        return False

    def __getitem__(self, idx: int) -> float:
        if idx == 0:
            return self.x
        elif idx == 1:
            return self.y
        raise IndexError(f"Vector2D index out of range: {idx}")

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __len__(self) -> int:
        return 2

    # ── Vector Calculus / Algebra ───────────────────────────────────────

    def length(self) -> float:
        """Computes Euclidean magnitude / length."""
        return math.hypot(self.x, self.y)

    def length_sq(self) -> float:
        """Computes squared magnitude."""
        return self.x * self.x + self.y * self.y

    def magnitude(self) -> float:
        """Alias for length()."""
        return self.length()

    def normalize(self) -> "Vector2D":
        """Returns unit vector in the same direction, or zero vector if length is 0."""
        l = self.length()
        if l < 1e-12:
            return Vector2D(0.0, 0.0)
        inv = 1.0 / l
        return Vector2D(self.x * inv, self.y * inv)

    def dot(self, other: PointLike) -> float:
        """Calculates scalar dot product."""
        v = Vector2D.from_value(other)
        return self.x * v.x + self.y * v.y

    def cross(self, other: PointLike) -> float:
        """Calculates 2D cross product scalar (z-component): x1*y2 - y1*x2."""
        v = Vector2D.from_value(other)
        return self.x * v.y - self.y * v.x

    def distance_to(self, other: PointLike) -> float:
        """Calculates Euclidean distance to another point."""
        v = Vector2D.from_value(other)
        return math.hypot(self.x - v.x, self.y - v.y)

    def distance_sq_to(self, other: PointLike) -> float:
        """Calculates squared distance to another point."""
        v = Vector2D.from_value(other)
        dx = self.x - v.x
        dy = self.y - v.y
        return dx * dx + dy * dy

    def angle(self) -> float:
        """Returns counter-clockwise polar angle in radians (-pi to +pi)."""
        return math.atan2(self.y, self.x)

    def angle_to(self, other: PointLike) -> float:
        """Returns angle from this vector to other vector in radians."""
        v = Vector2D.from_value(other)
        dot = self.dot(v)
        det = self.cross(v)
        return math.atan2(det, dot)

    def rotate(self, angle_rad: float) -> "Vector2D":
        """Rotates vector counter-clockwise by angle in radians."""
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return Vector2D(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a,
        )

    def rotate_deg(self, angle_deg: float) -> "Vector2D":
        """Rotates vector by angle in degrees."""
        return self.rotate(math.radians(angle_deg))

    def lerp(self, other: PointLike, t: float) -> "Vector2D":
        """Linear interpolation between self and other by factor t."""
        v = Vector2D.from_value(other)
        return Vector2D(
            self.x + (v.x - self.x) * t,
            self.y + (v.y - self.y) * t,
        )

    def reflect(self, normal: PointLike) -> "Vector2D":
        """Reflects this vector across a surface with the given unit normal."""
        n = Vector2D.from_value(normal).normalize()
        d = self.dot(n)
        return Vector2D(self.x - 2.0 * d * n.x, self.y - 2.0 * d * n.y)

    def project(self, normal: PointLike) -> "Vector2D":
        """Projects this vector onto another vector."""
        n = Vector2D.from_value(normal)
        l_sq = n.length_sq()
        if l_sq < 1e-12:
            return Vector2D(0.0, 0.0)
        scale = self.dot(n) / l_sq
        return n * scale

    def perpendicular(self) -> "Vector2D":
        """Returns perpendicular vector (-y, x)."""
        return Vector2D(-self.y, self.x)

    def to_tuple(self) -> Tuple[float, float]:
        return (round(self.x, 6), round(self.y, 6))

    def to_list(self) -> Sequence[float]:
        return [round(self.x, 6), round(self.y, 6)]

    def __repr__(self) -> str:
        return f"Vector2D({round(self.x, 4)}, {round(self.y, 4)})"


def vec2(x: Union[int, float] = 0.0, y: Union[int, float] = 0.0) -> Vector2D:
    """Convenience constructor for Vector2D."""
    return Vector2D(x, y)
