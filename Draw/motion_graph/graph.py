"""Draw Motion Graph API — MotionGraph Definition and Evaluation.

Implements the MotionGraph class representing time-to-progress curves defined
via control points or combination/blending of existing graphs.
"""

import math
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)
from .errors import (
    InvalidMotionGraphError,
    InvalidGraphPointsError,
    InvalidGraphCombineError,
    GraphDefinitionConflictError,
    CircularGraphReferenceError,
    MotionGraphNotFoundError,
)
from .interpolation import (
    LINEAR,
    SMOOTH,
    STEP,
    validate_interpolation_mode,
    interpolate_linear,
    interpolate_step,
    interpolate_smooth,
    MonotoneCubicSpline,
)


def _ease_out_bounce_impl(u: float) -> float:
    n1 = 7.5625
    d1 = 2.75
    if u < 1.0 / d1:
        return n1 * u * u
    elif u < 2.0 / d1:
        u -= 1.5 / d1
        return n1 * u * u + 0.75
    elif u < 2.5 / d1:
        u -= 2.25 / d1
        return n1 * u * u + 0.9375
    else:
        u -= 2.625 / d1
        return n1 * u * u + 0.984375


def _ease_in_bounce_impl(u: float) -> float:
    return 1.0 - _ease_out_bounce_impl(1.0 - u)


def evaluate_builtin_easing(name: str, x: float) -> float:
    """Evaluates one of the 35 standard Draw easing graphs at normalized time x."""
    u = max(0.0, min(1.0, float(x)))
    n = name.strip().lower()

    if n == "linear":
        return u
    elif n in ("ease_in", "ease_in_quad"):
        return u * u
    elif n in ("ease_out", "ease_out_quad"):
        return 1.0 - (1.0 - u) * (1.0 - u)
    elif n in ("ease_in_out", "ease_in_out_quad"):
        return 2.0 * u * u if u < 0.5 else 1.0 - math.pow(-2.0 * u + 2.0, 2) / 2.0
    elif n == "ease_in_cubic":
        return u * u * u
    elif n == "ease_out_cubic":
        return 1.0 - math.pow(1.0 - u, 3)
    elif n == "ease_in_out_cubic":
        return 4.0 * u * u * u if u < 0.5 else 1.0 - math.pow(-2.0 * u + 2.0, 3) / 2.0
    elif n == "ease_in_quart":
        return u * u * u * u
    elif n == "ease_out_quart":
        return 1.0 - math.pow(1.0 - u, 4)
    elif n == "ease_in_out_quart":
        return 8.0 * u * u * u * u if u < 0.5 else 1.0 - math.pow(-2.0 * u + 2.0, 4) / 2.0
    elif n == "ease_in_quint":
        return u * u * u * u * u
    elif n == "ease_out_quint":
        return 1.0 - math.pow(1.0 - u, 5)
    elif n == "ease_in_out_quint":
        return 16.0 * u * u * u * u * u if u < 0.5 else 1.0 - math.pow(-2.0 * u + 2.0, 5) / 2.0
    elif n == "ease_in_sine":
        return 1.0 - math.cos((u * math.pi) / 2.0)
    elif n == "ease_out_sine":
        return math.sin((u * math.pi) / 2.0)
    elif n == "ease_in_out_sine":
        return -(math.cos(math.pi * u) - 1.0) / 2.0
    elif n == "ease_in_expo":
        return 0.0 if u == 0.0 else math.pow(2.0, 10.0 * u - 10.0)
    elif n == "ease_out_expo":
        return 1.0 if u == 1.0 else 1.0 - math.pow(2.0, -10.0 * u)
    elif n == "ease_in_out_expo":
        if u == 0.0:
            return 0.0
        if u == 1.0:
            return 1.0
        return math.pow(2.0, 20.0 * u - 10.0) / 2.0 if u < 0.5 else (2.0 - math.pow(2.0, -20.0 * u + 10.0)) / 2.0
    elif n == "ease_in_circ":
        return 1.0 - math.sqrt(max(0.0, 1.0 - u * u))
    elif n == "ease_out_circ":
        return math.sqrt(max(0.0, 1.0 - math.pow(u - 1.0, 2)))
    elif n == "ease_in_out_circ":
        if u < 0.5:
            return (1.0 - math.sqrt(max(0.0, 1.0 - math.pow(2.0 * u, 2)))) / 2.0
        return (math.sqrt(max(0.0, 1.0 - math.pow(-2.0 * u + 2.0, 2))) + 1.0) / 2.0
    elif n == "ease_in_back":
        c1 = 1.70158
        c3 = c1 + 1.0
        return c3 * u * u * u - c1 * u * u
    elif n == "ease_out_back":
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * math.pow(u - 1.0, 3) + c1 * math.pow(u - 1.0, 2)
    elif n == "ease_in_out_back":
        c1 = 1.70158
        c2 = c1 * 1.525
        if u < 0.5:
            return (math.pow(2.0 * u, 2) * ((c2 + 1.0) * 2.0 * u - c2)) / 2.0
        return (math.pow(2.0 * u - 2.0, 2) * ((c2 + 1.0) * (u * 2.0 - 2.0) + c2) + 2.0) / 2.0
    elif n == "ease_in_elastic":
        if u == 0.0:
            return 0.0
        if u == 1.0:
            return 1.0
        c4 = (2.0 * math.pi) / 3.0
        return -math.pow(2.0, 10.0 * u - 10.0) * math.sin((u * 10.0 - 10.75) * c4)
    elif n == "ease_out_elastic":
        if u == 0.0:
            return 0.0
        if u == 1.0:
            return 1.0
        c4 = (2.0 * math.pi) / 3.0
        return math.pow(2.0, -10.0 * u) * math.sin((u * 10.0 - 0.75) * c4) + 1.0
    elif n == "ease_in_out_elastic":
        if u == 0.0:
            return 0.0
        if u == 1.0:
            return 1.0
        c5 = (2.0 * math.pi) / 4.5
        if u < 0.5:
            return -(math.pow(2.0, 20.0 * u - 10.0) * math.sin((20.0 * u - 11.125) * c5)) / 2.0
        return (math.pow(2.0, -20.0 * u + 10.0) * math.sin((20.0 * u - 11.125) * c5)) / 2.0 + 1.0
    elif n == "ease_out_bounce":
        return _ease_out_bounce_impl(u)
    elif n == "ease_in_bounce":
        return _ease_in_bounce_impl(u)
    elif n == "ease_in_out_bounce":
        if u < 0.5:
            return (1.0 - _ease_out_bounce_impl(1.0 - 2.0 * u)) / 2.0
        return (1.0 + _ease_out_bounce_impl(2.0 * u - 1.0)) / 2.0
    elif n == "smooth":
        return u * u * (3.0 - 2.0 * u)

    raise ValueError(f"Unknown built-in easing '{name}'.")


