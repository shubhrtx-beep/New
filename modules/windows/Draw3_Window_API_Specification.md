# Draw3 Window API Specification (SDL2)

**Status:** Design agreed; not yet implemented\
**Backend:** SDL2 (PySDL2)\
**Scope:** Window creation, lifecycle, events, layout regions, and
hit-testing. Drawing remains in the Draw renderer.

------------------------------------------------------------------------

## 1. Imports

``` python
from Draw import shapes, color, motion, window
```

`window` is a module, like `shapes`, `color`, and `motion`. It contains
the frame factories, element registry, window registry, and
window-management functions.

------------------------------------------------------------------------

## 2. Core model

  -----------------------------------------------------------------------
  Concept                             Meaning
  ----------------------------------- -----------------------------------
  **Window**                          One SDL2 window, created with
                                      `window.create(...)`.

  **Frame**                           A description of how the window is
                                      configured. Created by
                                      `window.display(...)`,
                                      `window.custom(...)`, or
                                      `window.titlebar(...)`.

  **ratio**                           Splits the window's own area into
                                      named regions, such as `top_bar`
                                      and `main_display`.

  **region**                          A named area created by `ratio`, or
                                      an element used as a container.
                                      Shapes use `region="..."` to
                                      specify where they sit.

  **element**                         A named drawable item declared with
                                      `window.element("name")`.

  **elements list**                   Belongs to a frame and determines
                                      which elements are included in that
                                      window.
  -----------------------------------------------------------------------

### Core rules

1.  `ratio` decides **area**. `elements` decides **membership**. They
    are independent.
2.  An element is declared once and is not tied to a window when
    declared.
3.  A window claims an element by listing it in `elements`.
4.  An element does not have to belong to every window. In a two-window
    application, an element can belong to only one window.
5.  An element can also act as a region (container). Other shapes can
    use `region="<element name>"` to sit inside it.
6.  A shared element definition can appear in multiple windows, but each
    window has its own placement, hit-testing context, and action
    target.

------------------------------------------------------------------------

## 3. Creating windows

### 3.1 Normal window (native OS title bar)

``` python
window.create(
    name="main",
    frame=window.display(
        title="Nebula",
        size=(1400, 850),
        min_size=(800, 500),
        max_size=(1920, 1080),
        resizable=True,
        visible=True,
        icon="logo.png",
    ),
)
```

`window.display(...)` creates a normal SDL2 window with the operating
system's native title bar and window controls.

### 3.2 Custom window (borderless)

``` python
window.create(
    name="main",
    frame=window.custom(
        size=(1400, 850),
        ratio={"top_bar": 0.05, "main_display": 0.95},
        elements=["min", "max", "close", "card"],
        drag_region="top_bar",
        resize_border=6,
    ),
)
```

A custom window uses `SDL_WINDOW_BORDERLESS`.

#### Native title bar removal

When `window.custom(...)` is used:

-   The native operating-system title bar is completely removed.
-   Native minimize, maximize, and close buttons are removed.
-   The native window border is removed.
-   The top of the client area is simply blank until the developer draws
    something there.
-   Draw does not automatically create a replacement title bar.

The developer creates any title bar, menus, search bar, and window
controls using Draw shapes and elements.

`drag_region` and `resize_border` provide the corresponding window
interactions. A blank area is not automatically draggable unless it is
included in `drag_region`.

### 3.3 `window.custom(...)` arguments

  -----------------------------------------------------------------------
  Argument                Type                    Notes
  ----------------------- ----------------------- -----------------------
  `size`                  `(w, h)`                Starting size.

  `ratio`                 `dict[str, float]`      Region name to share of
                                                  the window area. Values
                                                  may be `0` (collapsed)
                                                  through `1`. Must sum
                                                  to `1`, within a small
                                                  floating-point
                                                  tolerance.

  `elements`              `list[str]`             Element names that
                                                  belong to this window.

  `drag_region`           `str`, list, or `None`  Region or element that
                                                  moves the window when
                                                  dragged. `None` means
                                                  not draggable.

  `resize_border`         `int`                   Width of the invisible
                                                  resize edge in pixels.
                                                  `0` disables edge
                                                  resizing.

  `min_size`              `(w, h)`                Optional minimum
                                                  dimensions.

  `max_size`              `(w, h)`                Optional maximum
                                                  dimensions.

  `visible`               `bool`                  Initial visibility;
                                                  defaults to `True`.
  -----------------------------------------------------------------------

