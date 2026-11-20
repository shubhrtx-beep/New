# Draw V3 Motion & Timeline API — Discussion Summary

**Status:** Design proposal based on the discussion  
**Purpose:** Preserve the decisions and open questions from the design conversation, so implementation can continue without losing context.

---

## 1. Design goals

The proposed Draw V3 motion system should:

- Keep the public Python API concise and easy to read.
- Separate **what changes** from **when it changes**.
- Support multiple animation channels on one shape.
- Allow named timeline sections to be reused by multiple motion objects.
- Let the Python layer validate and resolve timing references before sending serializable data to the C++/OpenGL motion engine.
- Keep physics separate from ordinary transform animation.

The syntax below is a design proposal, not an implemented or finalized API.

---

# Part A — Draw.motion

## 2. Basic motion API

The motion API starts with a named target:

```python
import Draw
from Draw import motion

Draw.motion(
    name="ball",
    move=motion.move(
        translate=[(300, 200), "ease_out", 2.0],
        rotate=[90, "ease_in_out", 1.5],
        opacity=[0.0, "linear", 1.0],
        size=[(200, 100), "ease_out", 2.0],
        skew=[(10, 0), "ease_in", 1.0],
        edges=[20, "ease_out", 1.0],
    )
)
```

### Channel format

The proposed channel format is:

```python
[property] = [target_value, easing, duration_or_time_reference]
```

Examples:

```python
translate=[(300, 200), "ease_out", 2.0]
rotate=[90, "ease_in_out", 1.5]
opacity=[0.0, "linear", 1.0]
```

- `target_value`: the value the property should reach.
- `easing`: the easing/graph name.
- `duration_or_time_reference`: either a numeric duration in seconds or, when using a timeline, a named timeline section.

The starting value is intended to be inferred from the shape's current state unless a future API adds an explicit `from` value.

### Proposed supported channels

| Channel | Purpose |
|---|---|
| `translate` | Position movement |
| `rotate` | Rotation |
| `scale` | Scale |
| `size` | Width/height |
| `opacity` | Transparency |
| `blur` | Blur |
| `color` | Color animation / integration with Draw Color |
| `glow` | Glow-related visual animation |
| `skew` | Skew |
| `edges` | Shape corner-rounding animation, where supported |

`edges` is shape-specific. It should only be accepted for shape types that support corner rounding.

## 3. `move` and `transform` relationship

The intended relationship is:

**`move` is a simpler subset/interface of `transform`.**

- `motion.move(...)` is the concise interface for common property animation.
- `motion.transform(...)` is the more comprehensive interface for spatial, visual, and geometry transformations.
- The two should share a consistent channel/timing model.

A simple transform example:

```python
Draw.motion(
    name="card",
    transform=motion.transform(
        to={
            "translate": (300, 200),
            "rotate": 90,
            "scale": (1.5, 1.5),
            "size": (200, 100),
            "skew": (10, 0),
            "opacity": 0.5,
            "edges": 20,
        },
        duration=2.0,
        graph="ease_out",
    )
)
```

Here, `duration` and `graph` act as defaults for the properties in `to`.

A property may optionally override those defaults:

```python
Draw.motion(
    name="card",
    transform=motion.transform(
        to={
            "translate": {
                "value": (300, 200),
                "duration": 2.0,
                "graph": "ease_out_back",
            },
            "rotate": {
                "value": 180,
                "origin": "center",
                "duration": 1.5,
            },
            "scale": (1.5, 1.5),
            "opacity": 0.5,
        },
        duration=2.0,
        graph="linear",
    )
)
```

The exact override representation remains a proposal and needs API review.

## 4. Geometry transformation / morphing

The design discussion included changing one shape geometry into another, for example rectangle to triangle.

Conceptual example:

```python
Draw.motion(
    name="shape",
    transform=motion.transform(
        to={
            "geometry": {
                "shape": "triangle",
                "resample": "distribute",
            }
        },
        duration=2.0,
        graph="ease_in_out",
    )
)
```

A custom-vertex alternative:

```python
to={
    "geometry": {
        "vertices": [(-50, -50), (50, -50), (0, 50)],
        "resample": "distribute",
    }
}
```

