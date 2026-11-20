"""Draw Shape API — ShapeGroup and Batch Collection Management.

Implements collective batch transformations, aggregate bounding boxes,
and Python context manager lifecycles (with Draw.shapes(...) as group:).
"""

from typing import (
    Sequence,
    List,
    Optional,
    Tuple,
    Union,
    Dict,
    Any,
)
from .shape import Shape
from .transform import Transform2D

# Thread-local/context stack for active shape groups
_ACTIVE_GROUP_STACK: List["ShapeGroup"] = []


def get_active_group() -> Optional["ShapeGroup"]:
    """Returns the currently active context group if inside a 'with Draw.shapes():' block."""
    return _ACTIVE_GROUP_STACK[-1] if _ACTIVE_GROUP_STACK else None


class ShapeGroup:
    """Represents a collection of shapes with collective transform and lifecycle management."""

    def __init__(
        self,
        items: Optional[Sequence[Shape]] = None,
        name: Optional[str] = None,
        position: Tuple[Union[float, str], Union[float, str]] = (0.0, 0.0),
        scale: Tuple[float, float] = (1.0, 1.0),
        rotation: float = 0.0,
        origin: Tuple[float, float] = (0.0, 0.0),
        z_offset: int = 0,
        tags: Optional[Sequence[str]] = None,
        dynamic: Optional[Sequence[str]] = None,
        _registry: Optional[Any] = None,
    ) -> None:
        self.name: Optional[str] = name
        self.shapes: List[Shape] = list(items or [])
        self.position = position
        self.scale = scale
        self.rotation = float(rotation)
        self.origin = origin
        self.z_offset = int(z_offset)
        self.tags = list(tags or [])
        self.dynamic = list(dynamic or [])
        self._registry = _registry

        # Apply initial z_offset and tags to member shapes
        if self.z_offset != 0:
            for s in self.shapes:
                s.z += self.z_offset
        if self.tags:
            for s in self.shapes:
                for t in self.tags:
                    if t not in s.tags:
                        s.tags.append(t)

    def add(self, shape: Shape) -> None:
        """Adds a shape into the group."""
        if shape not in self.shapes:
            if self.z_offset != 0:
                shape.z += self.z_offset
            for t in self.tags:
                if t not in shape.tags:
                    shape.tags.append(t)
            self.shapes.append(shape)

    @property
    def bounds(self) -> Dict[str, float]:
        """Calculates aggregate Axis-Aligned Bounding Box (AABB) enclosing all member shapes."""
        if not self.shapes:
            return {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0, "width": 0.0, "height": 0.0}

        all_vertices = []
        for s in self.shapes:
            # Transform vertices by shape local transform
            transformed = s.transform.apply_to_vertices(s.vertices)
            all_vertices.extend(transformed)

        return Transform2D.compute_bounds(all_vertices)

    def update(self, **kwargs: Any) -> "ShapeGroup":
        """Applies batch updates across all member shapes."""
        for s in self.shapes:
            s.update(**kwargs)
        return self

    def remove(self) -> int:
        """Atomically unregisters all member shapes from the scene registry."""
        names = [s.name for s in self.shapes]
        if self._registry:
            count = self._registry.remove(names)
            self.shapes.clear()
            return count
        return 0

    def __iter__(self):
        return iter(self.shapes)

    def __len__(self) -> int:
        return len(self.shapes)

    def __getitem__(self, index: int) -> Shape:
        return self.shapes[index]

    def __enter__(self) -> "ShapeGroup":
        _ACTIVE_GROUP_STACK.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if _ACTIVE_GROUP_STACK and _ACTIVE_GROUP_STACK[-1] is self:
            _ACTIVE_GROUP_STACK.pop()