### 3.4 Ratio rules

-   Keys are region names. Values are fractions of the relevant window
    axis.
-   `0` is valid: the region exists but is collapsed and hidden. It can
    be shown later, for example `w.region("top_bar").ratio = 0.05`, and
    animated with `motion`.
-   Values must be between `0` and `1`, inclusive.
-   All ratio values must sum to `1`, within a small floating-point
    tolerance.
-   Invalid ratios raise `InvalidRegionRatioError`.
-   Ratios must never be silently normalized.
-   Region dimensions must be recalculated when the window is resized.
-   All size, position, and ratio values go through the future
    `units.resolve(value, axis_length_px)` hook.

#### 3.4.1 Ratio validation errors

Valid example:

``` python
ratio={
    "top_bar": 0.05,
    "main_display": 0.95,
}
```

Invalid example: values do not sum to `1`.

``` python
ratio={
    "top_bar": 0.05,
    "main_display": 0.80,
}
```

Expected error message:

``` text
InvalidRegionRatioError:
Region ratios must sum to 1.0.

Received:
    top_bar      = 0.05
    main_display = 0.80

Total = 0.85
Expected = 1.0

Difference = 0.15
```

Invalid example: a value is outside the allowed range.

``` python
ratio={
    "top_bar": -0.05,
    "main_display": 1.05,
}
```

Expected error message:

``` text
InvalidRegionRatioError:
Invalid ratio for region 'top_bar'.

Received: -0.05
Allowed range: 0.0 to 1.0
```

The exception should include the offending region, received value,
allowed range, and/or actual total and expected total as applicable.

------------------------------------------------------------------------

## 4. Elements

``` python
window.element("min")  # returns the element name "min"
```

-   Declares an element name and returns it as a tagged string
    (`ElementName`).
-   It does not need a window. It does not know which window will claim
    it.
-   Calling it again with the same name returns the same tag; it does
    not raise an error.

### 4.1 Shape usage

``` python
shapes.shape(
    name=window.element("min"),
    region="top_bar",
    type="rectangle",
    size=(46, 30),
)
```

Meaning: the shape is named `min` and is an element. It is placed in the
`top_bar` region. `top_bar` is part of the window's display area, so the
shape appears in the top bar of each window that lists `"min"` in
`elements`.

### 4.2 Must not raise an error at shape creation

All of these are valid and silent when the shape is declared:

-   `window.element("min")` is used in a shape before any window exists.
-   `region="top_bar"` is used before any window defines `top_bar`.
-   `region="menu"` is used where `menu` is another element declared
    later.
-   An element has not yet been claimed by a window.

Region and element references are checked lazily, when a window is built
or first opened/rendered. Creation order must not matter.

Warnings, not errors:

-   An element is not claimed by any window when the application starts.
-   A window lists an element name that was never declared.
-   An element's region does not exist in a particular window; see
    section 4.3.

Unresolved references should be reported at a predictable lifecycle
point, preferably when the window is first opened, rather than
unpredictably during normal rendering.

### 4.3 One element in several windows

An element may be listed in several windows. It is drawn in each of
them.

-   The element definition may be shared.
-   Placement and layout are resolved independently for each window.
-   Hit-testing and interaction context are independent for each window.
-   An action such as `action="close"` applies to the window in which
    the element was clicked.
-   If its `region` does not exist in a particular window, it fills that
    window's whole area and logs a warning.

------------------------------------------------------------------------

## 5. Shape module changes

Required changes in the shape module:

1.  **Add `region=` to `shapes.shape(...)`.**
    -   Type: `str | None`, default `None` (whole window area).
    -   Accepts a region name from a window's `ratio`, or the name of
        another element (`region="menu"`).
    -   Positions are local to the region; `(0, 0)` is the region's
        top-left corner.
    -   It is not validated at shape creation time.
