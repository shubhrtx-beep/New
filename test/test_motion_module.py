"""Draw Motion & Timeline Module — Comprehensive Test Suite.

Tests all of Part A (motion.move) and Part B (Draw.timeline / Draw.time_line)
from the Draw V3 Motion & Timeline Design Summary.
"""

import sys
import os

# Ensure Draw package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Draw
from Draw import motion, time_line, timeline, move
from Draw.motion import (
    GLOBAL_MOTION_REGISTRY,
    MoveAnimation,
    ChannelAnimation,
    Timeline,
    TimelineSection,
    Motion,
    ResolvedChannel,
    SUPPORTED_EASINGS,
    SUPPORTED_MOVE_CHANNELS,
)
from Draw.motion.errors import (
    DrawMotionError,
    InvalidEasingError,
    InvalidChannelError,
    InvalidChannelFormatError,
    InvalidDurationError,
    DuplicateMotionNameError,
    MotionNotFoundError,
    DuplicateTimelineNameError,
    TimelineNotFoundError,
    TimelineSectionNotFoundError,
    TimelineSectionCountMismatchError,
    InvalidTimelineError,
)

passed = 0
failed = 0
errors_log = []


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        errors_log.append(label)
        print(f"  [FAIL] {label}")


def check_raises(label, exc_type, fn):
    global passed, failed
    try:
        fn()
        failed += 1
        errors_log.append(f"{label} (no exception raised)")
        print(f"  [FAIL] {label} — expected {exc_type.__name__}, got nothing")
    except exc_type as e:
        passed += 1
        print(f"  [PASS] {label} — raised {exc_type.__name__}: {e}")
    except Exception as e:
        failed += 1
        errors_log.append(f"{label} (wrong exception: {type(e).__name__})")
        print(f"  [FAIL] {label} — expected {exc_type.__name__}, got {type(e).__name__}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# SETUP: Clear registries before each major test group
# ═══════════════════════════════════════════════════════════════════════

def reset():
    GLOBAL_MOTION_REGISTRY.clear()


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 1: motion.move() — Channel Parsing & Validation
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 1: motion.move() — Channel Parsing & Validation ═══")
reset()

# 1.1 Basic 3-element channel with numeric duration
m = motion.move(
    translate=[(300, 200), "ease_out", 2.0],
    rotate=[90, "ease_in_out", 1.5],
    opacity=[0.0, "linear", 1.0],
)
check("1.1a move creates MoveAnimation", isinstance(m, MoveAnimation))
check("1.1b has 3 channels", len(m.channels) == 3)
check("1.1c translate target", m.get_channel("translate").target == (300.0, 200.0))
check("1.1d rotate target", m.get_channel("rotate").target == 90.0)
check("1.1e opacity target", m.get_channel("opacity").target == 0.0)
check("1.1f translate easing", m.get_channel("translate").easing == "ease_out")
check("1.1g rotate time_ref", m.get_channel("rotate").time_ref == 1.5)

# 1.2 Channel with section name reference
m2 = motion.move(
    translate=[(300, 200), "ease_out", "intro"],
    rotate=[90, "ease_in_out", "move"],
)
check("1.2a section name in translate", m2.get_channel("translate").time_ref == "intro")
check("1.2b section name in rotate", m2.get_channel("rotate").time_ref == "move")

# 1.3 Channel with 2-element spec (timing inherited)
m3 = motion.move(
    translate=[(300, 200), "ease_out"],
    rotate=[90, "ease_in_out"],
)
check("1.3a inherited timing (None)", m3.get_channel("translate").time_ref is None)
check("1.3b inherited timing (None)", m3.get_channel("rotate").time_ref is None)

# 1.4 All supported channels
m4 = motion.move(
    translate=[(100, 200), "linear", 1.0],
    rotate=[45, "ease_in", 1.0],
    scale=[(2.0, 2.0), "ease_out", 1.0],
    size=[(200, 100), "ease_in_out", 1.0],
    opacity=[0.5, "linear", 1.0],
    blur=[10.0, "ease_out", 1.0],
    skew=[(10, 5), "ease_in", 1.0],
    edges=[20, "ease_out", 1.0],
)
check("1.4 all 8 channels created", len(m4.channels) == 8)
check("1.4a channel_names", set(m4.channel_names()) == {"translate", "rotate", "scale", "size", "opacity", "blur", "skew", "edges"})

# 1.5 Scalar broadcast to tuple channel
m5 = motion.move(scale=[2.0, "linear", 1.0])
check("1.5 scalar broadcast", m5.get_channel("scale").target == (2.0, 2.0))

# 1.6 to_dict serialization
d = m.to_dict()
check("1.6a to_dict type", d["type"] == "move")
check("1.6b to_dict channels count", len(d["channels"]) == 3)
ch0 = d["channels"][0]
check("1.6c channel dict has target", "target" in ch0)
check("1.6d channel dict has easing", "easing" in ch0)

# 1.7 Error: unsupported channel
check_raises("1.7 unsupported channel", InvalidChannelError,
             lambda: motion.move(foobar=[10, "linear", 1.0]))

# 1.8 Error: bad easing
check_raises("1.8 bad easing", InvalidEasingError,
             lambda: motion.move(rotate=[90, "not_a_real_easing", 1.0]))

# 1.9 Error: wrong spec length
check_raises("1.9a spec too short", InvalidChannelFormatError,
             lambda: motion.move(rotate=[90]))
check_raises("1.9b spec too long", InvalidChannelFormatError,
             lambda: motion.move(rotate=[90, "linear", 1.0, "extra"]))

# 1.10 Error: negative duration
check_raises("1.10 negative duration", InvalidDurationError,
             lambda: motion.move(rotate=[90, "linear", -1.0]))

# 1.11 Error: wrong value type for tuple channel
check_raises("1.11 wrong tuple length", InvalidChannelFormatError,
             lambda: motion.move(translate=[(1, 2, 3), "linear", 1.0]))

# 1.12 Error: non-numeric scalar channel
check_raises("1.12 non-numeric scalar", InvalidChannelFormatError,
             lambda: motion.move(opacity=["full", "linear", 1.0]))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 2: Draw.timeline() — Timeline Creation
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 2: Draw.timeline() — Timeline Creation ═══")
reset()

# 2.1 Basic timeline creation
tl = Draw.timeline(
    time=[2, 4, 5, 7],
    names=["intro", "move", "rotate", "ending"],
)
check("2.1a is Timeline", isinstance(tl, Timeline))
check("2.1b has 4 sections", len(tl.sections) == 4)
check("2.1c total_duration", tl.total_duration == 18.0)

# 2.2 Section boundaries
intro = tl.get_section("intro")
move_sec = tl.get_section("move")
rotate_sec = tl.get_section("rotate")
ending = tl.get_section("ending")
check("2.2a intro start=0", intro.start == 0.0)
check("2.2b intro end=2", intro.end == 2.0)
check("2.2c move start=2", move_sec.start == 2.0)
check("2.2d move end=6", move_sec.end == 6.0)
check("2.2e rotate start=6", rotate_sec.start == 6.0)
check("2.2f rotate end=11", rotate_sec.end == 11.0)
check("2.2g ending start=11", ending.start == 11.0)
check("2.2h ending end=18", ending.end == 18.0)

# 2.3 Section names
check("2.3 section_names", tl.section_names() == ["intro", "move", "rotate", "ending"])

# 2.4 has_section
check("2.4a has intro", tl.has_section("intro"))
check("2.4b no foobar", not tl.has_section("foobar"))

# 2.5 resolve_timing with section name
start, dur = tl.resolve_timing("move")
check("2.5a section start", start == 2.0)
check("2.5b section duration", dur == 4.0)

# 2.6 resolve_timing with numeric duration
start, dur = tl.resolve_timing(1.5)
check("2.6a numeric start=0", start == 0.0)
check("2.6b numeric duration=1.5", dur == 1.5)

# 2.7 Timeline with motion list
tl2 = Draw.timeline(
    time=[2, 4],
    names=["a", "b"],
    motion=["ball", "n4"],
)
check("2.7a motion_names", tl2.motion_names == ["ball", "n4"])

# 2.8 to_dict serialization
d = tl.to_dict()
check("2.8a schema", d["schema"] == "draw.timeline")
check("2.8b version", d["version"] == 1)
check("2.8c sections count", len(d["sections"]) == 4)
check("2.8d total_duration", d["total_duration"] == 18.0)

# 2.9 Error: mismatched time/names
check_raises("2.9 mismatched lengths", TimelineSectionCountMismatchError,
             lambda: Draw.timeline(time=[1, 2], names=["a"]))

# 2.10 Error: empty time
check_raises("2.10 empty time", InvalidTimelineError,
             lambda: Draw.timeline(time=[], names=[]))

# 2.11 Error: duplicate section names
check_raises("2.11 duplicate names", InvalidTimelineError,
             lambda: Draw.timeline(time=[1, 2], names=["a", "a"]))

# 2.12 Error: negative section duration
check_raises("2.12 negative duration", InvalidDurationError,
             lambda: Draw.timeline(time=[1, -2], names=["a", "b"]))

# 2.13 Error: nonexistent section lookup
check_raises("2.13 section not found", TimelineSectionNotFoundError,
             lambda: tl.get_section("nonexistent"))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 3: Draw.time_line() — Timeline Registration
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 3: Draw.time_line() — Timeline Registration ═══")
reset()

# 3.1 Register a timeline
tl = Draw.timeline(
    time=[2, 4, 5, 7],
    names=["intro", "move", "rotate", "ending"],
)
registered_tl = Draw.time_line(name="n1", time_line=tl)
check("3.1a returns Timeline", isinstance(registered_tl, Timeline))
check("3.1b same object", registered_tl is tl)
check("3.1c exists", Draw.time_line.exists("n1"))

# 3.2 Retrieve registered timeline
retrieved = Draw.time_line.get("n1")
check("3.2 get returns same", retrieved is tl)

# 3.3 List timelines
names = Draw.time_line.list()
check("3.3 list returns name", "n1" in names)

# 3.4 Error: duplicate timeline name
check_raises("3.4 duplicate timeline name", DuplicateTimelineNameError,
             lambda: Draw.time_line(name="n1", time_line=Draw.timeline(time=[1], names=["x"])))

# 3.5 Error: get nonexistent timeline
check_raises("3.5 timeline not found", TimelineNotFoundError,
             lambda: Draw.time_line.get("nonexistent"))

# 3.6 Remove timeline
removed = Draw.time_line.remove("n1")
check("3.6a removed count", removed == 1)
check("3.6b no longer exists", not Draw.time_line.exists("n1"))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 4: Draw.motion() — Motion Registration & Timeline Attachment
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 4: Draw.motion() — Motion Registration & Attachment ═══")
reset()

# 4.1 Register a motion without timeline (explicit durations)
m = Draw.motion(
    name="ball",
    move=motion.move(
        translate=[(300, 200), "ease_out", 2.0],
        rotate=[90, "ease_in_out", 1.5],
        opacity=[0.0, "linear", 1.0],
    ),
)
check("4.1a returns Motion", isinstance(m, Motion))
check("4.1b exists", Draw.motion.exists("ball"))
check("4.1c name", m.name == "ball")
check("4.1d move_anim set", m.move_anim is not None)
check("4.1e no timeline", m.timeline is None)

# 4.2 Resolve without timeline — explicit durations
resolved = m.resolve()
check("4.2a 3 resolved channels", len(resolved) == 3)
# translate: explicit 2.0s from t=0
tr = resolved[0]
check("4.2b translate start=0", tr.start == 0.0)
check("4.2c translate duration=2.0", tr.duration == 2.0)
check("4.2d translate target", tr.target == (300.0, 200.0))
check("4.2e translate easing", tr.easing == "ease_out")

# 4.3 to_dict
d = m.to_dict()
check("4.3a schema", d["schema"] == "draw.motion")
check("4.3b name", d["name"] == "ball")
check("4.3c has move", "move" in d)

# 4.4 to_resolved_dict
rd = m.to_resolved_dict()
check("4.4a resolved schema", rd["schema"] == "draw.motion.resolved")
check("4.4b resolved channels count", len(rd["channels"]) == 3)

# 4.5 Error: duplicate motion name
check_raises("4.5 duplicate motion name", DuplicateMotionNameError,
             lambda: Draw.motion(name="ball", move=motion.move(rotate=[45, "linear", 1.0])))

# 4.6 Error: get nonexistent motion
check_raises("4.6 motion not found", MotionNotFoundError,
             lambda: Draw.motion.get("nonexistent"))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 5: Motion + Timeline Integration (Design Doc Example)
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 5: Motion + Timeline Integration ═══")
reset()

# 5.1 Full design doc example — Step 1: Define and register timeline
Draw.time_line(
    name="n1",
    time_line=Draw.timeline(
        time=[2, 4, 5, 7],
        names=["intro", "move", "rotate", "ending"],
    ),
)

# 5.2 Step 2: Attach timeline to motion and reference sections
m = Draw.motion(
    name="ball",
    time_line="n1",
    move=motion.move(
        translate=[(300, 200), "ease_out", "intro"],
        rotate=[90, "ease_in_out", "intro"],
        opacity=[0.0, "linear", "move"],
        size=[(200, 100), "ease_out", "move"],
        skew=[(10, 0), "ease_in", 1.0],
        edges=[20, "ease_out", "ending"],
    ),
)
check("5.2a timeline attached", m.timeline is not None)
check("5.2b timeline_name", m.timeline_name == "n1")

# 5.3 Resolve and verify section timing
resolved = m.resolve()
check("5.3a 6 resolved channels", len(resolved) == 6)

# Build lookup
by_ch = {r.channel: r for r in resolved}

# translate -> "intro" section: start=0, duration=2
check("5.3b translate start=0", by_ch["translate"].start == 0.0)
check("5.3c translate duration=2", by_ch["translate"].duration == 2.0)

# rotate -> "intro" section: start=0, duration=2
check("5.3d rotate start=0", by_ch["rotate"].start == 0.0)
check("5.3e rotate duration=2", by_ch["rotate"].duration == 2.0)

# opacity -> "move" section: start=2, duration=4
check("5.3f opacity start=2", by_ch["opacity"].start == 2.0)
check("5.3g opacity duration=4", by_ch["opacity"].duration == 4.0)

# size -> "move" section: start=2, duration=4
check("5.3h size start=2", by_ch["size"].start == 2.0)
check("5.3i size duration=4", by_ch["size"].duration == 4.0)

# skew -> explicit 1.0s from t=0
check("5.3j skew start=0", by_ch["skew"].start == 0.0)
check("5.3k skew duration=1", by_ch["skew"].duration == 1.0)

# edges -> "ending" section: start=11, duration=7
check("5.3l edges start=11", by_ch["edges"].start == 11.0)
check("5.3m edges duration=7", by_ch["edges"].duration == 7.0)

# 5.4 Resolved dict output for C++ engine
rd = m.to_resolved_dict()
check("5.4a resolved schema", rd["schema"] == "draw.motion.resolved")
check("5.4b has time_line field", rd["time_line"] == "n1")
check("5.4c 6 channels in resolved", len(rd["channels"]) == 6)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 6: Multiple Motions Sharing One Timeline
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 6: Multiple Motions Sharing One Timeline ═══")
reset()

# 6.1 Register shared timeline
Draw.time_line(
    name="n1",
    time_line=Draw.timeline(
        time=[2, 4, 5, 7],
        names=["intro", "move", "rotate", "ending"],
        motion=["ball", "n4"],
    ),
)

# 6.2 First motion — uses inherited timing (2-element specs)
m1 = Draw.motion(
    name="ball",
    time_line="n1",
    move=motion.move(
        translate=[(300, 200), "ease_out"],
        opacity=[0.0, "linear"],
    ),
)

# 6.3 Second motion — uses inherited timing
m2 = Draw.motion(
    name="n4",
    time_line="n1",
    move=motion.move(
        rotate=[90, "ease_in_out"],
    ),
)

check("6.2a ball timeline attached", m1.timeline is not None)
check("6.3a n4 timeline attached", m2.timeline is not None)
check("6.3b same timeline object", m1.timeline is m2.timeline)

# 6.4 Resolve inherited timing — defaults to first section ("intro": start=0, dur=2)
r1 = m1.resolve()
r2 = m2.resolve()
check("6.4a ball translate inherits intro start", r1[0].start == 0.0)
check("6.4b ball translate inherits intro dur", r1[0].duration == 2.0)
check("6.4c n4 rotate inherits intro start", r2[0].start == 0.0)
check("6.4d n4 rotate inherits intro dur", r2[0].duration == 2.0)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 7: Timeline Registered After Motion (Late Attachment)
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 7: Late Timeline Attachment ═══")
reset()

# 7.1 Register motion first, referencing a timeline that doesn't exist yet
m = Draw.motion(
    name="late_ball",
    time_line="late_tl",
    move=motion.move(
        translate=[(100, 100), "ease_out", "a"],
    ),
)
check("7.1a no timeline yet", m.timeline is None)

# 7.2 Error if we try to resolve section before timeline exists
check_raises("7.2 resolve without timeline", TimelineSectionNotFoundError,
             lambda: m.resolve())

# 7.3 Now register the timeline — auto-attaches
Draw.time_line(
    name="late_tl",
    time_line=Draw.timeline(time=[3], names=["a"]),
)
check("7.3a auto-attached", m.timeline is not None)

# 7.4 Resolve now works
resolved = m.resolve()
check("7.4a start=0", resolved[0].start == 0.0)
check("7.4b duration=3", resolved[0].duration == 3.0)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 8: Registry Operations (list, remove, clear)
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 8: Registry Operations ═══")
reset()

Draw.time_line(
    name="tl1",
    time_line=Draw.timeline(time=[1, 2], names=["a", "b"]),
)
Draw.motion(name="m1", move=motion.move(rotate=[45, "linear", 1.0]))
Draw.motion(name="m2", move=motion.move(opacity=[0.5, "ease_in", 2.0]))

# 8.1 List motions
check("8.1 list all motions", Draw.motion.list() == ["m1", "m2"])

# 8.2 List timelines
check("8.2 list all timelines", Draw.time_line.list() == ["tl1"])

# 8.3 List single motion detail
detail = Draw.motion.list("m1")
check("8.3 detail name", detail["name"] == "m1")

# 8.4 Remove motion
removed = Draw.motion.remove("m1")
check("8.4a removed count", removed == 1)
check("8.4b no longer exists", not Draw.motion.exists("m1"))
check("8.4c m2 still exists", Draw.motion.exists("m2"))

# 8.5 Remove timeline (detaches from motions)
Draw.motion(name="m3", time_line="tl1", move=motion.move(rotate=[90, "ease_out"]))
m3 = Draw.motion.get("m3")
check("8.5a m3 timeline attached", m3.timeline is not None)
Draw.time_line.remove("tl1")
check("8.5b m3 timeline detached", m3.timeline is None)

# 8.6 Clear all
Draw.time_line(name="tl2", time_line=Draw.timeline(time=[1], names=["x"]))
Draw.motion.clear()
check("8.6a motions cleared", Draw.motion.list() == [])
check("8.6b timelines still exist", Draw.time_line.exists("tl2"))
Draw.time_line.clear()
check("8.6c timelines cleared", Draw.time_line.list() == [])


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 9: Easing Validation
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 9: Easing Validation ═══")

# 9.1 All basic easings work
basic_easings = ["linear", "ease_in", "ease_out", "ease_in_out", "smooth"]
for e in basic_easings:
    m = motion.move(rotate=[90, e, 1.0])
    check(f"9.1 easing '{e}' accepted", m.get_channel("rotate").easing == e)

# 9.2 Extended easings work
extended = ["ease_in_back", "ease_out_bounce", "ease_in_out_elastic", "ease_in_cubic"]
for e in extended:
    m = motion.move(rotate=[90, e, 1.0])
    check(f"9.2 easing '{e}' accepted", m.get_channel("rotate").easing == e)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 10: Draw namespace integration
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 10: Draw Namespace Integration ═══")
reset()

# 10.1 Draw.motion is callable
check("10.1 Draw.motion callable", callable(Draw.motion))

# 10.2 Draw.motion.move is accessible
check("10.2 Draw.motion.move callable", callable(Draw.motion.move))

# 10.3 Draw.timeline is the factory
check("10.3 Draw.timeline callable", callable(Draw.timeline))

# 10.4 Draw.time_line is the registrar
check("10.4 Draw.time_line callable", callable(Draw.time_line))

# 10.5 Full API usage from Draw namespace
Draw.time_line(
    name="test_tl",
    time_line=Draw.timeline(
        time=[1, 2],
        names=["part1", "part2"],
    ),
)
m = Draw.motion(
    name="test_shape",
    time_line="test_tl",
    move=Draw.motion.move(
        translate=[(50, 50), "ease_out", "part1"],
        rotate=[180, "ease_in_out", "part2"],
    ),
)
resolved = m.resolve()
check("10.5a translate resolves to part1", resolved[0].start == 0.0 and resolved[0].duration == 1.0)
check("10.5b rotate resolves to part2", resolved[1].start == 1.0 and resolved[1].duration == 2.0)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 11: "z" Channel in motion.move()
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 11: 'z' Channel in motion.move() ═══")
reset()

# 11.1 Basic z channel with integer value
mz1 = motion.move(z=[5, "linear", 1.0])
check("11.1a z channel exists", mz1.get_channel("z") is not None)
check("11.1b z target is int 5", mz1.get_channel("z").target == 5)
check("11.1c z target type is int", isinstance(mz1.get_channel("z").target, int))
check("11.1d z easing", mz1.get_channel("z").easing == "linear")
check("11.1e z time_ref", mz1.get_channel("z").time_ref == 1.0)

# 11.2 Float value rounded to int for z
mz2 = motion.move(z=[3.7, "ease_out", 2.0])
check("11.2a z float rounded to int 4", mz2.get_channel("z").target == 4)
check("11.2b z type is int", isinstance(mz2.get_channel("z").target, int))

# 11.3 Multi-channel with z and translate
mz3 = motion.move(
    translate=[(100, 200), "ease_out", 2.0],
    z=[10, "linear", 1.0],
    opacity=[0.5, "ease_in", 1.5],
)
check("11.3a 3 channels including z", len(mz3.channels) == 3)
check("11.3b channel names contain z", "z" in mz3.channel_names())
check("11.3c z target is 10", mz3.get_channel("z").target == 10)

# 11.4 Resolution of z channel in Draw.motion
Draw.time_line(
    name="z_tl",
    time_line=Draw.timeline(time=[2, 3], names=["first", "second"]),
)
mot_z = Draw.motion(
    name="layered_card",
    time_line="z_tl",
    move=motion.move(
        translate=[(0, 50), "ease_out", "first"],
        z=[3, "linear", "second"],
    ),
)
res_z = mot_z.resolve()
by_name = {r.channel: r for r in res_z}
check("11.4a z resolved exists", "z" in by_name)
check("11.4b z resolved start=2", by_name["z"].start == 2.0)
check("11.4c z resolved duration=3", by_name["z"].duration == 3.0)
check("11.4d z resolved target=3", by_name["z"].target == 3)

# 11.5 Error on invalid non-numeric z value
check_raises("11.5 non-numeric z", InvalidChannelFormatError,
             lambda: motion.move(z=["top", "linear", 1.0]))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 12: Playback Directives & Configurations
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 12: Playback Directives & Configurations ═══")
from Draw.motion import (
    PlaybackConfig,
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
    InvalidPlaybackError,
)

# 12.1 once — Play one time
p_once = once()
check("12.1a once mode", p_once.mode == ONCE)
check("12.1b once repeat=1", p_once.repeat_count == 1)
check("12.1c once direction=forward", p_once.direction == "forward")
check("12.1d once not ping_pong", not p_once.is_ping_pong)

# 12.2 repeat — Repeat continuously or a specific integer count
p_rep_inf = repeat()
check("12.2a repeat continuous mode", p_rep_inf.mode == REPEAT)
check("12.2b repeat continuous repeat=-1", p_rep_inf.repeat_count == -1)

p_rep_3 = repeat(3)
check("12.2c repeat count=3 mode", p_rep_3.mode == REPEAT)
check("12.2d repeat count=3 repeat=3", p_rep_3.repeat_count == 3)

# 12.3 loop — Play again after finishing
p_loop = loop()
check("12.3a loop mode", p_loop.mode == LOOP)
check("12.3b loop repeat=-1 (infinite)", p_loop.repeat_count == -1)

p_loop_5 = loop(5)
check("12.3c loop with count repeat=5", p_loop_5.repeat_count == 5)

# 12.4 ping_pong — Forward, then backward
p_pp = ping_pong()
check("12.4a ping_pong mode", p_pp.mode == PING_PONG)
check("12.4b ping_pong is True", p_pp.is_ping_pong is True)

# 12.5 reverse — Play backward
p_rev = reverse()
check("12.5a reverse is True", p_rev.is_reverse is True)
check("12.5b reverse direction backward", p_rev.direction == "backward")
check("12.5c reverse mode", p_rev.mode == REVERSE)

# 12.6 alternate — Alternate direction each cycle
p_alt = alternate()
check("12.6a alternate is True", p_alt.is_alternate is True)
check("12.6b alternate mode", p_alt.mode == ALTERNATE)

# 12.7 yoyo — Forward and backward repeatedly
p_yoyo = yoyo()
check("12.7a yoyo is True", p_yoyo.is_yoyo is True)
check("12.7b yoyo sets ping_pong", p_yoyo.is_ping_pong is True)
check("12.7c yoyo sets alternate", p_yoyo.is_alternate is True)
check("12.7d yoyo mode", p_yoyo.mode == YOYO)
check("12.7e yoyo default repeat=-1", p_yoyo.repeat_count == -1)

# 12.8 restart — Restart from the beginning
p_rest = restart()
check("12.8a restart sets state to playing", p_rest.state == "playing")

# 12.9 hold — Stay at the final value
p_hold = hold()
check("12.9a hold sets fill to hold", p_hold.fill == HOLD)

# 12.10 freeze — Freeze at the current value
p_frz = freeze()
check("12.10a freeze sets fill to freeze", p_frz.fill == FREEZE)
check("12.10b freeze sets state to frozen", p_frz.state == "frozen")

# 12.11 PlaybackConfig string initialization
p_str = PlaybackConfig(mode="loop")
check("12.11a mode from string", p_str.mode == LOOP and p_str.repeat_count == -1)

# 12.12 Error on invalid playback mode
check_raises("12.12 bad playback mode", InvalidPlaybackError,
             lambda: PlaybackConfig(mode="invalid_mode"))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 13: Playback Integration in Move, Motion, and Timeline
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 13: Playback Integration in Move, Motion, and Timeline ═══")
reset()

# 13.1 motion.move with playback kwargs
mv_loop = motion.move(
    translate=[(100, 0), "ease_out", 1.0],
    loop=True,
)
check("13.1a mv_loop has loop mode", mv_loop.playback.mode == LOOP)
check("13.1b mv_loop repeat=-1", mv_loop.playback.repeat_count == -1)

# 13.2 motion.move with string playback="ping_pong"
mv_pp = motion.move(
    rotate=[90, "linear", 2.0],
    playback="ping_pong",
)
check("13.2a mv_pp ping_pong mode", mv_pp.playback.mode == PING_PONG)
check("13.2b mv_pp ping_pong is True", mv_pp.playback.is_ping_pong is True)

# 13.3 motion.move with repeat=4 and yoyo=True
mv_yy = motion.move(
    z=[3, "linear", 1.0],
    repeat=4,
    yoyo=True,
)
check("13.3a mv_yy repeat=4", mv_yy.playback.repeat_count == 4)
check("13.3b mv_yy yoyo is True", mv_yy.playback.is_yoyo is True)

# 13.4 Fluent playback chaining on MoveAnimation
mv_fluent = motion.move(translate=[(0, 100), "linear", 1.0]).alternate().loop()
check("13.4a fluent alternate", mv_fluent.playback.is_alternate is True)
check("13.4b fluent loop", mv_fluent.playback.mode == LOOP)

# 13.5 Draw.motion inherits playback from MoveAnimation
mot_inh = Draw.motion(name="inherited_play", move=mv_loop)
check("13.5a motion inherited loop mode", mot_inh.playback.mode == LOOP)
check("13.5b motion inherited repeat=-1", mot_inh.playback.repeat_count == -1)

# 13.6 Draw.motion explicit playback override
mot_over = Draw.motion(
    name="overridden_play",
    move=motion.move(rotate=[180, "ease_in_out", 2.0]),
    playback="reverse",
)
check("13.6a motion explicit reverse", mot_over.playback.is_reverse is True)
check("13.6b motion direction backward", mot_over.playback.direction == "backward")

# 13.7 Fluent playback methods on Motion instance
mot_fl = Draw.motion(name="fluent_motion", move=motion.move(opacity=[0.0, "linear", 1.0]))
mot_fl.ping_pong().hold()
check("13.7a motion ping_pong", mot_fl.playback.is_ping_pong is True)
check("13.7b motion hold fill", mot_fl.playback.fill == HOLD)
mot_fl.freeze()
check("13.7c motion freeze state", mot_fl.playback.state == "frozen")
mot_fl.restart()
check("13.7d motion restart state", mot_fl.playback.state == "playing")

# 13.8 Draw.timeline with playback options
tl_play = Draw.timeline(
    time=[1, 2],
    names=["a", "b"],
    playback="yoyo",
)
check("13.8a timeline yoyo", tl_play.playback.is_yoyo is True)
check("13.8b timeline ping_pong", tl_play.playback.is_ping_pong is True)

# 13.9 Fluent playback on Timeline
tl_play.repeat(10).play_reverse()
check("13.9a timeline repeat 10", tl_play.playback.repeat_count == 10)
check("13.9b timeline reverse", tl_play.playback.is_reverse is True)


# 13.10 Serialization of playback in to_dict() and to_resolved_dict()
mot_dict = mot_over.to_dict()
check("13.10a to_dict has playback", "playback" in mot_dict)
check("13.10b playback reverse in dict", mot_dict["playback"]["reverse"] is True)

mot_res_dict = mot_over.to_resolved_dict()
check("13.10c to_resolved_dict has playback", "playback" in mot_res_dict)
check("13.10d resolved playback direction", mot_res_dict["playback"]["direction"] == "backward")

tl_dict = tl_play.to_dict()
check("13.10e timeline dict has playback", "playback" in tl_dict)
check("13.10f timeline dict repeat=10", tl_dict["playback"]["repeat"] == 10)

# 13.11 Draw.motion namespace direct attribute access
check("13.11a Draw.motion.loop callable", callable(Draw.motion.loop))
check("13.11b Draw.motion.ping_pong callable", callable(Draw.motion.ping_pong))
check("13.11c Draw.motion.once callable", callable(Draw.motion.once))
check("13.11d Draw.motion.repeat callable", callable(Draw.motion.repeat))
check("13.11e Draw.motion.reverse callable", callable(Draw.motion.reverse))
check("13.11f Draw.motion.alternate callable", callable(Draw.motion.alternate))
check("13.11g Draw.motion.yoyo callable", callable(Draw.motion.yoyo))
check("13.11h Draw.motion.restart callable", callable(Draw.motion.restart))
check("13.11i Draw.motion.hold callable", callable(Draw.motion.hold))
check("13.11j Draw.motion.freeze callable", callable(Draw.motion.freeze))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 14: Mathematical Motion System (Shared Foundation & Priorities 1–10)
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 14: Mathematical Motion System ═══")
import math
from Draw.motion import (
    Vector2D,
    vec2,
    math as mm,
)

# 14.1 Vector Mathematics (Priority 1)
v1 = vec2(3.0, 4.0)
v2 = vec2(1.0, 2.0)
check("14.1a length of (3, 4) is 5", abs(v1.length() - 5.0) < 1e-6)
check("14.1b vector add", v1 + v2 == (4.0, 6.0))
check("14.1c vector sub", v1 - v2 == (2.0, 2.0))
check("14.1d vector scalar mul", v1 * 2.0 == (6.0, 8.0))
check("14.1e vector normalize", abs(v1.normalize().length() - 1.0) < 1e-6)
check("14.1f dot product", abs(v1.dot(v2) - 11.0) < 1e-6)
check("14.1g 2D cross product", abs(v1.cross(v2) - 2.0) < 1e-6)
check("14.1h distance to (0, 0)", abs(v1.distance_to((0, 0)) - 5.0) < 1e-6)
v_rot = v1.rotate(math.pi * 0.5)
check("14.1i rotate 90 deg", abs(v_rot.x - (-4.0)) < 1e-6 and abs(v_rot.y - 3.0) < 1e-6)
v_ref = vec2(1.0, -1.0).reflect((0.0, 1.0))
check("14.1j reflect vector", abs(v_ref.x - 1.0) < 1e-6 and abs(v_ref.y - 1.0) < 1e-6)

# 14.2 Time & Interpolation (Priority 2)
check("14.2a clamp", mm.clamp(1.5, 0.0, 1.0) == 1.0 and mm.clamp(-0.5, 0.0, 1.0) == 0.0)
check("14.2b lerp", abs(mm.lerp(10.0, 20.0, 0.5) - 15.0) < 1e-6)
check("14.2c inverse_lerp", abs(mm.inverse_lerp(10.0, 20.0, 15.0) - 0.5) < 1e-6)
check("14.2d remap", abs(mm.remap(5.0, 0.0, 10.0, 100.0, 200.0) - 150.0) < 1e-6)
check("14.2e smoothstep", abs(mm.smoothstep(0.0, 1.0, 0.5) - 0.5) < 1e-6)
check("14.2f mix vectors", mm.mix(vec2(0, 0), vec2(10, 20), 0.5) == (5.0, 10.0))

# 14.3 Trigonometric functions (Priority 3)
check("14.3a polar conversion", abs(mm.polar(10.0, 0.0)[0] - 10.0) < 1e-6)
r, theta = mm.to_polar(0.0, 5.0)
check("14.3b to_polar radius", abs(r - 5.0) < 1e-6 and abs(theta - math.pi * 0.5) < 1e-6)
p_rot = mm.rotate((10.0, 0.0), math.pi * 0.5)
check("14.3c rotate point", abs(p_rot[0]) < 1e-6 and abs(p_rot[1] - 10.0) < 1e-6)

# 14.4 Curves and paths (Priority 4)
bez_pt = mm.bezier_curve((0, 0), (50, 100), (100, 0), t=0.5)
check("14.4a quad bezier midpoint", abs(bez_pt[0] - 50.0) < 1e-6 and abs(bez_pt[1] - 50.0) < 1e-6)
arc_pt = mm.arc((0, 0), 100.0, 0.0, math.pi, t=0.5)
check("14.4b arc midpoint", abs(arc_pt[0]) < 1e-6 and abs(arc_pt[1] - 100.0) < 1e-6)
poly = [(0, 0), (100, 0), (100, 100)]
sample_pt = mm.path_sample(poly, 0.25)
check("14.4c path_sample", abs(sample_pt[0] - 50.0) < 1e-6 and abs(sample_pt[1]) < 1e-6)

# 14.5 Noise and Randomness (Priority 5)
n_val = mm.noise(1.5, 2.5, seed=123)
check("14.5a coherent noise in range", -1.0 <= n_val <= 1.0)
fbm_val = mm.fbm(1.2, 3.4, octaves=4, seed=456)
check("14.5b fbm noise in range", -1.0 <= fbm_val <= 1.0)
curl = mm.curl_noise(2.0, 3.0, seed=789)
check("14.5c curl noise returns Vector2D", isinstance(curl, Vector2D))

# 14.6 Wave and Oscillation (Priority 6)
check("14.6a sine wave at t=0", abs(mm.sine_wave(0.0)) < 1e-6)
check("14.6b triangle wave at t=0", abs(mm.triangle_wave(0.0) - 0.0) < 1e-6)
check("14.6c square wave at t=0.25", mm.square_wave(0.25) == 1.0)
check("14.6d damped oscillation decays", abs(mm.damped_oscillation(10.0, decay_rate=2.0)) < 1e-4)

# 14.7 Fields (Priority 7)
rad_f = mm.radial_field((0, 0), 10.0, 0.0, strength=5.0)
check("14.7a radial field outward", rad_f.x > 0 and abs(rad_f.y) < 1e-6)
att = mm.attractor((100, 0), 0.0, 0.0, strength=10.0)
check("14.7b attractor pulls right", att.x > 0)
rep = mm.repeller((100, 0), 0.0, 0.0, strength=10.0)
check("14.7c repeller pushes left", rep.x < 0)

# 14.8 Growth & Decay (Priority 8)
check("14.8a exp decay", mm.exponential_decay(100.0, 1.0, 0.0) == 100.0)
check("14.8b exp decay drops", mm.exponential_decay(100.0, 1.0, 2.0) < 20.0)
check("14.8c falloff quadratic", mm.falloff(50.0, 100.0, mode="quadratic") == 0.25)

# 14.9 Particle and Flow (Priority 9)
def sample_flow_field(x, y):
    return (10.0, 0.0)
adv_pos = mm.advect((0, 0), sample_flow_field, 0.5)
check("14.9a advect 10m/s for 0.5s", abs(adv_pos[0] - 5.0) < 1e-6)
vort = mm.vortex((10, 0), (0, 0), strength=10.0, radius=50.0)
check("14.9b vortex velocity perpendicular", abs(vort.x) < 1e-6 and vort.y > 0)
particles = mm.scatter((0, 0), 20, radius=50.0)
check("14.9c scatter creates 20 particles", len(particles) == 20)

# 14.10 Transformations (Priority 10)
tr_pt = mm.translate((10, 20), (5, -5))
check("14.10a translate", tr_pt == (15.0, 15.0))
sc_pt = mm.scale((10, 20), 2.0)
check("14.10b scale", sc_pt == (20.0, 40.0))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 15: Physical Motion System (Quantities, Methods & Presets)
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 15: Physical Motion System ═══")
from Draw.motion import (
    PhysicalBody,
    PhysicalTransform,
    projectile,
    free_fall,
    circular,
    uniform_circular,
    elliptical,
    oscillation,
    pendulum,
    spring,
    collision,
    rolling,
    sliding,
    bouncing,
)

# 15.1 Foundational quantities & integration
body = PhysicalBody(mass=10.0, position=(0.0, 0.0), velocity=(5.0, 0.0), gravity=(0.0, 0.0))
check("15.1a mass is 10", body.mass == 10.0)
check("15.1b momentum p=m*v is (50, 0)", body.calculate_momentum() == (50.0, 0.0))
check("15.1c kinetic energy 0.5*m*v^2 is 125", abs(body.calculate_energy() - 125.0) < 1e-6)

body.integrate(1.0)
check("15.1d position after 1s is (5, 0)", body.position == (5.0, 0.0))

# 15.2 Force and impulse application
body.apply_force((20.0, 0.0))
body.integrate(1.0) # a = F/m = 20/10 = 2 m/s^2; v = 5 + 2 = 7; pos = 5 + 7 = 12
check("15.2a velocity after force is (7, 0)", body.velocity == (7.0, 0.0))
check("15.2b position after force is (12, 0)", body.position == (12.0, 0.0))

body.apply_impulse((30.0, 0.0)) # delta_v = 30/10 = 3; v = 7 + 3 = 10
check("15.2c velocity after impulse is (10, 0)", body.velocity == (10.0, 0.0))

# 15.3 Rotational dynamics
body.apply_torque(10.0)
body.integrate_rotation(1.0)
check("15.3 angular velocity updated", body.angular_velocity > 0 and body.rotation > 0)

# 15.4 Collision detection and response
b1 = PhysicalBody(mass=2.0, position=(0.0, 0.0), velocity=(10.0, 0.0), radius=5.0, restitution=1.0)
b2 = PhysicalBody(mass=2.0, position=(8.0, 0.0), velocity=(0.0, 0.0), radius=5.0, restitution=1.0)
check("15.4a collision detected", b1.detect_collision(b2))
resolved = b1.resolve_collision(b2)
check("15.4b collision resolved", resolved)
check("15.4c momentum transferred (elastic)", b1.velocity.x < b2.velocity.x)

# 15.5 Physical presets
proj = projectile(position=(0, 0), velocity=(20, 15), gravity=(0, -9.8), mass=12.0)
check("15.5a projectile mass=12", proj.mass == 12.0)
check("15.5b projectile initial velocity", proj.velocity == (20.0, 15.0))
proj.integrate(1.0)
check("15.5c projectile moved horizontally to 20", abs(proj.position.x - 20.0) < 1e-6)

ff = free_fall(position=(0, 100), gravity=(0, -9.8))
ff.integrate(1.0)
check("15.5d free fall moves downward", ff.position.y < 100.0)

circ = uniform_circular(center=(0, 0), radius=50.0, speed=10.0)
check("15.5e circular body created", circ.radius == 50.0)

pend = pendulum(length=100.0, angle_deg=45.0)
check("15.5f pendulum rotation set", pend.rotation > 0)

b_roll = rolling(radius=20.0, linear_velocity=10.0)
check("15.5g rolling angular velocity matches v/r", abs(b_roll.angular_velocity - (-0.5)) < 1e-6)

b_bounce = bouncing(position=(0, 50), velocity=(0, -10), restitution=0.75)
check("15.5h bouncing restitution is 0.75", b_bounce.restitution == 0.75)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 16: motion.transform & Draw.motion Integration
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 16: motion.transform & Draw.motion Integration ═══")
reset()
from Draw.motion import MathematicalTransform, StandardTransform

# 16.1 Physical Motion prompt example:
# Draw.motion( name="projectile", motion = motion.transfrom (type = "physical",mass=12, position=(0, 0), velocity=(20, 15), acceleration=(0, -10),) )
m_proj = Draw.motion(
    name="projectile_sample",
    motion=Draw.motion.transform(
        type="physical",
        mass=12,
        position=(0, 0),
        velocity=(20, 15),
        acceleration=(0, -10),
    ),
)
check("16.1a projectile motion created", m_proj.transform_anim is not None)
check("16.1b transform is PhysicalTransform", isinstance(m_proj.transform_anim, PhysicalTransform))
check("16.1c body mass is 12", m_proj.transform_anim.body.mass == 12.0)
check("16.1d body velocity", m_proj.transform_anim.body.velocity == (20.0, 15.0))
check("16.1e to_dict contains physical transform", m_proj.to_dict()["transform"]["type"] == "physical")

# 16.2 Typo alias motion.transfrom works identically
m_typo = Draw.motion.transfrom(type="physical", mass=5)
check("16.2 motion.transfrom alias works", isinstance(m_typo, PhysicalTransform))

# 16.3 Mathematical Motion prompt example:
# Draw.motion( name="smoke", position=(100, 300), motion=motion.transform(direction= (0, -1), noise = 0.5, turbulence = 0.8, expansion= 1.2, decay = 0.3, )
m_smoke = Draw.motion(
    name="smoke_sample",
    position=(100, 300),
    motion=Draw.motion.transform(
        direction=(0, -1),
        noise=0.5,
        turbulence=0.8,
        expansion=1.2,
        decay=0.3,
    ),
)
check("16.3a smoke motion created", m_smoke.transform_anim is not None)
check("16.3b is MathematicalTransform", isinstance(m_smoke.transform_anim, MathematicalTransform))
check("16.3c direction is (0, -1)", m_smoke.transform_anim.direction == (0.0, -1.0))
check("16.3d noise amount", m_smoke.transform_anim.noise_amount == 0.5)
check("16.3e turbulence amount", m_smoke.transform_anim.turbulence_amount == 0.8)
check("16.3f position in to_dict", m_smoke.to_dict()["position"] == [100, 300])
check("16.3g transform type in to_dict", m_smoke.to_dict()["transform"]["type"] == "mathematical")

# 16.4 Standard transform (to={...})
m_card = Draw.motion(
    name="card_trans",
    transform=Draw.motion.transform(
        to={
            "translate": (300, 200),
            "rotate": 90,
            "z": 5,
        },
        duration=2.0,
        graph="ease_out",
    ),
)
check("16.4a standard transform created", m_card.transform_anim is not None)
check("16.4b to_dict properties", m_card.to_dict()["transform"]["to"]["translate"] == [300.0, 200.0])
check("16.4c to_dict z target is 5", m_card.to_dict()["transform"]["to"]["z"] == 5)
check("16.4d to_dict graph is ease_out", m_card.to_dict()["transform"]["graph"] == "ease_out")

# 16.5 Draw.motion.physical and Draw.motion.math namespaces
check("16.5a Draw.motion.physical has PhysicalBody", hasattr(Draw.motion.physical, "PhysicalBody"))
check("16.5b Draw.motion.physical has projectile", callable(Draw.motion.physical.projectile))
check("16.5c Draw.motion.math has lerp", callable(Draw.motion.math.lerp))
check("16.5d Draw.motion.math has curl_noise", callable(Draw.motion.math.curl_noise))
check("16.5e Draw.motion.math has fbm", callable(Draw.motion.math.fbm))


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 17: Registry CRUD, Directives, Effects & 3D Channels
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 17: Registry CRUD, Directives, Effects & 3D Channels ═══")
reset()

# 17.1 Registry CRUD: update, copy, all
m_orig = Draw.motion(name="ship", move=motion.move(translate=[(100, 100), "linear"]))
check("17.1a motion registered", Draw.motion.exists("ship"))
all_m = Draw.motion.all()
check("17.1b all motions has ship", "ship" in all_m)

# Update motion
Draw.motion.update("ship", position=(50, 50))
check("17.1c updated position", m_orig.position == (50, 50))

# Copy motion
m_clone = Draw.motion.copy("ship", "ship_copy")
check("17.1d copy created", Draw.motion.exists("ship_copy"))
check("17.1e copy has same position", m_clone.position == (50, 50))

# 17.2 Seek controls
m_orig.seek(2.5)
check("17.2a motion seek", m_orig.playback.time == 2.5)
Draw.motion.seek("ship_copy", 4.0)
check("17.2b api seek", m_clone.playback.time == 4.0)

# 17.3 Timeline update, all, seek, and bidirectional auto-attachment
tl_test = Draw.time_line(
    name="tl_auto",
    time_line=Draw.timeline(
        time=[1, 2],
        names=["part1", "part2"],
        motion=["auto_car"],
    )
)
check("17.3a timeline registered", Draw.time_line.exists("tl_auto"))
all_tl = Draw.time_line.all()
check("17.3b all timelines has tl_auto", "tl_auto" in all_tl)

# Register auto_car without time_line kwarg; should auto-attach because tl_auto declared it!
m_car = Draw.motion(name="auto_car", move=motion.move(translate=[(10, 0), "linear"]))
check("17.3c car auto-attached to timeline", m_car.timeline is not None and m_car.timeline_name == "tl_auto")

# 17.4 Dedicated visual effect presets
fx_fire = Draw.motion.fire(noise=0.8, decay=0.5)
check("17.4a fire effect is MathematicalTransform", isinstance(fx_fire, MathematicalTransform))
check("17.4b fire effect_name", fx_fire.effect_name == "fire")
check("17.4c fire noise", fx_fire.noise_amount == 0.8)

m_fx = Draw.motion(name="fx_sample", motion=motion.transform(effect="shockwave", amplitude=60.0))
check("17.4d transform with effect", m_fx.transform_anim.effect_name == "shockwave")
check("17.4e shockwave amplitude", m_fx.transform_anim.amplitude == 60.0)

# 17.5 Pseudo-3D channels
mv_3d = motion.move(
    rotate_x=[45.0, "ease_out", 1.0],
    rotate_y=[-30.0, "linear", 1.0],
    rotate_3d=[(10, 20, 30), "ease_in_out", 2.0],
    perspective=[800.0, "ease_out", 1.0],
)
check("17.5a move with 3D channels created", len(mv_3d.channels) == 4)
check("17.5b rotate_3d target", mv_3d.get_channel("rotate_3d").target == (10.0, 20.0, 30.0))
check("17.5c perspective target", mv_3d.get_channel("perspective").target == 800.0)

# 17.6 PhysicalTransform direct method delegation
pt_body = PhysicalTransform(mass=5.0, velocity=(10, 0), gravity=(0, 0))
pt_body.apply_force((50, 0))
pt_body.integrate(1.0)
check("17.6a delegated apply_force and integrate", pt_body.velocity == (20.0, 0.0))
check("17.6b delegated momentum", pt_body.calculate_momentum() == (100.0, 0.0))




# ═══════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("═" * 60)
if errors_log:
    print("\n  Failed tests:")
    for e in errors_log:
        print(f"    ✗ {e}")
else:
    print("\n  ✓ All tests passed!")
print()
