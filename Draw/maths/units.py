"""Draw Maths Module — Universal Unit Conversion System.

Provides a single, centralised unit resolver used by **every** Draw3
subsystem (Shape, Color, Window, Motion).  All string-unit parsing,
physical-unit conversion, percentage/ratio resolution, and canvas-scope
management lives here — no other module should duplicate this logic.

Supported unit suffixes
-----------------------
Absolute (resolve to pixels at the current DPI):
    px   — pixels (identity, 1 px = 1 px)
    pt   — points (1 pt = DPI / 72 px)
    in   — inches (1 in = DPI px)
    cm   — centimetres (1 cm = DPI / 2.54 px)
    mm   — millimetres (1 mm = DPI / 25.4 px)

Relative (require a reference dimension):
    %    — percentage of the reference  (50% × ref → 0.5 × ref)
    vw   — percentage of canvas width   (50vw → 0.5 × canvas_w)
    vh   — percentage of canvas height  (50vh → 0.5 × canvas_h)

Ratio (fractional 0.0–1.0, multiplied by reference):
    raw float between 0 and 1 used in ``ratio={}`` dicts

Bare numbers (int / float) are treated as **pixels**.
"""

from typing import Union, Tuple, List, Dict, Optional
from .errors import (
    InvalidUnitError,
    InvalidUnitValueError,
    MissingReferenceError,
    InvalidRatioError,
)


# ───────────────────────────────────────────────────────────────
# Global defaults
# ───────────────────────────────────────────────────────────────
_CANVAS_SIZE: Tuple[float, float] = (1920.0, 1080.0)
_DPI: float = 96.0  # Default screen DPI (Windows / web standard)

# Absolute unit conversion factors (unit → pixels) at DPI=96
# Recomputed whenever _DPI changes.
_UNIT_FACTORS: Dict[str, float] = {}


def _recompute_factors() -> None:
    """Recomputes absolute-unit → pixel factors for the current DPI."""
    global _UNIT_FACTORS
    _UNIT_FACTORS = {
        "px": 1.0,
        "pt": _DPI / 72.0,
        "in": _DPI,
        "cm": _DPI / 2.54,
        "mm": _DPI / 25.4,
    }

_recompute_factors()


# ───────────────────────────────────────────────────────────────
# Canvas & DPI configuration
# ───────────────────────────────────────────────────────────────

def set_canvas_size(width: float, height: float) -> None:
    """Sets the global canvas reference dimensions for vw / vh / root-% units."""
    global _CANVAS_SIZE
    if width <= 0.0 or height <= 0.0:
        raise ValueError(f"Canvas dimensions must be positive, got ({width}, {height})")
    _CANVAS_SIZE = (float(width), float(height))


def get_canvas_size() -> Tuple[float, float]:
    """Returns the current global canvas reference dimensions (width, height)."""
    return _CANVAS_SIZE


def set_dpi(dpi: float) -> None:
    """Sets the global DPI used by physical units (pt, in, cm, mm)."""
    global _DPI
    if dpi <= 0.0:
        raise ValueError(f"DPI must be positive, got {dpi}")
    _DPI = float(dpi)
    _recompute_factors()


def get_dpi() -> float:
    """Returns the current global DPI value."""
    return _DPI


# ───────────────────────────────────────────────────────────────
# Core resolver
# ───────────────────────────────────────────────────────────────

def _validate_finite(val: float, source: object) -> float:
    """Guards against NaN / ±Inf."""
    if val != val or val == float("inf") or val == float("-inf"):
        raise InvalidUnitValueError(
            f"Resolved value cannot be NaN or Infinite (from '{source}')"
        )
    return val


