# SPDX-License-Identifier: LGPL-2.1-or-later
"""Geometry components against known answers, in console FreeCAD (no window).

    freecadcmd.exe tests/test_geometry.py     (KATYDID_OUT chooses where results go)
"""

import json
import math
import os
import sys
import traceback
import unittest

import FreeCAD
import Part

V = FreeCAD.Vector
TOL = 1e-6

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # run as a macro
    import katydid
    _HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__))), "tests")
sys.path.insert(0, os.path.dirname(_HERE))

from katydid import components as lib  # noqa: E402
from katydid import demo  # noqa: E402
from katydid.engine import Graph  # noqa: E402


class FakeScene:
    """Just enough of KatydidScene for the demo builders, without Qt."""

    def __init__(self):
        self.graph = Graph()

    def add_component(self, comp, pos, centre=False):
        self.graph.add(comp)

    def rebuild_wires(self):
        pass

    def request_solve(self):
        pass


def vclose(a, b):
    return (a - b).Length < TOL


class Points(unittest.TestCase):
    def test_construct_deconstruct_distance_vector(self):
        p = lib.ConstructPoint().solve_instance(1, 2, 3)
        self.assertTrue(vclose(p.Point, V(1, 2, 3)))
        self.assertEqual(lib.Deconstruct().solve_instance(p), (1, 2, 3))
        self.assertAlmostEqual(lib.Distance().solve_instance((0, 0, 0), V(3, 4, 0)), 5.0)
        v, length = lib.Vector2Pt().solve_instance(Part.Vertex(V(1, 1, 0)), V(4, 5, 0))
        self.assertTrue(vclose(v, V(3, 4, 0)))
        self.assertAlmostEqual(length, 5.0)
        v, length = lib.VectorXYZ().solve_instance(0, 0, 2)
        self.assertEqual((tuple(v), length), ((0, 0, 2), 2.0))


class Curves(unittest.TestCase):
    def test_line_and_degenerate_line(self):
        self.assertAlmostEqual(lib.Line().solve_instance((0, 0, 0), (10, 0, 0)).Length, 10.0)
        with self.assertRaises(ValueError):
            lib.Line().solve_instance((1, 1, 1), (1, 1, 1))

    def test_arc_through_three_points(self):
        arc = lib.Arc3Pt().solve_instance(V(1, 0, 0), V(0, 1, 0), V(-1, 0, 0))
        self.assertAlmostEqual(arc.Length, math.pi, places=6)

    def test_circle_cnr(self):
        c = lib.CircleCNR().solve_instance(V(1, 2, 3), (0, 0, 1), 2.0)
        self.assertAlmostEqual(c.Length, 4 * math.pi, places=6)
        self.assertTrue(vclose(c.Curve.Center, V(1, 2, 3)))

    def test_interpolate_passes_through_its_points(self):
        pts = [V(0, 0, 0), V(5, 4, 0), V(10, 0, 0), V(15, -3, 2)]
        curve = lib.Interpolate().solve_instance(pts, False)
        for p in pts:
            self.assertLess(curve.distToShape(Part.Vertex(p))[0], 1e-6)

    def test_evaluate_curve_midpoint_and_tangent(self):
        point, tangent = lib.EvaluateCurve().solve_instance(
            lib.Line().solve_instance((0, 0, 0), (10, 0, 0)), 0.5)
        self.assertTrue(vclose(point.Point, V(5, 0, 0)))
        self.assertTrue(vclose(tangent, V(1, 0, 0)))

    def test_offset_circle(self):
        out = lib.OffsetCurve().solve_instance(Part.makeCircle(5), 1.0)
        self.assertAlmostEqual(out.Length, 2 * math.pi * 6, places=4)


class Surfaces(unittest.TestCase):
    def test_extrude_circle_then_cap_is_a_cylinder(self):
        side = lib.Extrude().solve_instance(Part.makeCircle(2), (0, 0, 10))
        self.assertAlmostEqual(side.Area, 2 * math.pi * 2 * 10, places=4)
        solid = lib.CapHoles().solve_instance(side)
        self.assertTrue(solid.isValid())
        self.assertAlmostEqual(solid.Volume, math.pi * 4 * 10, places=3)

    def test_pipe_volume(self):
        pipe = lib.Pipe().solve_instance(lib.Line().solve_instance((0, 0, 0), (0, 0, 10)), 1.0)
        self.assertTrue(pipe.isValid())
        self.assertAlmostEqual(pipe.Volume, math.pi * 10, places=3)


