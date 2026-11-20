# Draw Shape API — Build Specification

## Purpose

**import every thing with**
```python
import Draw
from Draw import shapes
``` 

This document specifies the architecture, data types, and implementation stages of the Draw Shape API.
Each subsystem is divided into modular parts so that it can be built, verified, and tested independently.

**Authority and version scope.** This is the build specification for the public API. `expected_output.md` is the authoritative contract for return values, transfer packets, and shared-memory publication. Where older examples conflict with that contract, the rewritten output contract wins. The first implementation release is limited to the features marked **v1** below; curves, holes, FFD, symmetry, and nested clipping remain staged extensions.

The Shape API is strictly responsible for **defining, generating, modifying, and releasing 2D geometry**.
External systems such as the main Color API, Alignment API, Motion API, and the C++ Rendering Engine are independent modules.
The Shape API connects to them via clean interfaces without implementing their internal logic.

---

# PART 1 — Shape Entry Point

## Standard Syntax: Direct Single-Call Definition

Each shape is defined and registered individually in a single clean call:

```python
import Draw

# Define and register a shape in a single call
Draw.shape(
    name="card",
    position=(0.0, 0.0),
    type="rectangle",
    size=(100.0, 50.0),
    closed=True,
    z=0,
)
```

The call creates the geometry, registers it under its unique `name`, and returns a `Shape` instance for direct object-oriented access.

## Core Parameters

```python
Draw.shape(
    name: str,
    position: Tuple[Union[float, str], Union[float, str]] = (0.0, 0.0),
    closed: bool = True,
    type: Optional[str] = None,
    vertices: Optional[int] = None,
    coordinates: Optional[Sequence[Tuple[float, float]]] = None,
    generate: Optional[Sequence[str]] = None,
    size: Tuple[Union[float, str], Union[float, str]] = (100.0, 100.0),
    scale: Tuple[float, float] = (1.0, 1.0),
    origin: Tuple[float, float] = (0.0, 0.0),
    z: int = 0,
    parent: Optional[str] = None,
    clip: bool = False,
    scoped: bool = False,
    side_edit: Optional[side_edit] = None,
    edit: Optional[edit] = None,
    sub_edit: Optional[sub_edit] = None,
    dynamic: Optional[Sequence[str]] = None,
) -> Shape
```

`coordinate` is accepted only as a deprecated compatibility alias for `coordinates`; passing both is an error. Mutable list defaults are deliberately not part of the public signature.

### `name` (str)
Unique string identifier for the shape in the scene registry.
```python
name = "card"
```
The name allows lookup and manipulation across all API methods:
```python
Draw.shape.update("card", size=(120.0, 60.0))
Draw.shape.list("card", data=["size", "z"])
Draw.shape.copy("card", new_name="card_copy")
Draw.shape.remove(["card"])
```

### `closed` (bool)
**Intrinsic topological property** of the geometry:
- `closed = True`: Closed polygon boundary (e.g. rectangle, regular polygon, closed path).
- `closed = False`: Open path or polyline strip.

### Geometry Definition Modes (Mutually Exclusive)
Geometry is defined using exactly one of three alternative inputs:
1. `type: str`: Predefined geometric primitive (e.g. `"rectangle"`, `"circle"`, `"triangle"`).
2. `vertices: int`: Regular N-gon polygon with `N` equidistant vertices (requires `size`).
3. `coordinates: Sequence[Tuple[float, float]]`: Explicit ordered list of vertex points.

```text
type: str
  OR
vertices: int (with size)
  OR
coordinates: Sequence[Tuple[float, float]]
```

---

# PART 2 — Generation

Generation controls what secondary metadata Draw creates from the geometry.

```python
generate: List[str] = [
    "indexing",  # Generate edge and vertex indexing metadata
    "hitbox",    # Generate collision / boundary coordinates
    "map",       # Generate coordinate mapping and export table
]
```
Use the shape query API rather than a global `Draw.map` call:
```python
result = Draw.shape.list("card", data=["map"])
# {"map": {"vertices": [...], "edges": [...]}}
```
### 0-Based Indexing Standard
All vertex and side indexing follows the standard **0-based convention**:
```text
For generated closed primitives, the top-most vertex / top edge is `0`.
Coordinates use local Cartesian space: +X is right and +Y is up.
Generated vertices are clockwise in screen space after the renderer's Y-axis projection; their stored local winding is explicitly recorded with the mesh.
```
- Standard 0-based indexing aligns seamlessly with Python slicing, list indexing, and GPU index buffers (EBO / IBO).
- Eliminates off-by-one translation overhead.

