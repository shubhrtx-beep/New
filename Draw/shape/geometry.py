"""Draw Shape API — Geometry Generation, Tessellation, and Ear-Clipping Triangulation.

Implements zero-dependency 2D geometry synthesis for built-in primitives,
regular N-gons, 0-based clockwise indexing standards, and robust Ear-Clipping
triangulation supporting concave polygons and internal cutout holes.
"""

import math
from typing import List, Tuple, Sequence, Dict, Any, Optional
from .errors import (
    UnknownShapeTypeError,
    InvalidPolygonVertexCountError,
    InvalidLineVertexCountError,
    DegenerateGeometryError,
    InvalidCoordinateValueError,
    UndefinedGeometryBoundsError,
    HoleOutsideBoundaryError,
)

Point2D = Tuple[float, float]


def is_valid_point(pt: Point2D) -> bool:
    """Checks if a 2D point consists of finite real numbers."""
    if not isinstance(pt, (tuple, list)) or len(pt) != 2:
        return False
    x, y = pt[0], pt[1]
    return (
        isinstance(x, (int, float))
        and isinstance(y, (int, float))
        and not math.isnan(x)
        and not math.isnan(y)
        and not math.isinf(x)
        and not math.isinf(y)
    )


def compute_polygon_area(vertices: Sequence[Point2D]) -> float:
    """Computes signed area of a 2D polygon using the Shoelace formula.

    In Cartesian coordinates (+Y up):
    - Positive area -> Counter-Clockwise (CCW)
    - Negative area -> Clockwise (CW)
    """
    n = len(vertices)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        area += (x1 * y2) - (x2 * y1)
    return area / 2.0


def point_in_triangle(p: Point2D, a: Point2D, b: Point2D, c: Point2D) -> bool:
    """Determines whether point P lies strictly inside triangle ABC using barycentric coordinates."""
    px, py = p
    ax, ay = a
    bx, by = b
    cx, cy = c

    v0x, v0y = cx - ax, cy - ay
    v1x, v1y = bx - ax, by - ay
    v2x, v2y = px - ax, py - ay

    dot00 = v0x * v0x + v0y * v0y
    dot01 = v0x * v1x + v0y * v1y
    dot02 = v0x * v2x + v0y * v2y
    dot11 = v1x * v1x + v1y * v1y
    dot12 = v1x * v2x + v1y * v2y

    denom = dot00 * dot11 - dot01 * dot01
    if abs(denom) < 1e-12:
        return False

    inv_denom = 1.0 / denom
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom

    return (u > 1e-9) and (v > 1e-9) and (u + v < 1.0 - 1e-9)


def point_in_polygon(p: Point2D, polygon: Sequence[Point2D]) -> bool:
    """Tests if point P lies inside a polygon using the ray casting algorithm."""
    px, py = p
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside


def triangulate_simple_polygon(vertices: Sequence[Point2D]) -> List[int]:
    """Triangulates a simple polygon (convex or concave) using the Ear-Clipping algorithm.

    Returns:
        List of vertex indices representing triangles (e.g. [0, 1, 2, 0, 2, 3]).
    """
    n = len(vertices)
    if n < 3:
        return []
    if n == 3:
        return [0, 1, 2]

    # Index list
    indices = list(range(n))
    triangles: List[int] = []

    # Signed area: positive if CCW, negative if CW
    area = compute_polygon_area(vertices)
    if abs(area) < 1e-9:
        raise DegenerateGeometryError("Polygon area is zero or collinear; cannot triangulate.")

    is_ccw = area > 0.0

    def is_convex(i_prev: int, i_curr: int, i_next: int) -> bool:
        p_prev = vertices[i_prev]
        p_curr = vertices[i_curr]
        p_next = vertices[i_next]
        dx1 = p_curr[0] - p_prev[0]
        dy1 = p_curr[1] - p_prev[1]
        dx2 = p_next[0] - p_curr[0]
        dy2 = p_next[1] - p_curr[1]
        cross = dx1 * dy2 - dy1 * dx2
        return (cross > 1e-9) if is_ccw else (cross < -1e-9)

    def is_ear(i: int) -> bool:
        idx_curr = indices[i]
        idx_prev = indices[(i - 1) % len(indices)]
        idx_next = indices[(i + 1) % len(indices)]

        if not is_convex(idx_prev, idx_curr, idx_next):
            return False

        a = vertices[idx_prev]
        b = vertices[idx_curr]
        c = vertices[idx_next]

        # Check if any other vertex lies strictly inside triangle abc
        for j in range(len(indices)):
            if j in ((i - 1) % len(indices), i, (i + 1) % len(indices)):
                continue
            test_pt = vertices[indices[j]]
            if point_in_triangle(test_pt, a, b, c):
                return False
        return True

    count = 0
    max_iterations = len(indices) * len(indices) * 2

    while len(indices) > 3 and count < max_iterations:
        ear_found = False
        for i in range(len(indices)):
            count += 1
            if is_ear(i):
                idx_prev = indices[(i - 1) % len(indices)]
                idx_curr = indices[i]
                idx_next = indices[(i + 1) % len(indices)]

                triangles.extend([idx_prev, idx_curr, idx_next])
                indices.pop(i)
                ear_found = True
                break

        if not ear_found:
            # Fallback for near-degenerate or self-touching ears: force slice closest convex
            for i in range(len(indices)):
                idx_prev = indices[(i - 1) % len(indices)]
                idx_curr = indices[i]
                idx_next = indices[(i + 1) % len(indices)]
                if is_convex(idx_prev, idx_curr, idx_next):
                    triangles.extend([idx_prev, idx_curr, idx_next])
                    indices.pop(i)
                    ear_found = True
                    break
            if not ear_found and len(indices) > 0:
                # Emergency pop to avoid infinite loop
                triangles.extend([indices[0], indices[1], indices[2]])
                indices.pop(1)

    if len(indices) == 3:
        triangles.extend([indices[0], indices[1], indices[2]])

    return triangles