class Transforms(unittest.TestCase):
    def test_rotate_scale_mirror_array(self):
        p = Part.Vertex(V(1, 0, 0))
        self.assertTrue(vclose(lib.Rotate().solve_instance(p, 90, (0, 0, 0), (0, 0, 1)).Point, V(0, 1, 0)))
        self.assertTrue(vclose(lib.Mirror().solve_instance(p, (0, 0, 0), (1, 0, 0)).Point, V(-1, 0, 0)))
        box = Part.makeBox(1, 1, 1)
        self.assertAlmostEqual(lib.Scale().solve_instance(box, 2.0, (0, 0, 0)).Volume, 8.0, places=6)
        self.assertAlmostEqual(box.Volume, 1.0)  # the input is not modified
        copies = lib.LinearArray().solve_instance(box, (10, 0, 0), 3)
        self.assertEqual([round(c.BoundBox.XMin, 6) for c in copies], [0, 10, 20])


class Booleans(unittest.TestCase):
    def test_difference_and_intersection(self):
        a = Part.makeBox(10, 10, 10)
        b = Part.makeBox(5, 5, 5, V(5, 5, 5))
        self.assertAlmostEqual(lib.Difference().solve_instance(a, [b]).Volume, 875.0, places=4)
        self.assertAlmostEqual(lib.Intersection().solve_instance(a, b).Volume, 125.0, places=4)
        with self.assertRaises(ValueError):
            lib.Intersection().solve_instance(a, Part.makeBox(1, 1, 1, V(50, 0, 0)))