def resolve(
    value: Union[float, int, str],
    reference: Optional[float] = None,
    axis: Optional[str] = None,
) -> float:
    """Universal scalar unit resolver.

    Parameters
    ----------
    value : float | int | str
        The raw value to resolve.  Can be a bare number, or a string
        with a unit suffix (``"100px"``, ``"50%"``, ``"2.5cm"``, ``"10vw"``).
    reference : float, optional
        The parent / container dimension that ``%`` resolves against.
        Required when value contains ``%``.
    axis : str, optional
        ``"x"`` or ``"y"`` — used by ``vw`` / ``vh`` to pick the right
        canvas dimension.  If omitted and vw/vh is encountered, ``"x"``
        is assumed for ``vw`` and ``"y"`` for ``vh``.

    Returns
    -------
    float
        Resolved value in **pixels**.
    """
    # ── Fast path: bare numbers ──
    if isinstance(value, (int, float)):
        return _validate_finite(float(value), value)

    # ── String parsing ──
    if not isinstance(value, str):
        try:
            return _validate_finite(float(value), value)
        except (ValueError, TypeError) as err:
            raise InvalidUnitValueError(f"Cannot convert {type(value).__name__} to a unit value: {value!r}") from err

    cleaned = value.strip()
    if not cleaned:
        raise InvalidUnitValueError("Empty string is not a valid unit value.")

    low = cleaned.lower()

    # Relative: percentage
    if low.endswith("%"):
        if reference is None:
            raise MissingReferenceError(
                f"Percentage unit '{value}' requires a reference dimension, but none was provided."
            )
        try:
            pct = float(low[:-1].strip()) / 100.0
        except ValueError as err:
            raise InvalidUnitValueError(f"Invalid percentage value: '{value}'") from err
        return _validate_finite(pct * reference, value)

    # Viewport units
    if low.endswith("vw"):
        try:
            num = float(low[:-2].strip()) / 100.0
        except ValueError as err:
            raise InvalidUnitValueError(f"Invalid vw value: '{value}'") from err
        return _validate_finite(num * _CANVAS_SIZE[0], value)

    if low.endswith("vh"):
        try:
            num = float(low[:-2].strip()) / 100.0
        except ValueError as err:
            raise InvalidUnitValueError(f"Invalid vh value: '{value}'") from err
        return _validate_finite(num * _CANVAS_SIZE[1], value)

    # Absolute physical units (longest suffix first to avoid 'mm' matching 'm' + 'm')
    for suffix in ("mm", "cm", "in", "px", "pt"):
        if low.endswith(suffix):
            try:
                num = float(low[:-len(suffix)].strip())
            except ValueError as err:
                raise InvalidUnitValueError(f"Invalid {suffix} value: '{value}'") from err
            return _validate_finite(num * _UNIT_FACTORS[suffix], value)

    # Bare numeric string
    try:
        return _validate_finite(float(cleaned), value)
    except ValueError as err:
        raise InvalidUnitError(
            f"Unrecognised unit in '{value}'. "
            f"Supported: px, pt, in, cm, mm, %, vw, vh"
        ) from err


# ───────────────────────────────────────────────────────────────
# Convenience resolvers for 2D tuples
# ───────────────────────────────────────────────────────────────

def resolve_size(
    size: Tuple[Union[float, int, str], Union[float, int, str]],
    ref_width: Optional[float] = None,
    ref_height: Optional[float] = None,
) -> Tuple[float, float]:
    """Resolves a ``(width, height)`` tuple with mixed unit types."""
    if not isinstance(size, (tuple, list)) or len(size) != 2:
        raise InvalidUnitValueError(f"Size must be a 2-tuple (width, height), got {size}")
    return (
        resolve(size[0], reference=ref_width, axis="x"),
        resolve(size[1], reference=ref_height, axis="y"),
    )


def resolve_position(
    pos: Tuple[Union[float, int, str], Union[float, int, str]],
    ref_width: Optional[float] = None,
    ref_height: Optional[float] = None,
) -> Tuple[float, float]:
    """Resolves an ``(x, y)`` position tuple with mixed unit types."""
    if not isinstance(pos, (tuple, list)) or len(pos) != 2:
        raise InvalidUnitValueError(f"Position must be a 2-tuple (x, y), got {pos}")
    return (
        resolve(pos[0], reference=ref_width, axis="x"),
        resolve(pos[1], reference=ref_height, axis="y"),
    )


