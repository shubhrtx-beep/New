# Draw3 Color Subsystem — Working Data Architecture & Implementation Guide

## 1. System Overview

This document records the exact architecture, data structures, math algorithms, and design choices used to build the **Python Working Data Structure** for the Draw3 Color API (`d:\draw3\Draw\color\`).

The implementation strictly fulfills:
1. **Working Data Structure Only**: Editable, Python-native source of truth for visual styling, colors, gradients, and procedural animations.
2. **Zero External C / Binary Dependencies**: Uses pure Python standard library types (`float`, `int`, `list`, `tuple`, `dict`) and standard packages (`math`, `re`, `weakref`, `typing`).
3. **Deterministic Backend Serialization**: Produces JSON-compatible transfer packets matching `expected_output` and `color.md` for seamless C++ rendering engine integration without Python runtime execution.

---

## 2. Directory & Module Structure

```text
d:\draw3\
├── Draw\
│   ├── __init__.py           # Root entry point: exposes shape, shapes, line, color, palette
│   └── color\
│       ├── __init__.py       # Color subsystem exports & ColorAPI callable namespace
│       ├── errors.py         # Complete custom exception hierarchy
│       ├── color_value.py    # ColorValue model, color.rgb, rgba, hsv, hex, CSS lookup, normalization
│       ├── channels.py       # Visual channels: ColorBody, ColorBorder, ColorShadow, ColorGlow, ColorFilter
│       ├── gradient.py       # ColorGradient: linear, radial, conical, normalized stops & spread
│       ├── motion.py         # Semantic drivers (cycle, pulse, oscillate), keyframes, AST ExpressionNode & time
│       ├── harmonies.py      # Color theory: complement, analogous, triadic, monochromatic, mix, with_alpha
│       ├── binding.py        # ColorBinding working data model, dirty version tracking, to_dict() contract
│       ├── palette.py        # Palette design tokens & theme engine (Draw.palette, Draw.color.theme, use_theme)
│       └── registry.py       # Scene ColorRegistry, weakref/strong lifecycles, and ColorAPI callable namespace
└── test\
    ├── test_shape_module.py  # Full shape subsystem test suite
    └── test_color_module.py  # Full color subsystem test suite (25 tests, 100% GREEN)
```

---

## 3. Key Classes, Methods & Implementation Mechanics

### 3.1 `ColorValue` & Constructors (`color_value.py`)
* **Role**: Canonical representation of a single color value in RGBA or dynamic HSV/RGB space.
* **Constructors**:
  - `color.rgb(r, g, b, a=1.0)`: Accepts integer `0..255` or float `0.0..1.0`. Strict boundary validation.
  - `color.rgba(r, g, b, a=1.0)`: Alias for explicit alpha.
  - `color.hsv(h, s, v, a=1.0)`: Hue in degrees `[0, 360)`, Saturation in `[0, 100]`, Value in `[0, 100]`.
  - `color.hex("#...")`: Parses `#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA`.
* **Dynamic Awareness**:
  - If any channel (e.g. `h` in `color.hsv`) is an instance of `MotionDriver` or `ExpressionNode`, `ColorValue.is_dynamic` returns `True`.
  - In static mode, converts HSV $\to$ RGBA via standard conversion equations.
  - In dynamic mode, serializes as structured descriptor `{"type": "hsv", "h": {...}, "s": 90.0, "v": 100.0, "a": 1.0}`.

### 3.2 Visual Channels (`channels.py`)
* `ColorBody(fill, opacity=1.0, blend="normal", filters=[])`
* `ColorBorder(fill, width=1.0, style="solid", opacity=1.0, blend="normal")`
* `ColorShadow(fill, blur=16.0, spread=0.0, offset=(0.0, 4.0), opacity=0.5, inner=False)`
* `ColorGlow(fill, blur=24.0, spread=0.0, opacity=0.8)`
* `ColorFilter(name, amount=1.0)`

### 3.3 Gradients (`gradient.py`)
* Supports `type` in `{"linear", "radial", "conical"}`.
* Normalizes percentage stops (`"0%"`, `"50%"`, `"100%"`) and numeric floats (`0.0..1.0`).
* Sorts stops automatically by ascending offset.
* Supports `spread` in `{"pad", "repeat", "reflect"}`.

### 3.4 Motion Drivers & Expression AST (`motion.py`)
* **Semantic Drivers**:
  - `color.cycle(speed, offset, repeat, yoyo, delay, enabled, fallback)`
  - `color.pulse(min_val, max_val, speed, easing, repeat, yoyo, delay, enabled, fallback)`
  - `color.oscillate(from_val, to_val, duration, easing, repeat, yoyo, delay, enabled, fallback)`
  - `color.keyframes(property, frames, easing, repeat, yoyo)`
  - `color.transition(duration, easing, delay)`
* **Expression AST**:
  - `color.time` represents the global animation clock in seconds.
  - Overloads standard Python operators: `+`, `-`, `*`, `/`, `//`, `%`, `**`, unary `-`, and `abs()`.
  - Factory helpers: `sin()`, `cos()`, `clamp()`, `lerp()`, `map_range()`.
  - Evaluates to structured JSON trees for C++ worker threads without Python `eval()`.

### 3.5 `ColorBinding` (`binding.py`)
* **Authoritative Style Container**:
  - Fields: `name`, `body`, `border`, `shadow`, `glow`, `scoped`, `metadata`.
  - Dirty version tracking: `versions = {"body": 1, "border": 1, "shadow": 1, "glow": 1, "metadata": 1}`.
  - `@property dynamic`: Evaluates `True` if any attached channel is dynamic.
  - Serialization: Outputs authoritative transfer schema:
    ```json
    {
      "schema": "draw.color",
      "version": 1,
      "name": "...",
      "dynamic": false,
      "channels": {
        "body": { ... },
        "border": { ... },
        "shadow": null,
        "glow": null
      },
      "metadata": null
    }
    ```

### 3.6 Color Registry & Lifecycles (`registry.py`)
* **Dual Namespace (`ColorAPI`)**:
  - Callable constructor: `Draw.color(name="...", body=...)`.
  - Registry manager: `Draw.color.update()`, `Draw.color.get()`, `Draw.color.exists()`, `Draw.color.list()`, `Draw.color.copy()`, `Draw.color.remove()`, `Draw.color.clear()`.
* **Weakref Scoped Mode (`scoped=True`)**:
  - Uses `weakref.ref` with cleanup callback. Automatically removed from registry once local reference goes out of scope.
* **Inline Sentinel (`IN_SHAPE = "$__in_shape__"`)**:
  - Unnamed inline styles remain unattached until `Draw.shape()` receives them, preventing global name collisions.

### 3.7 Palette & Themes (`palette.py`)
* Centralized token store: `Draw.palette(primary="#3b82f6", surface="#1e293b")`.
* Property access syntax: `palette.primary`.
* Cyclic dependency detection: Aliased tokens `@token` raise `ColorTokenCycleError` if a loop occurs.
* Themes: `Draw.color.theme(name="dark", tokens={...})` and `Draw.color.use_theme("dark")`.

### 3.8 Shape Integration (`Draw.shape(..., color=...)`)
* Accepts:
  1. Registered theme name: `color="card_theme"`.
  2. Inline style binding: `color=Draw.color(...)`.
  3. Shorthand hex/CSS/tuple: `color="#ff0000"`, automatically wrapped into `ColorBinding` with default body fill.
