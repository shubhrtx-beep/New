# Draw3 Maths Module — Universal Unit Conversion Architecture

## 1. Overview
The `Draw.maths` subsystem is the single, centralised unit and metric resolution engine across all Draw3 modules:
- **Shape**: Pure numeric or string units (`px`, `%`, `cm`, `mm`, `in`, `pt`, `vw`, `vh`) for position, size, origin, and corner rounding. Declarative `sub_edit` nesting computes all relative dimensions against the parent.
- **Window**: Frame sizes, elements, layout placement, margins, and `ratio` dicts allowing fractional ratios (`0.05`, `0.95`), percentage strings (`"5%"`, `"95%"`), or physical/pixel units (`"40px"`, `"2cm"`). Window regions also serve as parent scopes for shapes.
- **Color**: Gradient stop offsets (`0.5`, `"50%"`).
- **Motion**: Animation channels (`translate`, `size`, `edges`) supporting numeric and unit tuples.

---

## 2. Directory Structure
```text
d:\draw3\Draw\maths\
├── __init__.py      # Package exports (resolve, resolve_size, resolve_ratio, set_canvas_size, etc.)
├── errors.py        # Exception hierarchy (DrawMathsError, InvalidUnitError, etc.)
└── units.py         # Universal Unit Resolver implementation
```

---

## 3. Supported Units and Conversion Factors

### Absolute Physical Units (at DPI standard, default 96.0):
| Suffix | Description | Formula to Pixels | At DPI=96 |
|---|---|---|---|
| `px` | Pixels | $\text{val} \times 1.0$ | $1.0\text{ px}$ |
| `in` | Inches | $\text{val} \times \text{DPI}$ | $96.0\text{ px}$ |
| `pt` | Points | $\text{val} \times \frac{\text{DPI}}{72.0}$ | $\approx 1.333\text{ px}$ |
| `cm` | Centimetres | $\text{val} \times \frac{\text{DPI}}{2.54}$ | $\approx 37.795\text{ px}$ |
| `mm` | Millimetres | $\text{val} \times \frac{\text{DPI}}{25.4}$ | $\approx 3.7795\text{ px}$ |

### Relative Units:
| Suffix | Description | Reference Context |
|---|---|---|
| `%` | Percentage | Resolved against parent/container dimension: $\frac{\text{pct}}{100.0} \times \text{reference}$ |
| `vw` | Viewport width | Resolved against canvas width: $\frac{\text{pct}}{100.0} \times \text{canvas\_w}$ |
| `vh` | Viewport height | Resolved against canvas height: $\frac{\text{pct}}{100.0} \times \text{canvas\_h}$ |

---

## 4. Key Subsystem Integrations

### 4.1 Window Ratio & Region Parent Scopes
In window frame creation:
```python
window.create(
    name="main",
    frame=window.custom(
        size=(1400, 850),
        ratio={"top_bar": 0.05, "main_display": 0.95},
    )
)
```
- `top_bar` gets height $0.05 \times 850 = 42.5\text{px}$.
- `main_display` gets height $0.95 \times 850 = 807.5\text{px}$.
- Mixed units are fully supported, e.g. `{"top_bar": "40px", "main_display": 0.95}` or `{"top_bar": "2cm", "main_display": "95%"}`.
- Any shape with `parent="main_display"` automatically inherits `(1400.0, 807.5)` as its parent reference dimensions.

### 4.2 Declarative Shape Sub-Edit Nesting (Parent Reference)
```python
card = Draw.shape(
    name="card",
    type="rectangle",
    size=(400.0, 200.0),
    sub_edit=Draw.sub_edit(
        shapes=[
            Draw.shape(
                name="card_header",
                type="rectangle",
                size=("100%", "40px"),
            )
        ]
    )
)
```
- `card_header` resolves `100%` against parent width ($400.0\text{px} \to 400.0$) and `40px` height ($40.0$).
- All calculations derive strictly from the parent shape or parent window region.