Because the source and destination may have different vertex counts, geometry morphing needs a vertex correspondence/resampling strategy. The earlier discussion mentioned `distribute`, `subdivide`, and `polar_map` as candidate strategies. Their exact V3 semantics still need specification.

## 5. Additional transform capabilities considered

These were identified as useful capabilities to consider in the comprehensive `transform` interface:

- Translation, rotation, scale, size, and skew.
- Rotation origin/pivot.
- Path following, including tangent orientation and orientation offset.
- Geometry morphing and dynamic vertices.
- Path trim, stroke dash, and dash offset.
- Pseudo-3D rotation (`rotate_x`, `rotate_y`, `rotate_3d`) and perspective, clearly distinguished from true 3D geometry.
- Keyframes, including Bezier handles.
- Opacity and blur.
- Color/glow integration with the Draw Color system.

These are design scope items, not a claim that all are implemented.

## 6. Keep physics and procedural motion separate

The discussion recommended keeping physics out of ordinary `transform` animation.

Potential separate physics capabilities:

- Spring
- Gravity / bounce
- Projectile
- Inertia
- Pendulum
- Attractor

Potential procedural effects:

- Wiggle
- Wave
- Pulse
- Orbit
- Lissajous
- Spiral
- Stretch / squash

A timeline may coordinate these systems, but physics should remain a distinct motion category with its own parameters and evaluation rules.

---

# Part B — Draw.timeline

## 7. Timeline's responsibility

The timeline is intended to control **when** animations run.

It should not itself define how a shape moves. The separation is:

- `Draw.motion(...)`: declares what properties change and their target values.
- `motion.move(...)` / `motion.transform(...)`: describes the animation operation.
- `Draw.timeline(...)`: defines time sections and their durations.
- `Draw.time_line(...)`: registers a named timeline so motion objects can refer to it.

The proposed Python layer should resolve named timing references into numeric start times/durations before serializing motion data for the C++ engine.

## 8. Two-step timeline design

The user requested a two-step, easy-to-use approach.

### Step 1 — Define and register a named timeline

```python
Draw.time_line(
    name="n1",
    time_line=Draw.timeline(
        time=[2, 4, 5, 7],
        names=["intro", "move", "rotate", "ending"],
    )
)
```

The example uses four sequential section durations:

| Section name | Duration |
|---|---:|
| `intro` | 2 seconds |
| `move` | 4 seconds |
| `rotate` | 5 seconds |
| `ending` | 7 seconds |

Total timeline duration: **18 seconds**.

The `time` list represents section durations, not absolute timestamps. The cumulative section boundaries would therefore be:

| Section | Start | End |
|---|---:|---:|
| `intro` | 0 | 2 |
| `move` | 2 | 6 |
| `rotate` | 6 | 11 |
| `ending` | 11 | 18 |

### Step 2 — Attach the timeline to a motion and reference sections

```python
Draw.motion(
    name="ball",
    time_line="n1",
    move=motion.move(
        translate=[(300, 200), "ease_out", "intro"],
        rotate=[90, "ease_in_out", "intro"],
        opacity=[0.0, "linear", "move"],
        size=[(200, 100), "ease_out", "move"],
        skew=[(10, 0), "ease_in", 1.0],

        # Shape-specific animation
        edges=[20, "ease_out", "ending"],
    )
)
```

Intended interpretation:

- `"intro"` refers to the `intro` section's timing.
- `"move"` refers to the `move` section's timing.
- `"ending"` refers to the `ending` section's timing.
- A numeric value such as `1.0` is an explicit duration in seconds, independent of a named section.
- Multiple channels referring to the same section share that section's timing.

**Important unresolved detail:** The examples establish a section duration but do not yet fully define whether every channel starts at the section's beginning, how it behaves if its own duration is shorter than the section, or whether it fills the whole section. This must be decided before implementation.

## 9. Multiple motions sharing one timeline

The second timeline example adds a `motion` list to the timeline definition. It declares which named motion objects belong to the timeline.

