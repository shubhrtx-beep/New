"""Comprehensive Unit Test Suite for Draw3 Color Subsystem.

Tests color representations, range validation, channels, gradients,
dynamic motion AST, harmonies, registry lifecycles, palette tokens,
and shape integration.
"""

import gc
import unittest
from typing import Dict, Any

import Draw
from Draw import color, palette
from Draw.color import (
    ColorBinding,
    ColorValue,
    ColorGradient,
    ColorBody,
    ColorBorder,
    ColorShadow,
    ColorGlow,
    ColorFilter,
    GLOBAL_COLOR_REGISTRY,
    IN_SHAPE,
    DrawColorError,
    InvalidColorValueError,
    UnknownColorNameError,
    InvalidHexColorError,
    ColorTokenCycleError,
    InvalidMotionError,
    DuplicateColorNameError,
    ColorNotFoundError,
)


class TestColorRepresentations(unittest.TestCase):
    """Tests color constructors: rgb, rgba, hsv, hex, and parsing."""

    def test_rgb_integers_and_floats(self):
        c1 = color.rgb(255, 0, 128)
        self.assertAlmostEqual(c1.to_rgba_tuple()[0], 1.0)
        self.assertAlmostEqual(c1.to_rgba_tuple()[1], 0.0)
        self.assertAlmostEqual(c1.to_rgba_tuple()[2], 128 / 255.0, places=4)
        self.assertEqual(c1.to_rgba_tuple()[3], 1.0)

        # Floats
        c2 = color.rgba(0.2, 0.4, 0.6, 0.8)
        self.assertEqual(c2.to_rgba_tuple(), (0.2, 0.4, 0.6, 0.8))

    def test_hsv(self):
        # Pure red: h=0, s=100, v=100
        red = color.hsv(0.0, 100.0, 100.0)
        r, g, b, a = red.to_rgba_tuple()
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(g, 0.0)
        self.assertAlmostEqual(b, 0.0)

        # Pure green: h=120, s=100, v=100
        green = color.hsv(120.0, 100.0, 100.0)
        r, g, b, _ = green.to_rgba_tuple()
        self.assertAlmostEqual(r, 0.0)
        self.assertAlmostEqual(g, 1.0)
        self.assertAlmostEqual(b, 0.0)

        # Pure blue: h=240, s=100, v=100
        blue = color.hsv(240.0, 100.0, 100.0)
        r, g, b, _ = blue.to_rgba_tuple()
        self.assertAlmostEqual(r, 0.0)
        self.assertAlmostEqual(g, 0.0)
        self.assertAlmostEqual(b, 1.0)

    def test_hex(self):
        # 6-char
        c = color.hex("#ff0000")
        self.assertEqual(c.to_rgba_tuple(), (1.0, 0.0, 0.0, 1.0))

        # 3-char
        c = color.hex("#0f0")
        self.assertEqual(c.to_rgba_tuple(), (0.0, 1.0, 0.0, 1.0))

        # 8-char
        c = color.hex("#0000ff80")
        self.assertAlmostEqual(c.to_rgba_tuple()[2], 1.0)
        self.assertAlmostEqual(c.to_rgba_tuple()[3], 128 / 255.0, places=3)

    def test_css_names(self):
        red = Draw.color.body(fill="red")
        self.assertEqual(red.fill.to_rgba_tuple(), (1.0, 0.0, 0.0, 1.0))

        transparent = Draw.color.body(fill="transparent")
        self.assertEqual(transparent.fill.to_rgba_tuple(), (0.0, 0.0, 0.0, 0.0))


class TestColorValidationAndErrors(unittest.TestCase):
    """Tests strict validation: clamping is forbidden, explicit exceptions must be raised."""

    def test_out_of_range_integers(self):
        with self.assertRaises(InvalidColorValueError):
            color.rgb(256, 0, 0)
        with self.assertRaises(InvalidColorValueError):
            color.rgb(-1, 0, 0)

    def test_out_of_range_floats(self):
        with self.assertRaises(InvalidColorValueError):
            color.rgb(1.5, 0.0, 0.0)
        with self.assertRaises(InvalidColorValueError):
            color.rgb(-0.1, 0.0, 0.0)

    def test_invalid_hex(self):
        with self.assertRaises(InvalidHexColorError):
            color.hex("#XYZ123")
        with self.assertRaises(InvalidHexColorError):
            color.hex("ff0000")  # missing #
        with self.assertRaises(InvalidHexColorError):
            color.hex("#12345")  # invalid length

    def test_unknown_css_name(self):
        with self.assertRaises(UnknownColorNameError):
            color.body(fill="not_a_real_color")


