"""Draw Motion API — Mathematical Motion System.

Function-based procedural animation and visual effects generation through
pure mathematical formulas, curves, noise, fields, waves, and flows.
"""

import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
from .vector import Vector2D, vec2

Point2D = Tuple[float, float]


# ═══════════════════════════════════════════════════════════════════════
# 1. INTERPOLATION
# ═══════════════════════════════════════════════════════════════════════

def clamp(val: float, low: float = 0.0, high: float = 1.0) -> float:
    """Restricts a value within [low, high]."""
    return max(low, min(high, float(val)))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * t


def inverse_lerp(a: float, b: float, val: float) -> float:
    """Finds normalized progress u in [0, 1] of val between a and b."""
    if abs(b - a) < 1e-12:
        return 0.0
    return clamp((val - a) / (b - a), 0.0, 1.0)


def remap(
    val: float,
    in_min: float,
    in_max: float,
    out_min: float,
    out_max: float,
) -> float:
    """Converts a value from input range [in_min, in_max] to output range [out_min, out_max]."""
    u = inverse_lerp(in_min, in_max, val)
    return lerp(out_min, out_max, u)


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """Smooth Hermite transition between edge0 and edge1."""
    t = clamp((x - edge0) / (edge1 - edge0) if abs(edge1 - edge0) >= 1e-12 else 0.0, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def mix(a: Any, b: Any, t: float) -> Any:
    """Blends two scalar values, tuples, or Vector2D objects by factor t."""
    if isinstance(a, Vector2D) or isinstance(b, Vector2D):
        va = Vector2D.from_value(a)
        vb = Vector2D.from_value(b)
        return va.lerp(vb, t)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return tuple(lerp(float(x), float(y), t) for x, y in zip(a, b))
    return lerp(float(a), float(b), t)


# ═══════════════════════════════════════════════════════════════════════
# 2. EASING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def linear(u: float) -> float:
    return clamp(u, 0.0, 1.0)


def ease_in(u: float, power: float = 2.0) -> float:
    return math.pow(clamp(u, 0.0, 1.0), power)


def ease_out(u: float, power: float = 2.0) -> float:
    u = clamp(u, 0.0, 1.0)
    return 1.0 - math.pow(1.0 - u, power)


def ease_in_out(u: float, power: float = 2.0) -> float:
    u = clamp(u, 0.0, 1.0)
    if u < 0.5:
        return 0.5 * math.pow(u * 2.0, power)
    return 1.0 - 0.5 * math.pow((1.0 - u) * 2.0, power)


def ease_in_back(u: float, s: float = 1.70158) -> float:
    u = clamp(u, 0.0, 1.0)
    return u * u * ((s + 1.0) * u - s)


def ease_out_back(u: float, s: float = 1.70158) -> float:
    u = clamp(u, 0.0, 1.0) - 1.0
    return u * u * ((s + 1.0) * u + s) + 1.0


def ease_out_bounce(u: float) -> float:
    u = clamp(u, 0.0, 1.0)
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


def ease_out_elastic(u: float) -> float:
    u = clamp(u, 0.0, 1.0)
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return math.pow(2.0, -10.0 * u) * math.sin((u * 10.0 - 0.75) * c4) + 1.0


def bezier(p1: float, p2: float, u: float) -> float:
    """1D cubic Bezier progression curve from (0,0) with control points p1, p2 to (1,1)."""
    u = clamp(u, 0.0, 1.0)
    inv = 1.0 - u
    return 3.0 * inv * inv * u * p1 + 3.0 * inv * u * u * p2 + u * u * u


# ═══════════════════════════════════════════════════════════════════════
# 3. TRIGONOMETRIC FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def sin(angle_rad: float) -> float:
    return math.sin(angle_rad)


def cos(angle_rad: float) -> float:
    return math.cos(angle_rad)


def tan(angle_rad: float) -> float:
    return math.tan(angle_rad)


def atan2(y: float, x: float) -> float:
    return math.atan2(y, x)


def rotate(point: Sequence[float], angle_rad: float, origin: Sequence[float] = (0.0, 0.0)) -> Tuple[float, float]:
    """Rotates a 2D point around an origin by angle in radians."""
    ox, oy = float(origin[0]), float(origin[1])
    px, py = float(point[0]) - ox, float(point[1]) - oy
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rx = px * cos_a - py * sin_a + ox
    ry = px * sin_a + py * cos_a + oy
    return (rx, ry)


def polar(radius: float, angle_rad: float) -> Tuple[float, float]:
    """Converts radius and angle (radians) to Cartesian (x, y)."""
    return (radius * math.cos(angle_rad), radius * math.sin(angle_rad))


def to_polar(x: float, y: float) -> Tuple[float, float]:
    """Converts Cartesian (x, y) to polar (radius, angle_rad)."""
    return (math.hypot(x, y), math.atan2(y, x))


# ═══════════════════════════════════════════════════════════════════════
# 4. CURVES AND PATHS
# ═══════════════════════════════════════════════════════════════════════

def quadratic_curve(p0: Sequence[float], p1: Sequence[float], p2: Sequence[float], t: float) -> Tuple[float, float]:
    """Evaluates 2D quadratic Bezier curve at parameter t in [0, 1]."""
    t = clamp(t, 0.0, 1.0)
    inv = 1.0 - t
    x = inv * inv * p0[0] + 2.0 * inv * t * p1[0] + t * t * p2[0]
    y = inv * inv * p0[1] + 2.0 * inv * t * p1[1] + t * t * p2[1]
    return (x, y)


def cubic_curve(
    p0: Sequence[float],
    p1: Sequence[float],
    p2: Sequence[float],
    p3: Sequence[float],
    t: float,
) -> Tuple[float, float]:
    """Evaluates 2D cubic Bezier curve at parameter t in [0, 1]."""
    t = clamp(t, 0.0, 1.0)
    inv = 1.0 - t
    x = (inv * inv * inv * p0[0]
         + 3.0 * inv * inv * t * p1[0]
         + 3.0 * inv * t * t * p2[0]
         + t * t * t * p3[0])
    y = (inv * inv * inv * p0[1]
         + 3.0 * inv * inv * t * p1[1]
         + 3.0 * inv * t * t * p2[1]
         + t * t * t * p3[1])
    return (x, y)


def bezier_curve(
    p0: Sequence[float],
    p1: Sequence[float],
    p2: Sequence[float],
    p3: Optional[Sequence[float]] = None,
    t: float = 0.0,
) -> Tuple[float, float]:
    """Evaluates quadratic (if p3 is None) or cubic Bezier curve."""
    if p3 is None:
        return quadratic_curve(p0, p1, p2, t)
    return cubic_curve(p0, p1, p2, p3, t)


def catmull_rom(
    p0: Sequence[float],
    p1: Sequence[float],
    p2: Sequence[float],
    p3: Sequence[float],
    t: float,
) -> Tuple[float, float]:
    """Evaluates 2D Catmull-Rom spline between p1 and p2 at t in [0, 1]."""
    t = clamp(t, 0.0, 1.0)
    t2 = t * t
    t3 = t2 * t
    x = 0.5 * (
        (2.0 * p1[0])
        + (-p0[0] + p2[0]) * t
        + (2.0 * p0[0] - 5.0 * p1[0] + 4.0 * p2[0] - p3[0]) * t2
        + (-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0]) * t3
    )
    y = 0.5 * (
        (2.0 * p1[1])
        + (-p0[1] + p2[1]) * t
        + (2.0 * p0[1] - 5.0 * p1[1] + 4.0 * p2[1] - p3[1]) * t2
        + (-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1]) * t3
    )
    return (x, y)


