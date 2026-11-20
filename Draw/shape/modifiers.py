"""Draw Shape API — Side Modifiers, Whole-Shape Edits, and Sub-Editing.

Implements:
- side_edit: bend (normal edge displacement), side_length, side_angle, side_scale, 2x2 warp (FFD cage), exclude (holes).
- edit: rotate, flip, corner rounding (edges filleting), edge removal (remove), symmetry.
- sub_edit: child shapes container and boundary clipping flags.
"""

import math
from typing import List, Tuple, Dict, Any, Optional, Sequence, Union
from .errors import (
    ClosedShapeTopologyError,
    OverConstrainedTopologyError,
    SideIndexOutOfBoundsError,
    InvalidWarpGridError,
    DegenerateGeometryError,
)

Point2D = Tuple[float, float]


class SideEdit:
    """Encapsulates side-level deformations (bend, warp, exclude, side kinematics)."""

    def __init__(
        self,
        bend: Optional[List[Dict[str, Any]]] = None,
        warp: Optional[List[List[Point2D]]] = None,
        exclude: Optional[List[Dict[str, Any]]] = None,
        side_angle: Optional[Dict[int, float]] = None,
        side_length: Optional[Dict[int, float]] = None,
        side_scale: Optional[Dict[int, Tuple[float, float]]] = None,
        force_open: bool = False,
    ) -> None:
        self.bend = bend or []
        self.warp = warp
        self.exclude = exclude or []
        self.side_angle = side_angle or {}
        self.side_length = side_length or {}
        self.side_scale = side_scale or {}
        self.force_open = force_open