### Hitbox
Generates simplified boundary / collision vertices for collision testing.

### Map
Generates a structured dictionary containing normalized vertex mapping coordinates, edge lengths, and local bounding offsets.

---

# PART 3 — Basic Shape Geometry

Properties defining the shape's local transformation and metric space:

```python
position: Tuple[float, float] = (0.0, 0.0)
size: Tuple[float, float] = (100.0, 50.0)
scale: Tuple[float, float] = (1.0, 1.0)
origin: Tuple[float, float] = (0.0, 0.0)
```

- `position`: World or parent space placement coordinates `(x, y)`. Supports unit resolution (e.g. `("50%", "50%")`). Default is `(0.0, 0.0)`.
- `size`: Base width and height in world/local units `(width, height)`.
- `scale`: Scaling multiplier `(sx, sy)`. Default is `(1.0, 1.0)`.
- `origin`: Local transform origin and rotation pivot point `(x, y)`. All rotation, scaling, and deformation operations pivot around this point. Default is `(0.0, 0.0)`.

*(Note: `center_point` is removed. The single canonical reference point is `origin`. Geometric centroids are computed automatically by the engine).*

---

# PART 4 — External Module Connections & Overlap Priority

Shape generates geometry and its transform only. Styling, layout, alignment, and motion belong to separate modules and are not Shape parameters.

## Overlap Priority: `z` (int)
```python
z: int = 0
```
- `z` controls depth sorting and draw priority when shapes overlap.
- Higher `z` values promote a shape to render on top of shapes with lower `z` values.
- Pure integer depth ranking for draw-order ordering.

## Module Boundary & External Module Linking (`ip` / `name`)

Shape does not accept `color`, `fill`, `stroke`, `opacity`, `visible`, alignment, or motion parameters. A scene/composition layer associates a `shape_id` with components owned by the Color, Alignment, Motion, and Visibility modules:

* **Public API Level (`ip` Binding)**: The shape's unique `name` (e.g. `name="card"`) serves directly as the string identifier `ip` required by the Color module:
  ```python
  # Shape definition (Geometry only)
  Draw.shape(name="card", type="rectangle", size=(100.0, 50.0))

  # Color module binding (Joined via name / ip)
  Draw.color(ip="card", color=[{"for": "body", "color": "#1e293b"}])
  ```
* **Backend/Renderer Level**: The scene compositor resolves `ip` to the fixed 32-bit `shape_id` stored in the DGF packet header and `ShapeRecord`. The renderer receives the resolved geometry and the separately resolved render state.

---

# PART 5 — Side Editing (`side_edit`)

> **Concept:** `side_edit` modifies the **outer perimeter and edge boundaries** of the shape itself (0-based indexing).
> It does not create internal sub-shapes (for nested inner shapes, see `sub_edit`).

```python
card = Draw.shape(
    name="card",
    type="rectangle",
    size=(100.0, 50.0),
    closed=True,
    z=0,
    side_edit=Draw.shape.side.edit(
        bend=[
            {
                "side": 0,
                "affect": (-1.0, 1.0),
                "offset": 35.0,
                "direction": "out",
            }
        ],
        warp=[
            [(0.0, 0.0), (-25.0, 25.0)],
            [(0.0, 0.0), (0.0, 0.0)],
        ],
        exclude=[...],
    )
)
```

---

## 5.1 — Bend

Displaces a side along its normal vector to create curved edges.

```python
bend: List[Dict[str, Any]] = [
    {
        "side": 0,                      # 0-indexed side number
        "affect": (-1.0, 1.0),          # Range: -1.0 (start vertex) -> 0.0 (midpoint) -> 1.0 (end vertex)
        "offset": 35.0,                 # Peak displacement in pixels / units (float)
        "direction": "out",             # "out" (pushes outward) or "in" (pulls inward)
    }
]
```

- Evaluated as a parametric Bezier or quadratic curve between vertices `side` and `side + 1`.

---

## 5.2 — Exclude

Creates internal holes or cutout polygons within the shape.

