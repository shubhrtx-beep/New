"""Draw Motion API — Motion Registry and Resolution Engine.

Manages registered Motion instances and named Timeline instances.
Resolves timeline section references into numeric timing before
producing serializable motion data for the C++/OpenGL engine.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
)
from .errors import (
    DuplicateMotionNameError,
    MotionNotFoundError,
    DuplicateTimelineNameError,
    TimelineNotFoundError,
    TimelineSectionNotFoundError,
    InvalidTimelineError,
)
from .timeline import Timeline
from .move import MoveAnimation, ChannelAnimation
from .transform import transform, transfrom
from .physical import PhysicalTransform, PhysicalBody
from .math_motion import MathematicalTransform
from . import physical
from . import math_motion as math_module
from .playback import (
    PlaybackConfig,
    parse_playback,
    PLAYBACK_KWARG_NAMES,
    ONCE,
    REPEAT,
    LOOP,
    PING_PONG,
    REVERSE,
    ALTERNATE,
    YOYO,
    RESTART,
    HOLD,
    FREEZE,
    once,
    repeat,
    loop,
    ping_pong,
    reverse,
    alternate,
    yoyo,
    restart,
    hold,
    freeze,
    playback,
    seek as playback_seek,
)


class ResolvedChannel:
    """A fully resolved channel with absolute start time and duration.

    Produced by resolving a ChannelAnimation against a Timeline.

    Attributes:
        channel: Channel name.
        target: Normalized target value.
        easing: Easing/graph name.
        start: Absolute start time in seconds.
        duration: Duration in seconds.
    """

    def __init__(
        self,
        channel: str,
        target: Any,
        easing: str,
        start: float,
        duration: float,
    ) -> None:
        self.channel: str = channel
        self.target: Any = target
        self.easing: str = easing
        self.start: float = start
        self.duration: float = duration

    def to_dict(self) -> Dict[str, Any]:
        target = list(self.target) if isinstance(self.target, tuple) else self.target
        return {
            "channel": self.channel,
            "target": target,
            "easing": self.easing,
            "start": round(self.start, 6),
            "duration": round(self.duration, 6),
        }

    def __repr__(self) -> str:
        return (
            f"ResolvedChannel({self.channel!r}, target={self.target!r}, "
            f"easing={self.easing!r}, start={self.start}, duration={self.duration})"
        )


class Motion:
    """A named motion object binding animation channels to a target shape.

    Attributes:
        name: Name of the target shape / motion identifier.
        move_anim: Optional MoveAnimation from motion.move().
        transform_anim: Optional transform from motion.transform().
        timeline_name: Optional name of an attached timeline.
        timeline: Optional resolved Timeline object reference.
        playback: PlaybackConfig object governing looping, repetition, direction, etc.
        position: Optional base/spawn position tuple.
    """

    def __init__(
        self,
        name: str,
        move: Optional[MoveAnimation] = None,
        time_line: Optional[str] = None,
        playback: Optional[Union[str, PlaybackConfig]] = None,
        transform: Optional[Any] = None,
        motion: Optional[Any] = None,
        position: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        self.name: str = name
        self.move_anim: Optional[MoveAnimation] = move
        self.timeline_name: Optional[str] = time_line
        self.timeline: Optional[Timeline] = None  # Set by registry on attachment
        self.position: Optional[Any] = position

        # Handle transform / motion keyword aliases
        resolved_transform = transform if transform is not None else motion
        if isinstance(resolved_transform, MoveAnimation) and self.move_anim is None:
            self.move_anim = resolved_transform
            self.transform_anim = None
        else:
            self.transform_anim = resolved_transform

        # Configure playback settings
        has_explicit_playback = playback is not None or any(k in kwargs for k in PLAYBACK_KWARG_NAMES)
        if has_explicit_playback:
            self.playback: PlaybackConfig = parse_playback(playback, **kwargs)
        elif self.move_anim is not None and (
            self.move_anim.playback.mode != ONCE
            or self.move_anim.playback.repeat_count != 1
            or self.move_anim.playback.is_reverse
            or self.move_anim.playback.is_ping_pong
            or self.move_anim.playback.is_alternate
            or self.move_anim.playback.is_yoyo
            or self.move_anim.playback.fill != HOLD
        ):
            # Inherit from move animation if move had explicit playback options
            self.playback = self.move_anim.playback.copy()
        else:
            self.playback = parse_playback()

    def resolve(self) -> List[ResolvedChannel]:
        """Resolves all channel animations to absolute timing.

        For each channel:
        - If it has a string time_ref and a timeline is attached, looks up
          the section's start and duration.
        - If it has a numeric time_ref, uses (0.0, numeric_duration).
        - If time_ref is None and a timeline is attached, the channel
          inherits the first section of the timeline as default.
        - If time_ref is None and no timeline, uses (0.0, 0.0) — the channel
          is instantaneous / must be given a duration at playback.

        Returns:
            List of ResolvedChannel objects.
        """
        resolved: List[ResolvedChannel] = []

        if self.move_anim is None:
            return resolved

        for ch in self.move_anim.channels:
            start, duration = self._resolve_channel_timing(ch)
            resolved.append(
                ResolvedChannel(
                    channel=ch.channel,
                    target=ch.target,
                    easing=ch.easing,
                    start=start,
                    duration=duration,
                )
            )

        return resolved

    def _resolve_channel_timing(
        self, ch: ChannelAnimation
    ) -> tuple:
        """Resolves a single channel's timing reference.

        Returns:
            (start_time, duration) tuple.
        """
        if ch.time_ref is not None:
            if isinstance(ch.time_ref, str):
                # Named section reference — requires attached timeline
                if self.timeline is None:
                    raise TimelineSectionNotFoundError(
                        f"Channel '{ch.channel}' references section '{ch.time_ref}' "
                        f"but motion '{self.name}' has no attached timeline."
                    )
                return self.timeline.resolve_timing(ch.time_ref)
            else:
                # Explicit numeric duration — starts at t=0
                return (0.0, float(ch.time_ref))
        else:
            # No timing specified
            if self.timeline is not None and self.timeline.sections:
                # Inherit the first section as default
                first = self.timeline.sections[0]
                return (first.start, first.duration)
            else:
                # No timeline, no explicit timing — instantaneous
                return (0.0, 0.0)

    # ── Playback Fluent Methods ─────────────────────────────────────────

    def once(self) -> "Motion":
        """Play one time."""
        self.playback.once()
        return self

    def repeat(self, count: Optional[Union[int, bool]] = None) -> "Motion":
        """Repeat continuously or an integer count."""
        self.playback.repeat(count)
        return self

    def loop(self, count: Optional[Union[int, bool]] = None) -> "Motion":
        """Play again after finishing."""
        self.playback.loop(count)
        return self

    def ping_pong(self, enable: bool = True) -> "Motion":
        """Forward, then backward."""
        self.playback.ping_pong(enable)
        return self

    def reverse(self, enable: bool = True) -> "Motion":
        """Play backward."""
        self.playback.reverse(enable)
        return self

    def play_reverse(self, enable: bool = True) -> "Motion":
        """Alias for reverse()."""
        return self.reverse(enable)

    def alternate(self, enable: bool = True) -> "Motion":
        """Alternate direction each cycle."""
        self.playback.alternate(enable)
        return self

    def yoyo(self, enable: bool = True) -> "Motion":
        """Forward and backward repeatedly."""
        self.playback.yoyo(enable)
        return self

    def restart(self) -> "Motion":
        """Restart from the beginning."""
        self.playback.restart()
        return self

    def hold(self) -> "Motion":
        """Stay at the final value."""
        self.playback.hold()
        return self

    def freeze(self) -> "Motion":
        """Freeze at the current value."""
        self.playback.freeze()
        return self

    def play(self) -> "Motion":
        """Start or resume playing."""
        self.playback.play()
        return self

    def pause(self) -> "Motion":
        """Pause playback."""
        self.playback.pause()
        return self

    def stop(self) -> "Motion":
        """Stop playback."""
        self.playback.stop()
        return self

    def seek(self, t: float) -> "Motion":
        """Sets motion playhead to t seconds."""
        self.playback.seek(t)
        return self

    def update(
        self,
        move: Optional[MoveAnimation] = None,
        time_line: Optional[str] = None,
        playback: Optional[Union[str, PlaybackConfig]] = None,
        transform: Optional[Any] = None,
        motion: Optional[Any] = None,
        position: Optional[Any] = None,
        **kwargs: Any,
    ) -> "Motion":
        """Updates animation channels, timeline attachment, transform, or playback."""
        if move is not None:
            self.move_anim = move
        resolved_transform = transform if transform is not None else motion
        if resolved_transform is not None:
            if isinstance(resolved_transform, MoveAnimation) and self.move_anim is None:
                self.move_anim = resolved_transform
            else:
                self.transform_anim = resolved_transform
        if time_line is not None:
            self.timeline_name = time_line
            self.timeline = None
            if self.timeline_name in GLOBAL_MOTION_REGISTRY._timelines:
                self.timeline = GLOBAL_MOTION_REGISTRY._timelines[self.timeline_name]
        if position is not None:
            self.position = position
        if playback is not None or any(k in kwargs for k in PLAYBACK_KWARG_NAMES):
            raw_p = playback if playback is not None else kwargs.get("playback", None)
            self.playback = parse_playback(raw_p, **kwargs)
        return self

    def copy(self, new_name: str) -> "Motion":
        """Clones this motion with a new name and registers it."""
        return GLOBAL_MOTION_REGISTRY.copy(self.name, new_name)

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the motion to a JSON-compatible dictionary."""
        data: Dict[str, Any] = {
            "schema": "draw.motion",
            "version": 1,
            "name": self.name,
            "playback": self.playback.to_dict(),
        }
        if self.timeline_name:
            data["time_line"] = self.timeline_name
        if self.move_anim:
            data["move"] = self.move_anim.to_dict()
        if self.transform_anim:
            data["transform"] = (
                self.transform_anim.to_dict()
                if hasattr(self.transform_anim, "to_dict")
                else self.transform_anim
            )
        if self.position is not None:
            data["position"] = list(self.position) if isinstance(self.position, tuple) else self.position
        return data

    def to_resolved_dict(self) -> Dict[str, Any]:
        """Serializes the motion with fully resolved timing for the C++ engine."""
        resolved = self.resolve()
        data: Dict[str, Any] = {
            "schema": "draw.motion.resolved",
            "version": 1,
            "name": self.name,
            "playback": self.playback.to_dict(),
            "channels": [r.to_dict() for r in resolved],
        }
        if self.timeline_name:
            data["time_line"] = self.timeline_name
        if self.transform_anim:
            data["transform"] = (
                self.transform_anim.to_dict()
                if hasattr(self.transform_anim, "to_dict")
                else self.transform_anim
            )
        if self.position is not None:
            data["position"] = list(self.position) if isinstance(self.position, tuple) else self.position
        return data

    def __repr__(self) -> str:
        parts = [f"Motion(name={self.name!r}"]
        if self.timeline_name:
            parts.append(f", time_line={self.timeline_name!r}")
        if self.move_anim:
            parts.append(f", move={self.move_anim!r}")
        parts.append(f", playback={self.playback!r})")
        return "".join(parts)


