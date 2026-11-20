"""Draw Shape Subsystem Package.

Exposes shape creation, batch collections, line primitives, and modifiers.
"""

from typing import (
    Tuple,
    Union,
    Optional,
    Sequence,
    Dict,
    Any,
)
from .errors import *
from .units import (
    UnitResolver,
    set_canvas_size,
    get_canvas_size,
)
from .geometry import (
    GeometryBuilder,
    MetadataGenerator,
    triangulate_simple_polygon,
    triangulate_polygon_with_holes,
)
from .transform import Transform2D
from .modifiers import (
    SideEdit,
    WholeEdit,
    SubEdit,
    ModifierPipeline,
)
from .shape import Shape
from .group import ShapeGroup
from .registry import (
    SceneRegistry,
    ShapesNamespace,
    GLOBAL_REGISTRY,
)

# Canonical Registry / Batch Namespace
shapes = ShapesNamespace(GLOBAL_REGISTRY)


def shape(
    name: str,
    position: Tuple[Union[float, str], Union[float, str]] = (0.0, 0.0),
    closed: bool = True,
    type: Optional[str] = None,
    vertices: Optional[int] = None,
    coordinates: Optional[Sequence[Tuple[float, float]]] = None,
    generate: Optional[Sequence[str]] = None,
    size: Tuple[Union[float, str], Union[float, str]] = (100.0, 100.0),
    scale: Tuple[float, float] = (1.0, 1.0),
    origin: Union[Tuple[float, float], str] = (0.0, 0.0),
    z: int = 0,
    parent: Optional[str] = None,
    clip: bool = False,
    scoped: bool = False,
    side_edit: Optional[Union[SideEdit, Dict[str, Any]]] = None,
    edit: Optional[Union[WholeEdit, Dict[str, Any]]] = None,
    sub_edit: Optional[Union[SubEdit, Dict[str, Any]]] = None,
    dynamic: Optional[Sequence[str]] = None,
    tags: Optional[Sequence[str]] = None,
    color: Optional[Union[str, Any]] = None,
    coordinate: Optional[Sequence[Tuple[float, float]]] = None,  # Deprecated compatibility alias
) -> Shape:
    """Creates, registers, and returns an authoritative 2D Shape instance."""
    # Compatibility normalization
    if coordinate is not None:
        if coordinates is not None:
            raise ConflictingGeometryDefinitionError("Cannot pass both 'coordinate' and 'coordinates'.")
        coordinates = coordinate

    s = Shape(
        name=name,
        position=position,
        closed=closed,
        type=type,
        vertices=vertices,
        coordinates=coordinates,
        generate=generate,
        size=size,
        scale=scale,
        origin=origin,
        z=z,
        parent=parent,
        clip=clip,
        scoped=scoped,
        side_edit=side_edit,
        edit=edit,
        sub_edit=sub_edit,
        dynamic=dynamic,
        tags=tags,
        color=color,
        _registry=GLOBAL_REGISTRY,
    )
    GLOBAL_REGISTRY.register(s)
    return s


def line(
    name: str,
    coordinates: Sequence[Tuple[float, float]],
    position: Tuple[Union[float, str], Union[float, str]] = (0.0, 0.0),
    scale: Tuple[float, float] = (1.0, 1.0),
    origin: Union[Tuple[float, float], str] = (0.0, 0.0),
    z: int = 0,
    parent: Optional[str] = None,
    clip: bool = False,
    scoped: bool = False,
    dynamic: Optional[Sequence[str]] = None,
    tags: Optional[Sequence[str]] = None,
    closed: bool = False,
) -> Shape:
    """Creates, registers, and returns an open path Line shape (closed=False by default)."""
    return shape(
        name=name,
        coordinates=coordinates,
        position=position,
        scale=scale,
        origin=origin,
        z=z,
        parent=parent,
        clip=clip,
        scoped=scoped,
        dynamic=dynamic,
        tags=tags,
        closed=closed,
    )


# Attach backward-compatibility delegates onto shape constructor
class _SideNamespace:
    edit = SideEdit

shape.update = GLOBAL_REGISTRY.update  # type: ignore[attr-defined]
shape.list = GLOBAL_REGISTRY.list      # type: ignore[attr-defined]
shape.copy = GLOBAL_REGISTRY.copy      # type: ignore[attr-defined]
shape.remove = GLOBAL_REGISTRY.remove  # type: ignore[attr-defined]
shape.side = _SideNamespace()          # type: ignore[attr-defined]


__all__ = [
    "shape",
    "shapes",
    "line",
    "Shape",
    "ShapeGroup",
    "SideEdit",
    "WholeEdit",
    "SubEdit",
    "set_canvas_size",
    "get_canvas_size",
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
]