```python
exclude: List[Dict[str, Any]] = [
    {
        "id": 0,
        "anchor": "center",             # Anchor: "center", "top-left", "bottom-right", etc.
        "scale": (1.0, 1.0),            # Local scale of hole
        "line": [                       # Hole polygon vertices (List of float tuples)
            (-30.0, -30.0),
            (30.0, -30.0),
            (30.0, 30.0),
            (-30.0, 30.0),
        ],
        "edges": [10.0, 10.0, 10.0, 10.0],  # Per-corner rounding radii (List[float])
        "width_between": 0.0,           # 0.0 = solid hole cut-out; > 0.0 = ribbon/border cut
        "curve_mode": "line",           # "line", "smooth", "bezier"
    }
]
```

- Uses standard `"anchor"` instead of `"let_it"`.
- Geometry is represented with native typed `List[Tuple[float, float]]`.
- Edge corner radii are specified as `edges: List[float]`.

---

## 5.3 — Side Angle & 5.4 — Side Length (Topology Constraints)

```python
side_angle: Dict[int, float] = {
    0: 30.0,   # Side 0 rotated by +30.0 degrees
}

side_length: Dict[int, float] = {
    0: 50.0,   # Set Side 0 length to 50.0 units
}
```

> **Topology Rule:**
> - In **open paths (`closed=False`)**, `side_angle` and `side_length` operate via forward kinematics.
> - In **closed shapes (`closed=True`)**, arbitrarily changing an individual side length or angle breaks polygon closure. Modifying them requires explicit resolution modes or converting to `closed=False`. See `conditions_and_errors.md`.

---

## 5.5 — Side Scale

Scales an individual side's local dimension.

```python
side_scale: Dict[int, Tuple[float, float]] = {
    0: (1.0, 0.8),  # Scale side 0 by 1.0 in x and 0.8 in y
}
```

---

## 5.6 — Warp (Bounding-Box FFD Cage)

Warp is mathematically defined as a **Bounding-Box Free-Form Deformation (FFD) Cage**.

```python
warp: List[List[Tuple[float, float]]] = [
    [(0.0, 0.0), (-25.0, 25.0)],  # Row 0: [top-left offset, top-right offset]
    [(0.0, 0.0), (0.0, 0.0)],      # Row 1: [bottom-left offset, bottom-right offset]
]
```

- Operates across normalized $[0, 1] \times [0, 1]$ bounding box space.
- v1 supports a 2x2 cage using bilinear interpolation. Larger cages and bicubic interpolation are deferred until their basis and boundary rules are specified.

---

# PART 6 — Whole-Shape Edit (`edit`)

Operations that modify the completed shape geometry:

```python
edit(
    rotate=30.0,
    edges=0.5,
    remove=[0, 2],
    flip="horizontal",
    anchor="center",
    symmetry={
        "type": "radial",
        "count": 6,
    },
)
```

### Core Parameters
- `rotate`: Rotation in degrees (float, e.g. `30.0`).
- `edges`: Corner rounding radius `Union[float, List[float]]`. A float specifies uniform corner rounding; a list specifies per-vertex rounding. It is an edit-only property.
- `remove`: List of 0-based side indices to remove (e.g. `[0, 2]`). Note: removing edges from a closed shape breaks closure and automatically converts it to `closed = False`.
- `flip`: Flipping orientation (`"horizontal"`, `"vertical"`, `"both"`).
- `anchor`: Anchor point name (`"center"`, `"top-left"`, etc.) or custom `(x, y)` tuple.
- `symmetry`: Whole-shape symmetry replication (`"radial"` or `"mirror"`).

The transform pivot is always the top-level `origin`; `edit` must not redefine it. `anchor` controls placement for the operation only.

---

# PART 7 — Sub Editing & Nested Geometry (`sub_edit`)

> **Concept:** `sub_edit` moves **inside the shape** to define and position nested sub-shapes relative to the parent shape's coordinate frame and bounding box.

Nested child shapes can be defined either declaratively inside the parent's `sub_edit` parameter or by passing `parent="parent_name"` directly:

```python
# Mode A: Declarative nesting via sub_edit block
card = Draw.shape(
    name="card",
    type="rectangle",
    size=(400.0, 200.0),
    closed=True,
    z=0,
    sub_edit=Draw.sub_edit(
        shapes=[
            Draw.shape(
                name="card_header",
                type="rectangle",
                size=("100%", "40px"),   # 100% of parent width (400px), 40px height
                origin=("center", "top"),
                z=1,
            )
        ],
        clip=True,  # Clips child shapes strictly to the parent's boundary (stencil mask)
    ),
)

# Mode B: Direct creation referencing parent name
Draw.shape(
    name="card_button",
    parent="card",             # Parent shape identifier
    type="rectangle",
    size=("40%", "30px"),
    origin=("center", "bottom"),
    z=2,
    clip=True,
)
```

