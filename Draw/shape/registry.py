"""Draw Shape API — Scene Registry and Namespace Delegation.

Maintains the authoritative scene graph of active shapes, handles duplicate name
detection, weakref-scoped lifecycles, and exposes Draw.shapes both as a callable
batch constructor and as the canonical scene query/mutation namespace.
"""

import weakref
from typing import (
    Dict,
    Union,
    List,
    Tuple,
    Optional,
    Sequence,
    Any,
)
from .errors import (
    DuplicateShapeNameError,
    ShapeNotFoundError,
)
from .shape import Shape
from .group import ShapeGroup, get_active_group


class SceneRegistry:
    """Manages registered Shape instances in the active scene."""

    def __init__(self) -> None:
        self._strong_registry: Dict[str, Shape] = {}
        self._weak_registry: Dict[str, weakref.ref] = {}
        self._groups: Dict[str, ShapeGroup] = {}

    def register(self, shape: Shape) -> Shape:
        """Registers a Shape under its unique string identifier."""
        name = shape.name
        if self.exists(name):
            raise DuplicateShapeNameError(
                f"Shape with name '{name}' already exists. Use Draw.shapes.update('{name}', ...) or provide a unique name."
            )

        shape._registry = self

        if shape.scoped:
            self._weak_registry[name] = weakref.ref(
                shape, lambda ref, n=name: self._cleanup_weak(n)
            )
        else:
            self._strong_registry[name] = shape

        # If inside a 'with Draw.shapes():' context, auto-add to active group
        active_group = get_active_group()
        if active_group is not None:
            active_group.add(shape)

        return shape

    def _cleanup_weak(self, name: str) -> None:
        self._weak_registry.pop(name, None)

    def get(self, name: str) -> Shape:
        """Retrieves an active Shape by name."""
        if name in self._strong_registry:
            return self._strong_registry[name]
        if name in self._weak_registry:
            shape = self._weak_registry[name]()
            if shape is not None:
                return shape
            else:
                self._weak_registry.pop(name, None)

        # Support hierarchical sub-shape lookup (e.g. "card.card_header")
        if "." in name:
            parent_name, child_name = name.split(".", 1)
            parent_shape = self.get(parent_name)
            for child in parent_shape.sub_shapes:
                if child.name == child_name or child.name == name:
                    return child

        raise ShapeNotFoundError(f"No registered shape found with name '{name}'.")

    def exists(self, name: str) -> bool:
        """Checks if a shape name is registered and alive."""
        if name in self._strong_registry:
            return True
        if name in self._weak_registry:
            if self._weak_registry[name]() is not None:
                return True
            else:
                self._weak_registry.pop(name, None)
        return False

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
        data: Optional[List[str]] = None,
    ) -> Any:
        """Inspects one or more registered shapes and returns requested fields."""
        data_keys = list(data or ["size", "vertices", "z", "closed", "bounds", "position"])

        # Case 1: Single shape inspection: Draw.shapes.list("card", data=[...])
        if isinstance(name_or_names, str):
            shape = self.get(name_or_names)
            return shape.query(data_keys)

        # Case 2: Multi-shape inspection: Draw.shapes.list(["card1", "card2"], data=[...])
        names = name_or_names if name_or_names is not None else list(self.all().keys())
        result: Dict[str, Any] = {}
        for n in names:
            if self.exists(n):
                result[n] = self.get(n).query(data_keys)
        return result

    def update(
        self,
        name_or_names: Union[str, Sequence[str]],
        **kwargs: Any,
    ) -> Union[Shape, List[Shape]]:
        """Updates one or more registered shapes."""
        if isinstance(name_or_names, str):
            shape = self.get(name_or_names)
            shape.update(**kwargs)
            return shape

        updated_shapes: List[Shape] = []
        for n in name_or_names:
            shape = self.get(n)
            shape.update(**kwargs)
            updated_shapes.append(shape)
        return updated_shapes

    def remove(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Unregisters shapes from the scene. Returns count of removed shapes."""
        if all:
            count = len(self._strong_registry) + len(self._weak_registry)
            self._strong_registry.clear()
            self._weak_registry.clear()
            return count

        if names is None:
            return 0

        target_names = [names] if isinstance(names, str) else list(names)
        removed_count = 0
        for n in target_names:
            if n in self._strong_registry:
                del self._strong_registry[n]
                removed_count += 1
            if n in self._weak_registry:
                del self._weak_registry[n]
                removed_count += 1
        return removed_count

    def copy(self, name: str, new_name: str) -> Shape:
        """Clones an existing registered shape with a new name."""
        shape = self.get(name)
        return shape.copy(new_name=new_name)

    def find_by_tag(self, tag: str) -> List[Shape]:
        """Queries and returns all registered shapes marked with a specific tag."""
        matches: List[Shape] = []
        for s in self.all().values():
            if tag in s.tags:
                matches.append(s)
        return matches

    def all(self) -> Dict[str, Shape]:
        """Returns a snapshot of all active registered shapes."""
        alive: Dict[str, Shape] = dict(self._strong_registry)
        for n, ref in list(self._weak_registry.items()):
            s = ref()
            if s is not None:
                alive[n] = s
            else:
                self._weak_registry.pop(n, None)
        return alive

    def clear(self) -> None:
        """Flushes the registry."""
        self._strong_registry.clear()
        self._weak_registry.clear()
        self._groups.clear()


# Global Singleton Registry Instance
GLOBAL_REGISTRY = SceneRegistry()


class ShapesNamespace:
    """Callable class acting as both Draw.shapes(...) constructor and registry query service."""

    def __init__(self, registry: SceneRegistry) -> None:
        self._registry = registry

    def __call__(
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
    ) -> ShapeGroup:
        """Constructs a ShapeGroup for batch grouping, collection transforms, or context management."""
        group = ShapeGroup(
            items=items,
            name=name,
            position=position,
            scale=scale,
            rotation=rotation,
            origin=origin,
            z_offset=z_offset,
            tags=tags,
            dynamic=dynamic,
            _registry=self._registry,
        )
        if name:
            self._registry._groups[name] = group
        return group

    def get(self, name: str) -> Shape:
        """Retrieves registered shape by name."""
        return self._registry.get(name)

    def exists(self, name: str) -> bool:
        """Checks if a shape name is currently registered."""
        return self._registry.exists(name)

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
        data: Optional[List[str]] = None,
    ) -> Any:
        """Inspects registered shapes."""
        return self._registry.list(name_or_names=name_or_names, data=data)

    def update(self, name_or_names: Union[str, Sequence[str]], **kwargs: Any) -> Any:
        """Batch updates registered shapes."""
        return self._registry.update(name_or_names=name_or_names, **kwargs)

    def remove(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Removes registered shape(s)."""
        return self._registry.remove(names=names, all=all)

    def copy(self, name: str, new_name: str) -> Shape:
        """Clones a registered shape."""
        return self._registry.copy(name=name, new_name=new_name)

    def find_by_tag(self, tag: str) -> List[Shape]:
        """Finds shapes by tag."""
        return self._registry.find_by_tag(tag)

    def all(self) -> Dict[str, Shape]:
        """Returns all registered shapes."""
        return self._registry.all()

    def clear(self) -> None:
        """Flushes the registry."""
        self._registry.clear()