2.  **Accept `ElementName` in `name=`.**
    -   `name=window.element("min")` must work like a plain string name.
    -   Registering the shape under that name also registers it as an
        element.
3.  **Add `anchor=` and `margin=`** so placement can remain aligned
    during resizing.
    -   `anchor` supports values such as `"left"`, `"right"`,
        `"top_left"`, `"top_right"`, and `"center"`.
    -   `margin` is `(x, y)`.
4.  **Add `action=`.**
    -   Supported actions: `"close"`, `"minimize"`, `"maximize"`, and
        `"restore"`.
    -   Keep `callback=` for menus, search bars, and other custom
        interactions.
5.  **Drag exclusion.**
    -   Any shape with `action` or `callback` inside a drag region is
        excluded from dragging so it remains clickable.

### 5.1 Nested region coordinate calculation

For an element used as a region, child positions are local to that
immediate parent.

Conceptually:

``` text
absolute_position = parent_absolute_position + child_local_position
```

Nested regions should resolve from the outermost parent inward. Layout
must be recalculated when the window or a parent region changes size or
position.

------------------------------------------------------------------------

## 6. Using an element as a region (menus)

``` python
shapes.shape(
    name=window.element("menu"),
    region="top_bar",
    type="rectangle",
    size=("30%", "100%"),
    anchor="left",
)

shapes.shape(
    name=window.element("file_btn"),
    region="menu",
    type="rectangle",
    size=(50, 28),
)
```

`menu` and `file_btn` must both be in the window's `elements` list.

------------------------------------------------------------------------

## 7. Managing windows

``` python
w = window.get("main")  # returns the Window object

window.close("main")    # closes the OS window; definition stays
window.open("main")     # reopens a closed window
window.remove("main")   # closes it and deletes it from the registry
```

  -----------------------------------------------------------------------
  Function/property                   Behaviour
  ----------------------------------- -----------------------------------
  `window.create(name, frame)`        Builds and registers a window.
                                      Duplicate name raises
                                      `DuplicateWindowNameError`.

  `window.get(name)`                  Returns the `Window` object.
                                      Unknown name raises
                                      `WindowNotFoundError`.

  `window.close(name)`                Destroys the SDL window but keeps
                                      its definition.

  `window.open(name)`                 Recreates the SDL window from the
                                      stored definition.

  `window.remove(name)`               Closes the window and deletes it
                                      from the registry. The name becomes
                                      available again.

  `window.element(name)`              Declares an element name. See
                                      section 4.

  `window.focus(name)`                Recommended management function:
                                      gives the named window focus.

  `window.get_all()`                  Recommended management function:
                                      returns registered windows.
  -----------------------------------------------------------------------

Recommended `Window` properties:

``` python
w.is_open
w.is_visible
w.is_minimized
w.is_maximized
w.size
w.position
```

These properties should reflect the actual SDL window state.
Maximize/restore actions must update the state consistently.

------------------------------------------------------------------------

## 8. Example: VS Code-style window

``` python
from Draw import shapes, window

window.create(
    name="main",
    frame=window.custom(
        size=(1400, 850),
        ratio={"top_bar": 0.04, "main_display": 0.96},
        elements=["menu", "search", "controls", "min", "max", "close"],
        drag_region="top_bar",
        resize_border=6,
    ),
)

shapes.shape(
    name=window.element("menu"),
    region="top_bar",
    type="rectangle",
    size=("30%", "100%"),
    anchor="left",
)

shapes.shape(
    name=window.element("search"),
    region="top_bar",
    type="rectangle",
    size=("40%", 24),
    anchor="center",
)

shapes.shape(
    name=window.element("controls"),
    region="top_bar",
    type="rectangle",
    size=("30%", "100%"),
    anchor="right",
)

shapes.shape(
    name=window.element("min"),
    region="controls",
    type="rectangle",
    size=(46, 30),
    action="minimize",
)

shapes.shape(
    name=window.element("max"),
    region="controls",
    type="rectangle",
    size=(46, 30),
    action="maximize",
)

shapes.shape(
    name=window.element("close"),
    region="controls",
    type="rectangle",
    size=(46, 30),
    action="close",
)
```