### Key Principles of `sub_edit`:
1. **Parent-Relative Percentage Sizing:**
   * In `sub_edit`, a size of `"100%"` resolves to the **parent shape's bounding box** ($400\text{px} \times 200\text{px}$), **NOT the full screen or root canvas**.
   * `"50%"` width resolves to $0.50 \times \text{parent.width} = 200\text{px}$.
2. **Local Coordinate Space:**
   * Coordinates and offsets inside `sub_edit` are relative to the parent's `origin` or `anchor`.
3. **Hierarchical Transform Inheritance:**
   * Rotating, scaling, or moving the parent shape (`card`) automatically transforms all inner shapes inside `sub_edit`.
4. **Boundary Clipping (`clip: bool = True`):**
   * If `clip=True`, the C++ render engine applies a stencil/scissor mask using the parent polygon so inner shapes never bleed outside the parent.
5. **Runtime Sub-Shape Access:**
   * Sub-shapes can be addressed via hierarchical dot-notation:
   ```python
   Draw.shape.update("card.card_header", size=("100%", "50px"))
   ```

### Comparison: `side_edit` vs `edit` vs `sub_edit`

| Modifier | Target | Purpose | Example |
| :--- | :--- | :--- | :--- |
| **`side_edit`** | Outer perimeter edges | Granular deformation of shape's own edges | `bend`, `warp`, `exclude`, `side_length` |
| **`edit`** | Whole shape | Global transforms & modifiers on completed geometry | `rotate`, `edges`, `flip`, `symmetry` |
| **`sub_edit`** | Inside of shape | Nested child shapes scoped to parent dimensions | Inner cards, badges, icons, clipped layers |

---

# PART 8 — Dynamic / Backend Optimization Hints

The `dynamic` list provides optimization hints to the backend cache.

```python
dynamic: List[str] = [
    "position",
    "rotation",
    "scale",
    "z",
    "geometry",
]
```

### Purpose
- `dynamic=[]`: Fully static shape. Geometry and vertex buffers are baked once and cached aggressively.
- `dynamic=["position", "rotation", "z"]`: Geometry mesh remains cached; only uniform model matrices and z-order index change.
- `dynamic=["geometry"]`: Geometry is mutable; backend prepares dynamic vertex buffer allocations.

---

# PART 9 — Line Shape

A Line is created directly using `Draw.line()`, defaulting to an open path (`closed=False`):

```python
Draw.line(
    name="connector",
    position=(0.0, 0.0),
    closed=False,
    coordinates=[
        (0.0, 0.0),
        (25.0, 50.0),
        (75.0, 20.0),
        (100.0, 80.0),
    ],
    scale=(1.0, 1.0),
    origin=(0.0, 0.0),
    z=1,
)
```

---

# PART 10 — Shape Update API

Shapes are mutable at runtime using clean keyword arguments:

```python
# 1. Via object reference:
card.update(
    size=(200.0, 100.0),
    rotate=45.0,
    z=5,
)

# 2. Or via registry name:
Draw.shape.update(
    name="card",
    size=(200.0, 100.0),
    rotate=45.0,
    z=5,
)
```

---

# PART 11 — Shape List & Query API

Inspects active shapes in the scene:

```python
# 1. Via registry name:
Draw.shape.list(
    name="card",
    data=["size", "vertices", "z", "closed"]
)

# 2. Or via object reference:
info = card.query(["size", "vertices", "z", "closed"])
```

---

# PART 12 — Shape Removal

```python
# 1. Via object reference:
card.remove() 

# 2. Via registry by name(s):
Draw.remove(["card", "button"])

# 3. Remove all registered shapes:
Draw.remove(all=True)
```

---

# PART 13 — Shape Copy API

Clones an existing shape with an explicit new name:

```python
# 1. Via registry:
Draw.copy(
    name="card",
    new_name="card_copy",
)

# 2. Or via object reference:
card_copy = card.copy(new_name="card_copy")
```

---

# PART 14 — Build Order & Implementation Stages

Implement and test each stage independently:

1. **Stage 1 — Core Shape Definition:**
    `name`, `closed: bool`, `type`, `vertices`, `coordinates`, `size`, `scale`, `origin`, `z`, and triangle generation for rectangle, triangle, and regular polygon.
