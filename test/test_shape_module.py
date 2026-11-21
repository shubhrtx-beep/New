"""Comprehensive Test Suite for Draw3 Shape Subsystem (Working Data).
make a md file using this formet as shape.md 
remove compleately mouse_x section or in simple do not intrigate hardware hear 

Verifies primitives, units, 0-based indexing, topology invariants,
Ear-Clipping triangulation, cutout holes, side/whole modifiers,
registry management, context managers, and error handling.
"""

import sys
import os

# Add root directory to sys.path so 'import Draw' works directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import Draw
from Draw import shapes, line


def test_core_primitives():
    print("Testing core primitive shapes...")
    Draw.GLOBAL_REGISTRY.clear()

    # 1. Rectangle
    rect = Draw.shape(
        name="card",
        type="rectangle",
        size=(100.0, 50.0),
        position=(10.0, 20.0),
        closed=True,
        z=1,
    )
    assert rect.name == "card"
    assert rect.shape_id >= 101
    assert rect.closed is True
    assert rect.z == 1
    assert len(rect.vertices) == 4
    # 0-based rule: Vertex 0 is Top-Left (-50, 25), Vertex 1 is Top-Right (50, 25)
    assert rect.vertices[0] == (-50.0, 25.0)
    assert rect.vertices[1] == (50.0, 25.0)
    assert rect.vertices[2] == (50.0, -25.0)
    assert rect.vertices[3] == (-50.0, -25.0)
    # Indices triangulation: 2 triangles (6 indices)
    assert len(rect.indices) == 6

    # 2. Triangle
    tri = Draw.shape(
        name="tri",
        type="triangle",
        size=(60.0, 40.0),
    )
    assert len(tri.vertices) == 3
    assert tri.vertices[0] == (0.0, 20.0)  # Top center

    # 3. Regular Polygon (vertices=6)
    hex_poly = Draw.shape(
        name="hexagon",
        vertices=6,
        size=(100.0, 100.0),
    )
    assert len(hex_poly.vertices) == 6
    assert hex_poly.vertices[0] == (0.0, 50.0)  # Top center
    assert len(hex_poly.indices) == 12  # (6 - 2) * 3 = 12 indices

    print("  [PASS] Core primitives passed.")


def test_unit_resolution():
    print("Testing universal unit resolution ('px', '%', 'cm', canvas vs parent scope)...")
    Draw.GLOBAL_REGISTRY.clear()
    Draw.set_canvas_size(1920.0, 1080.0)

    # Percentage against canvas
    root = Draw.shape(
        name="root_banner",
        type="rectangle",
        size=("50%", "100px"),
        position=("10%", 50.0),
    )
    # 50% of 1920 = 960.0, 100px = 100.0
    assert root.resolved_size == (960.0, 100.0)
    # 10% of 1920 = 192.0
    assert root.resolved_position == (192.0, 50.0)

    # Sub_edit child nesting with relative units
    card = Draw.shape(
        name="parent_card",
        type="rectangle",
        size=(400.0, 200.0),
        sub_edit=Draw.sub_edit(
            shapes=[
                Draw.shape(
                    name="header",
                    type="rectangle",
                    size=("100%", "40px"),
                    origin="center",
                )
            ],
            clip=True,
        ),
    )
    header = Draw.GLOBAL_REGISTRY.get("header")
    # 100% of parent width (400) = 400.0, 40px = 40.0
    assert header.resolved_size == (400.0, 40.0)
    assert header.parent == "parent_card"
    assert header.clip is True

    # Physical units (cm at DPI=96: 2.54cm = 1.0in = 96px)
    Draw.set_dpi(96.0)
    phys = Draw.shape(
        name="phys_box",
        type="rectangle",
        size=("2.54cm", "1in"),
    )
    assert round(phys.resolved_size[0], 1) == 96.0
    assert round(phys.resolved_size[1], 1) == 96.0

    print("  [PASS] Universal unit resolution passed.")