------------------------------------------------------------------------

## 9. Example: image window with one close cross

``` python
window.create(
    name="viewer",
    frame=window.custom(
        size=(900, 600),
        ratio={"top_bar": 0, "body": 1},
        elements=["photo", "x"],
        drag_region="body",
    ),
)

shapes.shape(
    name=window.element("photo"),
    region="body",
    type="rectangle",
    size=("100%", "100%"),
)

shapes.shape(
    name=window.element("x"),
    region="body",
    type="cross",
    size=(24, 24),
    anchor="top_right",
    margin=(12, 12),
    action="close",
)
```

`drag_region="body"` is valid here because the body has no interactive
content other than the close cross. The close cross has an `action`, so
it is automatically excluded from dragging.

------------------------------------------------------------------------

## 10. `window.titlebar(...)` preset

`window.titlebar(...)` is a convenience frame factory built on top of
the existing custom-window system. It must not introduce a second layout
engine or a separate window backend.

It generates a normal custom frame, registers the generated elements,
assigns their regions/anchors/layout, and includes them in the frame's
element list.

### 10.1 Proposed syntax

``` python
window.create(
    name="main",
    frame=window.titlebar(
        size=(1400, 850),

        ratio={
            "title_bar": 0.05,
            "main_display": 0.95,
        },

        menus=["File", "Edit", "View"],
        search=True,

        controls=["minimize", "maximize", "close"],

        drag_region="title_bar",
        resize_border=6,
    ),
)
```

### 10.2 Arguments

  -----------------------------------------------------------------------
  Argument                Type                    Description
  ----------------------- ----------------------- -----------------------
  `size`                  `(w, h)`                Initial window
                                                  dimensions.

  `ratio`                 `dict[str, float]`      Region proportions.

  `menus`                 `list[str]`             Menu names to generate.

  `search`                `bool`                  Whether to generate a
                                                  search element.

  `controls`              `list[str]`             Window controls to
                                                  generate. Supported
                                                  values: `"minimize"`,
                                                  `"maximize"`,
                                                  `"close"`.

  `drag_region`           `str`, list, or `None`  Region or element used
                                                  for window dragging.

  `resize_border`         `int`                   Width of the invisible
                                                  resize edge in pixels.

  `min_size`              `(w, h)`                Optional minimum
                                                  dimensions.

  `max_size`              `(w, h)`                Optional maximum
                                                  dimensions.

  `visible`               `bool`                  Initial visibility;
                                                  defaults to `True`.
  -----------------------------------------------------------------------

### 10.3 Generated elements

For example:

``` python
menus=["File", "Edit", "View"]
search=True
controls=["minimize", "maximize", "close"]
```

The preset generates and registers elements with names equivalent to:

``` python
[
    "titlebar",
    "menu_file",
    "menu_edit",
    "menu_view",
    "search",
    "minimize",
    "maximize",
    "close",
]
```

Generated elements are included in the frame's element membership list.
The preset assigns their initial regions, anchors, and layout positions.

The exact visual styling remains controlled by the Draw renderer and can
be customized by the developer.

### 10.4 Accessing generated elements

The returned `Window` object should provide access to generated
elements:

``` python
w = window.get("main")

w.element("search")
w.element("menu_file")
w.element("close")
```

This lets developers customize generated shapes without rebuilding the
title bar.

### 10.5 Preset behaviour

-   `titlebar()` uses the custom borderless SDL2 window mode.
-   It replaces the removed native title bar with Draw-managed elements.
-   It uses the same region, element, anchor, margin, action, and
    hit-testing systems as manually created custom windows.
-   It must not create a second layout or interaction system.
-   Developers can still use `window.custom(...)` for complete manual
    control.

------------------------------------------------------------------------

## 11. Units hook (future `units` module)

A separate unit-conversion module is planned (pixels, ratios,
centimetres, similar to CSS).

