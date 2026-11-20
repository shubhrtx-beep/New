# Draw Shape API — Validation Conditions & Error Handling Specification

## Overview

This document specifies the validation conditions, topological invariants, error categories, and resolution strategies for the Draw.NEXUS Shape API.
It serves as the definitive reference for implementing input sanitization, geometric constraint checking, and error handling in both the Python frontend and the C++ geometry backend.

---

## 1. Topological & Shape Closure Constraints (`closed: bool`)

In 2D planar geometry, closed polygons and open paths have fundamentally different mathematical degrees of freedom.

### 1.1 `side_length` Constraints
* **Condition for Open Paths (`closed = False`):**
  * `side_length` is fully permitted.
  * **Mechanism:** Evaluated using forward kinematics (turtle chain). Modifying the length of segment $i$ translates all downstream vertices $V_{i+1}, V_{i+2}, \dots, V_n$ along the edge vector.
* **Condition for Closed Shapes (`closed = True`):**
  * **Invariant:** In a closed polygon, the distance between $V_i$ and $V_{i+1}$ cannot be changed in isolation without altering neighboring edge lengths or breaking polygon closure ($V_n \neq V_0$).
  * **Validation Rule:**
    * If `side_length` is provided on a `closed = True` shape:
    * **v1 Default Action:** Raise `ClosedShapeTopologyError`:
        ```text
        ClosedShapeTopologyError: Cannot apply independent 'side_length' to a closed shape 'card'. Modifying single edge lengths breaks closed polygon topology. Set closed=False or use 'scale' instead.
        ```
      * **Explicit Override (`force_open=True`):** The shape is deliberately converted to an open polyline (`closed = False`). This is never an implicit side effect.

---

### 1.2 `side_angle` Constraints
* **Condition for Open Paths (`closed = False`):**
  * `side_angle` is fully permitted.
  * **Mechanism:** Rotates edge $i$ relative to its starting vertex $V_i$, carrying all subsequent vertices along with the rotation.
* **Condition for Closed Shapes (`closed = True`):**
  * **Invariant:** The sum of interior angles in a closed planar $N$-gon must equal $(N - 2) \times 180^\circ$. Arbitrarily rotating one edge alters adjacent angles and breaks closure.
    * **v1 Validation Rule:** Raise `ClosedShapeTopologyError` for an independent edit. A future closure-solver mode may accept a complete constraint set, but it must document which vertices may move, tolerances, and failure behavior.

---

### 1.3 Combining `side_angle` AND `side_length`
* **v1 Rule:** Applying both `side_angle` and `side_length` to a closed shape is prohibited because v1 has no closure solver. A future solver may accept them only as an explicit, validated constraint system; they are not inherently mathematically impossible.
* **Error:** `OverConstrainedTopologyError`:
  ```text
  OverConstrainedTopologyError: Cannot specify both 'side_angle' and 'side_length' on closed shape 'card'.
  ```

---

### 1.4 Edge Removal (`remove=[...]`) on Closed Shapes
* **Condition:**
  * When `remove=[index, ...]` is invoked on a shape with `closed = True`:
  * Removing an edge removes the boundary line between $V_i$ and $V_{i+1}$.
* **Validation Rule:**
  1. The shape's topology is automatically converted to an open path (`closed = False`).
  2. If edge removal results in disconnected sub-paths, the engine creates a multi-path open geometry.
  3. If all edges are removed, raise `DegenerateGeometryError("Cannot remove all edges from shape.")`.

---

## 2. Geometry Definition Exclusivity & Bounds

A shape must be unambiguously defined using exactly one input mode.

### 2.1 Mode Exclusivity Rule
* **Inputs Checked:** `type`, `vertices`, `coordinates`. The legacy spelling `coordinate` is normalized to `coordinates` before this check; providing both is a conflict.
* **Conditions & Errors:**
  * **If count == 0:**
    ```text
    MissingGeometryDefinitionError: Shape 'card' must specify exactly one definition mode: 'type', 'vertices', or 'coordinates'.
    ```
  * **If count > 1:**
    ```text
    ConflictingGeometryDefinitionError: Shape 'card' received conflicting definitions (e.g., both 'type' and 'vertices'). Specify only one.
    ```

---

### 2.2 `vertices = N` Constraints
* **Minimum Vertex Count:**
  * If `closed = True`: `vertices >= 3` (minimum geometry to form a 2D area is a triangle).
    * If `vertices < 3`: Raise `InvalidPolygonVertexCountError("Closed polygons require at least 3 vertices, got N.")`.
  * If `closed = False`: `vertices >= 2` (minimum geometry to form a line segment is 2 points).
    * If `vertices < 2`: Raise `InvalidLineVertexCountError("Lines require at least 2 vertices, got N.")`.
* **Mandatory Bounds Requirement:**
  * `vertices = N` defines a regular $N$-gon. A regular polygon cannot be synthesized without metric dimensions.
  * **Condition:** `size[0] > 0 and size[1] > 0`.
  * If `size == (0.0, 0.0)`: Raise `UndefinedGeometryBoundsError`:
    ```text
    UndefinedGeometryBoundsError: Shape 'card' defined with vertices=N requires non-zero 'size' (width, height) to generate coordinates.
    ```
* **Default Orientation Invariant:**
  * For regular $N$-gons generated from `vertices = N`:
    * Vertex 0 is placed at **top center** $(x = 0, y = r)$ where $r = \text{height} / 2$ in local Cartesian space (+Y up).
    * Subsequent vertices follow clockwise in screen space after the renderer's Y-axis projection. The generated mesh records its local winding.

