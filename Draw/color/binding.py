"""Draw Color API — ColorBinding Model.

Represents an authoritative, editable visual styling container for fills,
borders, drop shadows, and outer glows, with dynamic dirty tracking and serialization.
"""

from typing import (
    Any,
    Dict,
    Optional,
    Union,
)
from .channels import (
    ColorBody,
    ColorBorder,
    ColorShadow,
    ColorGlow,
    body,
    border,
    shadow,
    glow,
)

IN_SHAPE: str = "$__in_shape__"


class ColorBinding:
    """Represents a validated, cohesive visual style binding."""

    def __init__(
        self,
        name: str,
        body: Optional[Union[ColorBody, Dict[str, Any], Any]] = None,
        border: Optional[Union[ColorBorder, Dict[str, Any], Any]] = None,
        shadow: Optional[Union[ColorShadow, Dict[str, Any], Any]] = None,
        glow: Optional[Union[ColorGlow, Dict[str, Any], Any]] = None,
        scoped: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        _registry: Any = None,
    ) -> None:
        self.name: str = name
        self.scoped: bool = bool(scoped)
        self.metadata: Dict[str, Any] = dict(metadata or {})
        self._registry = _registry

        # Normalize channels
        self.body: Optional[ColorBody] = self._normalize_body(body)
        self.border: Optional[ColorBorder] = self._normalize_border(border)
        self.shadow: Optional[ColorShadow] = self._normalize_shadow(shadow)
        self.glow: Optional[ColorGlow] = self._normalize_glow(glow)

        # Dirty version counters
        self.versions: Dict[str, int] = {
            "body": 1,
            "border": 1,
            "shadow": 1,
            "glow": 1,
            "metadata": 1,
        }

    @staticmethod
    def _normalize_body(val: Any) -> Optional[ColorBody]:
        if val is None:
            return None
        if isinstance(val, ColorBody):
            return val
        if isinstance(val, dict):
            return body(**val)
        return body(fill=val)

    @staticmethod
    def _normalize_border(val: Any) -> Optional[ColorBorder]:
        if val is None:
            return None
        if isinstance(val, ColorBorder):
            return val
        if isinstance(val, dict):
            return border(**val)
        return border(fill=val)

    @staticmethod
    def _normalize_shadow(val: Any) -> Optional[ColorShadow]:
        if val is None:
            return None
        if isinstance(val, ColorShadow):
            return val
        if isinstance(val, dict):
            return shadow(**val)
        return shadow(fill=val)

    @staticmethod
    def _normalize_glow(val: Any) -> Optional[ColorGlow]:
        if val is None:
            return None
        if isinstance(val, ColorGlow):
            return val
        if isinstance(val, dict):
            return glow(**val)
        return glow(fill=val)

    @property
    def dynamic(self) -> bool:
        """Returns True if any channel contains dynamic motion drivers or expression nodes."""
        return any(
            ch is not None and ch.is_dynamic
            for ch in (self.body, self.border, self.shadow, self.glow)
        )

    def update(self, **kwargs: Any) -> "ColorBinding":
        """Updates specific visual channels in-place and increments version counters."""
        if "body" in kwargs:
            self.body = self._normalize_body(kwargs["body"])
            self.versions["body"] += 1
        if "border" in kwargs:
            self.border = self._normalize_border(kwargs["border"])
            self.versions["border"] += 1
        if "shadow" in kwargs:
            self.shadow = self._normalize_shadow(kwargs["shadow"])
            self.versions["shadow"] += 1
        if "glow" in kwargs:
            self.glow = self._normalize_glow(kwargs["glow"])
            self.versions["glow"] += 1
        if "metadata" in kwargs:
            self.metadata.update(kwargs["metadata"])
            self.versions["metadata"] += 1

        return self

    def copy(self, new_name: str) -> "ColorBinding":
        """Creates an independent copy of this binding with a new name."""
        return ColorBinding(
            name=new_name,
            body=self.body,
            border=self.border,
            shadow=self.shadow,
            glow=self.glow,
            scoped=self.scoped,
            metadata=dict(self.metadata),
            _registry=self._registry,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes binding into authoritative C++ transfer packet schema."""
        return {
            "schema": "draw.color",
            "version": 1,
            "name": self.name,
            "dynamic": self.dynamic,
            "channels": {
                "body": self.body.to_dict() if self.body else None,
                "border": self.border.to_dict() if self.border else None,
                "shadow": self.shadow.to_dict() if self.shadow else None,
                "glow": self.glow.to_dict() if self.glow else None,
            },
            "metadata": self.metadata if self.metadata else None,
        }