def triangulate_polygon_with_holes(
    outer_ring: Sequence[Point2D],
    holes: Sequence[Sequence[Point2D]],
) -> Tuple[List[Point2D], List[int]]:
    """Triangulates an outer polygon with one or more internal hole cutouts.

    Uses bridge-edge seam insertion to combine outer and inner rings into a
    single simple polygon before running Ear-Clipping.

    Returns:
        (merged_vertices, indices)
    """
    if not holes:
        return list(outer_ring), triangulate_simple_polygon(outer_ring)

    # Validate holes are strictly inside outer ring
    for hole in holes:
        for pt in hole:
            if not point_in_polygon(pt, outer_ring):
                raise HoleOutsideBoundaryError(
                    f"Hole vertex {pt} lies outside outer polygon boundary."
                )

    combined_vertices: List[Point2D] = list(outer_ring)

    # For each hole, find the vertex with the maximum X coordinate
    for hole in holes:
        if len(hole) < 3:
            continue
        # Rightmost vertex of hole
        max_hole_idx = max(range(len(hole)), key=lambda k: hole[k][0])
        hole_pt = hole[max_hole_idx]

        # Find closest visible outer vertex
        best_outer_idx = 0
        min_dist_sq = float("inf")
        for idx, opt in enumerate(combined_vertices):
            if opt[0] >= hole_pt[0]:  # To the right of hole point
                dist_sq = (opt[0] - hole_pt[0]) ** 2 + (opt[1] - hole_pt[1]) ** 2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    best_outer_idx = idx

        # Reorder hole vertices starting at max_hole_idx
        reordered_hole = [hole[(max_hole_idx + i) % len(hole)] for i in range(len(hole))]
        # Stitch: insert hole sequence and duplicated bridge vertices into combined list
        bridge_outer = combined_vertices[best_outer_idx]
        bridge_hole = reordered_hole[0]

        # Insert seam: outer -> hole -> hole_start -> outer
        seam = [bridge_outer] + reordered_hole + [bridge_hole]
        combined_vertices[best_outer_idx:best_outer_idx + 1] = seam

    indices = triangulate_simple_polygon(combined_vertices)
    return combined_vertices, indices