def arc(
    center: Sequence[float],
    radius: float,
    start_angle: float,
    end_angle: float,
    t: float,
) -> Tuple[float, float]:
    """Computes point along circular arc at interpolation t in [0, 1]."""
    angle = lerp(start_angle, end_angle, clamp(t, 0.0, 1.0))
    return (
        center[0] + radius * math.cos(angle),
        center[1] + radius * math.sin(angle),
    )


def spiral(
    center: Sequence[float],
    a: float,
    b: float,
    t: float,
    turns: float = 3.0,
) -> Tuple[float, float]:
    """Computes point along Archimedean spiral r = a + b * theta."""
    theta = lerp(0.0, turns * 2.0 * math.pi, clamp(t, 0.0, 1.0))
    r = a + b * theta
    return (
        center[0] + r * math.cos(theta),
        center[1] + r * math.sin(theta),
    )


def path_sample(points: Sequence[Sequence[float]], t: float) -> Tuple[float, float]:
    """Samples piecewise linear polyline at normalized progress t in [0, 1]."""
    if not points:
        return (0.0, 0.0)
    if len(points) == 1:
        return (float(points[0][0]), float(points[0][1]))

    t = clamp(t, 0.0, 1.0)
    # Compute cumulative segment lengths
    lengths = []
    total_len = 0.0
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        dist = math.hypot(dx, dy)
        lengths.append(dist)
        total_len += dist

    if total_len < 1e-12:
        return (float(points[0][0]), float(points[0][1]))

    target_dist = t * total_len
    cum = 0.0
    for i, seg_len in enumerate(lengths):
        if cum + seg_len >= target_dist or i == len(lengths) - 1:
            seg_t = (target_dist - cum) / seg_len if seg_len > 1e-12 else 0.0
            return (
                lerp(points[i][0], points[i + 1][0], seg_t),
                lerp(points[i][1], points[i + 1][1], seg_t),
            )
        cum += seg_len

    return (float(points[-1][0]), float(points[-1][1]))