class TestChannelsAndGradients(unittest.TestCase):
    """Tests body, border, shadow, glow, and gradient constructions."""

    def test_body_and_border(self):
        b = color.body(fill="#1e293b", opacity=0.8, blend="screen")
        self.assertEqual(b.blend, "screen")
        self.assertEqual(b.opacity, 0.8)

        br = color.border(fill="cyan", width=2.5, style="dashed")
        self.assertEqual(br.width, 2.5)
        self.assertEqual(br.style, "dashed")

    def test_shadow_and_glow(self):
        s = color.shadow(fill="black", blur=12.0, spread=1.0, offset=(2.0, 4.0), opacity=0.6, inner=True)
        self.assertEqual(s.blur, 12.0)
        self.assertEqual(s.spread, 1.0)
        self.assertEqual(s.offset, (2.0, 4.0))
        self.assertTrue(s.inner)

        g = color.glow(fill="red", blur=20.0, opacity=0.9)
        self.assertEqual(g.blur, 20.0)
        self.assertEqual(g.opacity, 0.9)

    def test_gradient(self):
        grad = color.gradient(
            type="linear",
            angle=45.0,
            stops=[("0%", "#0ea5e9"), (0.5, "#8b5cf6"), ("100%", "#f43f5e")],
            spread="reflect",
        )
        self.assertEqual(grad.gradient_type, "linear")
        self.assertEqual(grad.spread, "reflect")
        self.assertEqual(len(grad.stops), 3)
        self.assertEqual(grad.stops[0][0], 0.0)
        self.assertEqual(grad.stops[1][0], 0.5)
        self.assertEqual(grad.stops[2][0], 1.0)


class TestDynamicValuesAndAST(unittest.TestCase):
    """Tests motion drivers and symbolic expression trees."""

    def test_drivers(self):
        c = color.cycle(speed=45.0, offset=90.0)
        self.assertTrue(c.is_dynamic)
        data = c.to_dict()
        self.assertEqual(data["type"], "cycle")
        self.assertEqual(data["speed"], 45.0)
        self.assertEqual(data["offset"], 90.0)

        p = color.pulse(min_val=10.0, max_val=50.0, speed=2.0)
        self.assertEqual(p.to_dict()["type"], "pulse")

        o = color.oscillate(from_val=0.0, to_val=1.0, duration=1.5)
        self.assertEqual(o.to_dict()["type"], "oscillate")

    def test_expressions(self):
        # time * 45 + 20
        expr_tree = color.time * 45 + 20
        self.assertTrue(expr_tree.is_dynamic)
        d = expr_tree.to_dict()
        self.assertEqual(d["op"], "add")
        self.assertEqual(d["args"][0]["op"], "mul")

        # math helpers
        sin_expr = color.sin(color.time * 2.0)
        self.assertEqual(sin_expr.to_dict()["op"], "sin")

        clamped = color.clamp(color.time, 0.0, 10.0)
        self.assertEqual(clamped.to_dict()["op"], "clamp")

    def test_dynamic_binding_serialization(self):
        binding = Draw.color(
            name="animated_panel",
            body=color.body(
                fill=color.hsv(
                    h=color.cycle(speed=60.0),
                    s=90.0,
                    v=100.0,
                )
            ),
            border=color.border(
                fill="#38bdf8",
                width=color.pulse(min_val=1.0, max_val=5.0),
            ),
        )
        self.assertTrue(binding.dynamic)
        serialized = binding.to_dict()
        self.assertEqual(serialized["schema"], "draw.color")
        self.assertEqual(serialized["version"], 1)
        self.assertTrue(serialized["dynamic"])
        self.assertEqual(serialized["channels"]["body"]["fill"]["type"], "hsv")
        self.assertEqual(serialized["channels"]["body"]["fill"]["h"]["type"], "cycle")
        self.assertEqual(serialized["channels"]["border"]["width"]["type"], "pulse")


