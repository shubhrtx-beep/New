"""Test Suite for Draw3 Universal Maths & Unit Conversion System.

Verifies:
1. Core scalar resolution (px, pt, in, cm, mm, %, vw, vh, raw numbers).
2. Canvas scope & DPI configuration.
3. 2D tuple resolution (resolve_size, resolve_position, resolve_origin).
4. Ratio resolution with mixed units (floats, %, px, cm) in window frames.
5. Window integration: window regions driving shape parent scopes.
6. Declarative sub_edit nesting with parent-relative units.
7. Color gradient stop offset resolution.
8. Motion channel unit resolution.
"""

import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import Draw
from Draw import maths
from Draw.maths.errors import (
    DrawMathsError,
    InvalidUnitError,
    InvalidUnitValueError,
    MissingReferenceError,
    InvalidRatioError,
)


def test_core_scalar_resolution():
    print("Testing core scalar resolution...")
    maths.set_canvas_size(1920.0, 1080.0)
    maths.set_dpi(96.0)

    # Bare numbers
    assert maths.resolve(100) == 100.0
    assert maths.resolve(42.5) == 42.5

    # Pixels
    assert maths.resolve("100px") == 100.0
    assert maths.resolve("  42.5px  ") == 42.5

    # Percentage
    assert maths.resolve("50%", reference=400.0) == 200.0
    assert maths.resolve("100%", reference=850.0) == 850.0
    assert maths.resolve("0%", reference=500.0) == 0.0

    # Missing reference for % raises error
    try:
        maths.resolve("50%")
        assert False, "Should raise MissingReferenceError"
    except MissingReferenceError:
        pass

    # Viewport units (vw of 1920, vh of 1080)
    assert maths.resolve("50vw") == 960.0
    assert maths.resolve("100vw") == 1920.0
    assert maths.resolve("50vh") == 540.0
    assert maths.resolve("100vh") == 1080.0

    # Physical units at DPI = 96
    # 1 in = 96 px
    assert math.isclose(maths.resolve("1in"), 96.0, rel_tol=1e-5)
    # 2.54 cm = 1 in = 96 px
    assert math.isclose(maths.resolve("2.54cm"), 96.0, rel_tol=1e-3)
    # 25.4 mm = 1 in = 96 px
    assert math.isclose(maths.resolve("25.4mm"), 96.0, rel_tol=1e-3)
    # 72 pt = 1 in = 96 px
    assert math.isclose(maths.resolve("72pt"), 96.0, rel_tol=1e-5)

    # Custom DPI
    maths.set_dpi(192.0)
    assert maths.get_dpi() == 192.0
    assert math.isclose(maths.resolve("1in"), 192.0, rel_tol=1e-5)
    maths.set_dpi(96.0)  # Reset

    # Invalid unit raises error
    try:
        maths.resolve("100foobar")
        assert False, "Should raise InvalidUnitError"
    except InvalidUnitError:
        pass

    # NaN / Inf raises error
    try:
        maths.resolve(float("nan"))
        assert False, "Should raise InvalidUnitValueError"
    except InvalidUnitValueError:
        pass

    print("  [PASS] Core scalar resolution passed.")


def test_2d_tuple_resolution():
    print("Testing 2D tuple resolution (size, position, origin)...")
    maths.set_canvas_size(1920.0, 1080.0)

    # Size with mixed units
    size = maths.resolve_size(("50%", "100px"), ref_width=800.0, ref_height=600.0)
    assert size == (400.0, 100.0)

    # Position with mixed units
    pos = maths.resolve_position(("10%", "20px"), ref_width=1000.0, ref_height=500.0)
    assert pos == (100.0, 20.0)

    # Origin anchors
    assert maths.resolve_origin("center", 200.0, 100.0) == (0.0, 0.0)
    assert maths.resolve_origin("top", 200.0, 100.0) == (0.0, 50.0)
    assert maths.resolve_origin("bottom", 200.0, 100.0) == (0.0, -50.0)
    assert maths.resolve_origin("left", 200.0, 100.0) == (-100.0, 0.0)
    assert maths.resolve_origin("right", 200.0, 100.0) == (100.0, 0.0)
    assert maths.resolve_origin("top-left", 200.0, 100.0) == (-100.0, 50.0)
    assert maths.resolve_origin("bottom-right", 200.0, 100.0) == (100.0, -50.0)

    print("  [PASS] 2D tuple resolution passed.")


def test_ratio_resolution():
    print("Testing ratio resolution with mixed units...")

    # Case 1: Pure fractional ratios
    r1 = maths.resolve_ratio({"top_bar": 0.05, "main_display": 0.95}, total_dimension=850.0)
    assert math.isclose(r1["top_bar"], 42.5, rel_tol=1e-5)
    assert math.isclose(r1["main_display"], 807.5, rel_tol=1e-5)
    assert math.isclose(sum(r1.values()), 850.0, rel_tol=1e-5)

    # Case 2: Percentage strings
    r2 = maths.resolve_ratio({"top_bar": "5%", "main_display": "95%"}, total_dimension=850.0)
    assert math.isclose(r2["top_bar"], 42.5, rel_tol=1e-5)
    assert math.isclose(r2["main_display"], 807.5, rel_tol=1e-5)

    # Case 3: Fixed pixels mixed with ratio
    r3 = maths.resolve_ratio({"top_bar": "42.5px", "main_display": 0.95}, total_dimension=850.0)
    assert math.isclose(r3["top_bar"], 42.5, rel_tol=1e-5)
    assert math.isclose(r3["main_display"], 807.5, rel_tol=1e-5)

    # Case 4: Physical units in ratio (e.g. 2cm at DPI=96 is ~75.59px)
    r4 = maths.resolve_ratio({"top_bar": "2cm", "main_display": 0.95}, total_dimension=850.0)
    assert math.isclose(r4["top_bar"], 96.0 / 2.54 * 2.0, rel_tol=1e-4)
    assert math.isclose(sum(r4.values()), 850.0, rel_tol=1e-5)

    # Case 5: Invalid ratio sum raises error
    try:
        maths.resolve_ratio({"a": 0.2, "b": 0.5}, total_dimension=100.0)
        assert False, "Should raise InvalidRatioError"
    except InvalidRatioError:
        pass

    print("  [PASS] Ratio resolution passed.")


