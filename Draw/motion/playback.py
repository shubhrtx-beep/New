"""Draw Motion API — Playback Directives & Controls.

Implements playback behavior models and control directives:
- once:        Play one time.
- repeat:      Repeat continuously or a specific integer count.
- loop:        Play again after finishing (continuous looping).
- ping_pong:   Forward, then backward.
- reverse:     Play backward.
- alternate:   Alternate direction each cycle.
- yoyo:        Forward and backward repeatedly.
- restart:     Restart from the beginning.
- hold:        Stay at the final value (fill mode).
- freeze:      Freeze at the current value.
"""

from typing import Any, Dict, Optional, Union
from .errors import InvalidPlaybackError

# String constants for playback directives & modes
ONCE = "once"
REPEAT = "repeat"
LOOP = "loop"
PING_PONG = "ping_pong"
REVERSE = "reverse"
ALTERNATE = "alternate"
YOYO = "yoyo"
RESTART = "restart"
HOLD = "hold"
FREEZE = "freeze"

SUPPORTED_PLAYBACK_MODES = frozenset({
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
})

SUPPORTED_FILL_MODES = frozenset({
    HOLD,
    FREEZE,
    "none",
    "backwards",
    "both",
})


class PlaybackConfig:
    """Encapsulates playback parameters, loop behavior, and runtime directives.

    Attributes:
        mode: Main playback mode string ('once', 'loop', 'ping_pong', etc.).
        repeat_count: Number of repetitions. 1 for 'once', integer N for specific count,
                      or -1 for continuous / infinite repeating.
        direction: 'forward' or 'backward'.
        is_reverse: True if playback direction is reversed.
        is_ping_pong: True if playback plays forward then backward.
        is_alternate: True if direction alternates on each cycle.
        is_yoyo: True if playing forward and backward repeatedly.
        fill: Post-animation fill behavior ('hold', 'freeze', 'none').
        state: Playback status ('stopped', 'playing', 'paused', 'frozen').
        speed: Playback speed multiplier (default 1.0).
    """

    def __init__(
        self,
        mode: str = ONCE,
        repeat: Optional[Union[int, bool]] = 1,
        reverse: bool = False,
        ping_pong: bool = False,
        alternate: bool = False,
        yoyo: bool = False,
        fill: str = HOLD,
        state: str = "stopped",
        speed: float = 1.0,
    ) -> None:
        self.mode: str = mode
        self.repeat_count: int = self._normalize_repeat(repeat)
        self.is_reverse: bool = bool(reverse)
        self.direction: str = "backward" if self.is_reverse else "forward"
        self.is_ping_pong: bool = bool(ping_pong)
        self.is_alternate: bool = bool(alternate)
        self.is_yoyo: bool = bool(yoyo)
        self.fill: str = fill
        self.state: str = state
        self.speed: float = float(speed)
        self.time: float = 0.0

        # Apply mode defaults if a specific mode was requested
        self._apply_mode(mode)

    @staticmethod
    def _normalize_repeat(val: Optional[Union[int, bool]]) -> int:
        if val is None or val is True:
            return -1  # Infinite
        if val is False:
            return 1
        val_int = int(val)
        if val_int < -1:
            raise InvalidPlaybackError(f"Repeat count cannot be less than -1, got {val_int}.")
        return val_int

    def _apply_mode(self, mode: str) -> None:
        if mode not in SUPPORTED_PLAYBACK_MODES:
            raise InvalidPlaybackError(
                f"Unsupported playback mode '{mode}'. "
                f"Supported modes: {', '.join(sorted(SUPPORTED_PLAYBACK_MODES))}."
            )
        self.mode = mode
        if mode == ONCE:
            self.repeat_count = 1
        elif mode == LOOP:
            self.repeat_count = -1
        elif mode == REPEAT:
            if self.repeat_count == 1:
                self.repeat_count = -1
        elif mode == PING_PONG:
            self.is_ping_pong = True
        elif mode == REVERSE:
            self.is_reverse = True
            self.direction = "backward"
        elif mode == ALTERNATE:
            self.is_alternate = True
            if self.repeat_count == 1:
                self.repeat_count = -1
        elif mode == YOYO:
            self.is_yoyo = True
            self.is_ping_pong = True
            self.is_alternate = True
            if self.repeat_count == 1:
                self.repeat_count = -1
        elif mode == RESTART:
            self.state = "playing"
        elif mode == HOLD:
            self.fill = HOLD
        elif mode == FREEZE:
            self.fill = FREEZE
            self.state = "frozen"

    # ── Directive / Builder Methods ─────────────────────────────────────

    def once(self) -> "PlaybackConfig":
        """Play one time."""
        self.mode = ONCE
        self.repeat_count = 1
        self.is_ping_pong = False
        self.is_alternate = False
        self.is_yoyo = False
        self.is_reverse = False
        self.direction = "forward"
        return self

    def repeat(self, count: Optional[Union[int, bool]] = None) -> "PlaybackConfig":
        """Repeat continuously or a specific integer count."""
        self.mode = REPEAT
        if count is None or count is True:
            self.repeat_count = -1
        else:
            self.repeat_count = self._normalize_repeat(count)
        return self

    def repeat_count_set(self, count: Optional[Union[int, bool]] = None) -> "PlaybackConfig":
        """Alias for repeat()."""
        return self.repeat(count)

    def loop(self, count: Optional[Union[int, bool]] = None) -> "PlaybackConfig":
        """Play again after finishing (continuous loop or repeat count)."""
        self.mode = LOOP
        if count is None or count is True:
            self.repeat_count = -1
        else:
            self.repeat_count = self._normalize_repeat(count)
        return self

    def ping_pong(self, enable: bool = True) -> "PlaybackConfig":
        """Forward, then backward."""
        self.is_ping_pong = bool(enable)
        if enable and self.mode == ONCE:
            self.mode = PING_PONG
        return self

    def reverse(self, enable: bool = True) -> "PlaybackConfig":
        """Play backward."""
        self.is_reverse = bool(enable)
        self.direction = "backward" if self.is_reverse else "forward"
        if enable and self.mode == ONCE:
            self.mode = REVERSE
        return self

    def play_reverse(self, enable: bool = True) -> "PlaybackConfig":
        """Alias for reverse()."""
        return self.reverse(enable)

    def alternate(self, enable: bool = True) -> "PlaybackConfig":
        """Alternate direction each cycle."""
        self.is_alternate = bool(enable)
        if enable and self.mode == ONCE:
            self.mode = ALTERNATE
        return self

    def yoyo(self, enable: bool = True) -> "PlaybackConfig":
        """Forward and backward repeatedly."""
        self.is_yoyo = bool(enable)
        self.is_ping_pong = bool(enable)
        self.is_alternate = bool(enable)
        if enable and self.mode in (ONCE, PING_PONG):
            self.mode = YOYO
            if self.repeat_count == 1:
                self.repeat_count = -1
        return self

    def restart(self) -> "PlaybackConfig":
        """Restart from the beginning."""
        self.state = "playing"
        return self

    def hold(self) -> "PlaybackConfig":
        """Stay at the final value."""
        self.fill = HOLD
        return self

    def freeze(self) -> "PlaybackConfig":
        """Freeze at the current value."""
        self.fill = FREEZE
        self.state = "frozen"
        return self

    # ── Runtime State Controls ──────────────────────────────────────────

    def play(self) -> "PlaybackConfig":
        """Start or resume playing."""
        self.state = "playing"
        return self

    def pause(self) -> "PlaybackConfig":
        """Pause playback at the current position."""
        self.state = "paused"
        return self

    def stop(self) -> "PlaybackConfig":
        """Stop playback and reset to start."""
        self.state = "stopped"
        self.time = 0.0
        return self

    def seek(self, t: float) -> "PlaybackConfig":
        """Sets the playhead to a specific timestamp in seconds."""
        self.time = max(0.0, float(t))
        return self

    # ── Serialization ───────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serializes playback configuration for the C++/OpenGL engine."""
        return {
            "mode": self.mode,
            "repeat": self.repeat_count,
            "direction": self.direction,
            "reverse": self.is_reverse,
            "ping_pong": self.is_ping_pong,
            "alternate": self.is_alternate,
            "yoyo": self.is_yoyo,
            "fill": self.fill,
            "state": self.state,
            "speed": round(self.speed, 4),
        }

    def copy(self) -> "PlaybackConfig":
        """Returns an independent clone of this PlaybackConfig."""
        cfg = PlaybackConfig(
            mode=self.mode,
            repeat=self.repeat_count,
            reverse=self.is_reverse,
            ping_pong=self.is_ping_pong,
            alternate=self.is_alternate,
            yoyo=self.is_yoyo,
            fill=self.fill,
            state=self.state,
            speed=self.speed,
        )
        cfg.direction = self.direction
        return cfg

    def __repr__(self) -> str:
        flags = [f"mode={self.mode!r}"]
        if self.repeat_count != 1:
            flags.append(f"repeat={self.repeat_count}")
        if self.is_reverse:
            flags.append("reverse=True")
        if self.is_ping_pong:
            flags.append("ping_pong=True")
        if self.is_alternate:
            flags.append("alternate=True")
        if self.is_yoyo:
            flags.append("yoyo=True")
        if self.fill != HOLD:
            flags.append(f"fill={self.fill!r}")
        if self.state != "stopped":
            flags.append(f"state={self.state!r}")
        return f"PlaybackConfig({', '.join(flags)})"


