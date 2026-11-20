"""Draw Motion API — Unified motion.transform Interface.

Supports:
1. Physical Motion: rigid body simulation, forces, impulse, torque, collisions, presets.
2. Mathematical Motion: function-based procedural motion, noise, fields, waves, flows, effects.
3. Standard Transform: multi-property spatial/visual transitions (to={...}, duration, graph).
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from .vector import Vector2D, PointLike
from .physical import PhysicalBody, PhysicalTransform
from .math_motion import MathematicalTransform
from .easings import validate_easing
from .channels import validate_channel_value


class StandardTransform:
    """Standard multi-property spatial and visual transform container (to={...})."""

    def __init__(
        self,
        to: Optional[Dict[str, Any]] = None,
        duration: float = 1.0,
        graph: str = "linear",
        **kwargs: Any,
    ) -> None:
        self.type: str = "standard"
        self.duration: float = float(duration)
        self.graph: str = validate_easing(graph)
        self.properties: Dict[str, Any] = {}
        self.overrides: Dict[str, Dict[str, Any]] = {}

        raw_to = to or {}
        for prop_name, val in raw_to.items():
            if isinstance(val, dict) and "value" in val:
                # Property override: e.g. "translate": {"value": (300, 200), "duration": 1.5}
                self.properties[prop_name] = validate_channel_value(prop_name, val["value"])
                override_dict = {}
                if "duration" in val:
                    override_dict["duration"] = float(val["duration"])
                if "graph" in val:
                    override_dict["graph"] = validate_easing(val["graph"])
                if "origin" in val:
                    override_dict["origin"] = val["origin"]
                self.overrides[prop_name] = override_dict
            else:
                self.properties[prop_name] = validate_channel_value(prop_name, val)

    def to_dict(self) -> Dict[str, Any]:
        serialized_props = {}
        for k, v in self.properties.items():
            if isinstance(v, tuple):
                serialized_props[k] = list(v)
            else:
                serialized_props[k] = v

        data: Dict[str, Any] = {
            "type": "standard",
            "to": serialized_props,
            "duration": round(self.duration, 4),
            "graph": self.graph,
        }
        if self.overrides:
            data["overrides"] = self.overrides
        return data

    def __repr__(self) -> str:
        return f"StandardTransform(to={self.properties}, duration={self.duration}, graph={self.graph!r})"


# Keywords indicative of physical motion
_PHYSICAL_KWARGS = frozenset({
    "mass",
    "velocity",
    "acceleration",
    "force",
    "angular_velocity",
    "torque",
    "inertia",
    "restitution",
    "friction",
    "drag",
    "density",
    "gravity",
    "preset",
    "radius",
})

# Keywords indicative of mathematical motion
_MATH_KWARGS = frozenset({
    "noise",
    "turbulence",
    "expansion",
    "decay",
    "frequency",
    "amplitude",
    "phase",
    "direction",
    "seed",
    "vortex",
    "swirl",
    "wave",
    "advection",
    "diffusion",
    "effect",
    "effect_name",
})


def transform(
    type: Optional[str] = None,
    to: Optional[Dict[str, Any]] = None,
    duration: float = 1.0,
    graph: str = "linear",
    **kwargs: Any,
) -> Union[PhysicalTransform, MathematicalTransform, StandardTransform]:
    """Unified constructor for Physical, Mathematical, or Standard transforms.

    Usage:
        # 1. Physical motion
        motion.transform(
            type="physical",
            mass=12,
            position=(0, 0),
            velocity=(20, 15),
            acceleration=(0, -10),
        )

        # 2. Mathematical motion
        motion.transform(
            direction=(0, -1),
            noise=0.5,
            turbulence=0.8,
            expansion=1.2,
            decay=0.3,
        )

        # 3. Standard multi-property transform
        motion.transform(
            to={"translate": (300, 200), "rotate": 90, "z": 5},
            duration=2.0,
            graph="ease_out",
        )
    """
    # 0. Dedicated procedural effect recipes
    effect = kwargs.get("effect") or kwargs.get("effect_name")
    if effect:
        from .math_motion import fire, smoke, lightning, shockwave, water_splash, energy_vortex
        effect_map = {
            "fire": fire,
            "smoke": smoke,
            "lightning": lightning,
            "shockwave": shockwave,
            "water_splash": water_splash,
            "energy_vortex": energy_vortex,
        }
        if effect in effect_map:
            kw = dict(kwargs)
            kw.pop("effect", None)
            kw.pop("effect_name", None)
            return effect_map[effect](duration=duration, **kw)

    # 1. Explicit physical type or predominantly physical kwargs
    if type == "physical" or (type is None and to is None and any(k in kwargs for k in _PHYSICAL_KWARGS)):
        return PhysicalTransform(**kwargs)

    # 2. Explicit mathematical type or predominantly mathematical kwargs
    if type == "mathematical" or (type is None and to is None and any(k in kwargs for k in _MATH_KWARGS)):
        return MathematicalTransform(duration=duration, **kwargs)

    # 3. Standard property transform (to={...})
    if to is not None or type == "standard":
        return StandardTransform(to=to, duration=duration, graph=graph, **kwargs)

    # Fallback to standard if empty, or mathematical if extra kwargs
    if kwargs:
        return MathematicalTransform(duration=duration, **kwargs)
    return StandardTransform(to=to, duration=duration, graph=graph)


# Typo alias for convenience as seen in prompt
transfrom = transform
