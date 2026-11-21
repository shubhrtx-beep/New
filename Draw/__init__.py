"""Draw Library — Root Package Entry Point (Draw3).

Provides direct access to Shape, Shapes Collection, Line primitives,
Units, Color, Motion, Timeline, and Registry operations.
"""

from .shape import (
    shape,
    shapes,
    line,
    Shape,
    ShapeGroup,
    SideEdit,
    WholeEdit,
    SubEdit,
    GLOBAL_REGISTRY,
    DrawShapeError,
    ClosedShapeTopologyError,
    OverConstrainedTopologyError,
    ConflictingGeometryDefinitionError,
    MissingGeometryDefinitionError,
    UndefinedGeometryBoundsError,
    SideIndexOutOfBoundsError,
    DuplicateShapeNameError,
    ShapeNotFoundError,
    DegenerateGeometryError,
    InvalidCoordinateValueError,
    InvalidPolygonVertexCountError,
    InvalidLineVertexCountError,
    UnknownShapeTypeError,
    InvalidWarpGridError,
    HoleOutsideBoundaryError,
)
from .color import (
    color,
    palette,
    ColorAPI,
    ColorBinding,
    ColorValue,
    ColorGradient,
    ColorBody,
    ColorBorder,
    ColorShadow,
    ColorGlow,
    ColorFilter,
    ColorRegistry,
    GLOBAL_COLOR_REGISTRY,
    PaletteRegistry,
    IN_SHAPE,
    DrawColorError,
    InvalidColorValueError,
    UnknownColorNameError,
    InvalidHexColorError,
    ColorTokenCycleError,
    InvalidMotionError,
    DuplicateColorNameError,
    ColorNotFoundError,
)
from .motion import (
    motion_api,
    time_line_api,
    move,
    timeline,
    Motion,
    MoveAnimation,
    ChannelAnimation,
    Timeline,
    TimelineSection,
    ResolvedChannel,
    MotionAPI,
    TimelineAPI,
    MotionRegistry,
    GLOBAL_MOTION_REGISTRY,
    SUPPORTED_EASINGS,
    SUPPORTED_MOVE_CHANNELS,
    DrawMotionError,
    InvalidEasingError,
    InvalidChannelError,
    InvalidChannelFormatError,
    InvalidDurationError,
    DuplicateMotionNameError,
    MotionNotFoundError,
    DuplicateTimelineNameError,
    TimelineNotFoundError,
    TimelineSectionNotFoundError,
    TimelineSectionCountMismatchError,
    InvalidTimelineError,
    InvalidPlaybackError,
    PlaybackConfig,
    parse_playback,
    playback,
    once,
    repeat,
    loop,
    ping_pong,
    reverse,
    alternate,
    yoyo,
    restart,
    hold,
    freeze,
    seek,
    ONCE,
    REPEAT,
    LOOP,
    PING_PONG,
    REVERSE,
    ALTERNATE,
    YOYO,
    RESTART,
    HOLD,
    FREEZE,
    SUPPORTED_PLAYBACK_MODES,
    SUPPORTED_FILL_MODES,
    transform,
    transfrom,
    physical,
    math as motion_math,
    Vector2D,
    vec2,
    PhysicalBody,
    PhysicalTransform,
    MathematicalTransform,
    StandardTransform,
    fire,
    smoke,
    lightning,
    shockwave,
    water_splash,
    energy_vortex,
)
from .motion_graph import (
    motion_graph,
    MotionGraph,
    MotionGraphRegistry,
    MotionGraphAPI,
    GLOBAL_MOTION_GRAPH_REGISTRY,
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
from . import windows as window
from .windows import (
    Window,
    ElementName,
    Region,
    DrawWindowError,
    DuplicateWindowNameError,
    WindowNotFoundError,
    InvalidRegionRatioError,
    InvalidFrameConfigError,
    WindowLifecycleError,
    InvalidAnchorError,
    InvalidActionError,
    GLOBAL_WINDOW_REGISTRY,
    GLOBAL_ELEMENT_REGISTRY,
)
from . import maths
from .maths import (
    set_canvas_size,
    get_canvas_size,
    set_dpi,
    get_dpi,
    resolve,
    resolve_size,
    resolve_position,
    resolve_ratio,
)

# ── Motion callable namespace (Draw.motion, Draw.time_line, Draw.timeline) ──
motion = motion_api
time_line = time_line_api

# Attach sub-constructors and helpers directly onto motion namespace
motion.move = move  # type: ignore[attr-defined]
motion.transform = transform  # type: ignore[attr-defined]
motion.transfrom = transfrom  # type: ignore[attr-defined]
motion.physical = physical  # type: ignore[attr-defined]
motion.math = motion_math  # type: ignore[attr-defined]
motion.Vector2D = Vector2D  # type: ignore[attr-defined]
motion.vec2 = vec2  # type: ignore[attr-defined]
motion.playback = playback  # type: ignore[attr-defined]
motion.once = once  # type: ignore[attr-defined]
motion.repeat = repeat  # type: ignore[attr-defined]
motion.loop = loop  # type: ignore[attr-defined]
motion.ping_pong = ping_pong  # type: ignore[attr-defined]
motion.reverse = reverse  # type: ignore[attr-defined]
motion.alternate = alternate  # type: ignore[attr-defined]
motion.yoyo = yoyo  # type: ignore[attr-defined]
motion.restart = restart  # type: ignore[attr-defined]
motion.hold = hold  # type: ignore[attr-defined]
motion.freeze = freeze  # type: ignore[attr-defined]
motion.fire = fire  # type: ignore[attr-defined]
motion.smoke = smoke  # type: ignore[attr-defined]
motion.lightning = lightning  # type: ignore[attr-defined]
motion.shockwave = shockwave  # type: ignore[attr-defined]
motion.water_splash = water_splash  # type: ignore[attr-defined]
motion.energy_vortex = energy_vortex  # type: ignore[attr-defined]
motion.motion_graph = motion_graph  # type: ignore[attr-defined]
motion.graph = motion_graph  # type: ignore[attr-defined]
motion.ONCE = ONCE  # type: ignore[attr-defined]
motion.REPEAT = REPEAT  # type: ignore[attr-defined]
motion.LOOP = LOOP  # type: ignore[attr-defined]
motion.PING_PONG = PING_PONG  # type: ignore[attr-defined]
motion.REVERSE = REVERSE  # type: ignore[attr-defined]
motion.ALTERNATE = ALTERNATE  # type: ignore[attr-defined]
motion.YOYO = YOYO  # type: ignore[attr-defined]
motion.RESTART = RESTART  # type: ignore[attr-defined]
motion.HOLD = HOLD  # type: ignore[attr-defined]
motion.FREEZE = FREEZE  # type: ignore[attr-defined]


# Convenient top-level helpers
side_edit = SideEdit
edit = WholeEdit
sub_edit = SubEdit
group = shapes
remove = GLOBAL_REGISTRY.remove
copy = GLOBAL_REGISTRY.copy

__all__ = [
    # Shape
    "shape",
    "shapes",
    "line",
    "group",
    "remove",
    "copy",
    "side_edit",
    "edit",
    "sub_edit",
    "Shape",
    "ShapeGroup",
    "SideEdit",
    "WholeEdit",
    "SubEdit",
    "GLOBAL_REGISTRY",
    "DrawShapeError",
    "ClosedShapeTopologyError",
    "OverConstrainedTopologyError",
    "ConflictingGeometryDefinitionError",
    "MissingGeometryDefinitionError",
    "UndefinedGeometryBoundsError",
    "SideIndexOutOfBoundsError",
    "DuplicateShapeNameError",
    "ShapeNotFoundError",
    "DegenerateGeometryError",
    "InvalidCoordinateValueError",
    "InvalidPolygonVertexCountError",
    "InvalidLineVertexCountError",
    "UnknownShapeTypeError",
    "InvalidWarpGridError",
    "HoleOutsideBoundaryError",
    # Color
    "color",
    "palette",
    "ColorAPI",
    "ColorBinding",
    "ColorValue",
    "ColorGradient",
    "ColorBody",
    "ColorBorder",
    "ColorShadow",
    "ColorGlow",
    "ColorFilter",
    "ColorRegistry",
    "GLOBAL_COLOR_REGISTRY",
    "PaletteRegistry",
    "IN_SHAPE",
    "DrawColorError",
    "InvalidColorValueError",
    "UnknownColorNameError",
    "InvalidHexColorError",
    "ColorTokenCycleError",
    "InvalidMotionError",
    "DuplicateColorNameError",
    "ColorNotFoundError",
    # Motion & Timeline
    "motion",
    "time_line",
    "timeline",
    "move",
    "Motion",
    "MoveAnimation",
    "ChannelAnimation",
    "Timeline",
    "TimelineSection",
    "ResolvedChannel",
    "MotionAPI",
    "TimelineAPI",
    "MotionRegistry",
    "GLOBAL_MOTION_REGISTRY",
    "SUPPORTED_EASINGS",
    "SUPPORTED_MOVE_CHANNELS",
    "DrawMotionError",
    "InvalidEasingError",
    "InvalidChannelError",
    "InvalidChannelFormatError",
    "InvalidDurationError",
    "DuplicateMotionNameError",
    "MotionNotFoundError",
    "DuplicateTimelineNameError",
    "TimelineNotFoundError",
    "TimelineSectionNotFoundError",
    "TimelineSectionCountMismatchError",
    "InvalidTimelineError",
    "InvalidPlaybackError",
    "PlaybackConfig",
    "parse_playback",
    "playback",
    "once",
    "repeat",
    "loop",
    "ping_pong",
    "reverse",
    "alternate",
    "yoyo",
    "restart",
    "hold",
    "freeze",
    "seek",
    "ONCE",
    "REPEAT",
    "LOOP",
    "PING_PONG",
    "REVERSE",
    "ALTERNATE",
    "YOYO",
    "RESTART",
    "HOLD",
    "FREEZE",
    "transform",
    "transfrom",
    "physical",
    "Vector2D",
    "vec2",
    "PhysicalBody",
    "PhysicalTransform",
    "MathematicalTransform",
    "StandardTransform",
    "fire",
    "smoke",
    "lightning",
    "shockwave",
    "water_splash",
    "energy_vortex",
    # Motion Graph
    "motion_graph",
    "MotionGraph",
    "MotionGraphRegistry",
    "MotionGraphAPI",
    "GLOBAL_MOTION_GRAPH_REGISTRY",
    "DrawMotionGraphError",
    "InvalidMotionGraphError",
    "DuplicateMotionGraphNameError",
    "MotionGraphNotFoundError",
    "CircularGraphReferenceError",
    "InvalidInterpolationModeError",
    "InvalidGraphPointsError",
    "InvalidGraphCombineError",
    "GraphDefinitionConflictError",
    # Window
    "window",
    "Window",
    "ElementName",
    "Region",
    "GLOBAL_WINDOW_REGISTRY",
    "GLOBAL_ELEMENT_REGISTRY",
    "DrawWindowError",
    "DuplicateWindowNameError",
    "WindowNotFoundError",
    "InvalidRegionRatioError",
    "InvalidFrameConfigError",
    "WindowLifecycleError",
    "InvalidAnchorError",
    "InvalidActionError",
    # Maths & Units
    "maths",
    "resolve",
    "resolve_size",
    "resolve_position",
    "resolve_ratio",
    "set_canvas_size",
    "get_canvas_size",
    "set_dpi",
    "get_dpi",
]
