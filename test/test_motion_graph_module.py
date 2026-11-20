"""Draw Motion Graph Module — Comprehensive Test Suite.

Tests for Draw.motion_graph API specification:
- Point-based graphs with linear, smooth, and step interpolation.
- Boundary clamping and overshoot / undershoot values.
- Combined graphs with automatic weight normalization.
- Circular reference detection (direct, mutual, transitive).
- Registry operations (register, get, exists, list, update, copy, all, remove, clear, evaluate).
- Integration with motion.move() and motion.transform().
- Error hierarchy and validation edge cases.
- Serialization to JSON schema.
"""

import math
import sys
from typing import List

import Draw
from Draw import motion, motion_graph
from Draw.motion_graph import (
    MotionGraph,
    DrawMotionGraphError,
    InvalidMotionGraphError,
    DuplicateMotionGraphNameError,
    MotionGraphNotFoundError,
    CircularGraphReferenceError,
    InvalidInterpolationModeError,
    InvalidGraphPointsError,
    InvalidGraphCombineError,
    GraphDefinitionConflictError,
    LINEAR,
    SMOOTH,
    STEP,
)

passed = 0
failed = 0
errors_log: List[str] = []


def check(name: str, condition: bool, msg: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        detail = f" — {msg}" if msg else ""
        print(f"  [FAIL] {name}{detail}")
        errors_log.append(f"{name}{detail}")


def reset() -> None:
    Draw.motion_graph.clear()
    Draw.motion.clear()
    Draw.time_line.clear()


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 1: Point-Based Graphs & Interpolation Modes
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 1: Point-Based Graphs & Interpolation Modes ═══")
reset()

# 1.1 Linear interpolation
g_lin = Draw.motion_graph(
    name="linear_test",
    points=[(0.0, 0.0), (0.5, 0.8), (1.0, 1.0)],
    interpolation="linear",
)
check("1.1a is MotionGraph", isinstance(g_lin, MotionGraph))
check("1.1b linear at 0.0 is 0.0", abs(g_lin.evaluate(0.0) - 0.0) < 1e-6)
check("1.1c linear at 0.25 is 0.4", abs(g_lin.evaluate(0.25) - 0.4) < 1e-6)
check("1.1d linear at 0.5 is 0.8", abs(g_lin.evaluate(0.5) - 0.8) < 1e-6)
check("1.1e linear at 0.75 is 0.9", abs(g_lin.evaluate(0.75) - 0.9) < 1e-6)
check("1.1f linear at 1.0 is 1.0", abs(g_lin.evaluate(1.0) - 1.0) < 1e-6)
check("1.1g callable syntax g(0.5)", abs(g_lin(0.5) - 0.8) < 1e-6)

# 1.2 Step interpolation
g_step = Draw.motion_graph(
    name="step_test",
    points=[(0.0, 0.0), (0.4, 0.5), (0.8, 1.0)],
    interpolation="step",
)
check("1.2a step at 0.0 is 0.0", g_step.evaluate(0.0) == 0.0)
check("1.2b step at 0.39 is 0.0", g_step.evaluate(0.39) == 0.0)
check("1.2c step at 0.4 is 0.5", g_step.evaluate(0.4) == 0.5)
check("1.2d step at 0.79 is 0.5", g_step.evaluate(0.79) == 0.5)
check("1.2e step at 0.8 is 1.0", g_step.evaluate(0.8) == 1.0)
check("1.2f step at 1.0 is 1.0", g_step.evaluate(1.0) == 1.0)

# 1.3 Smooth interpolation (Monotone Cubic Hermite Spline)
g_smooth = Draw.motion_graph(
    name="smooth_test",
    points=[(0.0, 0.0), (0.25, 0.2), (0.5, 0.7), (0.75, 0.9), (1.0, 1.0)],
    interpolation="smooth",
)
check("1.3a smooth at 0.0 is 0.0", abs(g_smooth.evaluate(0.0) - 0.0) < 1e-6)
check("1.3b smooth at 0.5 is 0.7", abs(g_smooth.evaluate(0.5) - 0.7) < 1e-6)
check("1.3c smooth at 1.0 is 1.0", abs(g_smooth.evaluate(1.0) - 1.0) < 1e-6)
# Verify monotonicity between 0.0 and 1.0
vals = [g_smooth.evaluate(i / 20.0) for i in range(21)]
is_monotonic = all(vals[i] <= vals[i + 1] + 1e-9 for i in range(len(vals) - 1))
check("1.3d smooth preserves monotonicity without ringing", is_monotonic)

# 1.4 Boundary clamping (values outside [x0, xn])
check("1.4a clamp below x0", g_lin.evaluate(-0.5) == 0.0)
check("1.4b clamp above xn", g_lin.evaluate(1.5) == 1.0)
check("1.4c step clamp below x0", g_step.evaluate(-0.2) == 0.0)
check("1.4d step clamp above xn", g_step.evaluate(1.2) == 1.0)
check("1.4e smooth clamp below x0", g_smooth.evaluate(-0.1) == 0.0)
check("1.4f smooth clamp above xn", g_smooth.evaluate(1.1) == 1.0)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 2: Output Range and Overshoot / Undershoot
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 2: Output Range and Overshoot / Undershoot ═══")

# 2.1 Anticipation (y < 0.0) and overshoot (y > 1.0)
g_overshoot = Draw.motion_graph(
    name="anticipate_overshoot",
    points=[
        (0.0, 0.0),
        (0.2, -0.2),   # Anticipation / pull back
        (0.8, 1.25),   # Overshoot
        (1.0, 1.0),    # Settle
    ],
    interpolation="smooth",
)
check("2.1a reaches negative value", g_overshoot.evaluate(0.2) == -0.2)
check("2.1b reaches overshoot value > 1.0", g_overshoot.evaluate(0.8) == 1.25)
check("2.1c settles at 1.0", abs(g_overshoot.evaluate(1.0) - 1.0) < 1e-6)

# 2.2 Shake curve with alternating Y values
g_shake = Draw.motion_graph(
    name="shake_curve",
    points=[
        (0.0, 0.0),
        (0.1, 1.0),
        (0.2, -1.0),
        (0.3, 1.0),
        (0.4, -1.0),
        (0.5, 0.8),
        (0.7, -0.5),
        (1.0, 0.0),
    ],
    interpolation="smooth",
)
check("2.2a shake peak at 0.1", abs(g_shake.evaluate(0.1) - 1.0) < 1e-6)
check("2.2b shake valley at 0.2", abs(g_shake.evaluate(0.2) - (-1.0)) < 1e-6)
check("2.2c shake finishes at 0.0", abs(g_shake.evaluate(1.0) - 0.0) < 1e-6)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 3: Combining Graphs & Blending
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 3: Combining Graphs & Blending ═══")
reset()

# 3.1 Blend of built-in easings: ease_out (0.7) and ease_in (0.3)
g_comb1 = Draw.motion_graph(
    name="combined_ease",
    combine=[
        ("ease_out", 0.7),
        ("ease_in", 0.3),
    ],
)
check("3.1a combined graph created", isinstance(g_comb1, MotionGraph))
check("3.1b combined type is 'combine'", g_comb1.type == "combine")

# Test blend formula: G(x) = (0.7 * ease_out(x) + 0.3 * ease_in(x)) / 1.0
val_mid = g_comb1.evaluate(0.5)
expected_mid = 0.7 * (1.0 - 0.5 * 0.5) + 0.3 * (0.5 * 0.5)  # 0.7 * 0.75 + 0.3 * 0.25 = 0.525 + 0.075 = 0.6
check("3.1c combined evaluation at 0.5 matches blend formula", abs(val_mid - expected_mid) < 1e-6)

# 3.2 Non-normalized weights (e.g. 7 and 3 instead of 0.7 and 0.3)
g_comb2 = Draw.motion_graph(
    name="combined_unnormalized",
    combine=[
        ("ease_out", 7.0),
        ("ease_in", 3.0),
    ],
)
check("3.2 automatic weight normalization produces identical result", abs(g_comb2.evaluate(0.5) - expected_mid) < 1e-6)

# 3.3 Combine blending a custom graph and a built-in graph
g_custom_step = Draw.motion_graph(
    name="custom_step",
    points=[(0.0, 0.0), (0.5, 1.0), (1.0, 1.0)],
    interpolation="step",
)
g_hybrid = Draw.motion_graph(
    name="hybrid",
    combine=[
        ("custom_step", 0.5),
        ("linear", 0.5),
    ],
)
# At x=0.25: custom_step is 0.0, linear is 0.25 -> 0.5*0 + 0.5*0.25 = 0.125
check("3.3a hybrid blend at 0.25", abs(g_hybrid.evaluate(0.25) - 0.125) < 1e-6)
# At x=0.5: custom_step is 1.0, linear is 0.5 -> 0.5*1 + 0.5*0.5 = 0.75
check("3.3b hybrid blend at 0.5", abs(g_hybrid.evaluate(0.5) - 0.75) < 1e-6)

# 3.4 Multi-level combine (Graph A combines Graph B, Graph B combines Graph C)
g_level1 = Draw.motion_graph(name="lvl1", combine=[("linear", 1.0)])
g_level2 = Draw.motion_graph(name="lvl2", combine=[("lvl1", 1.0)])
check("3.4 multi-level combine evaluates cleanly", abs(g_level2.evaluate(0.4) - 0.4) < 1e-6)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 4: Validation & Error Handling
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 4: Validation & Error Handling ═══")
reset()

# 4.1 Definition exclusivity: both or neither
try:
    Draw.motion_graph(name="bad1", points=[(0, 0), (1, 1)], combine=[("linear", 1.0)])
    check("4.1a both points and combine rejected", False)
except GraphDefinitionConflictError:
    check("4.1a both points and combine rejected", True)

try:
    Draw.motion_graph(name="bad2")
    check("4.1b neither points nor combine rejected", False)
except GraphDefinitionConflictError:
    check("4.1b neither points nor combine rejected", True)

# 4.2 Point errors: < 2 points
try:
    Draw.motion_graph(name="single_pt", points=[(0.0, 0.0)])
    check("4.2a single point rejected", False)
except InvalidGraphPointsError:
    check("4.2a single point rejected", True)

# 4.3 Descending or duplicate X values
try:
    Draw.motion_graph(name="dup_x", points=[(0.0, 0.0), (0.5, 0.5), (0.5, 0.8), (1.0, 1.0)])
    check("4.3a duplicate X rejected", False)
except InvalidGraphPointsError:
    check("4.3a duplicate X rejected", True)

try:
    Draw.motion_graph(name="desc_x", points=[(0.0, 0.0), (0.6, 0.5), (0.4, 0.8), (1.0, 1.0)])
    check("4.3b descending X rejected", False)
except InvalidGraphPointsError:
    check("4.3b descending X rejected", True)

# 4.4 Non-finite coordinates
try:
    Draw.motion_graph(name="inf_pt", points=[(0.0, 0.0), (float("inf"), 1.0)])
    check("4.4 infinite coordinate rejected", False)
except InvalidGraphPointsError:
    check("4.4 infinite coordinate rejected", True)

# 4.5 Unsupported interpolation mode
try:
    Draw.motion_graph(name="bad_mode", points=[(0, 0), (1, 1)], interpolation="quantum_bezier")
    check("4.5 unsupported interpolation rejected", False)
except InvalidInterpolationModeError:
    check("4.5 unsupported interpolation rejected", True)

# 4.6 Combine errors: negative or zero weights
try:
    Draw.motion_graph(name="neg_w", combine=[("linear", -0.5), ("ease_out", 1.0)])
    check("4.6a negative weight rejected", False)
except InvalidGraphCombineError:
    check("4.6a negative weight rejected", True)

try:
    Draw.motion_graph(name="zero_w", combine=[("linear", 0.0), ("ease_out", 0.0)])
    check("4.6b zero total weight rejected", False)
except InvalidGraphCombineError:
    check("4.6b zero total weight rejected", True)

# 4.7 Unknown referenced graph in combine
try:
    Draw.motion_graph(name="unknown_ref", combine=[("non_existent_graph_xyz", 1.0)])
    check("4.7 unknown referenced graph rejected", False)
except MotionGraphNotFoundError:
    check("4.7 unknown referenced graph rejected", True)

# 4.8 Circular references
# 4.8a Direct self-combine
try:
    Draw.motion_graph(name="self_ref", combine=[("self_ref", 1.0)])
    check("4.8a direct self-combine rejected", False)
except CircularGraphReferenceError:
    check("4.8a direct self-combine rejected", True)

# 4.8b Mutual circular combine (A -> B, B -> A)
Draw.motion_graph(name="node_A", combine=[("linear", 1.0)])
try:
    Draw.motion_graph(name="node_B", combine=[("node_A", 1.0)])
    # Now update node_A to point to node_B
    Draw.motion_graph.update("node_A", combine=[("node_B", 1.0)])
    check("4.8b mutual circular reference rejected", False)
except CircularGraphReferenceError:
    check("4.8b mutual circular reference rejected", True)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 5: Registry Operations (CRUD)
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 5: Registry Operations (CRUD) ═══")
reset()

g1 = Draw.motion_graph(name="g1", points=[(0, 0), (1, 1)], interpolation="linear")
check("5.1a exists('g1')", Draw.motion_graph.exists("g1"))
check("5.1b get('g1')", Draw.motion_graph.get("g1") is g1)

# Duplicate registration error
try:
    Draw.motion_graph(name="g1", points=[(0, 0), (1, 1)])
    check("5.2 duplicate name rejected", False)
except DuplicateMotionGraphNameError:
    check("5.2 duplicate name rejected", True)

# list() and all()
all_graphs = Draw.motion_graph.all()
check("5.3a all() contains g1", "g1" in all_graphs)
list_names = Draw.motion_graph.list()
check("5.3b list() has 'g1'", "g1" in list_names)
dict_repr = Draw.motion_graph.list("g1")
check("5.3c list('g1') returns dict", dict_repr["name"] == "g1" and dict_repr["type"] == "points")

# update()
g1_up = Draw.motion_graph.update("g1", points=[(0, 0), (0.5, 0.9), (1, 1)], interpolation="linear")
check("5.4a update evaluation changed", g1_up.evaluate(0.5) == 0.9)

# copy()
g1_copy = Draw.motion_graph.copy("g1", "g1_cloned")
check("5.5a copy exists", Draw.motion_graph.exists("g1_cloned"))
check("5.5b copy has same evaluation", g1_copy.evaluate(0.5) == 0.9)

# evaluate() helper on API
check("5.6 evaluate on API", Draw.motion_graph.evaluate("g1_cloned", 0.5) == 0.9)

# remove() and clear()
removed_cnt = Draw.motion_graph.remove("g1_cloned")
check("5.7a remove count is 1", removed_cnt == 1)
check("5.7b removed no longer exists", not Draw.motion_graph.exists("g1_cloned"))

Draw.motion_graph.clear()
check("5.8 clear() emptied registry", len(Draw.motion_graph.all()) == 0)


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 6: Motion & Transform Integration
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 6: Motion & Transform Integration ═══")
reset()

# Define a custom bounce-anticipate motion graph
Draw.motion_graph(
    name="custom_curve",
    points=[(0.0, 0.0), (0.3, -0.1), (0.8, 1.1), (1.0, 1.0)],
    interpolation="smooth",
)

# 6.1 Using custom graph in motion.move()
# Draw.motion(name="box", move=motion.move(translate=[(300, 200), "custom_curve", 2.0]))
m_box = Draw.motion(
    name="box",
    move=motion.move(
        translate=[(300, 200), "custom_curve", 2.0],
        rotate=[90, "linear", 1.5],
    ),
)
check("6.1a motion registered with custom graph", m_box.move_anim is not None)
ch_trans = m_box.move_anim.get_channel("translate")
check("6.1b translate easing is 'custom_curve'", ch_trans.easing == "custom_curve")
resolved = m_box.resolve()
check("6.1c resolved channel preserves 'custom_curve'", resolved[0].easing == "custom_curve")

# 6.2 Using custom graph as default in motion.transform()
# Draw.motion(name="card", transform=motion.transform(to={...}, duration=2.0, graph="custom_curve"))
m_card = Draw.motion(
    name="card",
    transform=motion.transform(
        to={
            "translate": (300, 200),
            "rotate": 90,
            "scale": (1.5, 1.5),
        },
        duration=2.0,
        graph="custom_curve",
    ),
)
check("6.2a transform with custom graph", m_card.transform_anim is not None)
check("6.2b transform graph is 'custom_curve'", m_card.transform_anim.graph == "custom_curve")
check("6.2c to_dict serialization has 'custom_curve'", m_card.to_dict()["transform"]["graph"] == "custom_curve")

# 6.3 Using combined graph in motion
Draw.motion_graph(
    name="blend_soft",
    combine=[("custom_curve", 0.6), ("ease_out", 0.4)],
)
m_soft = Draw.motion(
    name="soft_box",
    move=motion.move(opacity=[0.5, "blend_soft", 1.0]),
)
check("6.3 combined graph accepted in move channel", m_soft.move_anim.get_channel("opacity").easing == "blend_soft")


# ═══════════════════════════════════════════════════════════════════════
# TEST GROUP 7: Serialization & JSON Schema
# ═══════════════════════════════════════════════════════════════════════

print("\n═══ TEST GROUP 7: Serialization & JSON Schema ═══")
reset()

g_pts = Draw.motion_graph(
    name="pts_graph",
    points=[(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)],
    interpolation="linear",
)
dict_pts = g_pts.to_dict()
check("7.1a schema is draw.motion_graph", dict_pts["schema"] == "draw.motion_graph")
check("7.1b version is 1", dict_pts["version"] == 1)
check("7.1c type is points", dict_pts["type"] == "points")
check("7.1d points list", dict_pts["points"] == [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]])
check("7.1e interpolation is linear", dict_pts["interpolation"] == "linear")

g_cmb = Draw.motion_graph(
    name="cmb_graph",
    combine=[("pts_graph", 0.8), ("linear", 0.2)],
)
dict_cmb = g_cmb.to_dict()
check("7.2a combine schema is draw.motion_graph", dict_cmb["schema"] == "draw.motion_graph")
check("7.2b combine type is combine", dict_cmb["type"] == "combine")
check("7.2c combine list", dict_cmb["combine"] == [["pts_graph", 0.8], ["linear", 0.2]])


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
    sys.exit(1)
else:
    print("\n  ✓ All tests passed!")
print()