def test_window_integration_and_region_parent_scope():
    print("Testing Window integration & region-driven shape calculation...")
    from Draw.windows import GLOBAL_WINDOW_REGISTRY

    # Clean window registry
    for name in list(GLOBAL_WINDOW_REGISTRY._windows.keys()):
        GLOBAL_WINDOW_REGISTRY.remove(name)

    # Create window with ratio as requested by user:
    # window.create(name="main", frame=window.custom(size=(1400, 850), ratio={"top_bar": 0.05, "main_display": 0.95}))
    win = Draw.window.create(
        name="main",
        frame=Draw.window.custom(
            size=(1400, 850),
            ratio={"top_bar": 0.05, "main_display": 0.95},
        ),
    )

    top_bar = win.region("top_bar")
    main_disp = win.region("main_display")

    assert top_bar is not None
    assert main_disp is not None
    assert math.isclose(top_bar.height, 42.5, rel_tol=1e-5)
    assert math.isclose(main_disp.height, 807.5, rel_tol=1e-5)
    assert top_bar.width == 1400.0
    assert main_disp.width == 1400.0

    # User's key case:
    # "main display is 0.95 then all calculation depends on it"
    # A shape nested in "main_display" resolves relative units against (1400, 807.5)!
    s = Draw.shape(
        name="viewport_canvas",
        type="rectangle",
        parent="main_display",
        size=("100%", "50%"),
    )
    assert s.resolved_size[0] == 1400.0
    assert math.isclose(s.resolved_size[1], 403.75, rel_tol=1e-5)

    # Window with physical size
    win_phys = Draw.window.create(
        name="phys_win",
        frame=Draw.window.custom(
            size=("20cm", "15cm"),
            ratio={"header": "40px", "body": 1.0},
        ),
    )
    expected_w = int(round(maths.resolve("20cm")))
    expected_h = int(round(maths.resolve("15cm")))
    assert win_phys.size == (expected_w, expected_h)
    assert win_phys.region("header").height == 40.0
    assert win_phys.region("body").height == expected_h - 40.0

    print("  [PASS] Window integration and region-driven shape calculation passed.")


def test_shape_sub_edit_declarative_nesting():
    print("Testing Mode A declarative sub_edit nesting...")
    Draw.GLOBAL_REGISTRY.clear()

    # User's exact Mode A case:
    # card = Draw.shape(
    #     name="card",
    #     type="rectangle",
    #     size=(400.0, 200.0),
    #     closed=True,
    #     z=0,
    #     sub_edit=Draw.sub_edit(
    #         shapes=[
    #             Draw.shape(
    #                 name="card_header",
    #                 type="rectangle",
    #                 size=("100%", "40px"),
    #             )
    #         ]
    #     )
    # )
    card = Draw.shape(
        name="card",
        type="rectangle",
        size=(400.0, 200.0),
        closed=True,
        z=0,
        sub_edit=Draw.sub_edit(
            shapes=[
                Draw.shape(
                    name="card_header",
                    type="rectangle",
                    size=("100%", "40px"),
                )
            ]
        ),
    )
    header = Draw.GLOBAL_REGISTRY.get("card_header")
    assert header is not None
    # 100% of parent width (400px) = 400.0, 40px height = 40.0
    assert header.resolved_size == (400.0, 40.0)
    assert header.parent == "card"

    print("  [PASS] Mode A declarative sub_edit nesting passed.")


def test_color_gradient_stop_resolution():
    print("Testing color gradient stop offset resolution...")
    assert maths.resolve_stop_offset(0.0) == 0.0
    assert maths.resolve_stop_offset(0.5) == 0.5
    assert maths.resolve_stop_offset("50%") == 0.5
    assert maths.resolve_stop_offset("100%") == 1.0

    # Gradient construction with string offsets
    grad = Draw.color.gradient(
        type="linear",
        stops=[(0.0, "#000000"), ("50%", "#777777"), (1.0, "#ffffff")],
    )
    assert grad.stops[1][0] == 0.5

    print("  [PASS] Color gradient stop offset resolution passed.")


def test_motion_channel_unit_resolution():
    print("Testing motion channel unit resolution...")
    from Draw.motion.channels import validate_channel_value

    assert validate_channel_value("translate", ("100px", "50px")) == (100.0, 50.0)
    assert validate_channel_value("size", ("200px", "100px")) == (200.0, 100.0)
    assert validate_channel_value("edges", "25px") == 25.0

    print("  [PASS] Motion channel unit resolution passed.")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING ALL DRAW3 MATHS & UNIVERSAL UNIT TESTS")
    print("=" * 60)
    test_core_scalar_resolution()
    test_2d_tuple_resolution()
    test_ratio_resolution()
    test_window_integration_and_region_parent_scope()
    test_shape_sub_edit_declarative_nesting()
    test_color_gradient_stop_resolution()
    test_motion_channel_unit_resolution()
    print("=" * 60)
    print("ALL MATHS & UNIT TESTS PASSED SUCCESSFULLY! (100% GREEN)")
    print("=" * 60)