2. **Stage 2 — 0-Based Indexing & Generation:**
   `top = 0` clockwise, `hitbox`, `map`.
3. **Stage 3 — Side Editing:**
    `bend`, `side_angle`, `side_length`, `side_scale`, 2x2 `warp` (FFD cage), and `exclude`.
4. **Stage 4 — Whole-Shape Editing:**
   `rotate`, `z` sorting, `edges` corner rounding, `remove`, `flip`, `symmetry`.
5. **Stage 5 — Sub Editing (`sub_edit`):**
   Parent-relative coordinate frame, percentage sizing against parent bounding box, clipping masks.
6. **Stage 6 — Curve Interpolation:**
   `line`, `smooth`, `bezier`, `quadratic`, `cubic`, `arc`.
7. **Stage 7 — Dynamic Hints & Caching:**
   Cache invalidation flags (`"position"`, `"rotation"`, `"geometry"`, `"z"`).
8. **Stage 8 — External Module Connectors:**
   Stable `shape_id` references consumed by Color, Alignment, Motion, and Visibility modules; no cross-module parameters in `Draw.shape`.
9. **Stage 9 — Release Pipeline (Zero Dependencies):**
    `to_dict()` export, `encode_transfer()` DGF packing, and `publish()` shared-memory handles.
10. **Stage 10 — Runtime Management:**
    `update()`, `list()`, `copy()`, `remove()`.

---
# PART 15 — Batch Shapes & Collection Management (`Draw.shapes`)

## 15.1 Batch Definition & Grouping Syntax

`Draw.shapes` serves two primary functions:
1. **Batch Constructor / Grouping Container**: Grouping multiple shapes together into a unified collection with collective transform and depth controls.
2. **Scene Registry Namespace**: Querying, updating, filtering, and removing registered shapes across the entire scene.

```python
import Draw

# Batch register multiple shapes with collective group attributes
deck = Draw.shapes(
    items=[
        Draw.shape(
            name="card_bg",
            type="rectangle",
            size=(120.0, 180.0),
            closed=True,
            z=0,
        ),
        Draw.shape(
            name="card_border",
            type="rectangle",
            size=(116.0, 176.0),
            closed=True,
            z=1,
        ),
    ],
    name="card_group",
    position=(50.0, 100.0),
    rotation=0.0,
    scale=(1.0, 1.0),
    origin=(0.0, 0.0),
    z_offset=10,
    tags=["cards", "ui"],
    dynamic=["position"],
)
```

## 15.2 Core Parameters

```python
Draw.shapes(
    items: Sequence[Shape],
    name: Optional[str] = None,
    position: Tuple[Union[float, str], Union[float, str]] = (0.0, 0.0),
    scale: Tuple[float, float] = (1.0, 1.0),
    rotation: float = 0.0,
    origin: Tuple[float, float] = (0.0, 0.0),
    z_offset: int = 0,
    tags: Optional[Sequence[str]] = None,
    dynamic: Optional[Sequence[str]] = None,
) -> ShapeGroup
```

### Parameter Breakdown

* **`items: Sequence[Shape]`** (Required)  
  Ordered collection of `Shape` instances to group and register.

* **`name: Optional[str]`** (Default: `None`)  
  Unique identifier for the shape group. Allows group-level lookups, transforms, and bulk lifecycle management (`"card_group"`).

* **`position: Tuple[Union[float, str], Union[float, str]]`** (Default: `(0.0, 0.0)`)  
  World/canvas placement offset `(x, y)` applied to every member shape in the collection. Supports unit and percentage resolution (`("20%", 100.0)`).

* **`scale: Tuple[float, float]`** (Default: `(1.0, 1.0)`)  
  Uniform or non-uniform scaling multiplier applied collectively across all items around the group `origin`.

* **`rotation: float`** (Default: `0.0`)  
  Collective rotation angle in degrees clockwise around the group `origin`.

* **`origin: Tuple[float, float]`** (Default: `(0.0, 0.0)`)  
  Group pivot anchor for collective rotations and scaling.

* **`z_offset: int`** (Default: `0`)  
  Base integer offset added to the individual `z` values of all member shapes, maintaining relative internal draw order while adjusting global depth.

* **`tags: Optional[Sequence[str]]`** (Default: `None`)  
  Metadata labels for semantic filtering, bulk queries, and category-wide updates (e.g. `["ui", "hud", "interactive"]`).

