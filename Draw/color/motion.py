"""Draw Color API — Motion Drivers, Expression AST & Animation Timeline.

Provides deterministic procedural animation drivers and symbolic expression trees
for serialization to C++ render backend without running unrestricted Python code.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from .errors import InvalidMotionError

SUPPORTED_EASINGS = {
    "linear",
    "smooth",
    "ease_in",
    "ease_out",
    "ease_in_out",
}


def is_dynamic_value(val: Any) -> bool:
    """Checks whether a value is a dynamic driver, expression node, or dynamic container."""
    if val is None:
        return False
    if getattr(val, "is_dynamic", False):
        return True
    return False


class MotionDriver:
    """Base class for all semantic motion drivers."""

    def __init__(
        self,
        driver_type: str,
        enabled: bool = True,
        delay: float = 0.0,
        fallback: Optional[float] = None,
    ) -> None:
        self.driver_type = driver_type
        self.enabled = bool(enabled)
        self.delay = float(delay)
        self.fallback = float(fallback) if fallback is not None else None
        self.is_dynamic: bool = True

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


class CycleDriver(MotionDriver):
    """Continuous angular or value rotation driver (e.g. hue cycling)."""

    def __init__(
        self,
        speed: float = 60.0,
        offset: float = 0.0,
        repeat: Optional[int] = None,
        yoyo: bool = False,
        delay: float = 0.0,
        enabled: bool = True,
        fallback: Optional[float] = None,
    ) -> None:
        super().__init__("cycle", enabled=enabled, delay=delay, fallback=fallback)
        self.speed = float(speed)
        self.offset = float(offset)
        self.repeat = int(repeat) if repeat is not None else None
        self.yoyo = bool(yoyo)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": "cycle",
            "speed": self.speed,
            "offset": self.offset,
            "delay": self.delay,
            "enabled": self.enabled,
        }
        if self.repeat is not None:
            data["repeat"] = self.repeat
        if self.yoyo:
            data["yoyo"] = self.yoyo
        if self.fallback is not None:
            data["fallback"] = self.fallback
        return data


class PulseDriver(MotionDriver):
    """Smooth oscillating breathing between min and max values."""

    def __init__(
        self,
        min_val: float = 0.0,
        max_val: float = 1.0,
        speed: float = 1.0,
        easing: str = "smooth",
        repeat: Optional[int] = None,
        yoyo: bool = False,
        delay: float = 0.0,
        enabled: bool = True,
        fallback: Optional[float] = None,
    ) -> None:
        super().__init__("pulse", enabled=enabled, delay=delay, fallback=fallback)
        if easing not in SUPPORTED_EASINGS:
            raise InvalidMotionError(f"Unsupported easing '{easing}'. Must be one of {sorted(SUPPORTED_EASINGS)}.")
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.speed = float(speed)
        self.easing = easing
        self.repeat = int(repeat) if repeat is not None else None
        self.yoyo = bool(yoyo)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": "pulse",
            "min": self.min_val,
            "max": self.max_val,
            "speed": self.speed,
            "easing": self.easing,
            "delay": self.delay,
            "enabled": self.enabled,
        }
        if self.repeat is not None:
            data["repeat"] = self.repeat
        if self.yoyo:
            data["yoyo"] = self.yoyo
        if self.fallback is not None:
            data["fallback"] = self.fallback
        return data


class OscillateDriver(MotionDriver):
    """Direct range oscillation between two values with specific duration."""

    def __init__(
        self,
        from_val: float = 0.0,
        to_val: float = 1.0,
        duration: float = 1.0,
        easing: str = "ease_in_out",
        repeat: Optional[int] = None,
        yoyo: bool = True,
        delay: float = 0.0,
        enabled: bool = True,
        fallback: Optional[float] = None,
    ) -> None:
        super().__init__("oscillate", enabled=enabled, delay=delay, fallback=fallback)
        if duration <= 0:
            raise InvalidMotionError(f"Oscillate duration must be positive, got {duration}.")
        if easing not in SUPPORTED_EASINGS:
            raise InvalidMotionError(f"Unsupported easing '{easing}'. Must be one of {sorted(SUPPORTED_EASINGS)}.")
        self.from_val = float(from_val)
        self.to_val = float(to_val)
        self.duration = float(duration)
        self.easing = easing
        self.repeat = int(repeat) if repeat is not None else None
        self.yoyo = bool(yoyo)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": "oscillate",
            "from": self.from_val,
            "to": self.to_val,
            "duration": self.duration,
            "easing": self.easing,
            "yoyo": self.yoyo,
            "delay": self.delay,
            "enabled": self.enabled,
        }
        if self.repeat is not None:
            data["repeat"] = self.repeat
        if self.fallback is not None:
            data["fallback"] = self.fallback
        return data


class KeyframesDriver(MotionDriver):
    """Authored timeline keyframes."""

    def __init__(
        self,
        property: str,
        frames: Sequence[Tuple[float, Any]],
        easing: str = "ease_in_out",
        repeat: Optional[int] = None,
        yoyo: bool = False,
        delay: float = 0.0,
        enabled: bool = True,
        fallback: Optional[float] = None,
    ) -> None:
        super().__init__("keyframes", enabled=enabled, delay=delay, fallback=fallback)
        if not frames:
            raise InvalidMotionError("Keyframes sequence cannot be empty.")
        if easing not in SUPPORTED_EASINGS:
            raise InvalidMotionError(f"Unsupported easing '{easing}'.")

        # Verify sorted non-negative times
        normalized_frames: List[Tuple[float, Any]] = []
        prev_t = -1.0
        for t, val in frames:
            t_flt = float(t)
            if t_flt < 0.0 or t_flt < prev_t:
                raise InvalidMotionError("Keyframe times must be non-negative and monotonically increasing.")
            normalized_frames.append((t_flt, val))
            prev_t = t_flt

        self.property = str(property)
        self.frames = normalized_frames
        self.easing = easing
        self.repeat = int(repeat) if repeat is not None else None
        self.yoyo = bool(yoyo)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "keyframes",
            "property": self.property,
            "frames": self.frames,
            "easing": self.easing,
            "repeat": self.repeat,
            "yoyo": self.yoyo,
            "delay": self.delay,
            "enabled": self.enabled,
        }


class TransitionDriver(MotionDriver):
    """Runtime transition helper when updating a color binding."""

    def __init__(
        self,
        duration: float = 0.35,
        easing: str = "ease_out",
        delay: float = 0.0,
    ) -> None:
        super().__init__("transition", enabled=True, delay=delay)
        if duration < 0:
            raise InvalidMotionError(f"Transition duration cannot be negative, got {duration}.")
        if easing not in SUPPORTED_EASINGS:
            raise InvalidMotionError(f"Unsupported easing '{easing}'.")
        self.duration = float(duration)
        self.easing = easing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "transition",
            "duration": self.duration,
            "easing": self.easing,
            "delay": self.delay,
        }


class ExpressionNode:
    """Safe symbolic expression AST node for procedural math serialization."""

    def __init__(self, op: str, args: Optional[Sequence[Any]] = None) -> None:
        self.op = op
        self.args = list(args) if args is not None else []
        self.is_dynamic: bool = True

    def __add__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("add", [self, _ensure_expr_node(other)])

    def __radd__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("add", [_ensure_expr_node(other), self])

    def __sub__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("sub", [self, _ensure_expr_node(other)])

    def __rsub__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("sub", [_ensure_expr_node(other), self])

    def __mul__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("mul", [self, _ensure_expr_node(other)])

    def __rmul__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("mul", [_ensure_expr_node(other), self])

    def __truediv__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("div", [self, _ensure_expr_node(other)])

    def __rtruediv__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("div", [_ensure_expr_node(other), self])

    def __floordiv__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("floordiv", [self, _ensure_expr_node(other)])

    def __rfloordiv__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("floordiv", [_ensure_expr_node(other), self])

    def __mod__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("mod", [self, _ensure_expr_node(other)])

    def __rmod__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("mod", [_ensure_expr_node(other), self])

    def __pow__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("pow", [self, _ensure_expr_node(other)])

    def __rpow__(self, other: Any) -> "ExpressionNode":
        return ExpressionNode("pow", [_ensure_expr_node(other), self])

    def __neg__(self) -> "ExpressionNode":
        return ExpressionNode("neg", [self])

    def __abs__(self) -> "ExpressionNode":
        return ExpressionNode("abs", [self])

    def to_dict(self) -> Dict[str, Any]:
        """Serializes expression tree into standard AST dictionary."""
        serialized_args: List[Any] = []
        for arg in self.args:
            if isinstance(arg, ExpressionNode):
                serialized_args.append(arg.to_dict())
            elif isinstance(arg, MotionDriver):
                serialized_args.append(arg.to_dict())
            else:
                serialized_args.append(arg)

        return {
            "op": self.op,
            "args": serialized_args,
        }


def _ensure_expr_node(val: Any) -> Union[ExpressionNode, Dict[str, Any]]:
    if isinstance(val, ExpressionNode):
        return val
    if isinstance(val, (int, float)):
        return ExpressionNode("const", [float(val)])
    return ExpressionNode("const", [val])


# Global time symbol
time = ExpressionNode("time")


def expr(value: Any) -> ExpressionNode:
    """Normalizes an expression or numeric value into an ExpressionNode."""
    if isinstance(value, ExpressionNode):
        return value
    if isinstance(value, (int, float)):
        return ExpressionNode("const", [float(value)])
    raise InvalidMotionError(f"Cannot convert {type(value).__name__} to an ExpressionNode.")


def sin(node: Any) -> ExpressionNode:
    return ExpressionNode("sin", [_ensure_expr_node(node)])


def cos(node: Any) -> ExpressionNode:
    return ExpressionNode("cos", [_ensure_expr_node(node)])


def expr_abs(node: Any) -> ExpressionNode:
    return ExpressionNode("abs", [_ensure_expr_node(node)])


def expr_min(*nodes: Any) -> ExpressionNode:
    if not nodes:
        raise InvalidMotionError("min() requires at least one argument.")
    return ExpressionNode("min", [_ensure_expr_node(n) for n in nodes])


def expr_max(*nodes: Any) -> ExpressionNode:
    if not nodes:
        raise InvalidMotionError("max() requires at least one argument.")
    return ExpressionNode("max", [_ensure_expr_node(n) for n in nodes])


def clamp(node: Any, low: Any, high: Any) -> ExpressionNode:
    return ExpressionNode("clamp", [_ensure_expr_node(node), _ensure_expr_node(low), _ensure_expr_node(high)])


def lerp(start: Any, end: Any, amount: Any) -> ExpressionNode:
    return ExpressionNode("lerp", [_ensure_expr_node(start), _ensure_expr_node(end), _ensure_expr_node(amount)])


def map_range(node: Any, in_min: Any, in_max: Any, out_min: Any, out_max: Any) -> ExpressionNode:
    return ExpressionNode(
        "map",
        [
            _ensure_expr_node(node),
            _ensure_expr_node(in_min),
            _ensure_expr_node(in_max),
            _ensure_expr_node(out_min),
            _ensure_expr_node(out_max),
        ],
    )


# Factory functions
def cycle(
    speed: float = 60.0,
    offset: float = 0.0,
    repeat: Optional[int] = None,
    yoyo: bool = False,
    delay: float = 0.0,
    enabled: bool = True,
    fallback: Optional[float] = None,
) -> CycleDriver:
    return CycleDriver(
        speed=speed,
        offset=offset,
        repeat=repeat,
        yoyo=yoyo,
        delay=delay,
        enabled=enabled,
        fallback=fallback,
    )


def pulse(
    min_val: float = 0.0,
    max_val: float = 1.0,
    speed: float = 1.0,
    easing: str = "smooth",
    repeat: Optional[int] = None,
    yoyo: bool = False,
    delay: float = 0.0,
    enabled: bool = True,
    fallback: Optional[float] = None,
) -> PulseDriver:
    return PulseDriver(
        min_val=min_val,
        max_val=max_val,
        speed=speed,
        easing=easing,
        repeat=repeat,
        yoyo=yoyo,
        delay=delay,
        enabled=enabled,
        fallback=fallback,
    )


def oscillate(
    from_val: float = 0.0,
    to_val: float = 1.0,
    duration: float = 1.0,
    easing: str = "ease_in_out",
    repeat: Optional[int] = None,
    yoyo: bool = True,
    delay: float = 0.0,
    enabled: bool = True,
    fallback: Optional[float] = None,
) -> OscillateDriver:
    return OscillateDriver(
        from_val=from_val,
        to_val=to_val,
        duration=duration,
        easing=easing,
        repeat=repeat,
        yoyo=yoyo,
        delay=delay,
        enabled=enabled,
        fallback=fallback,
    )


def keyframes(
    property: str,
    frames: Sequence[Tuple[float, Any]],
    easing: str = "ease_in_out",
    repeat: Optional[int] = None,
    yoyo: bool = False,
    delay: float = 0.0,
    enabled: bool = True,
    fallback: Optional[float] = None,
) -> KeyframesDriver:
    return KeyframesDriver(
        property=property,
        frames=frames,
        easing=easing,
        repeat=repeat,
        yoyo=yoyo,
        delay=delay,
        enabled=enabled,
        fallback=fallback,
    )


def transition(
    duration: float = 0.35,
    easing: str = "ease_out",
    delay: float = 0.0,
) -> TransitionDriver:
    return TransitionDriver(
        duration=duration,
        easing=easing,
        delay=delay,
    )
