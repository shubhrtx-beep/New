# Draw Shape API — Units, Standards & Predefined Defaults (`other.md`)

## Purpose

This document specifies:
1. The **Unit Conversion System** (resolving `"50%"`, `"500px"`, etc. across canvas, parent, and local scopes).
2. The **Predefined Geometry Defaults and Fallback Values** (dimensions and topology only).

---

# SECTION 1 — Unit Conversion System

## Architecture: Pure Number Pass-Through

> **The Performance Principle:**
> String-based unit conversion happens **strictly at the Python API boundary during shape definition or update**.
> All strings (`"50%"`, `"300px"`) are resolved into native `float` values before sending to the C++ Render Engine (`d:\draw3\rander_engin\c++files\`).
> The C++ OpenGL renderer receives **pure, contiguous 32-bit floats** (`float32`), ensuring zero string parsing latency and maximum rendering throughput.

---

## 1. Supported Units

| Unit Format | Example | Resolution Logic | Output Stored in Shape |
| :--- | :--- | :--- | :--- |
| **Raw Numeric** | `100`, `50.0` | Direct local units (zero parsing overhead) | `float` (e.g. `50.0`) |
| **Pixels (`px`)** | `"500px"`, `"35.5px"` | Strips `"px"` suffix and casts directly to float | `float` (e.g. `500.0`) |
| **Percentage (`%`)** | `"100%"`, `"50%"` | Scaled relative to the active reference scope (see below) | `float` (e.g. `0.5 * reference`) |

---

## 2. Percentage Scopes & Reference Bounds

When a percentage (`"%"`) is specified, it resolves relative to its active context:

### Scope A: Top-Level Shapes (Canvas Scope)
For shapes defined directly at the root `Draw` level:
* **Width (`size[0]`):** `"50%"` resolves against the total **canvas width**:
  $$\text{resolved\_width} = 0.50 \times \text{canvas.width}$$
* **Height (`size[1]`):** `"50%"` resolves against the total **canvas height**:
  $$\text{resolved\_height} = 0.50 \times \text{canvas.height}$$

### Scope B: Nested Shapes inside `sub_edit` (Parent Scope)
For sub-shapes created inside a parent shape's `sub_edit` block:
* **Width (`size[0]`):** `"100%"` resolves against the **parent shape's bounding box width**:
  $$\text{resolved\_width} = 1.00 \times \text{parent.size.width}$$
* **Height (`size[1]`):** `"50%"` resolves against the **parent shape's bounding box height**:
  $$\text{resolved\_height} = 0.50 \times \text{parent.size.height}$$
* **Example:**
  ```python
  # Parent card is 400px x 200px
  card = Draw.shape(name="card", size=(400, 200), sub_edit=sub_edit(
      shapes=[
          # This inner header resolves to 400px x 40px (100% of parent, NOT full canvas!)
          Draw.shape(name="header", size=("100%", "40px"))
      ]
  ))
  ```

### Scope C: Edge & Side Editing (Local Edge Scope)
* **`bend.offset = "20%"`:**
  Resolves against the length of the specific edge being bent:
  $$\text{offset} = 0.20 \times \text{length}(\text{side}_i)$$

### Scope D: Corner Rounding (`edges = "100%"` vs `"50%"`)
* Corner rounding percentage resolves against the maximum allowable corner radius $r_{\max} = \frac{\min(\text{width}, \text{height})}{2}$:
  $$r = \left(\frac{\text{percentage}}{100}\right) \times \frac{\min(\text{width}, \text{height})}{2}$$
* Therefore:
  * `"100%"` produces maximum rounding, forming a fully rounded pill or circle:
    $$r = 1.00 \times \frac{\min(\text{width}, \text{height})}{2} = 0.50 \times \min(\text{width}, \text{height})$$
  * `"50%"` produces half of the maximum allowable radius:
    $$r = 0.50 \times \frac{\min(\text{width}, \text{height})}{2} = 0.25 \times \min(\text{width}, \text{height})$$

---

## 3. Python `UnitResolver` Reference Implementation

```python
from typing import Union, Tuple

class UnitResolver:
    @staticmethod
    def to_float(val: Union[float, int, str], reference: float = 1.0) -> float:
        """Resolves raw numbers, 'px', or '%' against a reference metric."""
        if isinstance(val, (int, float)):
            return float(val)
        
        cleaned = str(val).strip().lower()
        try:
            if cleaned.endswith("px"):
                return float(cleaned[:-2].strip())
            elif cleaned.endswith("%"):
                pct = float(cleaned[:-1].strip()) / 100.0
                return pct * reference
            else:
                return float(cleaned)
        except (ValueError, TypeError) as err:
            raise ValueError(f"Invalid unit or coordinate value '{val}': cannot resolve to float.") from err

    @classmethod
    def resolve_size(
        cls, 
        size: Tuple[Union[float, str], Union[float, str]], 
        ref_width: float, 
        ref_height: float
    ) -> Tuple[float, float]:
        """Resolves (width, height) tuple with mixed unit types."""
        return (
            cls.to_float(size[0], ref_width),
            cls.to_float(size[1], ref_height),
        )

    @classmethod
    def resolve_position(
        cls, 
        pos: Tuple[Union[float, str], Union[float, str]], 
        ref_width: float, 
        ref_height: float
    ) -> Tuple[float, float]:
        """Resolves (x, y) position tuple with mixed unit types (e.g. ('50%', '50%'))."""
        return (
            cls.to_float(pos[0], ref_width),
            cls.to_float(pos[1], ref_height),
        )
```

---

# SECTION 2 — Predefined Defaults & System Fallbacks

When properties are omitted by the user during shape definition, the Shape API applies these deterministic system defaults.

---

## 1. Non-Geometry Module Boundary

Shape has no colour, fill, stroke, opacity, visibility, alignment, or motion defaults. Those values and their fallbacks are owned by their respective modules. Shape only supplies stable geometry and `shape_id` for the scene layer to join with external component data.

---

## 2. Default Geometric Properties

| Property | Default Value | Description |
| :--- | :--- | :--- |
| **`position`** | `(0.0, 0.0)` | Default position in world/parent coordinate space. |
| **`size`** | `(100.0, 100.0)` | Default base bounding size if omitted on primitive types (`type="rectangle"`). |
| **`scale`** | `(1.0, 1.0)` | Default scaling factor (neutral / 100% scale). |
| **`origin`** | `(0.0, 0.0)` | Default transform origin / pivot anchor. |
| **`z`** | `0` | Default overlap / draw priority layer. |
| **`edit.edges`** | `0.0` | Default corner rounding (sharp corners). This is not a top-level shape property. |

---

## 3. Default Topology (`closed`)

* **`Draw.shape(...)`:** Defaults to **`closed = True`** (closed 2D planar polygon boundary).
* **`Draw.line(...)`:** Defaults to **`closed = False`** (open polyline / path).

---

## 4. Default Dynamic / Optimization Caching

* **`dynamic: List[str] = []`** (Empty list by default).
* **Behavior:** By default, shapes are treated as **static geometry**.
* The C++ Render Engine generates and bakes vertex buffers (VBO / EBO) into GPU memory once and aggressively caches them.

---

## 5. Default Curve Resolution (Tessellation)

When curves (`smooth`, `bezier`, `arc`, or `bend`) are generated:
* **Segments per Curve:** Default is `16` linear segments per curved span.
* Higher fidelity can be set globally or per shape: `curve_segments = 32`.

---

## 6. Default Coordinate Space Convention

* **Orientation:** Standard 2D screen coordinate convention:
  * Origin `(0.0, 0.0)` is the local transform pivot.
  * $+X$ extends to the **right**.
  * $+Y$ extends **upward** in stored local geometry. The renderer may apply a Y-flip when projecting to screen space; that projection must not change API or mesh-winding semantics.
* **Regular Polygons (`vertices = N`):**
  * Vertex $0$ is positioned at **top center** $(x = 0, y = r)$.
  * Subsequent vertices follow clockwise in screen space after the renderer projection; the stored winding is recorded with the mesh.