# ═══════════════════════════════════════════════════════════════════════
# 5. NOISE AND RANDOMNESS
# ═══════════════════════════════════════════════════════════════════════

def _hash_2d(x: int, y: int, seed: int = 0) -> float:
    """Deterministic hash function returning pseudo-random float in [-1, 1]."""
    n = (int(x) * 374761393 + int(y) * 668265263 + int(seed) * 962592769) & 0x7FFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0x7FFFFFFF
    n = (n ^ (n >> 16)) & 0x7FFFFFFF
    return (n / 1073741823.5) - 1.0


def random(seed: Optional[int] = None) -> float:
    """Generates pseudo-random float in [0, 1]."""
    if seed is None:
        import time
        seed = int(time.time_ns() & 0x7FFFFFFF)
    return (_hash_2d(seed, 0, seed) + 1.0) * 0.5


def random_range(min_val: float, max_val: float, seed: Optional[int] = None) -> float:
    """Generates pseudo-random float in [min_val, max_val]."""
    return lerp(min_val, max_val, random(seed))


def noise(x: float, y: float = 0.0, seed: int = 0) -> float:
    """Smooth 2D coherent gradient noise in range [-1, 1]."""
    xi = math.floor(x)
    yi = math.floor(y)
    xf = x - xi
    yf = y - yi

    # Smooth Hermite curve
    u = xf * xf * (3.0 - 2.0 * xf)
    v = yf * yf * (3.0 - 2.0 * yf)

    # 4 corner hashes
    n00 = _hash_2d(xi, yi, seed)
    n10 = _hash_2d(xi + 1, yi, seed)
    n01 = _hash_2d(xi, yi + 1, seed)
    n11 = _hash_2d(xi + 1, yi + 1, seed)

    # Bilinear blend
    x1 = lerp(n00, n10, u)
    x2 = lerp(n01, n11, u)
    val = lerp(x1, x2, v)
    return clamp(val, -1.0, 1.0)


def perlin_noise(x: float, y: float = 0.0, seed: int = 0) -> float:
    """Alias for 2D coherent noise."""
    return noise(x, y, seed)


def simplex_noise(x: float, y: float = 0.0, seed: int = 0) -> float:
    """Simplex-like skewed triangular grid noise in [-1, 1]."""
    # Skew input space
    f2 = 0.5 * (math.sqrt(3.0) - 1.0)
    s = (x + y) * f2
    i = math.floor(x + s)
    j = math.floor(y + s)

    # Unskew back to Cartesian
    g2 = (3.0 - math.sqrt(3.0)) / 6.0
    t = (i + j) * g2
    x0 = x - (i - t)
    y0 = y - (j - t)

    # Determine simplex triangle
    if x0 > y0:
        i1, j1 = 1, 0
    else:
        i1, j1 = 0, 1

    x1 = x0 - i1 + g2
    y1 = y0 - j1 + g2
    x2 = x0 - 1.0 + 2.0 * g2
    y2 = y0 - 1.0 + 2.0 * g2

    # Corner contributions
    n0, n1, n2 = 0.0, 0.0, 0.0
    t0 = 0.5 - x0 * x0 - y0 * y0
    if t0 > 0:
        t0 *= t0
        n0 = t0 * t0 * _hash_2d(i, j, seed)

    t1 = 0.5 - x1 * x1 - y1 * y1
    if t1 > 0:
        t1 *= t1
        n1 = t1 * t1 * _hash_2d(i + i1, j + j1, seed)

    t2 = 0.5 - x2 * x2 - y2 * y2
    if t2 > 0:
        t2 *= t2
        n2 = t2 * t2 * _hash_2d(i + 1, j + 1, seed)

    return 70.0 * (n0 + n1 + n2)


def fractal_noise(
    x: float,
    y: float = 0.0,
    octaves: int = 4,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    seed: int = 0,
) -> float:
    """Fractal multi-octave coherent noise."""
    total = 0.0
    frequency = 1.0
    amplitude = 1.0
    max_val = 0.0

    for i in range(octaves):
        total += noise(x * frequency, y * frequency, seed + i * 31) * amplitude
        max_val += amplitude
        amplitude *= persistence
        frequency *= lacunarity

    return total / max_val if max_val > 0.0 else 0.0