def test_modifiers_and_topology():
    print("Testing modifiers (bend, warp, edges, remove, exclude holes)...")
    Draw.GLOBAL_REGISTRY.clear()

    # 1. Bend test
    bent = Draw.shape(
        name="bent_box",
        type="rectangle",
        size=(100.0, 100.0),
        side_edit=Draw.side_edit(
            bend=[
                {"side": 0, "offset": 20.0, "direction": "out"}
            ]
        ),
    )
    # Edge 0 has extra curved vertices
    assert len(bent.vertices) > 4

    # 2. Corner rounding (edges)
    rounded = Draw.shape(
        name="pill",
        type="rectangle",
        size=(100.0, 50.0),
        edit=Draw.edit(
            edges="100%",  # fully rounded pill
        ),
    )
    assert len(rounded.vertices) > 4
    # Max corner radius on 100x50 is 25.0
    assert rounded.bounds["width"] <= 100.0
    assert rounded.bounds["height"] <= 50.0

    # 3. Edge remove degrades closed to open
    sliced = Draw.shape(
        name="sliced",
        type="rectangle",
        size=(100.0, 100.0),
        closed=True,
        edit=Draw.edit(
            remove=[0],
        ),
    )
    assert sliced.closed is False  # Degraded to open path

    # 4. Exclude cutout holes
    donut = Draw.shape(
        name="donut",
        type="rectangle",
        size=(100.0, 100.0),
        closed=True,
        side_edit=Draw.side_edit(
            exclude=[
                {
                    "line": [
                        (-20.0, 20.0),
                        (20.0, 20.0),
                        (20.0, -20.0),
                        (-20.0, -20.0),
                    ]
                }
            ]
        ),
    )
    assert len(donut.indices) > 6  # Holes create stitched triangulation

    print("  [PASS] Modifiers and topology passed.")


def test_topology_validation_and_errors():
    print("Testing conditions and custom errors...")
    Draw.GLOBAL_REGISTRY.clear()

    # 1. Conflicting definition (both type and vertices)
    try:
        Draw.shape(name="bad1", type="rectangle", vertices=4)
        assert False, "Should have raised ConflictingGeometryDefinitionError"
    except Draw.ConflictingGeometryDefinitionError:
        pass

    # 2. Missing definition
    try:
        Draw.shape(name="bad2")
        assert False, "Should have raised MissingGeometryDefinitionError"
    except Draw.MissingGeometryDefinitionError:
        pass

    # 3. Closed shape independent side_length
    try:
        Draw.shape(
            name="bad3",
            type="rectangle",
            closed=True,
            side_edit=Draw.side_edit(side_length={0: 50.0}),
        )
        assert False, "Should have raised ClosedShapeTopologyError"
    except Draw.ClosedShapeTopologyError:
        pass

    # 4. Closed shape side_angle AND side_length
    try:
        Draw.shape(
            name="bad4",
            type="rectangle",
            closed=True,
            side_edit=Draw.side_edit(side_length={0: 50.0}, side_angle={0: 30.0}),
        )
        assert False, "Should have raised OverConstrainedTopologyError"
    except Draw.OverConstrainedTopologyError:
        pass

    # 5. Duplicate shape name
    Draw.shape(name="unique_item", type="rectangle")
    try:
        Draw.shape(name="unique_item", type="rectangle")
        assert False, "Should have raised DuplicateShapeNameError"
    except Draw.DuplicateShapeNameError:
        pass

    # 6. Shape not found
    try:
        Draw.shapes.get("non_existent_item")
        assert False, "Should have raised ShapeNotFoundError"
    except Draw.ShapeNotFoundError:
        pass

    print("  [PASS] Validation and custom errors passed.")