* **`dynamic: Optional[Sequence[str]]`** (Default: `None`)  
  Optimization and buffer allocation hints shared across the group (e.g. `["position", "transform"]`).

---

## 15.3 Registry Operations via `Draw.shapes`

As defined in the output specification, `Draw.shapes` acts as the canonical registry interface:

```python
# 1. Lookup shape by unique name
card = Draw.shapes.get("card")

# 2. Check existence in scene
if Draw.shapes.exists("card"):
    print("Shape is active")

# 3. Batch query shape properties
data = Draw.shapes.list(
    names=["card_bg", "card_border"],
    data=["position", "size", "z"]
)

# 4. Filter shapes by tag
ui_elements = Draw.shapes.find_by_tag("ui")

# 5. Bulk transform / update
Draw.shapes.update(
    names=["card_bg", "card_border"],
    position=(100.0, 200.0),
    scale=(1.2, 1.2),
)

# 6. Bulk removal
Draw.shapes.remove(["card_bg", "card_border"])
```

---

## 15.4 Batch Performance Benefits

1. **Atomic Registration**: All items are registered in a single scene graph pass, avoiding repeated lock acquisition in multi-threaded workflows.
2. **Unified Bounding Box**: The collection automatically calculates an aggregate bounding box for spatial culling and collision passes.
3. **Optimized Transfer Packing**: Groups can serialize contiguous geometry data in a single DGF packet rather than multiple disaggregated IPC transfers.

---

## 15.5 Context Management & Scoped Lifecycles

To prevent scene registry leaks in temporary scenes, menus, or HUD dialogs, `Draw.shapes` supports Python context manager protocol (`with` blocks):

```python
# Shapes declared within this scope are automatically tracked in a local group
with Draw.shapes(name="pause_menu", position=(200.0, 150.0), z_offset=100) as menu:
    Draw.shape(name="menu_bg", type="rectangle", size=(300.0, 400.0))
    Draw.shape(name="resume_btn", type="rectangle", size=(200.0, 50.0), position=(0.0, 60.0))
    Draw.shape(name="exit_btn", type="rectangle", size=(200.0, 50.0), position=(0.0, -60.0))

# All member shapes can be transformed, hidden, or cleanly removed together:
menu.update(scale=(1.1, 1.1))
menu.remove()  # Atomically unregisters "menu_bg", "resume_btn", and "exit_btn"
```

### Registry Lifecycle & Memory Model

1. **Strong Scene Registry (Default)**: By default, `Draw.shape()` creates an authoritative strong reference in the internal scene table. Calling `Draw.remove(["card"])` or `card.remove()` explicitly releases the shape and purges its vertex caches.
2. **WeakRef Scoped Mode (`scoped=True`)**: When `scoped=True` is passed to `Draw.shape(...)`, the registry only retains a `weakref` to the instance. The moment the local Python variable (e.g. `card`) goes out of scope or is deleted, the shape automatically deregisters from the scene and frees GPU/shared-memory allocations. 

---

# PART 16 — Final Architecture

```text
                         Draw
                          │
            ┌─────────────┴─────────────┐
            ↓                           ↓
      Draw.shape(...) / shapes      Draw.line(...)
            │                           │
            └─────────────┬─────────────┘
                          │
                     Shape Object
                          │
         ┌────────────────┼────────────────┐
         │                │                │
     Geometry         Topology        Connections
         │                │                │
    type/vertices    closed: bool        Color (API reference)
    coordinate        (True/False)       z (overlap / promotion)
    size / scale                           │
    origin (pivot)                         │
         │                                 │
         ↓                                 │
    Side Editing                           │
   (0-based index)                         │
   (bend, exclude,                         │
    FFD cage warp)                         │
         │                                 │
         ↓                                 │
    Whole Edit                             │
   (rotate, flip,                          │
    edges, symmetry)                       │
         │                                 │
         ↓                                 │
    Sub Editing (sub_edit)                 │
   (inner shapes,                          │
    parent-relative %)                     │
         │                                 │
         ↓                                 │
   Dynamic Hints                           │
         │                                 │
         ↓                                 │
    Release Layer (Pure Python / stdlib)   │
         │                                 │
    ┌────┴────┐                            │
    │         │                            │
 release() release_raw()                   │
 (flat lists) (array/ctypes)               │
    │         │                            │
    └────┬────┘                            │
         ↓                                 ↓
    Contiguous Geometry Data + Overlap Priority (z)
         ↓
    C++ Render Engine (OpenGL / Shaders)
```