class TestHarmonies(unittest.TestCase):
    """Tests color harmonies: complement, triadic, analogous, mix, etc."""

    def test_complement(self):
        # Red complement is Cyan
        red = color.rgb(255, 0, 0)
        comp = color.complement(red)
        r, g, b, _ = comp.to_rgba_tuple()
        self.assertAlmostEqual(r, 0.0)
        self.assertAlmostEqual(g, 1.0)
        self.assertAlmostEqual(b, 1.0)

    def test_mix(self):
        # 50% blend of black and white gives 50% gray
        mixed = color.mix("black", "white", 0.5)
        r, g, b, _ = mixed.to_rgba_tuple()
        self.assertAlmostEqual(r, 0.5, places=3)
        self.assertAlmostEqual(g, 0.5, places=3)
        self.assertAlmostEqual(b, 0.5, places=3)

    def test_dot_reference(self):
        # Setup source binding
        Draw.color(name="src_box", body=color.body(fill="red"))
        comp = color.complement("src_box.body")
        r, g, b, _ = comp.to_rgba_tuple()
        self.assertAlmostEqual(r, 0.0)
        self.assertAlmostEqual(g, 1.0)
        self.assertAlmostEqual(b, 1.0)


class TestPaletteAndThemes(unittest.TestCase):
    """Tests Draw.palette tokens and theme switching."""

    def setUp(self):
        palette.clear()

    def test_tokens(self):
        Draw.palette(primary="#3b82f6", surface="#1e293b")
        self.assertEqual(palette.primary, "#3b82f6")
        self.assertEqual(palette.surface, "#1e293b")

    def test_theme_switch(self):
        Draw.color.theme(
            name="dark",
            tokens={"primary": "#60a5fa", "surface": "#0f172a"},
        )
        Draw.color.theme(
            name="light",
            tokens={"primary": "#2563eb", "surface": "#ffffff"},
        )

        Draw.color.use_theme("dark")
        self.assertEqual(palette.primary, "#60a5fa")

        Draw.color.use_theme("light")
        self.assertEqual(palette.primary, "#2563eb")

    def test_circular_token_error(self):
        Draw.palette(a="@b", b="@a")
        with self.assertRaises(ColorTokenCycleError):
            _ = palette.a


class TestRegistryAndLifecycles(unittest.TestCase):
    """Tests ColorAPI registry operations and weakref-scoped bindings."""

    def setUp(self):
        Draw.color.clear()

    def test_registry_crud(self):
        b = Draw.color(name="card", body=color.body(fill="blue"))
        self.assertTrue(Draw.color.exists("card"))
        self.assertEqual(Draw.color.get("card"), b)

        # Duplicate error
        with self.assertRaises(DuplicateColorNameError):
            Draw.color(name="card", body=color.body(fill="red"))

        # Update
        Draw.color.update("card", body=color.body(fill="green"))
        self.assertAlmostEqual(Draw.color.get("card").body.fill.to_rgba_tuple()[1], 0.50196, places=3)

        # Copy
        Draw.color.copy("card", "card_copy")
        self.assertTrue(Draw.color.exists("card_copy"))

        # Remove
        Draw.color.remove("card")
        self.assertFalse(Draw.color.exists("card"))

    def test_scoped_weakref(self):
        def _create_scoped():
            scoped_binding = Draw.color(name="temp_scoped", scoped=True, body=color.body(fill="yellow"))
            self.assertTrue(Draw.color.exists("temp_scoped"))
            return None

        _create_scoped()
        gc.collect()
        self.assertFalse(Draw.color.exists("temp_scoped"))


class TestShapeIntegration(unittest.TestCase):
    """Tests connecting Draw.color to Draw.shape via registered names, inline styles, and shorthand."""

    def setUp(self):
        Draw.shapes.clear()
        Draw.color.clear()

    def test_shape_registered_color(self):
        Draw.color(name="card_theme", body=color.body(fill="#1e293b"))
        s = Draw.shape(name="box1", type="rectangle", size=(100, 50), color="card_theme")
        self.assertEqual(s.color.name, "card_theme")
        self.assertIn("color", s.to_dict())
        self.assertEqual(s.to_dict()["color"]["name"], "card_theme")

    def test_shape_inline_anonymous_color(self):
        # Inline color style automatically inherits shape's name
        s = Draw.shape(
            name="box2",
            type="rectangle",
            size=(100, 50),
            color=Draw.color(body=color.body(fill="crimson")),
        )
        self.assertEqual(s.color.name, "box2")
        self.assertTrue(Draw.color.exists("box2"))
        self.assertEqual(s.to_dict()["color"]["name"], "box2")

    def test_shape_shorthand_color(self):
        # Shorthand hex
        s = Draw.shape(name="box3", type="rectangle", size=(100, 50), color="#ff0000")
        self.assertEqual(s.color.name, "box3")
        self.assertEqual(s.color.body.fill.to_rgba_tuple(), (1.0, 0.0, 0.0, 1.0))


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING ALL DRAW3 COLOR MODULE TESTS (WORKING DATA)")
    print("=" * 60)
    unittest.main()