class Demos(unittest.TestCase):
    def build(self, builder):
        scene = FakeScene()
        parts = builder(scene)
        scene.graph.solve()
        bad = {c.nickname: c.messages for c in scene.graph.components if c.state != "ok"}
        self.assertEqual(bad, {})
        return parts

    def test_attractor_grid(self):
        c = self.build(demo.build_attractor)
        grid = c["grid"].outputs[0].data
        self.assertEqual(grid.branch_count, 10)
        self.assertEqual(len(grid), 100)
        radii = list(c["remap"].outputs[0].data)
        self.assertAlmostEqual(min(radii), c["rmin"].value)
        self.assertAlmostEqual(max(radii), c["rmax"].value)
        # The smallest circle sits on the grid point nearest the attractor.
        attractor = V(c["ax"].value, c["ay"].value, 0)
        nearest = min(grid, key=lambda p: (p.Point - attractor).Length)
        circles = list(c["circle"].outputs[0].data)
        smallest = min(circles, key=lambda e: e.Curve.Radius)
        self.assertTrue(vclose(smallest.Curve.Center, nearest.Point))
        tubes = list(c["extrude"].outputs[0].data)
        self.assertEqual(len(tubes), 100)
        self.assertAlmostEqual(max(t.BoundBox.ZLength for t in tubes), c["rmax"].value * c["height"].value)

    def test_voronoi_screen_volume_is_plate_minus_holes(self):
        from katydid import showcase
        c = self.build(showcase.build_voronoi)
        cells = list(c["voronoi"].outputs[0].data)
        self.assertEqual(len(cells), int(c["cells"].value))
        holes = list(c["surface"].outputs[0].data)
        t = c["thick"].value
        plate = (120 + 6) * (70 + 6) * t
        screen = list(c["stand"].outputs[0].data)[0]
        self.assertTrue(screen.isValid())
        self.assertAlmostEqual(screen.Volume, plate - t * sum(h.Area for h in holes), delta=1e-6 * plate)
        # the attractor makes holes near it smaller: the smallest hole is the nearest cell
        a = c["attractor"].outputs[0].data[0].Point
        cents = [x.Point for x in c["area"].outputs[1].data]
        shares = [h.Area / cell_area for h, cell_area in zip(holes, c["area"].outputs[0].data)]
        nearest = min(range(len(cents)), key=lambda i: (cents[i] - a).Length)
        self.assertAlmostEqual(shares[nearest], c["small"].value ** 2, places=6)

    def test_twisted_tower(self):
        from katydid import showcase
        c = self.build(showcase.build_tower)
        floors = int(c["floors"].value)
        self.assertEqual(len(list(c["slabs"].outputs[0].data)), floors)
        polys = list(c["poly"].outputs[0].data)
        first, last = polys[0].Vertexes[0].Point, polys[-1].Vertexes[0].Point
        turned = math.degrees(math.atan2(last.y, last.x) - math.atan2(first.y, first.x)) % 360
        self.assertAlmostEqual(turned, (floors - 1) * c["twist"].value, places=6)
        self.assertTrue(list(c["facade"].outputs[0].data)[0].isValid())

    def test_waffle_ribs(self):
        from katydid import showcase
        c = self.build(showcase.build_waffle)
        ribs = int(c["ribs"].value)
        x_ribs, y_ribs = list(c["x_ribs"].outputs[0].data), list(c["y_ribs"].outputs[0].data)
        self.assertEqual((len(x_ribs), len(y_ribs)), (ribs, ribs))
        self.assertTrue(all(r.isValid() and r.Volume > 0 for r in x_ribs + y_ribs))
        for r in x_ribs:
            self.assertAlmostEqual(r.BoundBox.XLength, c["thick"].value, places=6)
        self.assertTrue(list(c["dome"].outputs[0].data)[0].isValid())

    def test_wave_surface_and_contours(self):
        from katydid import showcase
        c = self.build(showcase.build_wave)
        surface = list(c["surface"].outputs[0].data)[0]
        self.assertTrue(surface.isValid())
        levels = c["contours"].outputs[0].data
        self.assertEqual(levels.branch_count, int(c["levels"].value) + 1)
        self.assertGreater(len(levels), int(c["levels"].value) // 2)
        z = [w.BoundBox.ZMin for w in levels]
        self.assertTrue(all(abs(w.BoundBox.ZMax - w.BoundBox.ZMin) < 1e-6 for w in levels))  # flat
        self.assertGreater(max(z) - min(z), 0)
        # mesh-traced contours lie on the exact surface within the stated tolerance
        tol = surface.BoundBox.DiagonalLength * lib.Contour.TOLERANCE
        pts = [v.Point for w in levels for v in w.Vertexes][::7]
        worst = max(surface.distToShape(Part.Vertex(p))[0] for p in pts)
        self.assertLess(worst, 2 * tol)
        # and match the exact cut: same number of curves on a middle level
        mid = levels.branches()[len(levels.branches()) // 2]
        level_z = mid[1][0].BoundBox.ZMin
        self.assertEqual(len(mid[1]), len(surface.slice(V(0, 0, 1), level_z)))

    def test_surface_from_points_passes_through_its_grid(self):
        pts = [V(x, y, (x * y) / 50.0) for y in range(0, 40, 10) for x in range(0, 50, 10)]
        srf = lib.SurfaceFromPoints().solve_instance(pts, 5)
        self.assertTrue(srf.isValid())
        self.assertLess(max(srf.distToShape(Part.Vertex(p))[0] for p in pts), 1e-6)
        with self.assertRaises(ValueError):
            lib.SurfaceFromPoints().solve_instance(pts, 3)

    def test_tree_and_box_demos_still_solve(self):
        t = self.build(demo.build_tree)
        lofts = list(t["loft"].outputs[0].data)
        self.assertEqual(len(lofts), 1)
        vase = lib.CapHoles().solve_instance(lofts[0])  # the open loft closes into a solid
        self.assertTrue(vase.isValid() and vase.Volume > 0)
        b = self.build(demo.build)
        self.assertEqual(len(list(b["move"].outputs[0].data)), 4)


def main():
    out = os.environ.get("KATYDID_OUT", _HERE)
    res = {"checks": {}}
    try:
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        names = [t.id().split(".", 1)[1] for t in _iter(suite)]  # run() drops the tests
        result = unittest.TestResult()
        suite.run(result)
        failed = {t.id().split(".", 1)[1]: msg for t, msg in result.failures + result.errors}
        for name in names:
            res["checks"][name] = {"ok": name not in failed, "detail": failed.get(name)}
    except Exception:
        res["exception"] = traceback.format_exc()
    res["passed"] = sum(c["ok"] for c in res["checks"].values())
    res["total"] = len(res["checks"])
    with open(os.path.join(out, "results_geometry.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)


def _iter(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _iter(t)
        else:
            yield t


main()
os._exit(0)
