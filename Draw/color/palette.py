"""Draw Color API — Palette Design Tokens & Theme Management.

Provides Draw.palette for centralized design tokens and Draw.color.theme
for theme registration and live theme switching with circular dependency detection.
"""

from typing import (
    Any,
    Dict,
    Optional,
    Set,
)
from .errors import (
    ColorTokenCycleError,
    UnknownColorNameError,
)
from .color_value import parse_color, ColorValue


class PaletteRegistry:
    """Manages global design tokens and themes."""

    def __init__(self) -> None:
        self._tokens: Dict[str, Any] = {}
        self._themes: Dict[str, Dict[str, Any]] = {}
        self._active_theme: Optional[str] = None

    def __call__(self, **kwargs: Any) -> "PaletteRegistry":
        """Allows direct invocation: Draw.palette(primary='#3b82f6', ...)."""
        self.update(**kwargs)
        return self

    def update(self, **kwargs: Any) -> None:
        """Sets or updates multiple design tokens."""
        for k, v in kwargs.items():
            self._tokens[k] = v

    def get(self, key: str, _visited: Optional[Set[str]] = None) -> Any:
        """Retrieves a token, resolving any alias references with cycle detection."""
        if _visited is None:
            _visited = set()

        if key in _visited:
            raise ColorTokenCycleError(f"Circular token dependency detected for key '{key}'.")
        _visited.add(key)

        if key not in self._tokens:
            raise UnknownColorNameError(f"Design token '{key}' is not defined in palette.")

        val = self._tokens[key]
        if isinstance(val, str) and val.startswith("@"):
            # Aliased token reference: e.g. "@primary"
            target_key = val[1:]
            return self.get(target_key, _visited=_visited)

        return val

    def exists(self, key: str) -> bool:
        """Checks if a token key is registered."""
        return key in self._tokens

    def remove(self, key: str) -> bool:
        """Removes a design token from the palette."""
        if key in self._tokens:
            del self._tokens[key]
            return True
        return False

    def clear(self) -> None:
        """Clears all tokens and registered themes."""
        self._tokens.clear()
        self._themes.clear()
        self._active_theme = None

    def theme(self, name: str, tokens: Dict[str, Any]) -> None:
        """Registers a named theme dictionary of tokens."""
        self._themes[name] = dict(tokens)

    def use_theme(self, name: str) -> None:
        """Applies a registered theme into active palette tokens."""
        if name not in self._themes:
            raise UnknownColorNameError(f"Theme '{name}' is not registered.")
        self._active_theme = name
        self.update(**self._themes[name])

    def __getattr__(self, name: str) -> Any:
        """Allows property access syntax: palette.primary, palette.surface."""
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._tokens:
            return self.get(name)
        raise AttributeError(f"'PaletteRegistry' has no token named '{name}'.")


palette = PaletteRegistry()