def resolve_origin(
    origin: Union[Tuple[Union[float, int, str], Union[float, int, str]], str],
    width: float,
    height: float,
) -> Tuple[float, float]:
    """Resolves named anchors or numeric / unit coordinates into local origin
    offsets.  Local coordinates have (0, 0) at the geometric center.

    Supported anchor names: center, top, bottom, left, right,
    top-left, top-right, bottom-left, bottom-right.
    """
    if isinstance(origin, (tuple, list)) and len(origin) == 2:
        return (
            resolve(origin[0], reference=width, axis="x"),
            resolve(origin[1], reference=height, axis="y"),
        )

    if isinstance(origin, str):
        anchor = origin.strip().lower().replace("_", "-")
        half_w = width / 2.0
        half_h = height / 2.0
        anchor_map = {
            "center": (0.0, 0.0),
            "top": (0.0, half_h),
            "bottom": (0.0, -half_h),
            "left": (-half_w, 0.0),
            "right": (half_w, 0.0),
            "top-left": (-half_w, half_h),
            "top-right": (half_w, half_h),
            "bottom-left": (-half_w, -half_h),
            "bottom-right": (half_w, -half_h),
        }
        if anchor in anchor_map:
            return anchor_map[anchor]

    return (0.0, 0.0)


def resolve_corner_radius(
    edges: Union[float, int, str, List[Union[float, int, str]]],
    min_dimension: float,
    vertex_count: int = 4,
) -> List[float]:
    """Resolves corner-rounding radii.

    ``%`` resolves against ``r_max = min_dimension / 2``:
    - ``"100%"`` → full pill/circle
    - ``"50%"``  → half-maximum rounding
    """
    r_max = max(0.0, min_dimension / 2.0)

    def _one(val: Union[float, int, str]) -> float:
        r = resolve(val, reference=r_max)
        return max(0.0, min(r, r_max))

    if isinstance(edges, (list, tuple)):
        return [_one(e) for e in edges]
    else:
        r = _one(edges)
        return [r] * vertex_count


# ───────────────────────────────────────────────────────────────
# Ratio helpers
# ───────────────────────────────────────────────────────────────
_RATIO_TOLERANCE = 1e-6


def _parse_ratio_value(val: Any) -> Tuple[str, float]:
    """Parses a single ratio dictionary value into ('ratio'|'pct'|'fixed', magnitude)."""
    if isinstance(val, (int, float)):
        f_val = float(val)
        if f_val < 0.0:
            raise InvalidRatioError(f"Ratio value cannot be negative, got {val}")
        if f_val <= 1.0:
            return ("ratio", f_val)
        else:
            return ("fixed", f_val)

    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned.endswith("%"):
            pct = float(cleaned[:-1].strip()) / 100.0
            if pct < 0.0:
                raise InvalidRatioError(f"Percentage cannot be negative, got {val}")
            return ("pct", pct)
        for sfx in ("mm", "cm", "in", "px", "pt"):
            if cleaned.endswith(sfx):
                px = resolve(val)
                if px < 0.0:
                    raise InvalidRatioError(f"Dimension cannot be negative, got {val}")
                return ("fixed", px)
        # Try bare number in string
        f_val = float(cleaned)
        if f_val < 0.0:
            raise InvalidRatioError(f"Ratio value cannot be negative, got {val}")
        if f_val <= 1.0:
            return ("ratio", f_val)
        return ("fixed", f_val)

    raise InvalidRatioError(f"Invalid ratio value type {type(val).__name__}: {val}")