Design hook to implement now:

-   Every size, position, and ratio value goes through
    `units.resolve(value, axis_length_px)`.
-   Initially, it accepts plain numbers and tuples, such as `0.05` and
    `(46, 30)`.
-   Later, it should accept values such as `"5%"`, `"40px"`, and
    `"1cm"`.
-   Centimetres require display DPI, obtained through SDL display
    information such as `SDL_GetDisplayDPI`.
-   Mixed-unit ratios (for example, `"top_bar": "40px"` with the rest
    filling the remaining space) require a remaining-space rule. Leave
    this for the future units module.

------------------------------------------------------------------------

## 12. SDL2 notes

-   Custom windows use `SDL_WINDOW_BORDERLESS`.
-   Dragging and edge-resizing use `SDL_SetWindowHitTest`.
-   One hit-test callback answers for each mouse position: draggable
    area, resize edge, or normal content.
-   The hit-test callback should determine OS-level drag/resize
    behaviour. Normal shape hit-testing and callbacks remain in Draw's
    interaction system.
-   Hit-test decisions are built from `drag_region`, `resize_border`,
    and interactive-shape exclusions.
-   SDL window events must be handled separately from shape drawing and
    normal renderer logic.
-   Window resize events trigger region/layout recalculation and redraw.
-   Rounded corners and transparency are limited in plain SDL2; leave
    them for later.

------------------------------------------------------------------------

## 13. Suggested file layout

``` text
Draw/window/
    __init__.py      # exports create, get, open, close, remove, element, display, custom, titlebar
    frame.py         # display(), custom(), titlebar() frame descriptions
    window.py        # Window object and SDL2 lifecycle
    region.py        # ratio split and region lookup
    element.py       # ElementName and element registry
    registry.py      # window registry
    hittest.py       # SDL_SetWindowHitTest callback
    events.py        # SDL resize, close, minimize, maximize, and focus events
    layout.py        # region sizing, nested coordinates, anchors, and margins
    errors.py        # DuplicateWindowNameError, WindowNotFoundError, InvalidRegionRatioError

test/
    test_window.py
    test_region.py
    test_element.py
    test_hittest.py
```

------------------------------------------------------------------------

## 14. Errors

  -----------------------------------------------------------------------
  Error                               When
  ----------------------------------- -----------------------------------
  `DuplicateWindowNameError`          `window.create(...)` uses a name
                                      already registered.

  `WindowNotFoundError`               `window.get/close/open/remove` uses
                                      an unknown name.

  `InvalidRegionRatioError`           Ratio values are outside `0..1` or
                                      do not sum to `1` within tolerance.
  -----------------------------------------------------------------------

The cases in section 4.2 are not errors at shape-creation time.
Unresolved references are reported as warnings at the defined validation
lifecycle point.

------------------------------------------------------------------------

## 15. Open decisions and recommendations

  -----------------------------------------------------------------------
  Decision                            Recommendation
  ----------------------------------- -----------------------------------
  Can an element belong to several    **Yes.** Share the definition, but
  windows?                            keep placement and interaction
                                      state window-specific.

  Should `elements=` accept a dict?   **No for V1.** Keep it as a list of
                                      names.

  Add `window.titlebar(...)`?         **Yes.** Implement it as a
                                      convenience preset over
                                      `window.custom(...)`.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 16. Recommended implementation order

1.  Window creation and SDL2 lifecycle.
2.  Frame descriptions: `display()` and `custom()`.
3.  Ratio validation and region calculations.
4.  Element registry and `ElementName`.
5.  Shape integration (`region`, `anchor`, `margin`, `action`).
6.  Nested regions and coordinate resolution.
7.  SDL window events and resize-driven layout updates.
8.  Hit-testing, dragging, resizing, and window actions.
9.  `titlebar()` preset.
10. Multi-window tests and lifecycle tests.

**Implementation principle:** Keep the window system responsible for
SDL2 window management and layout context. Keep the Draw renderer
responsible for drawing shapes. The title-bar preset should compose
existing capabilities rather than duplicate them.
