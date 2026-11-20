"""Draw Motion Graph API — Registry and Public Entry Point.

Manages registered MotionGraph instances, provides cycle-detection validation,
and exposes the callable Draw.motion_graph(...) interface.
"""

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
from .errors import (
    DuplicateMotionGraphNameError,
    MotionGraphNotFoundError,
    CircularGraphReferenceError,
)
from .graph import MotionGraph, evaluate_builtin_easing


class MotionGraphRegistry:
    """Registry managing custom motion graphs."""

    def __init__(self) -> None:
        self._graphs: Dict[str, MotionGraph] = {}

    def register(self, graph: MotionGraph) -> MotionGraph:
        """Registers a MotionGraph under its name.

        Validates that references exist and checks for cycles.
        """
        if graph.name in self._graphs:
            raise DuplicateMotionGraphNameError(
                f"Motion graph with name '{graph.name}' already exists. "
                f"Use Draw.motion_graph.update('{graph.name}', ...) or provide a unique name."
            )

        # Validate combined graph references and cycle detection
        if graph.type == "combine":
            self._validate_combine_acyclic(graph)

        self._graphs[graph.name] = graph
        return graph

    def _validate_combine_acyclic(self, graph: MotionGraph) -> None:
        """Validates that a combined graph does not introduce circular references."""
        visited: Set[str] = set()

        def _dfs(g_name: str, current_path: List[str]) -> None:
            if g_name in current_path:
                cycle_str = " -> ".join(current_path + [g_name])
                raise CircularGraphReferenceError(
                    f"Circular graph reference detected: {cycle_str}."
                )

            # Check if it's a registered custom graph
            if g_name in self._graphs:
                target_g = self._graphs[g_name]
                if target_g.type == "combine" and target_g.combine:
                    for sub_name, _ in target_g.combine:
                        _dfs(sub_name, current_path + [g_name])
            elif g_name == graph.name:
                cycle_str = " -> ".join(current_path + [g_name])
                raise CircularGraphReferenceError(
                    f"Circular graph reference detected: {cycle_str}."
                )
            else:
                # Must be a built-in easing or will fail lookup
                try:
                    evaluate_builtin_easing(g_name, 0.0)
                except ValueError:
                    raise MotionGraphNotFoundError(
                        f"Motion graph '{graph.name}' references unknown graph '{g_name}'."
                    )

        if graph.combine:
            for sub_name, _ in graph.combine:
                _dfs(sub_name, [graph.name])

    def get(self, name: str) -> MotionGraph:
        """Retrieves a registered custom motion graph by name."""
        if name not in self._graphs:
            raise MotionGraphNotFoundError(
                f"No registered motion graph found with name '{name}'."
            )
        return self._graphs[name]

    def exists(self, name: str) -> bool:
        """Checks if a motion graph name is registered."""
        return name in self._graphs

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
    ) -> Any:
        """Lists registered motion graphs."""
        if name_or_names is None:
            return sorted(self._graphs.keys())
        if isinstance(name_or_names, str):
            return self.get(name_or_names).to_dict()
        return [self.get(n).to_dict() for n in name_or_names]

    def update(
        self,
        name: str,
        points: Optional[Sequence[Sequence[float]]] = None,
        interpolation: str = "smooth",
        combine: Optional[Sequence[Union[Tuple[str, float], Sequence[Any]]]] = None,
        **kwargs: Any,
    ) -> MotionGraph:
        """Updates an existing motion graph."""
        if name not in self._graphs:
            raise MotionGraphNotFoundError(
                f"Cannot update non-existent motion graph '{name}'."
            )
        new_g = MotionGraph(
            name=name,
            points=points,
            interpolation=interpolation,
            combine=combine,
        )
        if new_g.type == "combine":
            self._validate_combine_acyclic(new_g)
        self._graphs[name] = new_g
        return new_g

    def copy(self, name: str, new_name: str) -> MotionGraph:
        """Clones a registered motion graph under a new name."""
        orig = self.get(name)
        if orig.type == "points":
            cloned = MotionGraph(
                name=new_name,
                points=list(orig.points),
                interpolation=orig.interpolation,
            )
        else:
            cloned = MotionGraph(
                name=new_name,
                combine=list(orig.combine) if orig.combine else [],
            )
        return self.register(cloned)

    def all(self) -> Dict[str, MotionGraph]:
        """Returns all registered custom motion graphs mapping name -> MotionGraph."""
        return dict(self._graphs)

    def remove(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Removes registered motion graph(s). Returns count of removed."""
        if all:
            count = len(self._graphs)
            self._graphs.clear()
            return count
        if names is None:
            return 0
        target = [names] if isinstance(names, str) else list(names)
        removed = 0
        for n in target:
            if n in self._graphs:
                del self._graphs[n]
                removed += 1
        return removed

    def clear(self) -> None:
        """Clears all registered motion graphs."""
        self._graphs.clear()

    def evaluate(self, name: str, x: float) -> float:
        """Evaluates a graph by name (custom or built-in) at normalized time x."""
        if name in self._graphs:
            return self._graphs[name].evaluate(x, registry_lookup=self._graphs.get)
        # Built-in fallback
        try:
            return evaluate_builtin_easing(name, x)
        except ValueError:
            raise MotionGraphNotFoundError(
                f"No registered or built-in motion graph found with name '{name}'."
            )


# Global Singleton Registry
GLOBAL_MOTION_GRAPH_REGISTRY = MotionGraphRegistry()


class MotionGraphAPI:
    """Callable namespace for Draw.motion_graph(...) — creates and registers a MotionGraph."""

    def __init__(self, registry: Optional[MotionGraphRegistry] = None) -> None:
        self._registry: MotionGraphRegistry = registry or GLOBAL_MOTION_GRAPH_REGISTRY

    def __call__(
        self,
        name: str,
        points: Optional[Sequence[Sequence[float]]] = None,
        interpolation: str = "smooth",
        combine: Optional[Sequence[Union[Tuple[str, float], Sequence[Any]]]] = None,
        **kwargs: Any,
    ) -> MotionGraph:
        """Creates, registers, and returns a MotionGraph.

        Usage:
            # Point-based
            Draw.motion_graph(
                name="custom_graph",
                points=[(0.0, 0.0), (0.5, 0.7), (1.0, 1.0)],
                interpolation="smooth",
            )

            # Combined
            Draw.motion_graph(
                name="combined_graph",
                combine=[("ease_out", 0.7), ("ease_in", 0.3)],
            )
        """
        g = MotionGraph(
            name=name,
            points=points,
            interpolation=interpolation,
            combine=combine,
        )
        self._registry.register(g)
        return g

    def get(self, name: str) -> MotionGraph:
        """Retrieves a registered motion graph."""
        return self._registry.get(name)

    def exists(self, name: str) -> bool:
        """Checks if a motion graph exists in the registry."""
        return self._registry.exists(name)

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
    ) -> Any:
        """Lists registered motion graphs."""
        return self._registry.list(name_or_names)

    def update(
        self,
        name: str,
        points: Optional[Sequence[Sequence[float]]] = None,
        interpolation: str = "smooth",
        combine: Optional[Sequence[Union[Tuple[str, float], Sequence[Any]]]] = None,
        **kwargs: Any,
    ) -> MotionGraph:
        """Updates an existing motion graph."""
        return self._registry.update(
            name=name,
            points=points,
            interpolation=interpolation,
            combine=combine,
            **kwargs,
        )

    def copy(self, name: str, new_name: str) -> MotionGraph:
        """Clones a motion graph under a new name."""
        return self._registry.copy(name, new_name)

    def all(self) -> Dict[str, MotionGraph]:
        """Returns all registered motion graphs."""
        return self._registry.all()

    def remove(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Removes motion graph(s)."""
        return self._registry.remove(names=names, all=all)

    def clear(self) -> None:
        """Clears all registered motion graphs."""
        self._registry.clear()

    def evaluate(self, name: str, x: float) -> float:
        """Evaluates a motion graph by name at normalized time x."""
        return self._registry.evaluate(name, x)
