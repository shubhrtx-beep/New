"""Draw Motion Graph Subsystem Package.

Exposes:
- Draw.motion_graph(): callable interface for defining time-to-progress curves
  using points or combined existing curves.
- MotionGraph: core motion graph representation and evaluation engine.
- MotionGraphRegistry: registry managing custom graphs.
"""

from .errors import (
    DrawMotionGraphError,
    InvalidMotionGraphError,
    DuplicateMotionGraphNameError,
    MotionGraphNotFoundError,
    CircularGraphReferenceError,
    InvalidInterpolationModeError,
    InvalidGraphPointsError,
    InvalidGraphCombineError,
    GraphDefinitionConflictError,
)
from .interpolation import (
    LINEAR,
    SMOOTH,
    STEP,
    SUPPORTED_INTERPOLATION_MODES,
    validate_interpolation_mode,
    interpolate_linear,
    interpolate_step,
    interpolate_smooth,
    MonotoneCubicSpline,
)
from .graph import (
    MotionGraph,
    evaluate_builtin_easing,
)
from .registry import (
    MotionGraphRegistry,
    MotionGraphAPI,
    GLOBAL_MOTION_GRAPH_REGISTRY,
)

# Canonical callable instance
motion_graph = MotionGraphAPI(GLOBAL_MOTION_GRAPH_REGISTRY)

__all__ = [
    # Errors
    "DrawMotionGraphError",
    "InvalidMotionGraphError",
    "DuplicateMotionGraphNameError",
    "MotionGraphNotFoundError",
    "CircularGraphReferenceError",
    "InvalidInterpolationModeError",
    "InvalidGraphPointsError",
    "InvalidGraphCombineError",
    "GraphDefinitionConflictError",
    # Interpolation
    "LINEAR",
    "SMOOTH",
    "STEP",
    "SUPPORTED_INTERPOLATION_MODES",
    "validate_interpolation_mode",
    "interpolate_linear",
    "interpolate_step",
    "interpolate_smooth",
    "MonotoneCubicSpline",
    # Graph & Evaluation
    "MotionGraph",
    "evaluate_builtin_easing",
    # Registry & API
    "MotionGraphRegistry",
    "MotionGraphAPI",
    "GLOBAL_MOTION_GRAPH_REGISTRY",
    "motion_graph",
]
