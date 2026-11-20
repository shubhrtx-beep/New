"""Draw Shape API — 2D Geometric Transforms and Hierarchical Coordinate Systems.

Implements affine 2D transformations: scaling, rotation around local pivot (origin),
translation, and hierarchical parent-to-child coordinate frame inheritance.
"""

import math
from typing import Tuple, List, Sequence, Dict, Any

Point2D = Tuple[float, float]


class Transform2D:
    """Represents a 2D affine transform state for a Shape."""

    def __init__(
        self,
        position: Point2D = (0.0, 0.0),
        scale: Point2D = (1.0, 1.0),
        rotation: float = 0.0,
        origin: Point2D = (0.0, 0.0),
    ) -> None:
        self.position: Point2D = (float(position[0]), float(position[1]))
        self.scale: Point2D = (float(scale[0]), float(scale[1]))
        self.rotation: float = float(rotation)
        self.origin: Point2D = (float(origin[0]), float(origin[1]))

    def apply_to_point(self, pt: Point2D) -> Point2D:
        """Transforms a local vertex by scale, rotation around origin, and translation."""
        x, y = pt
        ox, oy = self.origin
        sx, sy = self.scale

        # 1. Scale relative to origin
        x = ox + (x - ox) * sx
        y = oy + (y - oy) * sy

        # 2. Rotate relative to origin (clockwise rotation in screen space)
        if abs(self.rotation) > 1e-6:
            rad = math.radians(self.rotation)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            dx = x - ox
            dy = y - oy
            # In local Cartesian (+Y up), clockwise rotation is (dx*cos + dy*sin, -dx*sin + dy*cos)
            x_rot = ox + (dx * cos_a + dy * sin_a)
            y_rot = oy + (-dx * sin_a + dy * cos_a)
            x, y = x_rot, y_rot

        # 3. Translation
        return (round(x + self.position[0], 6), round(y + self.position[1], 6))

    def apply_to_vertices(self, vertices: Sequence[Point2D]) -> List[Point2D]:
        """Transforms an entire list of vertices."""
        return [self.apply_to_point(pt) for pt in vertices]

    def to_dict(self) -> Dict[str, Any]:
        """Serializes transform fields for inspection and export."""
        return {
            "position": list(self.position),
            "scale": list(self.scale),
            "rotation": round(self.rotation, 4),
            "origin": list(self.origin),
        }

    @staticmethod
    def compute_bounds(vertices: Sequence[Point2D]) -> Dict[str, float]:
        """Computes Axis-Aligned Bounding Box (AABB) extents from vertices."""
        if not vertices:
            return {
                "min_x": 0.0,
                "min_y": 0.0,
                "max_x": 0.0,
                "max_y": 0.0,
                "width": 0.0,
                "height": 0.0,
            }
        xs = [pt[0] for pt in vertices]
        ys = [pt[1] for pt in vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return {
            "min_x": round(min_x, 4),
            "min_y": round(min_y, 4),
            "max_x": round(max_x, 4),
            "max_y": round(max_y, 4),
            "width": round(max_x - min_x, 4),
            "height": round(max_y - min_y, 4),
        }
