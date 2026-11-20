"""Draw Motion API — Easing Functions Registry.

Defines the supported easing/graph names that the C++/OpenGL motion engine
understands. The Python layer validates easing names against this set before
serialization.
"""

from typing import FrozenSet

# Supported easing graph names.
# These map to cubic-bezier or procedural curves evaluated by the C++ engine.
SUPPORTED_EASINGS: FrozenSet[str] = frozenset({
    "linear",
    "ease_in",
    "ease_out",
    "ease_in_out",
    "ease_in_back",
    "ease_out_back",
    "ease_in_out_back",
    "ease_in_elastic",
    "ease_out_elastic",
    "ease_in_out_elastic",
    "ease_in_bounce",
    "ease_out_bounce",
    "ease_in_out_bounce",
    "ease_in_quad",
    "ease_out_quad",
    "ease_in_out_quad",
    "ease_in_cubic",
    "ease_out_cubic",
    "ease_in_out_cubic",
    "ease_in_quart",
    "ease_out_quart",
    "ease_in_out_quart",
    "ease_in_quint",
    "ease_out_quint",
    "ease_in_out_quint",
    "ease_in_sine",
    "ease_out_sine",
    "ease_in_out_sine",
    "ease_in_expo",
    "ease_out_expo",
    "ease_in_out_expo",
    "ease_in_circ",
    "ease_out_circ",
    "ease_in_out_circ",
    "smooth",
})


def validate_easing(name: str) -> str:
    """Validates and returns the easing or motion graph name, raising InvalidEasingError on failure."""
    from .errors import InvalidEasingError
    if name in SUPPORTED_EASINGS:
        return name

    # Check if a custom motion graph is registered under this name
    try:
        from ..motion_graph import motion_graph
        if motion_graph.exists(name):
            return name
    except Exception:
        pass

    raise InvalidEasingError(
        f"Unsupported easing or graph '{name}'. "
        f"Must be one of the built-in easings ({', '.join(sorted(SUPPORTED_EASINGS))}) "
        f"or a registered Draw.motion_graph."
    )
