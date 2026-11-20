"""Draw Color API — Scene Color Registry and Callable Namespace.

Maintains registered visual style bindings, handles weakref-scoped lifecycles,
and exposes Draw.color both as a callable constructor and as a registry query/mutation namespace.
"""

import weakref
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
)
from .errors import (
    DuplicateColorNameError,
    ColorNotFoundError,
)
from .binding import ColorBinding, IN_SHAPE
from .palette import palette
from .harmonies import set_registry_resolver


class ColorRegistry:
    """Manages active ColorBinding instances in the scene."""

    def __init__(self) -> None:
        self._strong_registry: Dict[str, ColorBinding] = {}
        self._weak_registry: Dict[str, weakref.ref] = {}

    def register(self, binding: ColorBinding) -> ColorBinding:
        """Registers a ColorBinding under its unique string identifier."""
        name = binding.name
        if self.exists(name):
            raise DuplicateColorNameError(
                f"Color binding with name '{name}' already exists. Use Draw.color.update('{name}', ...) or provide a unique name."
            )

        binding._registry = self

        if binding.scoped:
            self._weak_registry[name] = weakref.ref(
                binding, lambda ref, n=name: self._cleanup_weak(n)
            )
        else:
            self._strong_registry[name] = binding

        return binding

    def _cleanup_weak(self, name: str) -> None:
        self._weak_registry.pop(name, None)

    def get(self, name: str) -> ColorBinding:
        """Retrieves an active ColorBinding by name."""
        if name in self._strong_registry:
            return self._strong_registry[name]
        if name in self._weak_registry:
            binding = self._weak_registry[name]()
            if binding is not None:
                return binding
            self._weak_registry.pop(name, None)

        raise ColorNotFoundError(f"No registered color binding found with name '{name}'.")

    def exists(self, name: str) -> bool:
        """Checks if a color binding name is registered and alive."""
        if name in self._strong_registry:
            return True
        if name in self._weak_registry:
            if self._weak_registry[name]() is not None:
                return True
            self._weak_registry.pop(name, None)
        return False

    def update(self, name: str, **kwargs: Any) -> ColorBinding:
        """Updates specific channels of an existing registered color binding."""
        binding = self.get(name)
        binding.update(**kwargs)
        return binding

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
        data: Optional[List[str]] = None,
    ) -> Any:
        """Inspects one or more registered color bindings and returns requested fields."""
        data_keys = list(data or ["body", "border", "shadow", "glow"])

        if name_or_names is None:
            # Return summary of all registered names
            names = sorted(list(self._strong_registry.keys()) + list(self._weak_registry.keys()))
            return names

        single_query = isinstance(name_or_names, str)
        names_to_query = [name_or_names] if single_query else list(name_or_names)

        results: List[Dict[str, Any]] = []
        for n in names_to_query:
            b = self.get(n)
            item: Dict[str, Any] = {"name": n}
            for k in data_keys:
                channel = getattr(b, k, None)
                item[k] = channel.to_dict() if channel is not None else None
            results.append(item)

        return results[0] if single_query else results

    def copy(self, name: str, new_name: str, link: bool = False) -> ColorBinding:
        """Clones a registered binding under a new identifier."""
        source = self.get(name)
        new_binding = source.copy(new_name=new_name)
        return self.register(new_binding)

    def remove(self, names: Union[str, Sequence[str]]) -> int:
        """Removes one or more registered color bindings by name."""
        name_list = [names] if isinstance(names, str) else list(names)
        removed_count = 0
        for n in name_list:
            if n in self._strong_registry:
                del self._strong_registry[n]
                removed_count += 1
            if n in self._weak_registry:
                del self._weak_registry[n]
                removed_count += 1
        return removed_count

    def clear(self) -> None:
        """Clears all registered color bindings."""
        self._strong_registry.clear()
        self._weak_registry.clear()

    def resolve_reference(self, ref_str: str) -> Any:
        """Resolves dot references such as 'panel.body' or direct names."""
        if "." in ref_str:
            target_name, channel_name = ref_str.split(".", 1)
            if self.exists(target_name):
                binding = self.get(target_name)
                channel = getattr(binding, channel_name, None)
                if channel is not None and hasattr(channel, "fill"):
                    return channel.fill
        elif self.exists(ref_str):
            binding = self.get(ref_str)
            if binding.body is not None:
                return binding.body.fill
        return None


GLOBAL_COLOR_REGISTRY = ColorRegistry()
set_registry_resolver(GLOBAL_COLOR_REGISTRY.resolve_reference)


class ColorAPI:
    """Callable namespace managing color bindings and scene registry operations."""

    def __init__(self, registry: Optional[ColorRegistry] = None) -> None:
        self._registry = registry or GLOBAL_COLOR_REGISTRY

    def __call__(
        self,
        name: Optional[str] = None,
        body: Optional[Union[Any]] = None,
        border: Optional[Union[Any]] = None,
        shadow: Optional[Union[Any]] = None,
        glow: Optional[Union[Any]] = None,
        scoped: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ColorBinding:
        """Defines and registers a color binding, or creates an inline shape style."""
        is_inline = name is None or name == IN_SHAPE
        binding_name = IN_SHAPE if is_inline else name

        b = ColorBinding(
            name=binding_name,
            body=body,
            border=border,
            shadow=shadow,
            glow=glow,
            scoped=scoped,
            metadata=metadata,
            _registry=self._registry,
        )

        if not is_inline:
            self._registry.register(b)

        return b

    def update(self, name: str, **kwargs: Any) -> ColorBinding:
        return self._registry.update(name, **kwargs)

    def get(self, name: str) -> ColorBinding:
        return self._registry.get(name)

    def exists(self, name: str) -> bool:
        return self._registry.exists(name)

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
        data: Optional[List[str]] = None,
    ) -> Any:
        return self._registry.list(name_or_names=name_or_names, data=data)

    def copy(self, name: str, new_name: str, link: bool = False) -> ColorBinding:
        return self._registry.copy(name, new_name=new_name, link=link)

    def remove(self, names: Union[str, Sequence[str]]) -> int:
        return self._registry.remove(names)

    def clear(self) -> None:
        self._registry.clear()

    def theme(self, name: str, tokens: Dict[str, Any]) -> None:
        palette.theme(name=name, tokens=tokens)

    def use_theme(self, name: str) -> None:
        palette.use_theme(name)