def fbm(
    x: float,
    y: float = 0.0,
    octaves: int = 4,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    seed: int = 0,
) -> float:
    """Fractional Brownian Motion (alias for fractal_noise)."""
    return fractal_noise(x, y, octaves, persistence, lacunarity, seed)


def curl_noise(x: float, y: float, seed: int = 0, eps: float = 1e-3) -> Vector2D:
    """Calculates 2D curl of potential noise field: (dPsi/dy, -dPsi/dx)."""
    # Numerical derivatives of potential field Psi
    n_up = noise(x, y + eps, seed)
    n_dn = noise(x, y - eps, seed)
    n_rt = noise(x + eps, y, seed)
    n_lf = noise(x - eps, y, seed)

    dpsi_dy = (n_up - n_dn) / (2.0 * eps)
    dpsi_dx = (n_rt - n_lf) / (2.0 * eps)

    # Incompressible flow vector
    return Vector2D(dpsi_dy, -dpsi_dx)


# ═══════════════════════════════════════════════════════════════════════
# 6. WAVE AND OSCILLATION
# ═══════════════════════════════════════════════════════════════════════

def wave(
    t: float,
    frequency: float = 1.0,
    amplitude: float = 1.0,
    phase: float = 0.0,
) -> float:
    """General periodic sine wave oscillation."""
    return amplitude * math.sin(2.0 * math.pi * frequency * t + phase)


def sine_wave(t: float, frequency: float = 1.0, amplitude: float = 1.0, phase: float = 0.0) -> float:
    return wave(t, frequency, amplitude, phase)


def triangle_wave(t: float, frequency: float = 1.0, amplitude: float = 1.0, phase: float = 0.0) -> float:
    """Triangle wave in range [-amplitude, amplitude] in phase with sine wave (zero at t=0)."""
    cycle = (t * frequency + phase / (2.0 * math.pi)) % 1.0
    if cycle < 0.25:
        val = 4.0 * cycle
    elif cycle < 0.75:
        val = 2.0 - 4.0 * cycle
    else:
        val = 4.0 * cycle - 4.0
    return amplitude * val


def square_wave(t: float, frequency: float = 1.0, amplitude: float = 1.0, phase: float = 0.0) -> float:
    """Square wave switching between +amplitude and -amplitude."""
    cycle = (t * frequency + phase / (2.0 * math.pi)) % 1.0
    return amplitude if cycle < 0.5 else -amplitude


def sawtooth_wave(t: float, frequency: float = 1.0, amplitude: float = 1.0, phase: float = 0.0) -> float:
    """Linear ramp sawtooth wave in [-amplitude, amplitude]."""
    cycle = (t * frequency + phase / (2.0 * math.pi)) % 1.0
    return amplitude * (2.0 * cycle - 1.0)


def damped_oscillation(
    t: float,
    frequency: float = 1.0,
    amplitude: float = 1.0,
    decay_rate: float = 1.0,
    phase: float = 0.0,
) -> float:
    """Exponentially damped harmonic oscillation."""
    envelope = amplitude * math.exp(-decay_rate * max(0.0, t))
    return envelope * math.sin(2.0 * math.pi * frequency * t + phase)


def frequency_modulation(
    t: float,
    base_freq: float = 1.0,
    mod_freq: float = 0.2,
    mod_index: float = 0.5,
    amplitude: float = 1.0,
) -> float:
    """Frequency-modulated sine oscillation."""
    instantaneous_phase = 2.0 * math.pi * base_freq * t + mod_index * math.sin(2.0 * math.pi * mod_freq * t)
    return amplitude * math.sin(instantaneous_phase)


def amplitude_modulation(
    t: float,
    base_amp: float = 1.0,
    mod_freq: float = 0.2,
    mod_depth: float = 0.5,
    frequency: float = 1.0,
) -> float:
    """Amplitude-modulated sine oscillation."""
    inst_amp = base_amp * (1.0 + mod_depth * math.sin(2.0 * math.pi * mod_freq * t))
    return inst_amp * math.sin(2.0 * math.pi * frequency * t)


# ═══════════════════════════════════════════════════════════════════════
# 7. MATHEMATICAL FIELD OPERATIONS
# ═══════════════════════════════════════════════════════════════════════

