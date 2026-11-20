# Draw3 Shape Subsystem — Working Data Architecture & Implementation Guide

## 1. System Overview

This document records the exact methods, mathematical formulas, architectural decisions, and key design points used to build the **Python Working Data Structure** for the Draw3 Shape API (`d:\draw3\Draw\`).

The implementation strictly fulfills:
1. **Working Data Structure Only**: Editable, Python-native source of truth for 2D geometry, transformations, and hierarchy.
2. **Zero External C / Binary Dependencies**: Uses pure Python standard types (`float`, `int`, `list`, `tuple`) and standard library packages (`math`, `weakref`, `itertools`).
3. **No C++ Dependency**: Active Runtime Data and Transfer Data (DGF binary packets) remain staged for future backend integration without polluting the Python frontend.

---

## 2. Directory & Module Structure

```text
d:\draw3\
├── Draw\
│   ├── __init__.py          # Root entry point: Draw.shape, Draw.shapes, Draw.line, Draw.remove
│   └── shape\
│       ├── __init__.py      # Shape subsystem exports & compatibility delegates
│       ├── errors.py        # Complete custom exception hierarchy
│       ├── units.py         # UnitResolver: px, %, canvas/parent/edge scopes
│       ├── geometry.py      # Primitive generators, Ear-Clipping triangulation, seam hole stitching
│       ├── transform.py     # Transform2D, local origin rotation, bounds computation
│       ├── modifiers.py     # SideEdit (bend, warp), WholeEdit (edges, flip, remove), SubEdit
│       ├── shape.py         # Authoritative Shape class (Working Data)
│       ├── group.py         # ShapeGroup: batch transformations & context manager
│       └── registry.py      # SceneRegistry: duplicate checks, weakref scoped mode, ShapesNamespace
└── test\
    └── test_shape_module.py # Full verification suite (primitives, units, errors, lifecycle)
```

---

## 3. Key Classes, Methods & Implementation Mechanics

### 3.1 `Shape` (`Draw.shape.shape`)
* **Role**: Authoritative Working Data representation of a 2D shape.
* **Key Fields**:
  - `shape_id`: Unique 32-bit integer assigned monotonically via `itertools.count(101)`.
  - `name`: Unique string identifier in the scene registry.
  - `closed: bool`: Intrinsic topological boundary flag (`True` for closed polygon, `False` for open path).
  - `z: int`: Overlap depth ranking.
  - `resolved_size`: `(width, height)` resolved to floats.
  - `transform`: `Transform2D` object storing `(position, scale, rotation, origin)`.
  - `vertices`: Local Cartesian coordinates `[(x, y), ...]` centered at `(0, 0)` with $+X$ right and $+Y$ up.
  - `indices`: Flat list of triangle vertex indices `[0, 1, 2, 0, 2, 3, ...]`.
  - `versions`: Dirty version tracking dictionary:
    ```python
    {"geometry": 1, "transform": 1, "metadata": 1}
    ```
* **Key Method — `.update(**kwargs)`**:
  - Increments `geometry_version` only when geometry-altering parameters change (`size`, `side_edit`, `edit`).
  - Increments `transform_version` without re-triangulating when only `position`, `rotation`, `scale`, or `origin` change.
  - Increments `metadata_version` for `z`, `tags`, or `parent`.
* **Key Method — `.query(keys)`**:
  - Dynamically returns requested metadata (e.g. `bounds`, `map`, `hitbox`, `indexing`) without duplicating full vertex arrays unless explicitly requested.
* **Key Method — `.to_dict()`**:
  - Produces human-readable serialization matching the output contract in `expected_output.md`.

---

### 3.2 0-Based Clockwise Standard & Geometry Builders (`geometry.py`)
* **Standard Convention**:
  - Local Cartesian space has $(0, 0)$ at center: $+X$ right, $+Y$ up.
  - **Vertex 0 is Top-Left or Top-Center**:
    - For Rectangle: Vertex 0 is `(-w/2, h/2)` (Top-Left), Vertex 1 is `(w/2, h/2)` (Top-Right).
    - **Side 0 is the Top Edge** (from Vertex 0 to Vertex 1).
    - Follows clockwise order in screen space: Top-Left $\rightarrow$ Top-Right $\rightarrow$ Bottom-Right $\rightarrow$ Bottom-Left.
    - Regular $N$-gons place Vertex 0 at $(0, h/2)$ (Top-Center) and rotate clockwise:
      $$x_i = r_x \sin\left(\frac{2\pi i}{N}\right), \quad y_i = r_y \cos\left(\frac{2\pi i}{N}\right)$$

---

### 3.3 Pure Python Ear-Clipping Triangulation (`geometry.py`)
* **Method**: `triangulate_simple_polygon(vertices)`
  - Calculates polygon orientation via Shoelace signed area:
    $$A = \frac{1}{2} \sum_{i=0}^{n-1} (x_i y_{i+1} - x_{i+1} y_i)$$
  - Evaluates convex vertices using 2D cross product.
  - Checks if a candidate triangle contains any other polygon vertices using barycentric coordinate testing (`point_in_triangle`).
  - Progressively clips "ears", producing triangle indices in $O(n^2)$ time with zero external libraries.
* **Cutout Holes / `exclude` Support**: `triangulate_polygon_with_holes(outer_ring, holes)`
  - Implements **Bridge Seam Insertion**:
    1. Finds the rightmost vertex of each hole polygon.
    2. Ray-casts rightward to find the closest visible outer boundary edge.
    3. Slits the polygon by inserting duplicate bridge vertices, seamlessly joining the outer polygon and hole into a single continuous simple polygon.
    4. Runs ear-clipping on the combined ring.

---

### 3.4 Unit Resolution & Percentage Scopes (`units.py`)
* **Method**: `UnitResolver.to_float(val, reference)`
  - Strips `"px"` and parses float directly.
  - Parses `"%"`, dividing by $100.0$ and multiplying by the active `reference`.
* **Scope Rules**:
  - **Canvas Scope (Top-Level Shapes)**: Reference is `_CANVAS_SIZE` (default `1920.0 x 1080.0`). Configurable via `Draw.set_canvas_size(w, h)`.
  - **Parent Scope (Nested inside `sub_edit` or `parent="card"`)**:
    - Reference width and height are the parent's resolved bounding box (`parent.resolved_size`).
    - Handled via `_re_resolve_parent_scope(parent_size)`: when a child shape is attached to a parent, its relative percentage dimensions are automatically re-calculated against the parent's bounds.
  - **Corner Rounding Scope (`edges="50%"` vs `"100%"`)**:
    - Reference is the maximum bevel radius:
      $$r_{\max} = \frac{\min(\text{width}, \text{height})}{2}$$
    - `"100%"` yields full pill/circle rounding ($r = r_{\max} = 0.5 \min(w, h)$).
    - `"50%"` yields half-maximum rounding ($r = 0.25 \min(w, h)$).

---

### 3.5 Modifiers & Deformations (`modifiers.py`)
* **`bend`**:
  - Computes edge normal vector $\vec{n} = \left(\frac{\Delta y}{L}, -\frac{\Delta x}{L}\right)$ in Cartesian space (+Y up).
  - Tessellates the edge with a quadratic parabolic displacement profile:
    $$d(t) = 4t(1 - t) \times \text{offset}$$
    peaking at the midpoint $t = 0.5$.
* **`warp` (2x2 Free-Form Deformation Cage)**:
  - Normalizes vertex positions to $u, v \in [0, 1]$ across the bounding box.
  - Applies bilinear interpolation of the 4 corner displacement vectors:
    $$\Delta(u, v) = (1 - u)(1 - v)\vec{D}_{00} + u(1 - v)\vec{D}_{01} + (1 - u)v\vec{D}_{10} + uv\vec{D}_{11}$$
* **`edges` (Corner Filleting)**:
  - At vertex $V_i$, calculates incoming and outgoing unit vectors $\vec{u}_{\text{in}}, \vec{u}_{\text{out}}$.
  - Clamps radius to $r_{\max} = \frac{1}{2} \min(L_{\text{in}}, L_{\text{out}})$.
  - Slices corner with quadratic fillet arc between $V_i + \vec{u}_{\text{in}} r$ and $V_i + \vec{u}_{\text{out}} r$.
* **`remove` (Edge Removal & Topology Downgrade)**:
  - Removing an edge from a closed shape (`closed=True`) automatically downgrades it to an open polyline (`closed=False`).
  - Slices remaining edges into an open strip.

---

### 3.6 Scene Registry & Dual Namespace (`registry.py`)
* **Callable + Registry Object (`ShapesNamespace`)**:
  - `Draw.shapes` is an instance of `ShapesNamespace`:
    - Calling `Draw.shapes([...])` constructs a `ShapeGroup`.
    - Accessing `Draw.shapes.get("card")`, `Draw.shapes.list(...)`, `Draw.shapes.update(...)`, `Draw.shapes.remove(...)` operates on the central `GLOBAL_REGISTRY`.
  - Backward compatibility: `Draw.shape.update`, `Draw.shape.list`, `Draw.shape.copy`, `Draw.shape.remove` delegate directly to `GLOBAL_REGISTRY`.
* **Memory Lifecycle & Weak References (`scoped=True`)**:
  - `scoped=False` (Default): Authoritative strong reference in `_strong_registry`.
  - `scoped=True`: Stores a `weakref.ref(shape)`. Once the local Python variable falls out of scope, garbage collection auto-deregisters it via cleanup callback.
* **Context Manager (`with Draw.shapes(...) as group:`)**:
  - Pushes `ShapeGroup` onto `_ACTIVE_GROUP_STACK`.
  - All shapes instantiated within the `with` block auto-register into that group.
  - Exiting the block or calling `group.remove()` disposes of all contained shapes in a single atomic pass.

---

## 4. Troubleshooting & Maintenance Guide

| Symptom / Error | Root Cause | Resolution / Check Point |
| :--- | :--- | :--- |
| `ClosedShapeTopologyError` | User applied `side_length` or `side_angle` to a `closed=True` shape. | Expected invariant: Modifying isolated side lengths breaks polygon closure. Tell user to set `closed=False` or `force_open=True`. |
| `ConflictingGeometryDefinitionError` | Multiple definitions passed (e.g. `type` and `vertices`). | Ensure caller provides exactly one geometry input mode. |
| Percentage not scaling to parent | Child shape defined before parent in declarative sub-edit. | `_re_resolve_parent_scope` in `shape.py` handles this automatically upon child attachment. |
| Edge index out of bounds in `bend` | 0-based side index $\ge \text{num\_sides}$. | Sides are indexed $0 \dots N-1$. Side 0 is the top edge. Check `shape.num_sides`. |
| Cutout hole triangulation artifact | Hole vertex falls outside outer boundary. | Verified by `point_in_polygon` in `triangulate_polygon_with_holes`. Raises `HoleOutsideBoundaryError`. |
