"""Draw Motion API — Timeline Definition and Section Resolution.

Implements Draw.timeline() and Draw.time_line() for defining named time
sections, attaching them to motion objects, and configuring timeline playback.

A timeline is a sequence of named duration sections. Motion channels can
reference these sections by name instead of providing explicit numeric
durations, enabling coordinated multi-shape choreography.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from .errors import (
    InvalidTimelineError,
    TimelineSectionCountMismatchError,
    TimelineSectionNotFoundError,
    InvalidDurationError,
)
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
)


class TimelineSection:
    """Represents a single named duration section within a timeline.

    Attributes:
        name: The section identifier (e.g. "intro", "move").
        duration: Length of this section in seconds.
        start: Computed absolute start time in seconds.
        end: Computed absolute end time in seconds.
    """

    def __init__(self, name: str, duration: float, start: float) -> None:
        if duration < 0:
            raise InvalidDurationError(
                f"Timeline section '{name}' duration must be non-negative, got {duration}."
            )
        self.name: str = name
        self.duration: float = float(duration)
        self.start: float = float(start)
        self.end: float = self.start + self.duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration": self.duration,
            "start": round(self.start, 6),
            "end": round(self.end, 6),
        }

    def __repr__(self) -> str:
        return (
            f"TimelineSection(name={self.name!r}, duration={self.duration}, "
            f"start={self.start}, end={self.end})"
        )


class Timeline:
    """Defines a sequence of named time sections and playback behavior.

    Created by Draw.timeline(time=[...], names=[...]).

    The ``time`` list contains section durations in seconds (not absolute
    timestamps). The cumulative section boundaries are computed
    automatically.

    Example::

        tl = Timeline(
            time=[2, 4, 5, 7],
            names=["intro", "move", "rotate", "ending"],
            playback="loop",
        )

    Attributes:
        sections: Ordered list of TimelineSection objects.
        total_duration: Sum of all section durations.
        motion_names: Optional list of named motions that belong to this timeline.
        playback: PlaybackConfig object governing looping, repeat, direction, etc.
    """

    def __init__(
        self,
        time: Sequence[Union[int, float]],
        names: Sequence[str],
        motion: Optional[Sequence[str]] = None,
        playback: Optional[Union[str, PlaybackConfig]] = None,
        **kwargs: Any,
    ) -> None:
        if not time:
            raise InvalidTimelineError("Timeline 'time' list must not be empty.")
        if not names:
            raise InvalidTimelineError("Timeline 'names' list must not be empty.")
        if len(time) != len(names):
            raise TimelineSectionCountMismatchError(
                f"Timeline 'time' has {len(time)} entries but 'names' has {len(names)} entries. "
                "They must have the same length."
            )

        # Check for duplicate section names
        seen: Dict[str, int] = {}
        for i, n in enumerate(names):
            if not isinstance(n, str) or not n.strip():
                raise InvalidTimelineError(
                    f"Timeline section name at index {i} must be a non-empty string, got {n!r}."
                )
            if n in seen:
                raise InvalidTimelineError(
                    f"Duplicate timeline section name '{n}' at indices {seen[n]} and {i}."
                )
            seen[n] = i

        # Validate durations and build sections
        self.sections: List[TimelineSection] = []
        cumulative: float = 0.0
        for i, (dur, name) in enumerate(zip(time, names)):
            dur_float = float(dur)
            if dur_float < 0:
                raise InvalidDurationError(
                    f"Timeline section '{name}' duration must be non-negative, got {dur_float}."
                )
            section = TimelineSection(name=name, duration=dur_float, start=cumulative)
            self.sections.append(section)
            cumulative += dur_float

        self.total_duration: float = cumulative
        self.motion_names: Optional[List[str]] = list(motion) if motion else None

        # Build a fast lookup by section name
        self._section_map: Dict[str, TimelineSection] = {
            s.name: s for s in self.sections
        }

        # Initialize playback settings
        self.playback: PlaybackConfig = parse_playback(playback, **kwargs)

    def get_section(self, name: str) -> TimelineSection:
        """Returns the TimelineSection with the given name."""
        if name not in self._section_map:
            raise TimelineSectionNotFoundError(
                f"Timeline section '{name}' not found. "
                f"Available sections: {', '.join(s.name for s in self.sections)}."
            )
        return self._section_map[name]

    def has_section(self, name: str) -> bool:
        """Checks if a section name exists in this timeline."""
        return name in self._section_map

    def section_names(self) -> List[str]:
        """Returns ordered list of section names."""
        return [s.name for s in self.sections]

    def resolve_timing(self, time_ref: Union[str, int, float]) -> Tuple[float, float]:
        """Resolves a channel timing reference to (start_time, duration).

        Args:
            time_ref: Either a named section string, or a numeric duration in seconds.

        Returns:
            Tuple of (absolute_start_time, duration).
        """
        if isinstance(time_ref, str):
            section = self.get_section(time_ref)
            return (section.start, section.duration)
        elif isinstance(time_ref, (int, float)):
            dur = float(time_ref)
            if dur < 0:
                raise InvalidDurationError(f"Explicit duration must be non-negative, got {dur}.")
            return (0.0, dur)
        else:
            raise InvalidTimelineError(
                f"Timing reference must be a section name (str) or numeric duration, "
                f"got {type(time_ref).__name__}."
            )

    # ── Playback Fluent Methods ─────────────────────────────────────────

    def once(self) -> "Timeline":
        """Play one time."""
        self.playback.once()
        return self

    def repeat(self, count: Optional[Union[int, bool]] = None) -> "Timeline":
        """Repeat continuously or an integer count."""
        self.playback.repeat(count)
        return self

    def loop(self, count: Optional[Union[int, bool]] = None) -> "Timeline":
        """Play again after finishing."""
        self.playback.loop(count)
        return self

    def ping_pong(self, enable: bool = True) -> "Timeline":
        """Forward, then backward."""
        self.playback.ping_pong(enable)
        return self

    def reverse(self, enable: bool = True) -> "Timeline":
        """Play backward."""
        self.playback.reverse(enable)
        return self

    def play_reverse(self, enable: bool = True) -> "Timeline":
        """Alias for reverse()."""
        return self.reverse(enable)

    def alternate(self, enable: bool = True) -> "Timeline":
        """Alternate direction each cycle."""
        self.playback.alternate(enable)
        return self

    def yoyo(self, enable: bool = True) -> "Timeline":
        """Forward and backward repeatedly."""
        self.playback.yoyo(enable)
        return self

    def restart(self) -> "Timeline":
        """Restart from the beginning."""
        self.playback.restart()
        return self

    def hold(self) -> "Timeline":
        """Stay at the final value."""
        self.playback.hold()
        return self

    def freeze(self) -> "Timeline":
        """Freeze at the current value."""
        self.playback.freeze()
        return self

    def play(self) -> "Timeline":
        """Start or resume playing."""
        self.playback.play()
        return self

    def pause(self) -> "Timeline":
        """Pause playback."""
        self.playback.pause()
        return self

    def stop(self) -> "Timeline":
        """Stop playback."""
        self.playback.stop()
        return self

    def seek(self, t: float) -> "Timeline":
        """Sets timeline playhead to t seconds."""
        self.playback.seek(t)
        return self

    def update(
        self,
        time: Optional[Sequence[Union[int, float]]] = None,
        names: Optional[Sequence[str]] = None,
        motion: Optional[Sequence[str]] = None,
        playback: Optional[Union[str, PlaybackConfig]] = None,
        **kwargs: Any,
    ) -> "Timeline":
        """Updates timeline definition and/or playback parameters."""
        if time is not None and names is not None:
            if not time:
                raise InvalidTimelineError("Timeline 'time' list must not be empty.")
            if len(time) != len(names):
                raise TimelineSectionCountMismatchError(
                    f"Timeline 'time' has {len(time)} entries but 'names' has {len(names)} entries. "
                    "They must have the same length."
                )
            seen: Dict[str, int] = {}
            for i, n in enumerate(names):
                if not isinstance(n, str) or not n.strip():
                    raise InvalidTimelineError(
                        f"Timeline section name at index {i} must be a non-empty string, got {n!r}."
                    )
                if n in seen:
                    raise InvalidTimelineError(
                        f"Duplicate timeline section name '{n}' at indices {seen[n]} and {i}."
                    )
                seen[n] = i
            new_sections: List[TimelineSection] = []
            cumulative: float = 0.0
            for i, (dur, name) in enumerate(zip(time, names)):
                dur_float = float(dur)
                if dur_float < 0:
                    raise InvalidDurationError(
                        f"Timeline section '{name}' duration must be non-negative, got {dur_float}."
                    )
                new_sections.append(TimelineSection(name=name, duration=dur_float, start=cumulative))
                cumulative += dur_float
            self.sections = new_sections
            self.total_duration = cumulative
        elif time is not None or names is not None:
            raise InvalidTimelineError("Both 'time' and 'names' must be provided when updating sections.")

        if motion is not None:
            self.motion_names = list(motion)

        if playback is not None or any(k in kwargs for k in PLAYBACK_KWARG_NAMES):
            raw_p = playback if playback is not None else kwargs.get("playback", None)
            self.playback = parse_playback(raw_p, **kwargs)
        return self

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the timeline to a JSON-compatible dictionary."""
        data: Dict[str, Any] = {
            "schema": "draw.timeline",
            "version": 1,
            "total_duration": round(self.total_duration, 6),
            "sections": [s.to_dict() for s in self.sections],
            "playback": self.playback.to_dict(),
        }
        if self.motion_names:
            data["motion"] = self.motion_names
        return data

    def __repr__(self) -> str:
        section_strs = ", ".join(
            f"{s.name}={s.duration}s" for s in self.sections
        )
        return f"Timeline([{section_strs}], total={self.total_duration}s, playback={self.playback!r})"


def timeline(
    time: Sequence[Union[int, float]],
    names: Sequence[str],
    motion: Optional[Sequence[str]] = None,
    playback: Optional[Union[str, PlaybackConfig]] = None,
    **kwargs: Any,
) -> Timeline:
    """Creates a Timeline with named duration sections and playback behavior.

    This is the factory function for ``Draw.timeline(...)``.

    Args:
        time: List of section durations in seconds.
        names: List of section names, same length as ``time``.
        motion: Optional list of motion object names that use this timeline.
        playback: Playback mode string ('loop', 'ping_pong', 'yoyo', etc.) or PlaybackConfig.
        **kwargs: Playback keyword options (loop=True, repeat=3, ping_pong=True, etc.).

    Returns:
        A validated Timeline instance.

    Example::

        tl = Draw.timeline(
            time=[2, 4, 5, 7],
            names=["intro", "move", "rotate", "ending"],
            playback="loop",
        )
    """
    return Timeline(time=time, names=names, motion=motion, playback=playback, **kwargs)