def gradient(scalar_field: Callable[[float, float], float], x: float, y: float, eps: float = 1e-4) -> Vector2D:
    """Computes spatial gradient vector nabla(F) = (dF/dx, dF/dy)."""
    df_dx = (scalar_field(x + eps, y) - scalar_field(x - eps, y)) / (2.0 * eps)
    df_dy = (scalar_field(x, y + eps) - scalar_field(x, y - eps)) / (2.0 * eps)
    return Vector2D(df_dx, df_dy)


def vector_field(field_fn: Callable[[float, float], Sequence[float]], x: float, y: float) -> Vector2D:
    """Evaluates vector field at (x, y)."""
    return Vector2D.from_value(field_fn(x, y))


def direction_field(field_fn: Callable[[float, float], Sequence[float]], x: float, y: float) -> Vector2D:
    """Evaluates normalized direction vector at (x, y)."""
    return vector_field(field_fn, x, y).normalize()


def radial_field(
    center: Sequence[float],
    x: float,
    y: float,
    strength: float = 1.0,
    falloff_rate: float = 1.0,
) -> Vector2D:
    """Radial vector pushing outward from center with falloff."""
    dx = x - center[0]
    dy = y - center[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-12:
        return Vector2D(0.0, 0.0)
    mag = strength / (1.0 + falloff_rate * dist)
    return Vector2D((dx / dist) * mag, (dy / dist) * mag)


def distance_field(center: Sequence[float], x: float, y: float) -> float:
    """Signed/unsigned distance from point to center."""
    return math.hypot(x - center[0], y - center[1])


def attractor(
    target: Sequence[float],
    x: float,
    y: float,
    strength: float = 1.0,
    radius: float = 100.0,
) -> Vector2D:
    """Calculates attractive pull vector toward target."""
    dx = target[0] - x
    dy = target[1] - y
    dist = math.hypot(dx, dy)
    if dist < 1e-12:
        return Vector2D(0.0, 0.0)
    factor = clamp(dist / radius, 0.0, 1.0)
    return Vector2D((dx / dist) * strength * factor, (dy / dist) * strength * factor)


def repeller(
    source: Sequence[float],
    x: float,
    y: float,
    strength: float = 1.0,
    radius: float = 100.0,
) -> Vector2D:
    """Calculates repulsive push vector away from source."""
    return -attractor(source, x, y, strength, radius)


# ═══════════════════════════════════════════════════════════════════════
# 8. GROWTH AND DECAY
# ═══════════════════════════════════════════════════════════════════════

def exponential(t: float, base: float = 2.0) -> float:
    return math.pow(base, float(t))


def decay(value: float, rate: float, dt: float) -> float:
    """Applies exponential step decay: value * exp(-rate * dt)."""
    return value * math.exp(-rate * max(0.0, dt))


def exponential_decay(initial: float, rate: float, t: float) -> float:
    """Continuous exponential decay over time t."""
    return initial * math.exp(-rate * max(0.0, t))


def growth(initial: float, rate: float, t: float) -> float:
    """Continuous exponential growth over time t."""
    return initial * math.exp(rate * max(0.0, t))


def logarithmic(t: float, base: float = 10.0) -> float:
    t_val = max(1e-12, float(t))
    return math.log(t_val) / math.log(base)


def power(t: float, exp: float = 2.0) -> float:
    return math.pow(max(0.0, float(t)), exp)


def falloff(
    distance: float,
    max_distance: float,
    mode: str = "quadratic",
) -> float:
    """Calculates falloff multiplier in [0, 1] based on distance."""
    u = clamp(distance / max_distance if max_distance > 1e-12 else 1.0, 0.0, 1.0)
    if mode == "linear":
        return 1.0 - u
    elif mode == "inverse":
        return 1.0 / (1.0 + 4.0 * u)
    else:  # quadratic
        inv = 1.0 - u
        return inv * inv


# ═══════════════════════════════════════════════════════════════════════
# 9. PARTICLE AND FLOW MATHEMATICS
# ═══════════════════════════════════════════════════════════════════════

def advect(
    position: Sequence[float],
    field_fn: Callable[[float, float], Sequence[float]],
    dt: float,
) -> Tuple[float, float]:
    """Advects a particle position through a vector velocity field over dt."""
    x, y = float(position[0]), float(position[1])
    # Runge-Kutta 2nd order (midpoint) advection
    v1 = field_fn(x, y)
    mid_x = x + v1[0] * 0.5 * dt
    mid_y = y + v1[1] * 0.5 * dt
    v2 = field_fn(mid_x, mid_y)
    return (x + v2[0] * dt, y + v2[1] * dt)


def diffuse(
    particles: Sequence[Sequence[float]],
    rate: float,
    dt: float,
    seed: Optional[int] = None,
) -> List[Tuple[float, float]]:
    """Diffuses particles outward randomly with diffusion rate."""
    result = []
    base_seed = seed or 42
    spread = math.sqrt(2.0 * rate * dt) if rate > 0 and dt > 0 else 0.0
    for i, p in enumerate(particles):
        rx = _hash_2d(int(p[0] * 100), i, base_seed) * spread
        ry = _hash_2d(int(p[1] * 100), i + 1000, base_seed) * spread
        result.append((p[0] + rx, p[1] + ry))
    return result


def converge(
    position: Sequence[float],
    target: Sequence[float],
    strength: float,
    dt: float,
) -> Tuple[float, float]:
    """Moves particle toward target region."""
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    factor = clamp(strength * dt, 0.0, 1.0)
    return (position[0] + dx * factor, position[1] + dy * factor)


def diverge(
    position: Sequence[float],
    source: Sequence[float],
    strength: float,
    dt: float,
) -> Tuple[float, float]:
    """Spreads particle outward away from source."""
    dx = position[0] - source[0]
    dy = position[1] - source[1]
    return (position[0] + dx * strength * dt, position[1] + dy * strength * dt)


def turbulence(
    position: Sequence[float],
    scale: float = 1.0,
    strength: float = 1.0,
    seed: int = 0,
) -> Vector2D:
    """Generates irregular 2D turbulent displacement vector."""
    x, y = position[0] * scale, position[1] * scale
    tx = noise(x, y, seed) * strength
    ty = noise(x + 100.0, y + 100.0, seed + 1) * strength
    return Vector2D(tx, ty)


def vortex(
    position: Sequence[float],
    center: Sequence[float],
    strength: float = 1.0,
    radius: float = 100.0,
) -> Vector2D:
    """Calculates rotational tangential velocity around a center."""
    dx = position[0] - center[0]
    dy = position[1] - center[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-12:
        return Vector2D(0.0, 0.0)
    fall = falloff(dist, radius, mode="quadratic")
    speed = strength * fall
    # Perpendicular vector (-dy, dx) normalized
    return Vector2D((-dy / dist) * speed, (dx / dist) * speed)


def swirl(
    position: Sequence[float],
    center: Sequence[float],
    strength: float = 1.0,
    radius: float = 100.0,
    dt: float = 0.016,
) -> Tuple[float, float]:
    """Swirls position around center by rotational displacement over dt."""
    v = vortex(position, center, strength, radius)
    return (position[0] + v.x * dt, position[1] + v.y * dt)


def flow(
    position: Sequence[float],
    field_fn: Callable[[float, float], Sequence[float]],
    dt: float,
) -> Tuple[float, float]:
    """Steps particle position along mathematical flow field."""
    return advect(position, field_fn, dt)


def scatter(
    center: Sequence[float],
    count: int,
    radius: float,
    seed: Optional[int] = None,
) -> List[Tuple[float, float]]:
    """Distributes particles randomly inside a circular region."""
    base_seed = seed or 777
    particles = []
    for i in range(count):
        r = math.sqrt(random(base_seed + i * 2)) * radius
        theta = random(base_seed + i * 2 + 1) * 2.0 * math.pi
        particles.append((center[0] + r * math.cos(theta), center[1] + r * math.sin(theta)))
    return particles


def cluster(
    particles: Sequence[Sequence[float]],
    center: Sequence[float],
    strength: float,
    dt: float,
) -> List[Tuple[float, float]]:
    """Groups particles inward toward cluster center."""
    return [converge(p, center, strength, dt) for p in particles]


# ═══════════════════════════════════════════════════════════════════════
# 10. MATHEMATICAL TRANSFORMATIONS
# ═══════════════════════════════════════════════════════════════════════

def translate(point: Sequence[float], offset: Sequence[float]) -> Tuple[float, float]:
    return (point[0] + offset[0], point[1] + offset[1])


def rotate_transform(
    point: Sequence[float],
    angle_rad: float,
    origin: Sequence[float] = (0.0, 0.0),
) -> Tuple[float, float]:
    return rotate(point, angle_rad, origin)


def scale(
    point: Sequence[float],
    factor: Union[float, Sequence[float]],
    origin: Sequence[float] = (0.0, 0.0),
) -> Tuple[float, float]:
    ox, oy = float(origin[0]), float(origin[1])
    fx = factor[0] if isinstance(factor, (list, tuple)) else float(factor)
    fy = factor[1] if isinstance(factor, (list, tuple)) else float(factor)
    return (ox + (point[0] - ox) * fx, oy + (point[1] - oy) * fy)


def reflect(
    point: Sequence[float],
    line_pt: Sequence[float],
    line_dir: Sequence[float],
) -> Tuple[float, float]:
    """Reflects a point across a 2D line defined by line_pt and line_dir."""
    d = Vector2D.from_value(line_dir).normalize()
    n = Vector2D(-d.y, d.x)
    pt = Vector2D(point[0] - line_pt[0], point[1] - line_pt[1])
    dist = pt.dot(n)
    ref = pt - 2.0 * dist * n
    return (ref.x + line_pt[0], ref.y + line_pt[1])


def skew(point: Sequence[float], angles_rad: Sequence[float]) -> Tuple[float, float]:
    """Applies shear/skew transformation by (angle_x, angle_y) in radians."""
    tan_x = math.tan(angles_rad[0])
    tan_y = math.tan(angles_rad[1]) if len(angles_rad) > 1 else 0.0
    x = point[0] + point[1] * tan_x
    y = point[1] + point[0] * tan_y
    return (x, y)


def distort(
    point: Sequence[float],
    displacement_fn: Callable[[float, float], Sequence[float]],
) -> Tuple[float, float]:
    """Deforms geometry by spatial displacement function."""
    disp = displacement_fn(point[0], point[1])
    return (point[0] + disp[0], point[1] + disp[1])


def warp(
    point: Sequence[float],
    warp_grid_fn: Callable[[float, float], Sequence[float]],
) -> Tuple[float, float]:
    """Alias for distort."""
    return distort(point, warp_grid_fn)


# ═══════════════════════════════════════════════════════════════════════
# MATHEMATICAL TRANSFORM CONFIGURATION CLASS
# ═══════════════════════════════════════════════════════════════════════

class MathematicalTransform:
    """Configures and evaluates mathematical/procedural motion effects.

    Supports:
    - Fundamental quantities: duration, amplitude, frequency, phase, offset, scale, seed.
    - Effect parameters: direction, noise, turbulence, expansion, decay, vortex, swirl, diffusion.
    - Evaluation at any normalized time progress u or time t.
    """

    def __init__(
        self,
        duration: float = 1.0,
        amplitude: float = 1.0,
        frequency: float = 1.0,
        phase: float = 0.0,
        offset: Union[float, Sequence[float]] = 0.0,
        scale: Union[float, Sequence[float]] = 1.0,
        seed: int = 0,
        direction: Optional[Sequence[float]] = None,
        noise: float = 0.0,
        turbulence: float = 0.0,
        expansion: float = 1.0,
        decay: float = 0.0,
        effect_name: Optional[str] = None,
        **extra_params: Any,
    ) -> None:
        self.type: str = "mathematical"
        self.duration: float = max(1e-6, float(duration))
        self.amplitude: float = float(amplitude)
        self.frequency: float = float(frequency)
        self.phase: float = float(phase)
        self.offset: Any = offset
        self.scale: Any = scale
        self.seed: int = int(seed)
        self.direction: Optional[Tuple[float, float]] = (
            (float(direction[0]), float(direction[1])) if direction else None
        )
        self.noise_amount: float = float(noise)
        self.turbulence_amount: float = float(turbulence)
        self.expansion_amount: float = float(expansion)
        self.decay_rate: float = float(decay)
        self.effect_name: Optional[str] = effect_name
        self.extra_params: Dict[str, Any] = extra_params

    def evaluate(self, t: float, base_pos: Sequence[float] = (0.0, 0.0)) -> Tuple[float, float]:
        """Evaluates spatial displacement at time t."""
        u = clamp(t / self.duration, 0.0, 1.0)
        x, y = float(base_pos[0]), float(base_pos[1])

        # Directional flow / advection
        if self.direction:
            dir_v = Vector2D.from_value(self.direction).normalize()
            speed = self.amplitude * (1.0 + self.expansion_amount * u)
            decay_factor = math.exp(-self.decay_rate * t)
            x += dir_v.x * speed * t * decay_factor
            y += dir_v.y * speed * t * decay_factor

        # Noise & turbulence displacement
        if self.noise_amount > 0 or self.turbulence_amount > 0:
            nx = perlin_noise(x * 0.01 + t * self.frequency, y * 0.01, self.seed)
            ny = perlin_noise(x * 0.01 + 50.0, y * 0.01 + t * self.frequency, self.seed + 1)
            x += nx * (self.noise_amount * 20.0 + self.turbulence_amount * 10.0)
            y += ny * (self.noise_amount * 20.0 + self.turbulence_amount * 10.0)

        return (x, y)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes mathematical motion configuration to JSON dictionary."""
        data: Dict[str, Any] = {
            "type": "mathematical",
            "duration": round(self.duration, 4),
            "amplitude": round(self.amplitude, 4),
            "frequency": round(self.frequency, 4),
            "phase": round(self.phase, 4),
            "seed": self.seed,
            "noise": round(self.noise_amount, 4),
            "turbulence": round(self.turbulence_amount, 4),
            "expansion": round(self.expansion_amount, 4),
            "decay": round(self.decay_rate, 4),
        }
        if self.direction:
            data["direction"] = list(self.direction)
        if self.effect_name:
            data["effect"] = self.effect_name
        if self.extra_params:
            data["params"] = self.extra_params
        return data

    def __repr__(self) -> str:
        parts = ["MathematicalTransform("]
        if self.direction:
            parts.append(f"direction={self.direction}")
        if self.noise_amount:
            parts.append(f", noise={self.noise_amount}")
        if self.turbulence_amount:
            parts.append(f", turbulence={self.turbulence_amount}")
        parts.append(")")
        return "".join(parts)


# ═══════════════════════════════════════════════════════════════════════
# VISUAL EFFECT RECIPES (PROCEDURAL MATHEMATICAL PRESETS)
# ═══════════════════════════════════════════════════════════════════════

def fire(
    direction: Sequence[float] = (0.0, 1.0),
    noise: float = 0.6,
    turbulence: float = 0.7,
    decay: float = 0.4,
    expansion: float = 1.1,
    duration: float = 1.0,
    **kwargs: Any,
) -> MathematicalTransform:
    """Fire procedural effect preset: upward flow, noise, turbulence, decay, randomness."""
    return MathematicalTransform(
        duration=duration,
        direction=direction,
        noise=noise,
        turbulence=turbulence,
        decay=decay,
        expansion=expansion,
        effect_name="fire",
        **kwargs,
    )


def smoke(
    direction: Sequence[float] = (0.0, -1.0),
    noise: float = 0.5,
    turbulence: float = 0.8,
    expansion: float = 1.2,
    decay: float = 0.3,
    duration: float = 2.0,
    **kwargs: Any,
) -> MathematicalTransform:
    """Smoke procedural effect preset: advection, diffusion, noise, vortex expansion."""
    return MathematicalTransform(
        duration=duration,
        direction=direction,
        noise=noise,
        turbulence=turbulence,
        expansion=expansion,
        decay=decay,
        effect_name="smoke",
        **kwargs,
    )


def lightning(
    direction: Sequence[float] = (0.0, -1.0),
    noise: float = 0.9,
    turbulence: float = 1.0,
    frequency: float = 15.0,
    duration: float = 0.3,
    **kwargs: Any,
) -> MathematicalTransform:
    """Lightning procedural effect preset: branching randomness, flicker, jagged geometry."""
    return MathematicalTransform(
        duration=duration,
        direction=direction,
        noise=noise,
        turbulence=turbulence,
        frequency=frequency,
        effect_name="lightning",
        **kwargs,
    )


def shockwave(
    amplitude: float = 50.0,
    expansion: float = 2.0,
    decay: float = 1.5,
    frequency: float = 2.0,
    duration: float = 1.0,
    **kwargs: Any,
) -> MathematicalTransform:
    """Shockwave procedural effect preset: radial field expansion, falloff, distortion."""
    return MathematicalTransform(
        duration=duration,
        amplitude=amplitude,
        expansion=expansion,
        decay=decay,
        frequency=frequency,
        effect_name="shockwave",
        **kwargs,
    )


def water_splash(
    direction: Sequence[float] = (0.0, 1.0),
    noise: float = 0.4,
    expansion: float = 1.5,
    decay: float = 0.8,
    duration: float = 1.2,
    **kwargs: Any,
) -> MathematicalTransform:
    """Water splash procedural effect preset: divergence, particles, gravity falloff."""
    return MathematicalTransform(
        duration=duration,
        direction=direction,
        noise=noise,
        expansion=expansion,
        decay=decay,
        effect_name="water_splash",
        **kwargs,
    )


def energy_vortex(
    amplitude: float = 20.0,
    frequency: float = 3.0,
    expansion: float = 1.0,
    turbulence: float = 0.5,
    duration: float = 2.0,
    **kwargs: Any,
) -> MathematicalTransform:
    """Energy vortex procedural effect preset: rotational swirl, radial field, oscillation."""
    return MathematicalTransform(
        duration=duration,
        amplitude=amplitude,
        frequency=frequency,
        expansion=expansion,
        turbulence=turbulence,
        effect_name="energy_vortex",
        **kwargs,
    )