def test_batch_groups_and_context_manager():
    print("Testing batch shapes, registry namespace, and context manager...")
    Draw.GLOBAL_REGISTRY.clear()

    # 1. Batch creation via Draw.shapes([ ... ])
    group = Draw.shapes(
        items=[
            Draw.shape(name="btn1", type="rectangle", size=(80, 40), z=1),
            Draw.shape(name="btn2", type="rectangle", size=(80, 40), z=2),
        ],
        name="button_group",
        z_offset=10,
        tags=["ui", "hud"],
    )
    assert len(group) == 2
    assert Draw.shapes.get("btn1").z == 11
    assert Draw.shapes.get("btn2").z == 12
    assert "ui" in Draw.shapes.get("btn1").tags

    # Aggregate bounds
    gb = group.bounds
    assert gb["width"] > 0
    assert gb["height"] > 0

    # 2. Context manager 'with Draw.shapes():'
    with Draw.shapes(name="dialog", z_offset=100, tags=["dialog"]) as dlg:
        Draw.shape(name="dialog_bg", type="rectangle", size=(300, 200))
        Draw.shape(name="dialog_ok", type="rectangle", size=(100, 40))

    assert len(dlg) == 2
    assert Draw.shapes.exists("dialog_bg")
    assert Draw.shapes.get("dialog_bg").z == 100
    assert "dialog" in Draw.shapes.get("dialog_ok").tags

    # Bulk remove from group
    removed = dlg.remove()
    assert removed == 2
    assert not Draw.shapes.exists("dialog_bg")
    assert not Draw.shapes.exists("dialog_ok")

    print("  [PASS] Batch groups and context manager passed.")


def test_line_shape():
    print("Testing Draw.line()...")
    Draw.GLOBAL_REGISTRY.clear()

    l = Draw.line(
        name="connector",
        coordinates=[(0.0, 0.0), (100.0, 50.0), (200.0, 0.0)],
        z=3,
    )
    assert l.closed is False
    assert len(l.vertices) == 3
    assert l.z == 3
    assert l.indices == []  # Open paths have no fill indices

    print("  [PASS] Line shape passed.")


def test_to_dict_and_query():
    print("Testing to_dict() and query()...")
    Draw.GLOBAL_REGISTRY.clear()

    card = Draw.shape(
        name="export_card",
        type="rectangle",
        size=(100.0, 50.0),
        z=2,
    )

    # 1. to_dict()
    d = card.to_dict()
    assert d["name"] == "export_card"
    assert d["type"] == "rectangle"
    assert d["closed"] is True
    assert d["z"] == 2
    assert d["geometry"]["vertex_count"] == 4
    assert len(d["geometry"]["vertices"]) == 8  # 4 * 2 flat floats
    assert d["versions"]["geometry"] == 1

    # 2. query()
    q = card.query(["size", "vertices", "z", "closed", "bounds", "map"])
    assert q["size"] == (100.0, 50.0)
    assert q["vertices"] == 4  # count
    assert q["z"] == 2
    assert "bounds" in q
    assert "map" in q

    # 3. update tracking
    card.update(position=(10.0, 20.0))
    assert card.transform_version == 2
    assert card.geometry_version == 1

    card.update(size=(120.0, 60.0))
    assert card.geometry_version == 2

    print("  [PASS] to_dict() and query() passed.")


def test_scoped_lifecycle():
    print("Testing scoped=True weakref lifecycle...")
    Draw.GLOBAL_REGISTRY.clear()

    def _create_scoped():
        s = Draw.shape(name="temp_dialog", type="rectangle", scoped=True)
        assert Draw.shapes.exists("temp_dialog")
        return s.name

    name = _create_scoped()
    # Now s is out of scope and garbage collected
    import gc
    gc.collect()
    assert not Draw.shapes.exists(name), "Scoped shape should have been auto-deregistered after going out of scope."

    print("  [PASS] Scoped weakref lifecycle passed.")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING ALL DRAW3 SHAPE MODULE TESTS (WORKING DATA)")
    print("=" * 60)
    test_core_primitives()
    test_unit_resolution()
    test_modifiers_and_topology()
    test_topology_validation_and_errors()
    test_batch_groups_and_context_manager()
    test_line_shape()
    test_to_dict_and_query()
    test_scoped_lifecycle()
    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! (100% GREEN)")
    print("=" * 60)