class MotionRegistry:
    """Manages registered Motion and Timeline instances in the scene."""

    def __init__(self) -> None:
        self._motions: Dict[str, Motion] = {}
        self._timelines: Dict[str, Timeline] = {}

    # ── Timeline Registration ──────────────────────────────────────────

    def register_timeline(self, name: str, tl: Timeline) -> Timeline:
        """Registers a named Timeline."""
        if name in self._timelines:
            raise DuplicateTimelineNameError(
                f"Timeline with name '{name}' already exists."
            )
        self._timelines[name] = tl

        # Auto-attach to any already-registered motions referencing this timeline
        for motion in self._motions.values():
            if motion.timeline_name == name and motion.timeline is None:
                motion.timeline = tl
            elif motion.timeline_name is None and tl.motion_names and motion.name in tl.motion_names:
                motion.timeline_name = name
                motion.timeline = tl

        return tl

    def get_timeline(self, name: str) -> Timeline:
        """Retrieves a registered Timeline by name."""
        if name not in self._timelines:
            raise TimelineNotFoundError(
                f"No registered timeline found with name '{name}'."
            )
        return self._timelines[name]

    def timeline_exists(self, name: str) -> bool:
        """Checks if a timeline name is registered."""
        return name in self._timelines

    # ── Motion Registration ────────────────────────────────────────────

    def register_motion(self, motion: Motion) -> Motion:
        """Registers a Motion under its name."""
        if motion.name in self._motions:
            raise DuplicateMotionNameError(
                f"Motion with name '{motion.name}' already exists. "
                f"Use Draw.motion.update('{motion.name}', ...) or provide a unique name."
            )

        # Attach timeline if referenced and available
        if motion.timeline_name and motion.timeline is None:
            if motion.timeline_name in self._timelines:
                motion.timeline = self._timelines[motion.timeline_name]
        elif motion.timeline_name is None and motion.timeline is None:
            for tl_name, tl in self._timelines.items():
                if tl.motion_names and motion.name in tl.motion_names:
                    motion.timeline_name = tl_name
                    motion.timeline = tl
                    break

        self._motions[motion.name] = motion
        return motion

    def get_motion(self, name: str) -> Motion:
        """Retrieves a registered Motion by name."""
        if name not in self._motions:
            raise MotionNotFoundError(
                f"No registered motion found with name '{name}'."
            )
        return self._motions[name]

    def motion_exists(self, name: str) -> bool:
        """Checks if a motion name is registered."""
        return name in self._motions

    # ── Query & Mutation ───────────────────────────────────────────────

    def update(self, name: str, **kwargs: Any) -> Motion:
        """Updates a registered motion."""
        m = self.get_motion(name)
        return m.update(**kwargs)

    def copy(self, name: str, new_name: str) -> Motion:
        """Clones a registered motion under a new name."""
        orig = self.get_motion(name)
        new_m = Motion(
            name=new_name,
            move=orig.move_anim,
            time_line=orig.timeline_name,
            playback=orig.playback.copy(),
            transform=orig.transform_anim,
            position=orig.position,
        )
        return self.register_motion(new_m)

    def all(self) -> Dict[str, Motion]:
        """Returns a copy of all registered motions mapping name -> Motion."""
        return dict(self._motions)

    def update_timeline(self, name: str, **kwargs: Any) -> Timeline:
        """Updates a registered timeline."""
        tl = self.get_timeline(name)
        return tl.update(**kwargs)

    def all_timelines(self) -> Dict[str, Timeline]:
        """Returns a copy of all registered timelines mapping name -> Timeline."""
        return dict(self._timelines)

    def list_motions(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
    ) -> Any:
        """Lists registered motions."""
        if name_or_names is None:
            return sorted(self._motions.keys())

        if isinstance(name_or_names, str):
            return self.get_motion(name_or_names).to_dict()

        return [self.get_motion(n).to_dict() for n in name_or_names]

    def list_timelines(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
    ) -> Any:
        """Lists registered timelines."""
        if name_or_names is None:
            return sorted(self._timelines.keys())

        if isinstance(name_or_names, str):
            return self.get_timeline(name_or_names).to_dict()

        return [self.get_timeline(n).to_dict() for n in name_or_names]

    def remove_motion(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Removes registered motion(s). Returns count of removed."""
        if all:
            count = len(self._motions)
            self._motions.clear()
            return count

        if names is None:
            return 0

        target = [names] if isinstance(names, str) else list(names)
        removed = 0
        for n in target:
            if n in self._motions:
                del self._motions[n]
                removed += 1
        return removed

    def remove_timeline(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Removes registered timeline(s). Returns count of removed."""
        if all:
            count = len(self._timelines)
            self._timelines.clear()
            for m in self._motions.values():
                m.timeline = None
            return count

        if names is None:
            return 0

        target = [names] if isinstance(names, str) else list(names)
        removed = 0
        for n in target:
            if n in self._timelines:
                del self._timelines[n]
                removed += 1
                for m in self._motions.values():
                    if m.timeline_name == n:
                        m.timeline = None
        return removed

    def clear(self) -> None:
        """Clears all registered motions and timelines."""
        self._motions.clear()
        self._timelines.clear()


# Global Singleton Registry Instance
GLOBAL_MOTION_REGISTRY = MotionRegistry()


class MotionAPI:
    """Callable namespace for Draw.motion(...) — creates and registers a Motion.

    Also exposes registry operations, playback helper functions, and constants.
    """

    def __init__(self, registry: Optional[MotionRegistry] = None) -> None:
        self._registry = registry or GLOBAL_MOTION_REGISTRY

        # Attach transform constructors
        self.transform = transform
        self.transfrom = transfrom

        # Attach physical and mathematical subsystems
        self.physical = physical
        self.math = math_module

        # Attach procedural effect presets
        self.fire = math_module.fire
        self.smoke = math_module.smoke
        self.lightning = math_module.lightning
        self.shockwave = math_module.shockwave
        self.water_splash = math_module.water_splash
        self.energy_vortex = math_module.energy_vortex

        # Attach motion graph subsystem
        try:
            from ..motion_graph import motion_graph as mg_instance
            self.motion_graph = mg_instance
            self.graph = mg_instance
        except Exception:
            pass

        # Attach playback constants
        self.ONCE = ONCE
        self.REPEAT = REPEAT
        self.LOOP = LOOP
        self.PING_PONG = PING_PONG
        self.REVERSE = REVERSE
        self.ALTERNATE = ALTERNATE
        self.YOYO = YOYO
        self.RESTART = RESTART
        self.HOLD = HOLD
        self.FREEZE = FREEZE

        # Attach playback factory helpers
        self.playback = playback
        self.once = once
        self.repeat = repeat
        self.loop = loop
        self.ping_pong = ping_pong
        self.reverse = reverse
        self.alternate = alternate
        self.yoyo = yoyo
        self.restart = restart
        self.hold = hold
        self.freeze = freeze

    def __call__(
        self,
        name: str,
        move: Optional[MoveAnimation] = None,
        time_line: Optional[str] = None,
        playback: Optional[Union[str, PlaybackConfig]] = None,
        transform: Optional[Any] = None,
        motion: Optional[Any] = None,
        position: Optional[Any] = None,
        **kwargs: Any,
    ) -> Motion:
        """Creates, registers, and returns a Motion.

        Args:
            name: Target shape name / motion identifier.
            move: A MoveAnimation from motion.move(...).
            time_line: Name of a registered timeline to attach.
            playback: Playback mode string ('loop', 'ping_pong', etc.) or PlaybackConfig.
            transform: A transform from motion.transform(...).
            motion: Alias for transform or move.
            position: Spawn/base position.
            **kwargs: Extra parameters and playback options.

        Returns:
            The registered Motion instance.
        """
        m = Motion(
            name=name,
            move=move,
            time_line=time_line,
            playback=playback,
            transform=transform,
            motion=motion,
            position=position,
            **kwargs,
        )
        self._registry.register_motion(m)
        return m

    def get(self, name: str) -> Motion:
        """Retrieves a registered motion by name."""
        return self._registry.get_motion(name)

    def exists(self, name: str) -> bool:
        """Checks if a motion name is registered."""
        return self._registry.motion_exists(name)

    def update(self, name: str, **kwargs: Any) -> Motion:
        """Updates a registered motion."""
        return self._registry.update(name, **kwargs)

    def copy(self, name: str, new_name: str) -> Motion:
        """Clones a registered motion under a new name."""
        return self._registry.copy(name, new_name)

    def all(self) -> Dict[str, Motion]:
        """Returns all registered motions."""
        return self._registry.all()

    def seek(self, name_or_t: Union[str, float], t: Optional[float] = None) -> Any:
        """Sets playback playhead for a registered motion if called with (name, t),
        or returns a PlaybackConfig if called with (t).
        """
        if t is not None or isinstance(name_or_t, str):
            if t is None:
                raise TypeError("Draw.motion.seek(name, t) requires both name and timestamp.")
            m = self.get(str(name_or_t))
            m.seek(t)
            return m
        return playback_seek(float(name_or_t))

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
    ) -> Any:
        """Lists registered motions."""
        return self._registry.list_motions(name_or_names)

    def remove(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Removes registered motion(s)."""
        return self._registry.remove_motion(names=names, all=all)

    def clear(self) -> None:
        """Clears all registered motions."""
        self._registry.remove_motion(all=True)


class TimelineAPI:
    """Callable namespace for Draw.time_line(...) — registers a named Timeline.

    Also exposes timeline registry operations as methods.
    """

    def __init__(self, registry: Optional[MotionRegistry] = None) -> None:
        self._registry = registry or GLOBAL_MOTION_REGISTRY

    def __call__(
        self,
        name: str,
        time_line: Timeline,
    ) -> Timeline:
        """Registers a named Timeline.

        Args:
            name: Unique identifier for this timeline.
            time_line: A Timeline from Draw.timeline(...).

        Returns:
            The registered Timeline instance.
        """
        return self._registry.register_timeline(name, time_line)

    def get(self, name: str) -> Timeline:
        """Retrieves a registered timeline by name."""
        return self._registry.get_timeline(name)

    def exists(self, name: str) -> bool:
        """Checks if a timeline name is registered."""
        return self._registry.timeline_exists(name)

    def update(self, name: str, **kwargs: Any) -> Timeline:
        """Updates a registered timeline."""
        return self._registry.update_timeline(name, **kwargs)

    def all(self) -> Dict[str, Timeline]:
        """Returns all registered timelines."""
        return self._registry.all_timelines()

    def seek(self, name: str, t: float) -> Timeline:
        """Sets playback playhead for a registered timeline."""
        tl = self.get(name)
        tl.seek(t)
        return tl

    def list(
        self,
        name_or_names: Optional[Union[str, Sequence[str]]] = None,
    ) -> Any:
        """Lists registered timelines."""
        return self._registry.list_timelines(name_or_names)

    def remove(
        self,
        names: Optional[Union[str, Sequence[str]]] = None,
        all: bool = False,
    ) -> int:
        """Removes registered timeline(s)."""
        return self._registry.remove_timeline(names=names, all=all)

    def clear(self) -> None:
        """Clears all registered timelines."""
        self._registry.remove_timeline(all=True)
