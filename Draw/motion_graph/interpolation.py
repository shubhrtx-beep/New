"""Draw Motion Graph API — Interpolation Algorithms.

Implements interpolation routines for point-based motion graphs:
- linear: Straight-line interpolation between adjacent points.
- step: Holds a point's output until the next point.
- smooth: Monotone cubic Hermite spline (Fritsch-Carlson) ensuring C1
  smoothness and preserving monotonicity/overshoots without spurious ringing.
"""

import math
from typing import FrozenSet, List, Optional, Sequence, Tuple
from .errors import InvalidInterpolationModeError

LINEAR = "linear"
SMOOTH = "smooth"
STEP = "step"

SUPPORTED_INTERPOLATION_MODES: FrozenSet[str] = frozenset({
    LINEAR,
    SMOOTH,
    STEP,
})


def validate_interpolation_mode(mode: str) -> str:
    """Validates that the interpolation mode is supported."""
    if not isinstance(mode, str):
        raise InvalidInterpolationModeError(
            f"Interpolation mode must be a string, got {type(mode).__name__}."
        )
    m = mode.strip().lower()
    if m not in SUPPORTED_INTERPOLATION_MODES:
        raise InvalidInterpolationModeError(
            f"Unsupported interpolation mode '{mode}'. "
            f"Must be one of: {', '.join(sorted(SUPPORTED_INTERPOLATION_MODES))}."
        )
    return m


def interpolate_linear(points: Sequence[Tuple[float, float]], x: float) -> float:
    """Evaluates piecewise linear interpolation at normalized time x."""
    n = len(points)
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]

    # Find segment [x_i, x_{i+1}]
    for i in range(n - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= x <= x1:
            dx = x1 - x0
            if dx < 1e-12:
                return y0
            t = (x - x0) / dx
            return y0 + t * (y1 - y0)

    return points[-1][1]


def interpolate_step(points: Sequence[Tuple[float, float]], x: float) -> float:
    """Evaluates step interpolation at normalized time x (holds y until next point)."""
    n = len(points)
    if x < points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]

    for i in range(n - 1):
        x0, y0 = points[i]
        x1, _ = points[i + 1]
        if x0 <= x < x1:
            return y0

    return points[-1][1]


class MonotoneCubicSpline:
    """Precomputed Monotone Cubic Hermite Spline (Fritsch-Carlson algorithm).

    Provides C1 smooth interpolation through control points. Prevents spurious
    overshoots between monotonic points while preserving explicit local extrema.
    """

    def __init__(self, points: Sequence[Tuple[float, float]]) -> None:
        self.points: List[Tuple[float, float]] = [(float(p[0]), float(p[1])) for p in points]
        n = len(self.points)
        if n < 2:
            raise ValueError("MonotoneCubicSpline requires at least 2 points.")

        self.n: int = n
        self.x: List[float] = [p[0] for p in self.points]
        self.y: List[float] = [p[1] for p in self.points]

        # 1. Calculate secant slopes Delta_k = (y_{k+1} - y_k) / (x_{k+1} - x_k)
        h: List[float] = [self.x[k + 1] - self.x[k] for k in range(n - 1)]
        delta: List[float] = [(self.y[k + 1] - self.y[k]) / h[k] for k in range(n - 1)]
        self.h: List[float] = h

        # 2. Compute initial tangents d_k
        d: List[float] = [0.0] * n
        if n == 2:
            # For 2 points, flat tangents produce a smooth S-curve easing
            d[0] = 0.0
            d[1] = 0.0
        else:
            d[0] = delta[0]
            d[-1] = delta[-1]
            for k in range(1, n - 1):
                # Standard Fritsch-Carlson average of adjacent secants
                if delta[k - 1] * delta[k] <= 0:
                    d[k] = 0.0  # Local extremum
                else:
                    d[k] = (delta[k - 1] + delta[k]) * 0.5

            # 3. Monotonicity filter (Fritsch-Carlson)
            for k in range(n - 1):
                if abs(delta[k]) < 1e-12:
                    d[k] = 0.0
                    d[k + 1] = 0.0
                else:
                    alpha = d[k] / delta[k]
                    beta = d[k + 1] / delta[k]
                    if alpha < 0:
                        d[k] = 0.0
                    if beta < 0:
                        d[k + 1] = 0.0
                    hypot = math.hypot(alpha, beta)
                    if hypot > 3.0:
                        tau = 3.0 / hypot
                        d[k] = tau * alpha * delta[k]
                        d[k + 1] = tau * beta * delta[k]

        self.d: List[float] = d

    def evaluate(self, x: float) -> float:
        """Evaluates spline at normalized time x."""
        if x <= self.x[0]:
            return self.y[0]
        if x >= self.x[-1]:
            return self.y[-1]

        # Binary search / segment lookup
        low = 0
        high = self.n - 2
        while low <= high:
            mid = (low + high) // 2
            if self.x[mid] <= x <= self.x[mid + 1]:
                low = mid
                break
            elif self.x[mid] > x:
                high = mid - 1
            else:
                low = mid + 1

        k = max(0, min(self.n - 2, low))
        hk = self.h[k]
        if hk < 1e-12:
            return self.y[k]

        t = (x - self.x[k]) / hk
        t2 = t * t
        t3 = t2 * t

        # Hermite basis polynomials
        h00 = 2.0 * t3 - 3.0 * t2 + 1.0
        h10 = t3 - 2.0 * t2 + t
        h01 = -2.0 * t3 + 3.0 * t2
        h11 = t3 - t2

        return (
            h00 * self.y[k]
            + h10 * hk * self.d[k]
            + h01 * self.y[k + 1]
            + h11 * hk * self.d[k + 1]
        )


def interpolate_smooth(
    points: Sequence[Tuple[float, float]],
    x: float,
    cached_spline: Optional[MonotoneCubicSpline] = None,
) -> float:
    """Evaluates smooth Monotone Cubic Hermite Spline at normalized time x."""
    spline = cached_spline or MonotoneCubicSpline(points)
    return spline.evaluate(x)