---

### 2.3 `type = "..."` Constraints
* **Supported Built-in Types:**
  * `"rectangle"`
  * `"square"`
  * `"triangle"`
  * `"circle"`
  * `"ellipse"`
  *(Note: Arbitrary N-sided regular polygons such as hexagons, pentagons, etc. are created exclusively via `vertices=N` mode to maintain parameter exclusivity).*
* **Error:**
  * If `type` is not recognized:
    ```text
    UnknownShapeTypeError: Unknown shape type 'hexagon'. Did you mean vertices=6?
    ```

---

### 2.4 `coordinates = [...]` Constraints
* **Condition:**
  * Points must be a finite `Sequence[Tuple[float, float]]`; it is copied into the working representation.
  * For `closed = True`: minimum length is 3 non-collinear points.
  * For `closed = False`: minimum length is 2 points.
* **Error:**
  * If coordinates contain NaNs or Infinities: Raise `InvalidCoordinateValueError`.
  * For closed shapes, reject repeated consecutive points, zero-area polygons, and self-intersections unless the caller uses a future explicitly supported self-intersection mode. Open paths may be collinear.

---

## 3. 0-Based Index Boundary Validation (`side_edit`)

All side and vertex indexing is 0-based: `0 <= index < num_sides`.

### 3.1 Side Index Out of Bounds
* **Applies to:** `bend`, `side_angle`, `side_length`, `scale`, `remove`.
* **Validation Rule:**
  ```python
  if side < 0 or side >= shape.num_sides:
      raise SideIndexOutOfBoundsError(
          f"Side index {side} out of bounds for shape '{name}' with {shape.num_sides} sides. "
          f"Valid side indices are 0 to {shape.num_sides - 1}."
      )
  ```

---

## 4. Corner Rounding Constraints (`edges`)

### 4.1 Maximum Corner Radius Clamping
* **Condition:**
  * Corner rounding cuts into the two adjacent edges meeting at vertex $V_i$.
  * Let $L_{\text{prev}}$ be the length of edge $i-1$, and $L_{\text{next}}$ be the length of edge $i$.
  * The maximum possible bevel distance before colliding with neighboring corners is:
    $$r_{\max} = \frac{1}{2} \min(L_{\text{prev}}, L_{\text{next}})$$
* **Validation Rule:**
  * If `edges` specifies a radius $r > r_{\max}$: clamp it to $r_{\max}$ and emit `CornerRadiusClampedWarning`. v1 does not offer a configuration-dependent raise-or-clamp choice.
  * If $r < 0.0$:
    * Raise `ValueError("Corner rounding 'edges' radius must be non-negative.")`.

---

## 5. Free-Form Deformation (FFD) Cage Constraints (`warp`)

### 5.1 Grid Topology Rules
* **Condition:**
  * `warp` must be a 2D matrix of coordinate displacements `List[List[Tuple[float, float]]]`.
  * Minimum grid size: $2 \times 2$ (4 corners: top-left, top-right, bottom-left, bottom-right).
* **Validation Rule:**
  * Rows must have identical lengths: `len(row_i) == len(row_0) >= 2`.
  * If grid is ragged or smaller than $2 \times 2$:
    ```text
    InvalidWarpGridError: 'warp' grid must be a uniform rectangular matrix of at least 2x2 control points.
    ```

---

## 6. Internal Hole / Cutout Constraints (`exclude`)

### 6.1 Polygon Containment and Winding
* **Condition:**
  * An `exclude` polygon represents an internal cutout/hole.
  * Every cutout vertex must lie within or on the boundary of the parent polygon; bounding-box containment alone is insufficient.
  * v1 stores outer rings counter-clockwise and holes clockwise in local Cartesian space before triangulation. Intersecting rings and overlapping holes are rejected.
* **Validation Rule:**
  * If a hole lies outside or intersects the outer boundary: raise `HoleOutsideBoundaryError`; silently accepting an invisible hole is not permitted.
  * If `width_between < 0.0`:
    * Raise `ValueError("'width_between' in exclude must be >= 0.0.")`.

---

## 7. Scene Registry & Lifecycle Validation

### 7.1 Duplicate Name Collision
```python
Draw.shape(name="card", ...)
Draw.shape(name="card", ...)  # Collision!
```
* **Validation Rule:**
  * If `name` already exists in the active scene registry:
    * Raise `DuplicateShapeNameError: Shape with name 'card' already exists. Use Draw.shape.update('card', ...) or provide a unique name.`

### 7.2 Non-Existent Shape Lookups
* **Applies to:** `Draw.shape.update("unknown", ...)`, `Draw.copy("unknown")`, `Draw.shape.release("unknown")`.
* **Validation Rule:**
  * Raise `ShapeNotFoundError: No registered shape found with name 'unknown'.`

---

## Summary of Custom Exception Classes

All exceptions inherit from a base `DrawShapeError` for clean catching:

```python
class DrawShapeError(Exception):
    """Base exception for all Draw3 Shape module errors."""
    pass

class ClosedShapeTopologyError(DrawShapeError):
    """Raised when open-path operations (side_length, side_angle) are illegally applied to closed polygons."""
    pass

class OverConstrainedTopologyError(DrawShapeError):
    """Raised when conflicting constraints (both side_length and side_angle) are applied."""
    pass

class ConflictingGeometryDefinitionError(DrawShapeError):
    """Raised when multiple mutually exclusive geometry modes are provided."""
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
```