class GeometryBuilder:
    """Generates standard primitive 2D vertices following 0-based clockwise standards."""

    @staticmethod
    def create_rectangle(width: float, height: float) -> Tuple[List[Point2D], List[int]]:
        """Generates a rectangle centered at (0, 0) in Cartesian space (+X right, +Y up).

        0-Based Standard:
        - Vertex 0 is Top-Left (-w/2, h/2)
        - Side 0 is the Top Edge: Vertex 0 -> Vertex 1
        - Clockwise in screen coordinates (+Y down screen projection):
          Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left
        """
        hw = width / 2.0
        hh = height / 2.0
        vertices: List[Point2D] = [
            (-hw, hh),   # 0: Top-Left
            (hw, hh),    # 1: Top-Right
            (hw, -hh),   # 2: Bottom-Right
            (-hw, -hh),  # 3: Bottom-Left
        ]
        indices = [0, 1, 2, 0, 2, 3]
        return vertices, indices

    @staticmethod
    def create_square(size: float) -> Tuple[List[Point2D], List[int]]:
        """Generates a square with equal width and height."""
        return GeometryBuilder.create_rectangle(size, size)

    @staticmethod
    def create_triangle(width: float, height: float) -> Tuple[List[Point2D], List[int]]:
        """Generates an isosceles triangle centered at (0, 0).

        - Vertex 0: Top Center (0, h/2)
        - Vertex 1: Bottom Right (w/2, -h/2)
        - Vertex 2: Bottom Left (-w/2, -h/2)
        """
        hw = width / 2.0
        hh = height / 2.0
        vertices: List[Point2D] = [
            (0.0, hh),   # 0: Top-Center
            (hw, -hh),   # 1: Bottom-Right
            (-hw, -hh),  # 2: Bottom-Left
        ]
        indices = [0, 1, 2]
        return vertices, indices

    @staticmethod
    def create_regular_polygon(n_vertices: int, width: float, height: float) -> Tuple[List[Point2D], List[int]]:
        """Generates an N-sided regular polygon centered at (0, 0).

        0-Based Convention:
        - Vertex 0 is placed at Top-Center (0, h/2).
        - Subsequent vertices follow clockwise around the perimeter.
        """
        if n_vertices < 3:
            raise InvalidPolygonVertexCountError(
                f"Closed polygons require at least 3 vertices, got {n_vertices}."
            )
        if width <= 0.0 or height <= 0.0:
            raise UndefinedGeometryBoundsError(
                f"Shape defined with vertices={n_vertices} requires non-zero size (width, height), got ({width}, {height})."
            )

        rx = width / 2.0
        ry = height / 2.0
        vertices: List[Point2D] = []

        for i in range(n_vertices):
            # Clockwise from top (angle 0 at top center, increasing clockwise)
            angle = 2.0 * math.pi * i / n_vertices
            x = rx * math.sin(angle)
            y = ry * math.cos(angle)
            vertices.append((round(x, 6), round(y, 6)))

        indices = triangulate_simple_polygon(vertices)
        return vertices, indices

    @staticmethod
    def create_circle(diameter: float, segments: int = 32) -> Tuple[List[Point2D], List[int]]:
        """Generates a regular circle approximated by 32+ segments."""
        return GeometryBuilder.create_regular_polygon(segments, diameter, diameter)

    @staticmethod
    def create_ellipse(width: float, height: float, segments: int = 32) -> Tuple[List[Point2D], List[int]]:
        """Generates an ellipse approximated by 32+ segments."""
        return GeometryBuilder.create_regular_polygon(segments, width, height)

    @classmethod
    def generate_primitive(cls, shape_type: str, width: float, height: float) -> Tuple[List[Point2D], List[int]]:
        """Dispatches primitive geometry generation based on type string."""
        st = shape_type.strip().lower()
        if st in ("rectangle", "rect"):
            return cls.create_rectangle(width, height)
        elif st in ("square",):
            return cls.create_square(min(width, height))
        elif st in ("triangle",):
            return cls.create_triangle(width, height)
        elif st in ("circle",):
            return cls.create_circle(min(width, height))
        elif st in ("ellipse",):
            return cls.create_ellipse(width, height)
        else:
            raise UnknownShapeTypeError(
                f"Unknown shape type '{shape_type}'. Supported types: rectangle, square, triangle, circle, ellipse. "
                f"For regular polygons, use vertices=N."
            )


class MetadataGenerator:
    """Generates secondary geometry metadata tables ('indexing', 'hitbox', 'map')."""

    @staticmethod
    def generate_indexing(vertices: Sequence[Point2D], closed: bool) -> Dict[str, Any]:
        """Generates 0-based edge and vertex indexing metadata."""
        n = len(vertices)
        edges: List[Tuple[int, int]] = []
        edge_lengths: List[float] = []

        num_edges = n if closed else max(0, n - 1)
        for i in range(num_edges):
            j = (i + 1) % n if closed else i + 1
            edges.append((i, j))
            dx = vertices[j][0] - vertices[i][0]
            dy = vertices[j][1] - vertices[i][1]
            edge_lengths.append(round(math.hypot(dx, dy), 4))

        return {
            "vertex_count": n,
            "edge_count": len(edges),
            "edges": edges,
            "edge_lengths": edge_lengths,
        }

    @staticmethod
    def generate_hitbox(vertices: Sequence[Point2D]) -> List[Point2D]:
        """Generates simplified boundary / collision vertices (Axis-Aligned Bounding Box)."""
        if not vertices:
            return []
        xs = [pt[0] for pt in vertices]
        ys = [pt[1] for pt in vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return [
            (min_x, max_y),  # Top-Left
            (max_x, max_y),  # Top-Right
            (max_x, min_y),  # Bottom-Right
            (min_x, min_y),  # Bottom-Left
        ]

    @staticmethod
    def generate_map(vertices: Sequence[Point2D], closed: bool) -> Dict[str, Any]:
        """Generates normalized [0, 1] vertex coordinates and bounding extents."""
        if not vertices:
            return {"normalized_vertices": [], "bounds": {}}
        xs = [pt[0] for pt in vertices]
        ys = [pt[1] for pt in vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max_x - min_x
        h = max_y - min_y

        normalized: List[Point2D] = []
        for x, y in vertices:
            nx = (x - min_x) / w if w > 1e-9 else 0.5
            ny = (y - min_y) / h if h > 1e-9 else 0.5
            normalized.append((round(nx, 4), round(ny, 4)))

        indexing = MetadataGenerator.generate_indexing(vertices, closed)
        return {
            "normalized_vertices": normalized,
            "bounds": {
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
                "width": w,
                "height": h,
            },
            "edge_lengths": indexing["edge_lengths"],
        }