```python
Draw.time_line(
    name="n1",
    time_line=Draw.timeline(
        time=[2, 4, 5, 7],
        names=["intro", "move", "rotate", "ending"],
        motion=["ball", "n4"],
    )
)

Draw.motion(
    name="ball",
    time_line="n1",
    move=motion.move(
        translate=[(300, 200), "ease_out"],
        opacity=[0.0, "linear"],
    )
)

Draw.motion(
    name="n4",
    time_line="n1",
    move=motion.move(
        rotate=[90, "ease_in_out"],
    )
)
```

Intended interpretation:

- The timeline `"n1"` is shared by `"ball"` and `"n4"`.
- Each motion object can contain multiple animation channels.
- In this form, channels omit the third timing item and inherit timing from the timeline.

**Important unresolved detail:** The exact automatic assignment rule for channels without an explicit section is not finalized. Options include assigning them to the first section, assigning them by order, or requiring a default section. Do not silently implement one of these without deciding it.

## 10. Timeline channel timing formats

The discussion proposed three useful forms:

| Third item | Meaning |
|---|---|
| `"intro"` | Use a named timeline section |
| `1.0` | Use an explicit duration of one second |
| Omitted | Inherit timing from the attached timeline / its default assignment rule |

Recommended channel shape:

```python
[target_value, easing, time_reference]
```

Examples:

```python
translate=[(300, 200), "ease_out", "intro"]
rotate=[90, "ease_in_out", "intro"]
opacity=[0.0, "linear", 1.0]
```

For channels that inherit from the timeline:

```python
translate=[(300, 200), "ease_out"]
rotate=[90, "ease_in_out"]
```

A key naming distinction:

- A **duration** is an amount of time, such as `2.0` seconds.
- A **section name** identifies a named interval, such as `"intro"`.
- A **keyframe name** would identify a specific point in time. This is different from a section/duration name.

The user earlier suggested named durations such as `duration="rec_move"`. The later section-based timeline syntax provides a more concrete way to name intervals. Whether to support a separate named-duration registry in addition to timeline sections remains open.

---

# Part C — Design decisions and open questions

## 11. Current design direction

| Area | Current direction |
|---|---|
| Motion entry point | `Draw.motion(name=..., ...)` |
| Simple animation | `motion.move(...)` |
| Advanced animation | `motion.transform(...)` |
| Relationship | `move` is a simpler subset/interface of `transform` |
| Channel format | `[target_value, easing, duration_or_section]` |
| Timeline definition | `Draw.timeline(time=[...], names=[...])` |
| Timeline registration | `Draw.time_line(name=..., time_line=...)` |
| Timeline attachment | `Draw.motion(..., time_line="n1", ...)` |
| Shared timeline | Multiple named motions may use the same timeline |
| Timing unit | Seconds in the examples |
| Physics | Separate from ordinary transform animation |
| Backend | Python validates/resolves; C++/OpenGL evaluates motion |

## 12. Decisions still required before implementation

1. **Section playback:** Does a channel start at the beginning of its named section and use the full section duration by default?
2. **Explicit duration inside a section:** If a channel says `1.0` while attached to a timeline, does it start at the current/default section, or does it run independently from timeline time zero?
3. **No section supplied:** For shared-timeline motions, what should channels without a third item inherit?
4. **Motion list:** Is `motion=["ball", "n4"]` only a membership list, or should the timeline also define which section each motion belongs to?
5. **Concurrent channels:** Channels with the same section name should be allowed to run simultaneously; confirm this as the intended behavior.
6. **Timeline playback:** Decide where play/pause/restart/seek controls live. They were discussed, but are not yet part of the user's final syntax.
7. **Named durations:** Decide whether named durations are simply timeline sections or a separate reusable duration registry.
8. **2D/3D terminology:** The user's “2D” example means one motion using a timeline; the “3D” example means multiple motion objects sharing a timeline. It does not necessarily mean 3D spatial geometry.

## 13. Recommended next step

Finalize the timing semantics before writing implementation code. In particular, define precisely how a section reference maps to a channel's start time and duration, and how channels without a section are scheduled.

Once these rules are fixed, the Python API can validate the timeline and produce a deterministic, JSON-compatible representation for the C++ motion engine.
