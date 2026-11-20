"""Draw Motion API — Move Animation Builder.

Implements ``motion.move()`` — the concise animation interface that defines
per-channel property animations using the ``[target_value, easing, timing]``
channel format, along with playback behavior configuration.

Each channel describes:
    - target_value: The value the property should reach.
    - easing: The easing/graph curve name.
    - timing: Either a numeric duration (seconds), a named timeline section
      string, or omitted to inherit from the attached timeline.

Playback behaviors:
    - once: Play one time.
    - repeat: Repeat continuously or an integer count.
    - loop: Play again after finishing.
    - ping_pong: Forward, then backward.
    - reverse: Play backward.
    - alternate: Alternate direction each cycle.
    - yoyo: Forward and backward repeatedly.
    - restart: Restart from the beginning.
    - hold: Stay at the final value.
    - freeze: Freeze at the current value.
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
    InvalidChannelError,
    InvalidChannelFormatError,
    InvalidDurationError,
    InvalidEasingError,
)
from .easings import validate_easing
from .channels import (
    validate_channel_name,
    validate_channel_value,
    SUPPORTED_MOVE_CHANNELS,
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


class ChannelAnimation:
    """A single resolved channel animation entry.

    Attributes:
        channel: Channel name (e.g. "translate", "rotate", "z").
        target: Normalized target value.
        easing: Validated easing/graph name.
        time_ref: Timing reference — a section name (str), numeric duration
                  (float), or None if inherited from the timeline.
    """

    def __init__(
        self,
        channel: str,
        target: Any,
        easing: str,
        time_ref: Optional[Union[str, float]] = None,
    ) -> None:
        self.channel: str = channel
        self.target: Any = target
        self.easing: str = easing
        self.time_ref: Optional[Union[str, float]] = time_ref

    def to_dict(self) -> Dict[str, Any]:
        """Serializes to a JSON-compatible dictionary."""
        data: Dict[str, Any] = {
            "channel": self.channel,
            "target": _serialize_value(self.target),
            "easing": self.easing,
        }
        if self.time_ref is not None:
            if isinstance(self.time_ref, str):
                data["section"] = self.time_ref
            else:
                data["duration"] = round(self.time_ref, 6)
        return data

    def __repr__(self) -> str:
        return (
            f"ChannelAnimation(channel={self.channel!r}, target={self.target!r}, "
            f"easing={self.easing!r}, time_ref={self.time_ref!r})"
        )


def _serialize_value(val: Any) -> Any:
    """Converts a target value to a JSON-serializable form."""
    if isinstance(val, tuple):
        return list(val)
    return val


def _parse_channel_spec(
    channel_name: str,
    spec: Union[list, tuple],
) -> ChannelAnimation:
    """Parses a channel specification list into a ChannelAnimation.

    Valid formats:
        [target_value, easing]                      — timing inherited
        [target_value, easing, duration_or_section]  — explicit timing
    """
    validate_channel_name(channel_name)

    if not isinstance(spec, (list, tuple)):
        raise InvalidChannelFormatError(
            f"Channel '{channel_name}' expects a list [target, easing, ...], "
            f"got {type(spec).__name__}."
        )

    length = len(spec)

    if length == 2:
        target_raw, easing_raw = spec
        time_ref = None
    elif length == 3:
        target_raw, easing_raw, time_ref_raw = spec
        # Resolve timing reference
        if isinstance(time_ref_raw, str):
            time_ref = time_ref_raw  # Section name — validated later against timeline
        elif isinstance(time_ref_raw, (int, float)):
            dur = float(time_ref_raw)
            if dur < 0:
                raise InvalidDurationError(
                    f"Channel '{channel_name}' duration must be non-negative, got {dur}."
                )
            time_ref = dur
        else:
            raise InvalidChannelFormatError(
                f"Channel '{channel_name}' third element must be a section name (str) "
                f"or numeric duration, got {type(time_ref_raw).__name__}."
            )
    else:
        raise InvalidChannelFormatError(
            f"Channel '{channel_name}' expects 2 or 3 elements "
            f"[target, easing] or [target, easing, timing], got {length} elements."
        )

    # Validate easing
    if not isinstance(easing_raw, str):
        raise InvalidChannelFormatError(
            f"Channel '{channel_name}' easing must be a string, got {type(easing_raw).__name__}."
        )
    easing = validate_easing(easing_raw)

    # Validate and normalize target value
    target = validate_channel_value(channel_name, target_raw)

    return ChannelAnimation(
        channel=channel_name,
        target=target,
        easing=easing,
        time_ref=time_ref,
    )


class MoveAnimation:
    """Container for a set of channel animations created by motion.move().

    Attributes:
        channels: Ordered list of validated ChannelAnimation objects.
        playback: PlaybackConfig object governing repetition, loop, etc.
    """

    def __init__(
        self,
        channels: Optional[List[ChannelAnimation]] = None,
        playback: Optional[Union[str, PlaybackConfig]] = None,
        **kwargs: Any,
    ) -> None:
        self.channels: List[ChannelAnimation] = list(channels or [])
        playback_kwargs: Dict[str, Any] = {}
        channel_kwargs: Dict[str, Any] = {}

        for k, v in kwargs.items():
            if k in PLAYBACK_KWARG_NAMES:
                playback_kwargs[k] = v
            else:
                channel_kwargs[k] = v

        for channel_name, spec in channel_kwargs.items():
            anim = _parse_channel_spec(channel_name, spec)
            self.channels.append(anim)

        raw_playback = playback if playback is not None else playback_kwargs.pop("playback", None)
        self.playback: PlaybackConfig = parse_playback(raw_playback, **playback_kwargs)


    def get_channel(self, name: str) -> Optional[ChannelAnimation]:
        """Returns the ChannelAnimation for the given channel name, or None."""
        for ch in self.channels:
            if ch.channel == name:
                return ch
        return None

    def channel_names(self) -> List[str]:
        """Returns the ordered list of animated channel names."""
        return [ch.channel for ch in self.channels]

    # ── Playback Fluent Methods ─────────────────────────────────────────

    def once(self) -> "MoveAnimation":
        """Play one time."""
        self.playback.once()
        return self

    def repeat(self, count: Optional[Union[int, bool]] = None) -> "MoveAnimation":
        """Repeat continuously or an integer count."""
        self.playback.repeat(count)
        return self

    def loop(self, count: Optional[Union[int, bool]] = None) -> "MoveAnimation":
        """Play again after finishing."""
        self.playback.loop(count)
        return self

    def ping_pong(self, enable: bool = True) -> "MoveAnimation":
        """Forward, then backward."""
        self.playback.ping_pong(enable)
        return self

    def reverse(self, enable: bool = True) -> "MoveAnimation":
        """Play backward."""
        self.playback.reverse(enable)
        return self

    def play_reverse(self, enable: bool = True) -> "MoveAnimation":
        """Alias for reverse()."""
        return self.reverse(enable)

    def alternate(self, enable: bool = True) -> "MoveAnimation":
        """Alternate direction each cycle."""
        self.playback.alternate(enable)
        return self

    def yoyo(self, enable: bool = True) -> "MoveAnimation":
        """Forward and backward repeatedly."""
        self.playback.yoyo(enable)
        return self

    def restart(self) -> "MoveAnimation":
        """Restart from the beginning."""
        self.playback.restart()
        return self

    def hold(self) -> "MoveAnimation":
        """Stay at the final value."""
        self.playback.hold()
        return self

    def freeze(self) -> "MoveAnimation":
        """Freeze at the current value."""
        self.playback.freeze()
        return self

    def play(self) -> "MoveAnimation":
        """Start or resume playing."""
        self.playback.play()
        return self

    def pause(self) -> "MoveAnimation":
        """Pause playback."""
        self.playback.pause()
        return self

    def stop(self) -> "MoveAnimation":
        """Stop playback."""
        self.playback.stop()
        return self

    def seek(self, t: float) -> "MoveAnimation":
        """Seek playhead to t seconds."""
        self.playback.seek(t)
        return self

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serializes all channel animations to a JSON-compatible dictionary."""
        return {
            "type": "move",
            "channels": [ch.to_dict() for ch in self.channels],
            "playback": self.playback.to_dict(),
        }

    def __repr__(self) -> str:
        ch_strs = ", ".join(ch.channel for ch in self.channels)
        return f"MoveAnimation(channels=[{ch_strs}], playback={self.playback!r})"


def move(**kwargs: Any) -> MoveAnimation:
    """Creates a MoveAnimation with per-channel property animation specs and playback settings.

    This is the factory function for ``motion.move(...)``.

    Channel spec format: ``[target_value, easing, timing]``
    where timing is optional (a section name or numeric duration in seconds).

    Supported channels:
        translate, rotate, scale, size, opacity, blur, skew, edges, z, color, glow

    Playback options:
        once=True, repeat=3, loop=True, ping_pong=True, reverse=True,
        alternate=True, yoyo=True, restart=True, hold=True, freeze=True,
        or playback="loop"

    Example::

        motion.move(
            translate=[(300, 200), "ease_out", "intro"],
            z=[5, "linear", 1.0],
            rotate=[90, "ease_in_out", 1.5],
            opacity=[0.0, "linear", "move"],
            playback="loop",
        )

    Returns:
        A validated MoveAnimation instance.
    """
    return MoveAnimation(**kwargs)