def validate_ratios(
    ratio: Dict[str, Any],
    total_dimension: Optional[float] = None,
) -> None:
    """Validates that ratio definitions are well-formed and sum properly.

    Supports:
    * Standard fractional ratios (e.g. 0.05, 0.95 summing to 1.0)
    * Percentage strings (e.g. "5%", "95%" summing to 100%)
    * Absolute pixel / physical units (e.g. "40px", "2cm") mixed with ratios.
    """
    if not ratio:
        return

    parsed: Dict[str, Tuple[str, float]] = {}
    for name, value in ratio.items():
        try:
            parsed[name] = _parse_ratio_value(value)
        except (ValueError, TypeError, DrawMathsError) as err:
            raise InvalidRatioError(
                f"Invalid ratio for region '{name}'.\n\nReceived: {value}\nError: {err}"
            ) from err

    # Check if all entries are ratio / percentage
    all_fractional = all(kind in ("ratio", "pct") for kind, _ in parsed.values())
    if all_fractional:
        total = sum(mag for _, mag in parsed.values())
        if abs(total - 1.0) > _RATIO_TOLERANCE:
            lines = [f"Region ratios must sum to 1.0.\n\nReceived:"]
            max_name_len = max(len(n) for n in ratio)
            for name, val in ratio.items():
                lines.append(f"    {name:<{max_name_len}} = {val}")
            lines.append(f"\nTotal = {total}")
            lines.append(f"Expected = 1.0")
            lines.append(f"\nDifference = {round(abs(total - 1.0), 10)}")
            raise InvalidRatioError("\n".join(lines))
    elif total_dimension is not None:
        fixed_sum = sum(mag for kind, mag in parsed.values() if kind == "fixed")
        if fixed_sum > total_dimension:
            raise InvalidRatioError(
                f"Fixed region sizes ({fixed_sum}px) exceed total window dimension ({total_dimension}px)."
            )


def resolve_ratio(
    ratio: Dict[str, Any],
    total_dimension: float,
) -> Dict[str, float]:
    """Converts a ratio dict with mixed units (floats, %, px, cm, mm, in, pt)
    into absolute pixel dimensions summing to total_dimension.
    """
    validate_ratios(ratio, total_dimension=total_dimension)
    if not ratio:
        return {}

    parsed = {name: _parse_ratio_value(val) for name, val in ratio.items()}

    fixed_items = {n: mag for n, (k, mag) in parsed.items() if k == "fixed"}
    ratio_items = {n: mag for n, (k, mag) in parsed.items() if k in ("ratio", "pct")}

    fixed_total = sum(fixed_items.values())
    remaining = max(0.0, total_dimension - fixed_total)

    result: Dict[str, float] = {}

    if ratio_items:
        ratio_sum = sum(ratio_items.values())
        if fixed_total == 0.0 and abs(ratio_sum - 1.0) <= _RATIO_TOLERANCE:
            for n, mag in ratio_items.items():
                result[n] = mag * total_dimension
        elif ratio_sum > 0.0:
            for n, mag in ratio_items.items():
                result[n] = (mag / ratio_sum) * remaining
        else:
            per_item = remaining / len(ratio_items)
            for n in ratio_items:
                result[n] = per_item

    for n, mag in fixed_items.items():
        result[n] = mag

    return {name: result[name] for name in ratio}


# ───────────────────────────────────────────────────────────────
# Gradient stop offset resolver (for Color subsystem)
# ───────────────────────────────────────────────────────────────

def resolve_stop_offset(offset: Union[float, int, str]) -> float:
    """Resolves a gradient stop offset to a float in [0.0, 1.0].

    Accepts bare floats in [0, 1] or percentage strings ``"0%"``–``"100%"``.
    """
    if isinstance(offset, (int, float)):
        val = float(offset)
        if not (0.0 <= val <= 1.0):
            raise InvalidUnitValueError(f"Gradient stop offset {val} must be in [0.0, 1.0].")
        return _validate_finite(val, offset)

    if isinstance(offset, str):
        s = offset.strip()
        if s.endswith("%"):
            try:
                pct = float(s[:-1])
                val = pct / 100.0
                if not (0.0 <= val <= 1.0):
                    raise InvalidUnitValueError(f"Gradient stop offset {offset} out of [0%, 100%].")
                return _validate_finite(val, offset)
            except ValueError as e:
                raise InvalidUnitValueError(f"Invalid percentage stop offset '{offset}'.") from e
        try:
            val = float(s)
            if not (0.0 <= val <= 1.0):
                raise InvalidUnitValueError(f"Gradient stop offset {val} must be in [0.0, 1.0].")
            return _validate_finite(val, offset)
        except ValueError as e:
            raise InvalidUnitValueError(f"Invalid stop offset '{offset}'.") from e

    raise InvalidUnitValueError(f"Invalid gradient stop offset type {type(offset).__name__}.")