# ── Parsing & Factory Functions ─────────────────────────────────────────

PLAYBACK_KWARG_NAMES = frozenset({
    "playback",
    "mode",
    "loop",
    "repeat",
    "ping_pong",
    "reverse",
    "alternate",
    "yoyo",
    "restart",
    "hold",
    "freeze",
    "once",
    "fill",
    "speed",
    "state",
})


def parse_playback(
    val: Optional[Union[str, PlaybackConfig]] = None,
    **kwargs: Any,
) -> PlaybackConfig:
    """Parses and normalizes playback arguments into a PlaybackConfig."""
    if isinstance(val, PlaybackConfig):
        cfg = val.copy()
    elif isinstance(val, str):
        cfg = PlaybackConfig(mode=val)
    else:
        cfg = PlaybackConfig()

    # Apply keyword overrides
    if "mode" in kwargs and kwargs["mode"] is not None:
        cfg._apply_mode(kwargs["mode"])

    if "once" in kwargs and kwargs["once"]:
        cfg.once()

    if "repeat" in kwargs and kwargs["repeat"] is not None:
        cfg.repeat(kwargs["repeat"])

    if "loop" in kwargs and kwargs["loop"]:
        cfg.loop(kwargs.get("repeat"))

    if "ping_pong" in kwargs and kwargs["ping_pong"]:
        cfg.ping_pong(True)

    if "reverse" in kwargs and kwargs["reverse"]:
        cfg.reverse(True)

    if "alternate" in kwargs and kwargs["alternate"]:
        cfg.alternate(True)

    if "yoyo" in kwargs and kwargs["yoyo"]:
        cfg.yoyo(True)

    if "restart" in kwargs and kwargs["restart"]:
        cfg.restart()

    if "hold" in kwargs and kwargs["hold"]:
        cfg.hold()

    if "freeze" in kwargs and kwargs["freeze"]:
        cfg.freeze()

    if "fill" in kwargs and kwargs["fill"] is not None:
        cfg.fill = str(kwargs["fill"])

    if "state" in kwargs and kwargs["state"] is not None:
        cfg.state = str(kwargs["state"])

    if "speed" in kwargs and kwargs["speed"] is not None:
        cfg.speed = float(kwargs["speed"])

    return cfg