class MotionGraph:
    """Represents a time-to-progress curve.

    Maps normalized time X (normally 0.0 to 1.0) to progress value Y.
    Supports point-based curves (with linear, smooth, step interpolation)
    and combined curves blending existing graphs.
    """

    def __init__(
        self,
        name: str,
        points: Optional[Sequence[Sequence[float]]] = None,
        interpolation: str = "smooth",
        combine: Optional[Sequence[Union[Tuple[str, float], Sequence[Any]]]] = None,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise InvalidMotionGraphError(f"Motion graph name must be a non-empty string, got {name!r}.")
        self.name: str = name.strip()

        # Definition exclusivity
        has_points = points is not None
        has_combine = combine is not None

        if has_points and has_combine:
            raise GraphDefinitionConflictError(
                f"Motion graph '{self.name}' cannot specify both 'points' and 'combine'."
            )
        if not has_points and not has_combine:
            raise GraphDefinitionConflictError(
                f"Motion graph '{self.name}' must specify either 'points' or 'combine'."
            )

        if has_points:
            self.type: str = "points"
            self.interpolation: str = validate_interpolation_mode(interpolation)
            self.points: List[Tuple[float, float]] = self._validate_and_normalize_points(points)
            self.combine: Optional[List[Tuple[str, float]]] = None
            self.spline: Optional[MonotoneCubicSpline] = (
                MonotoneCubicSpline(self.points) if self.interpolation == SMOOTH else None
            )
        else:
            self.type = "combine"
            self.interpolation = "none"
            self.points = []
            self.spline = None
            self.combine = self._validate_and_normalize_combine(combine)

    def _validate_and_normalize_points(
        self, raw_points: Any
    ) -> List[Tuple[float, float]]:
        if not isinstance(raw_points, (list, tuple)):
            raise InvalidGraphPointsError(
                f"Motion graph '{self.name}' points must be a list or tuple of (x, y) coordinates."
            )
        if len(raw_points) < 2:
            raise InvalidGraphPointsError(
                f"Motion graph '{self.name}' points must contain at least 2 points, got {len(raw_points)}."
            )

        normalized: List[Tuple[float, float]] = []
        last_x: Optional[float] = None

        for idx, pt in enumerate(raw_points):
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise InvalidGraphPointsError(
                    f"Motion graph '{self.name}' point at index {idx} must be a 2-element (x, y) tuple, got {pt!r}."
                )
            x_raw, y_raw = pt
            if not isinstance(x_raw, (int, float)) or not isinstance(y_raw, (int, float)):
                raise InvalidGraphPointsError(
                    f"Motion graph '{self.name}' point coordinates at index {idx} must be numeric, got ({type(x_raw).__name__}, {type(y_raw).__name__})."
                )
            x = float(x_raw)
            y = float(y_raw)
            if not math.isfinite(x) or not math.isfinite(y):
                raise InvalidGraphPointsError(
                    f"Motion graph '{self.name}' point coordinates at index {idx} must be finite numbers, got ({x}, {y})."
                )

            if last_x is not None and x <= last_x:
                raise InvalidGraphPointsError(
                    f"Motion graph '{self.name}' X values must be strictly increasing. "
                    f"Point at index {idx} (x={x}) is <= previous point (x={last_x})."
                )
            last_x = x
            normalized.append((x, y))

        return normalized

    def _validate_and_normalize_combine(
        self, raw_combine: Any
    ) -> List[Tuple[str, float]]:
        if not isinstance(raw_combine, (list, tuple)):
            raise InvalidGraphCombineError(
                f"Motion graph '{self.name}' combine must be a list of (graph_name, weight) entries."
            )
        if len(raw_combine) < 1:
            raise InvalidGraphCombineError(
                f"Motion graph '{self.name}' combine must contain at least 1 entry."
            )

        normalized: List[Tuple[str, float]] = []
        total_weight: float = 0.0

        for idx, entry in enumerate(raw_combine):
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise InvalidGraphCombineError(
                    f"Motion graph '{self.name}' combine entry at index {idx} must be a 2-element (graph_name, weight) tuple, got {entry!r}."
                )
            g_name, w_raw = entry
            if not isinstance(g_name, str) or not g_name.strip():
                raise InvalidGraphCombineError(
                    f"Motion graph '{self.name}' combine entry at index {idx} must have a non-empty string name, got {g_name!r}."
                )
            if not isinstance(w_raw, (int, float)):
                raise InvalidGraphCombineError(
                    f"Motion graph '{self.name}' combine weight at index {idx} must be a number, got {type(w_raw).__name__}."
                )
            w = float(w_raw)
            if not math.isfinite(w) or w < 0.0:
                raise InvalidGraphCombineError(
                    f"Motion graph '{self.name}' combine weight at index {idx} must be finite and non-negative, got {w}."
                )
            target_name = g_name.strip()
            if target_name == self.name:
                raise CircularGraphReferenceError(
                    f"Motion graph '{self.name}' cannot directly combine itself."
                )
            total_weight += w
            normalized.append((target_name, w))

        if total_weight <= 0.0:
            raise InvalidGraphCombineError(
                f"Motion graph '{self.name}' total combine weight must be greater than zero, got {total_weight}."
            )

        return normalized

    def evaluate(
        self,
        x: float,
        registry_lookup: Optional[Callable[[str], Any]] = None,
        visited: Optional[Set[str]] = None,
    ) -> float:
        """Evaluates graph at normalized time x, returning the progress value Y."""
        x_val = float(x)

        if self.type == "points":
            if self.interpolation == LINEAR:
                return interpolate_linear(self.points, x_val)
            elif self.interpolation == STEP:
                return interpolate_step(self.points, x_val)
            else:  # SMOOTH
                return interpolate_smooth(self.points, x_val, self.spline)

        # Combined graph evaluation: G(x) = sum(w_i * G_i(x)) / sum(w_i)
        if visited is None:
            visited = set()
        if self.name in visited:
            raise CircularGraphReferenceError(
                f"Circular graph reference detected involving motion graph '{self.name}'."
            )
        visited.add(self.name)

        total_weighted_progress = 0.0
        total_weight = 0.0

        for target_name, weight in self.combine:  # type: ignore[union-attr]
            if weight <= 0.0:
                continue

            # 1. Check registry lookup
            lookup_fn = registry_lookup
            if lookup_fn is None:
                try:
                    from .registry import GLOBAL_MOTION_GRAPH_REGISTRY
                    lookup_fn = GLOBAL_MOTION_GRAPH_REGISTRY._graphs.get
                except Exception:
                    lookup_fn = None
            sub_graph = lookup_fn(target_name) if lookup_fn else None

            if sub_graph is not None:
                if isinstance(sub_graph, MotionGraph):
                    progress = sub_graph.evaluate(
                        x_val, registry_lookup=registry_lookup, visited=set(visited)
                    )
                elif callable(sub_graph):
                    progress = float(sub_graph(x_val))
                else:
                    raise MotionGraphNotFoundError(
                        f"Referenced motion graph '{target_name}' is not callable."
                    )
            else:
                # 2. Check built-in easings
                try:
                    progress = evaluate_builtin_easing(target_name, x_val)
                except ValueError:
                    raise MotionGraphNotFoundError(
                        f"Motion graph '{self.name}' references unknown graph '{target_name}'."
                    )

            total_weighted_progress += weight * progress
            total_weight += weight

        return total_weighted_progress / total_weight if total_weight > 0.0 else 0.0

    def __call__(self, x: float) -> float:
        return self.evaluate(x)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes motion graph definition for the C++/OpenGL engine."""
        data: Dict[str, Any] = {
            "schema": "draw.motion_graph",
            "version": 1,
            "name": self.name,
            "type": self.type,
        }
        if self.type == "points":
            data["interpolation"] = self.interpolation
            data["points"] = [list(p) for p in self.points]
        else:
            data["combine"] = [[name, w] for name, w in self.combine]  # type: ignore[union-attr]
        return data

    def __repr__(self) -> str:
        if self.type == "points":
            return (
                f"MotionGraph(name={self.name!r}, points={self.points!r}, "
                f"interpolation={self.interpolation!r})"
            )
        return f"MotionGraph(name={self.name!r}, combine={self.combine!r})"