class WholeEdit:
    """Encapsulates whole-shape transformations and topological modifications."""

    def __init__(
        self,
        rotate: float = 0.0,
        edges: Union[float, List[float]] = 0.0,
        remove: Optional[List[int]] = None,
        flip: Optional[str] = None,
        anchor: Optional[Union[str, Point2D]] = None,
        symmetry: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.rotate = float(rotate)
        self.edges = edges
        self.remove = remove or []
        self.flip = flip
        self.anchor = anchor
        self.symmetry = symmetry


class SubEdit:
    """Encapsulates nested child shapes and parent-boundary clipping."""

    def __init__(
        self,
        shapes: Optional[List[Any]] = None,
        clip: bool = True,
        p: Optional[bool] = None,  # Backward-compatibility alias
    ) -> None:
        self.shapes = shapes or []
        self.clip = clip if p is None else p


class ModifierPipeline:
    """Applies SideEdit and WholeEdit transformations to shape vertices."""

    @staticmethod
    def apply_warp(
        vertices: Sequence[Point2D],
        warp_grid: List[List[Point2D]],
    ) -> List[Point2D]:
        """Applies a 2x2 Free-Form Deformation (FFD) cage to vertices via bilinear interpolation."""
        if len(warp_grid) < 2 or any(len(row) < 2 for row in warp_grid):
            raise InvalidWarpGridError(
                "'warp' grid must be a uniform rectangular matrix of at least 2x2 control points."
            )

        xs = [pt[0] for pt in vertices]
        ys = [pt[1] for pt in vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max_x - min_x
        h = max_y - min_y

        d00 = warp_grid[0][0]  # Top-left offset
        d01 = warp_grid[0][1]  # Top-right offset
        d10 = warp_grid[1][0]  # Bottom-left offset
        d11 = warp_grid[1][1]  # Bottom-right offset

        warped: List[Point2D] = []
        for x, y in vertices:
            u = (x - min_x) / w if w > 1e-9 else 0.5
            # In Cartesian (+Y up), top is max_y, so v is 0 at top and 1 at bottom
            v = (max_y - y) / h if h > 1e-9 else 0.5
            u = max(0.0, min(1.0, u))
            v = max(0.0, min(1.0, v))

            # Bilinear interpolation of displacement
            dx = (1 - u) * (1 - v) * d00[0] + u * (1 - v) * d01[0] + (1 - u) * v * d10[0] + u * v * d11[0]
            dy = (1 - u) * (1 - v) * d00[1] + u * (1 - v) * d01[1] + (1 - u) * v * d10[1] + u * v * d11[1]

            warped.append((round(x + dx, 6), round(y + dy, 6)))

        return warped

    @staticmethod
    def apply_bend(
        vertices: Sequence[Point2D],
        bend_rules: List[Dict[str, Any]],
        closed: bool,
        segments: int = 16,
    ) -> List[Point2D]:
        """Bends specific edges outward or inward along their normal vectors."""
        n = len(vertices)
        if n < 2 or not bend_rules:
            return list(vertices)

        num_sides = n if closed else n - 1
        bend_map = {b["side"]: b for b in bend_rules}

        for side in bend_map:
            if side < 0 or side >= num_sides:
                raise SideIndexOutOfBoundsError(
                    f"Side index {side} out of bounds for shape with {num_sides} sides. Valid indices: 0 to {num_sides - 1}."
                )

        new_vertices: List[Point2D] = []
        for i in range(num_sides):
            v0 = vertices[i]
            v1 = vertices[(i + 1) % n]
            new_vertices.append(v0)

            if i in bend_map:
                rule = bend_map[i]
                offset = float(rule.get("offset", 0.0))
                direction = rule.get("direction", "out").strip().lower()
                sign = 1.0 if direction == "out" else -1.0

                # Edge normal vector
                dx = v1[0] - v0[0]
                dy = v1[1] - v0[1]
                length = math.hypot(dx, dy)
                if length > 1e-9:
                    # Normal vector (+Y up: right-hand normal is (dy, -dx))
                    nx = (dy / length) * sign * offset
                    ny = (-dx / length) * sign * offset

                    # Generate quadratic curve points between v0 and v1
                    for s in range(1, segments):
                        t = s / float(segments)
                        # Parabolic displacement profile (t * (1 - t) * 4 peaks at midpoint t=0.5 with factor 1.0)
                        displacement = 4.0 * t * (1.0 - t)
                        bx = (1 - t) * v0[0] + t * v1[0] + nx * displacement
                        by = (1 - t) * v0[1] + t * v1[1] + ny * displacement
                        new_vertices.append((round(bx, 6), round(by, 6)))

        if not closed:
            new_vertices.append(vertices[-1])

        return new_vertices

    @staticmethod
    def apply_corner_rounding(
        vertices: Sequence[Point2D],
        edges: Union[float, List[float]],
        closed: bool,
        arc_segments: int = 8,
    ) -> List[Point2D]:
        """Applies corner fillet rounding (edges parameter) to vertices.

        Clamps radius to r_max = 0.5 * min(L_prev, L_next) at each corner.
        """
        n = len(vertices)
        if n < 3 or not closed:
            return list(vertices)

        radii = [edges] * n if isinstance(edges, (int, float)) else list(edges)
        while len(radii) < n:
            radii.append(radii[-1] if radii else 0.0)

        rounded_vertices: List[Point2D] = []

        for i in range(n):
            v_curr = vertices[i]
            v_prev = vertices[(i - 1) % n]
            v_next = vertices[(i + 1) % n]
            r = max(0.0, float(radii[i]))

            if r < 1e-6:
                rounded_vertices.append(v_curr)
                continue

            # Incoming and outgoing edge vectors
            d_in = (v_prev[0] - v_curr[0], v_prev[1] - v_curr[1])
            d_out = (v_next[0] - v_curr[0], v_next[1] - v_curr[1])
            len_in = math.hypot(d_in[0], d_in[1])
            len_out = math.hypot(d_out[0], d_out[1])

            if len_in < 1e-6 or len_out < 1e-6:
                rounded_vertices.append(v_curr)
                continue

            # Maximum corner radius clamping
            r_max = 0.5 * min(len_in, len_out)
            r = min(r, r_max)

            u_in = (d_in[0] / len_in, d_in[1] / len_in)
            u_out = (d_out[0] / len_out, d_out[1] / len_out)

            # Cut points on edges
            p_start = (v_curr[0] + u_in[0] * r, v_curr[1] + u_in[1] * r)
            p_end = (v_curr[0] + u_out[0] * r, v_curr[1] + u_out[1] * r)

            # Generate rounded quadratic arc points from p_start -> v_curr -> p_end
            for s in range(arc_segments + 1):
                t = s / float(arc_segments)
                bx = (1 - t) ** 2 * p_start[0] + 2 * (1 - t) * t * v_curr[0] + t ** 2 * p_end[0]
                by = (1 - t) ** 2 * p_start[1] + 2 * (1 - t) * t * v_curr[1] + t ** 2 * p_end[1]
                rounded_vertices.append((round(bx, 6), round(by, 6)))

        return rounded_vertices

    @staticmethod
    def apply_flip(vertices: Sequence[Point2D], orientation: str) -> List[Point2D]:
        """Flips vertices horizontally, vertically, or both."""
        mode = orientation.strip().lower()
        flipped: List[Point2D] = []
        for x, y in vertices:
            fx = -x if mode in ("horizontal", "both") else x
            fy = -y if mode in ("vertical", "both") else y
            flipped.append((fx, fy))
        return flipped

    @staticmethod
    def apply_remove(
        vertices: Sequence[Point2D],
        remove_indices: List[int],
        closed: bool,
    ) -> Tuple[List[Point2D], bool]:
        """Removes specific edges from geometry.

        When edges are removed from a closed shape, it automatically downgrades to closed=False.
        """
        n = len(vertices)
        if not remove_indices or n < 2:
            return list(vertices), closed

        num_sides = n if closed else n - 1
        for idx in remove_indices:
            if idx < 0 or idx >= num_sides:
                raise SideIndexOutOfBoundsError(
                    f"Remove side index {idx} out of range for shape with {num_sides} sides."
                )

        if len(remove_indices) >= num_sides:
            raise DegenerateGeometryError("Cannot remove all edges from shape.")

        # Removing edge from closed polygon breaks closure
        new_closed = False
        remaining_vertices: List[Point2D] = []

        # Slicing at removed edge
        remove_set = set(remove_indices)
        for i in range(n):
            if i not in remove_set:
                remaining_vertices.append(vertices[i])

        return remaining_vertices, new_closed