# Convenient standalone factory helpers
def once() -> PlaybackConfig:
    """Play one time."""
    return PlaybackConfig(mode=ONCE)


def repeat(count: Optional[Union[int, bool]] = None) -> PlaybackConfig:
    """Repeat continuously or a specific integer count."""
    return PlaybackConfig().repeat(count)


def loop(count: Optional[Union[int, bool]] = None) -> PlaybackConfig:
    """Play again after finishing."""
    return PlaybackConfig().loop(count)


def ping_pong() -> PlaybackConfig:
    """Forward, then backward."""
    return PlaybackConfig().ping_pong()


def reverse(enable: bool = True) -> PlaybackConfig:
    """Play backward."""
    return PlaybackConfig().reverse(enable)


def alternate(enable: bool = True) -> PlaybackConfig:
    """Alternate direction each cycle."""
    return PlaybackConfig().alternate(enable)


def yoyo(enable: bool = True) -> PlaybackConfig:
    """Forward and backward repeatedly."""
    return PlaybackConfig().yoyo(enable)


def restart() -> PlaybackConfig:
    """Restart from the beginning."""
    return PlaybackConfig().restart()


def hold() -> PlaybackConfig:
    """Stay at the final value."""
    return PlaybackConfig().hold()


def freeze() -> PlaybackConfig:
    """Freeze at the current value."""
    return PlaybackConfig().freeze()


def seek(t: float) -> PlaybackConfig:
    """Sets playback playhead to t seconds."""
    return PlaybackConfig().seek(t)


def playback(
    mode: str = ONCE,
    repeat: Optional[Union[int, bool]] = 1,
    reverse: bool = False,
    ping_pong: bool = False,
    alternate: bool = False,
    yoyo: bool = False,
    fill: str = HOLD,
    state: str = "stopped",
    speed: float = 1.0,
    **kwargs: Any,
) -> PlaybackConfig:
    """Factory creating a PlaybackConfig instance."""
    return parse_playback(
        mode=mode,
        repeat=repeat,
        reverse=reverse,
        ping_pong=ping_pong,
        alternate=alternate,
        yoyo=yoyo,
        fill=fill,
        state=state,
        speed=speed,
        **kwargs,
    )
