"""Draw Shape API — Authoritative Working Data Structure (Shape).

Represents the Python-side source of truth for 2D geometry, transforms,
and hierarchy before serialization or runtime caching.
"""

import itertools
from typing import (
    Tuple,
    List,
    Dict,
    Any,
    Optional,
    Sequence,
    Union,
)
from .errors import (
    ConflictingGeometryDefinitionError,
    MissingGeometryDefinitionError,
    InvalidPolygonVertexCountError,
    InvalidLineVertexCountError,
    ClosedShapeTopologyError,
    OverConstrainedTopologyError,
    InvalidCoordinateValueError,
)
from ..maths import (
    resolve as maths_resolve,
    resolve_size as maths_resolve_size,
    resolve_position as maths_resolve_position,
    resolve_origin as maths_resolve_origin,
    resolve_corner_radius as maths_resolve_corner_radius,
    get_canvas_size,
)
from .geometry import (
    Point2D,
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

# Monotonically increasing unique shape ID generator
_SHAPE_ID_COUNTER = itertools.count(101)


class Shape:
    """Working Data Structure for a 2D Shape in Draw3."""

    def __init__(
        self,
        name: str,
        position: Tuple[Union[float, int, str], Union[float, int, str]] = (0.0, 0.0),
        closed: bool = True,
        type: Optional[str] = None,
        vertices: Optional[int] = None,
        coordinates: Optional[Sequence[Point2D]] = None,
        generate: Optional[Sequence[str]] = None,
        size: Tuple[Union[float, int, str], Union[float, int, str]] = (100.0, 100.0),
        scale: Tuple[float, float] = (1.0, 1.0),
        origin: Union[Tuple[Union[float, int, str], Union[float, int, str]], str] = (0.0, 0.0),
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
        # Internal reference to scene registry
        _registry: Optional[Any] = None,
    ) -> None:
        self.shape_id: int = next(_SHAPE_ID_COUNTER)
        self.name: str = str(name)
        self.closed: bool = bool(closed)
        self.z: int = int(z)
        self.parent: Optional[str] = parent
        self.clip: bool = bool(clip)
        self.scoped: bool = bool(scoped)
        self.dynamic: List[str] = list(dynamic or [])
        self.tags: List[str] = list(tags or [])
        self.sub_shapes: List["Shape"] = []
        self._registry = _registry
        self.color: Any = self._resolve_color(color)

        # Version counters
        self.geometry_version: int = 1
        self.transform_version: int = 1
        self.metadata_version: int = 1

        # Resolve sizing and position via Draw.maths universal units
        ref_w, ref_h = self._get_reference_dimensions()
        self.resolved_size: Tuple[float, float] = maths_resolve_size(size, ref_w, ref_h)
        self.resolved_position: Tuple[float, float] = maths_resolve_position(position, ref_w, ref_h)
        self.resolved_origin: Tuple[float, float] = maths_resolve_origin(
            origin, self.resolved_size[0], self.resolved_size[1]
        )

        self.transform: Transform2D = Transform2D(
            position=self.resolved_position,
            scale=scale,
            rotation=0.0,
            origin=self.resolved_origin,
        )

        # Store raw inputs for re-resolution on parent scope change
        self._raw_size_input = size
        self._raw_position_input = position
        self.raw_type = type
        self.raw_vertices_count = vertices
        self.raw_coordinates = coordinates
        self.raw_generate = list(generate or [])

        # Store side, whole, and sub edits
        self.side_edit_cfg = self._parse_side_edit(side_edit)
        self.whole_edit_cfg = self._parse_whole_edit(edit)
        self.sub_edit_cfg = self._parse_sub_edit(sub_edit)

        # Build geometry
        self.vertices: List[Point2D] = []
        self.indices: List[int] = []
        self._build_geometry()

        # Handle sub_edit children
        if self.sub_edit_cfg and self.sub_edit_cfg.shapes:
            for child in self.sub_edit_cfg.shapes:
                if isinstance(child, Shape):
                    child.parent = self.name
                    child.clip = self.sub_edit_cfg.clip
                    child._re_resolve_parent_scope(self.resolved_size)
                    self.sub_shapes.append(child)

    def _re_resolve_parent_scope(self, parent_size: Tuple[float, float]) -> None:
        """Re-evaluates parent-relative units (%, vw, etc.) against parent bounds."""
        ref_w, ref_h = parent_size
        self.resolved_size = maths_resolve_size(self._raw_size_input, ref_w, ref_h)
        self.resolved_position = maths_resolve_position(self._raw_position_input, ref_w, ref_h)
        self.transform.position = self.resolved_position
        self._build_geometry()

    def _get_reference_dimensions(self) -> Tuple[float, float]:
        """Returns parent bounds if nested, or canvas size if top-level.
        Parent can be another Shape, a Window name, or a Window Region name.
        """
        if self.parent:
            if self._registry and self._registry.exists(self.parent):
                parent_shape = self._registry.get(self.parent)
                if parent_shape:
                    return (parent_shape.resolved_size[0], parent_shape.resolved_size[1])

            try:
                from ..windows.registry import GLOBAL_WINDOW_REGISTRY
                parent_str = str(self.parent)
                if ":" in parent_str:
                    win_name, reg_name = parent_str.split(":", 1)
                    if GLOBAL_WINDOW_REGISTRY.exists(win_name):
                        win = GLOBAL_WINDOW_REGISTRY.get(win_name)
                        r = win.region(reg_name)
                        if r:
                            return (r.width, r.height)
                        return (float(win.size[0]), float(win.size[1]))

                if GLOBAL_WINDOW_REGISTRY.exists(parent_str):
                    win = GLOBAL_WINDOW_REGISTRY.get(parent_str)
                    return (float(win.size[0]), float(win.size[1]))

                for win in GLOBAL_WINDOW_REGISTRY._windows.values():
                    r = win.region(parent_str)
                    if r:
                        return (r.width, r.height)
            except Exception:
                pass

        return get_canvas_size()

    def _parse_side_edit(self, cfg: Any) -> Optional[SideEdit]:
        if isinstance(cfg, SideEdit):
            return cfg
        if isinstance(cfg, dict):
            return SideEdit(**cfg)
        return None

    def _parse_whole_edit(self, cfg: Any) -> Optional[WholeEdit]:
        if isinstance(cfg, WholeEdit):
            return cfg
        if isinstance(cfg, dict):
            return WholeEdit(**cfg)
        return None

    def _parse_sub_edit(self, cfg: Any) -> Optional[SubEdit]:
        if isinstance(cfg, SubEdit):
            return cfg
        if isinstance(cfg, dict):
            return SubEdit(**cfg)
        return None

    def _validate_geometry_mode(self) -> None:
        """Enforces mutual exclusivity among type, vertices, and coordinates."""
        modes = [
            self.raw_type is not None,
            self.raw_vertices_count is not None,
            self.raw_coordinates is not None,
        ]
        count = sum(modes)
        if count == 0:
            raise MissingGeometryDefinitionError(
                f"Shape '{self.name}' must specify exactly one definition mode: 'type', 'vertices', or 'coordinates'."
            )
        if count > 1:
            raise ConflictingGeometryDefinitionError(
                f"Shape '{self.name}' received conflicting definitions. Specify only one of 'type', 'vertices', or 'coordinates'."
            )

    def _build_geometry(self) -> None:
        """Synthesizes, modifies, and triangulates base vertices."""
        self._validate_geometry_mode()
        w, h = self.resolved_size

        # 1. Base Geometry Generation
        if self.raw_type is not None:
            verts, idxs = GeometryBuilder.generate_primitive(self.raw_type, w, h)
        elif self.raw_vertices_count is not None:
            verts, idxs = GeometryBuilder.create_regular_polygon(self.raw_vertices_count, w, h)
        elif self.raw_coordinates is not None:
            verts = list(self.raw_coordinates)
            if self.closed and len(verts) < 3:
                raise InvalidPolygonVertexCountError(
                    f"Closed polygons require at least 3 vertices, got {len(verts)}."
                )
            if not self.closed and len(verts) < 2:
                raise InvalidLineVertexCountError(
                    f"Open lines require at least 2 vertices, got {len(verts)}."
                )
            idxs = triangulate_simple_polygon(verts) if self.closed else []
        else:
            verts, idxs = [], []

        # 2. Side Edits (bend, warp, side length/angle kinematics)
        if self.side_edit_cfg:
            se = self.side_edit_cfg
            # Check topology constraints
            if self.closed and not se.force_open:
                if se.side_length and se.side_angle:
                    raise OverConstrainedTopologyError(
                        f"Cannot specify both 'side_angle' and 'side_length' on closed shape '{self.name}'."
                    )
                if se.side_length:
                    raise ClosedShapeTopologyError(
                        f"Cannot apply independent 'side_length' to closed shape '{self.name}'. "
                        f"Set closed=False or use 'scale' instead."
                    )
                if se.side_angle:
                    raise ClosedShapeTopologyError(
                        f"Cannot apply independent 'side_angle' to closed shape '{self.name}'. "
                        f"Set closed=False or use 'force_open=True'."
                    )

            if se.bend:
                verts = ModifierPipeline.apply_bend(verts, se.bend, self.closed)
            if se.warp:
                verts = ModifierPipeline.apply_warp(verts, se.warp)

        # 3. Whole Edits (corner rounding, remove, flip, rotate)
        if self.whole_edit_cfg:
            we = self.whole_edit_cfg
            if we.remove:
                verts, self.closed = ModifierPipeline.apply_remove(verts, we.remove, self.closed)
            if we.edges and self.closed:
                min_dim = min(self.resolved_size[0], self.resolved_size[1])
                resolved_radii = maths_resolve_corner_radius(we.edges, min_dim, len(verts))
                verts = ModifierPipeline.apply_corner_rounding(verts, resolved_radii, self.closed)
            if we.flip:
                verts = ModifierPipeline.apply_flip(verts, we.flip)
            if we.rotate:
                self.transform.rotation = we.rotate

        # 4. Handle Holes / Exclude Cutouts
        holes: List[List[Point2D]] = []
        if self.side_edit_cfg and self.side_edit_cfg.exclude:
            for ex in self.side_edit_cfg.exclude:
                if "line" in ex and len(ex["line"]) >= 3:
                    holes.append(list(ex["line"]))

        if holes and self.closed:
            verts, idxs = triangulate_polygon_with_holes(verts, holes)
        elif self.closed and len(verts) >= 3:
            idxs = triangulate_simple_polygon(verts)
        else:
            idxs = []

        self.vertices = verts
        self.indices = idxs

    @property
    def num_sides(self) -> int:
        """Returns the number of boundary edges in the shape."""
        n = len(self.vertices)
        return n if self.closed else max(0, n - 1)

    @property
    def bounds(self) -> Dict[str, float]:
        """Calculates Axis-Aligned Bounding Box (AABB) of the shape."""
        return Transform2D.compute_bounds(self.vertices)

    def update(self, **kwargs: Any) -> "Shape":
        """Mutates shape properties at runtime and increments relevant dirty versions."""
        geom_changed = False
        transform_changed = False
        meta_changed = False

        if "size" in kwargs:
            ref_w, ref_h = self._get_reference_dimensions()
            self.resolved_size = maths_resolve_size(kwargs["size"], ref_w, ref_h)
            self._raw_size_input = kwargs["size"]
            geom_changed = True

        if "position" in kwargs:
            ref_w, ref_h = self._get_reference_dimensions()
            self.resolved_position = maths_resolve_position(kwargs["position"], ref_w, ref_h)
            self._raw_position_input = kwargs["position"]
            self.transform.position = self.resolved_position
            transform_changed = True

        if "scale" in kwargs:
            self.transform.scale = (float(kwargs["scale"][0]), float(kwargs["scale"][1]))
            transform_changed = True

        if "rotate" in kwargs or "rotation" in kwargs:
            r = kwargs.get("rotate", kwargs.get("rotation"))
            self.transform.rotation = float(r)
            transform_changed = True

        if "origin" in kwargs:
            self.resolved_origin = maths_resolve_origin(
                kwargs["origin"], self.resolved_size[0], self.resolved_size[1]
            )
            self.transform.origin = self.resolved_origin
            transform_changed = True

        if "z" in kwargs:
            self.z = int(kwargs["z"])
            meta_changed = True

        if "tags" in kwargs:
            self.tags = list(kwargs["tags"])
            meta_changed = True

        if "color" in kwargs:
            self.color = self._resolve_color(kwargs["color"])
            meta_changed = True

        if "side_edit" in kwargs:
            self.side_edit_cfg = self._parse_side_edit(kwargs["side_edit"])
            geom_changed = True

        if "edit" in kwargs:
            self.whole_edit_cfg = self._parse_whole_edit(kwargs["edit"])
            geom_changed = True

        if geom_changed:
            self._build_geometry()
            self.geometry_version += 1

        if transform_changed:
            self.transform_version += 1

        if meta_changed:
            self.metadata_version += 1

        return self

    def query(self, keys: Sequence[str]) -> Dict[str, Any]:
        """Inspects and returns requested properties without allocating unrequested buffers."""
        b = self.bounds
        data_map: Dict[str, Any] = {
            "name": self.name,
            "id": self.shape_id,
            "position": self.transform.position,
            "size": self.resolved_size,
            "scale": self.transform.scale,
            "rotation": self.transform.rotation,
            "origin": self.transform.origin,
            "vertices": len(self.vertices),  # Returns count by default
            "z": self.z,
            "closed": self.closed,
            "bounds": b,
            "parent_id": self.parent if self.parent is not None else -1,
            "num_sub_shapes": len(self.sub_shapes),
            "tags": list(self.tags),
        }

        # Secondary metadata generators on explicit request
        if "map" in keys:
            data_map["map"] = MetadataGenerator.generate_map(self.vertices, self.closed)
        if "hitbox" in keys:
            data_map["hitbox"] = MetadataGenerator.generate_hitbox(self.vertices)
        if "indexing" in keys:
            data_map["indexing"] = MetadataGenerator.generate_indexing(self.vertices, self.closed)

        result: Dict[str, Any] = {}
        for k in keys:
            if k in data_map:
                result[k] = data_map[k]
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the authoritative Working Data representation into a dictionary."""
        flat_vertices: List[float] = []
        for x, y in self.vertices:
            flat_vertices.extend([x, y])

        color_data = None
        if self.color is not None:
            if hasattr(self.color, "to_dict"):
                color_data = self.color.to_dict()
            elif isinstance(self.color, str):
                color_data = self.color

        return {
            "id": self.shape_id,
            "name": self.name,
            "type": self.raw_type or ("regular_polygon" if self.raw_vertices_count else "custom"),
            "parent_id": self.parent if self.parent is not None else -1,
            "closed": self.closed,
            "z": self.z,
            "color": color_data,
            "transform": self.transform.to_dict(),
            "geometry": {
                "vertex_count": len(self.vertices),
                "index_count": len(self.indices),
                "vertices": flat_vertices,
                "indices": list(self.indices),
            },
            "sub_shape_ids": [child.shape_id for child in self.sub_shapes],
            "versions": {
                "geometry": self.geometry_version,
                "transform": self.transform_version,
                "metadata": self.metadata_version,
            },
        }

    def copy(self, new_name: str) -> "Shape":
        """Clones the shape with a new name and unique ID."""
        clone = Shape(
            name=new_name,
            position=self.resolved_position,
            closed=self.closed,
            type=self.raw_type,
            vertices=self.raw_vertices_count,
            coordinates=list(self.raw_coordinates) if self.raw_coordinates else None,
            generate=list(self.raw_generate),
            size=self.resolved_size,
            scale=self.transform.scale,
            origin=self.transform.origin,
            z=self.z,
            parent=self.parent,
            clip=self.clip,
            scoped=self.scoped,
            side_edit=self.side_edit_cfg,
            edit=self.whole_edit_cfg,
            sub_edit=self.sub_edit_cfg,
            dynamic=list(self.dynamic),
            tags=list(self.tags),
            color=self.color,
            _registry=self._registry,
        )
        if self._registry:
            self._registry.register(clone)
        return clone

    def _resolve_color(self, color_input: Any) -> Any:
        """Resolves color parameter: registered name, inline binding, or auto-wrapped value."""
        if color_input is None:
            return None
        try:
            from ..color import GLOBAL_COLOR_REGISTRY, ColorBinding, ColorValue, IN_SHAPE, body

            if isinstance(color_input, ColorBinding):
                if color_input.name == IN_SHAPE:
                    color_input.name = self.name
                    GLOBAL_COLOR_REGISTRY.register(color_input)
                return color_input

            if isinstance(color_input, str):
                if GLOBAL_COLOR_REGISTRY.exists(color_input):
                    return GLOBAL_COLOR_REGISTRY.get(color_input)
                # Auto-wrap hex or CSS color string
                try:
                    b = ColorBinding(name=self.name, body=body(fill=color_input))
                    GLOBAL_COLOR_REGISTRY.register(b)
                    return b
                except Exception:
                    return color_input

            if isinstance(color_input, (ColorValue, tuple, list)):
                try:
                    b = ColorBinding(name=self.name, body=body(fill=color_input))
                    GLOBAL_COLOR_REGISTRY.register(b)
                    return b
                except Exception:
                    return color_input
        except ImportError:
            pass

        return color_input

    def remove(self) -> bool:
        """Removes this shape from the active scene registry."""
        if self._registry:
            return self._registry.remove([self.name]) > 0
        return False
