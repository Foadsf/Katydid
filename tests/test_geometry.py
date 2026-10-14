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

    def test_pipe_along_an_s_curve_does_not_twist(self):
        # A rail that changes the way it bends: the Frenet frame flips at each
        # inflection, and a Frenet sweep came out 2.4x too big.
        wave = lib.Interpolate().solve_instance(
            [V(6 * j, 0, 1.1 * math.cos(math.pi * j)) for j in range(14)], False)
        pipe = lib.Pipe().solve_instance(wave, 1.0)
        self.assertTrue(pipe.isValid())
        self.assertAlmostEqual(pipe.Volume, math.pi * wave.Length, delta=0.01 * pipe.Volume)


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

    def test_phyllotaxis_golden_angle_and_sqrt_radius(self):
        from katydid import showcase
        c = self.build(showcase.build_phyllotaxis)
        seeds = list(c["seed"].outputs[0].data)
        self.assertEqual(len(seeds), int(c["seeds"].value))
        centres = [s.BoundBox.Center for s in seeds]
        step = math.degrees(math.atan2(centres[11].y, centres[11].x) - math.atan2(centres[10].y, centres[10].x)) % 360
        self.assertAlmostEqual(step, c["angle"].value % 360, places=6)
        r100 = math.hypot(centres[100].x, centres[100].y)
        self.assertAlmostEqual(r100, c["spacing"].value * 10, places=6)

    def test_hyperboloid_struts_rings_and_twist(self):
        from katydid import showcase
        c = self.build(showcase.build_hyperboloid)
        n, k = int(c["struts"].value), int(c["twist"].value)
        lines = list(c["struts_l"].outputs[0].data)
        self.assertEqual((len(lines), len(list(c["pipes_r"].outputs[0].data))), (n, n))
        a, b = lines[0].Vertexes[0].Point, lines[0].Vertexes[-1].Point
        self.assertAlmostEqual(math.hypot(a.x, a.y), c["base"].value, places=6)
        self.assertAlmostEqual(math.hypot(b.x, b.y), c["top"].value, places=6)
        turn = math.degrees(math.atan2(b.y, b.x) - math.atan2(a.y, a.x)) % 360
        self.assertAlmostEqual(turn, 360.0 * k / n, places=6)
        rings = c["ring"].outputs[0].data
        self.assertEqual(rings.branch_count, int(c["rings"].value) + 2)
        # every ring is a horizontal circle: its points share one radius and one height
        for _, pts in c["eval"].outputs[0].data.branches():
            radii = [math.hypot(p.Point.x, p.Point.y) for p in pts]
            self.assertLess(max(radii) - min(radii), 1e-6)
            self.assertLess(max(p.Point.z for p in pts) - min(p.Point.z for p in pts), 1e-6)
        self.assertTrue(all(p.isValid() for p in c["ring_pipes"].outputs[0].data))

    def test_spiral_staircase(self):
        from katydid import showcase
        c = self.build(showcase.build_staircase)
        steps = int(c["steps"].value)
        treads = list(c["stair"].outputs[0].data)
        self.assertEqual(len(treads), steps)
        self.assertAlmostEqual(treads[-1].BoundBox.ZMin, (steps - 1) * c["rise"].value, places=6)  # Box sits on z
        heads = [v.Point for v in c["head"].outputs[0].data]
        rail = list(c["rail"].outputs[0].data)[0]
        self.assertLess(max(rail.distToShape(Part.Vertex(p))[0] for p in heads), 1e-6)
        column = list(c["column"].outputs[0].data)[0]
        self.assertAlmostEqual(column.BoundBox.ZMax, max(p.z for p in heads), places=6)

    def test_voronoi_city_blocks(self):
        from katydid import showcase
        c = self.build(showcase.build_city)
        blocks = list(c["blocks"].outputs[0].data)
        self.assertEqual(len(blocks), int(c["plots"].value))
        heights = list(c["h"].outputs[0].data)
        floors = list(c["floor"].outputs[0].data)
        for blk, h, fl in zip(blocks, heights, floors):
            self.assertAlmostEqual(blk.Volume, fl.Area * h, delta=1e-6 * blk.Volume)
        ground = list(c["ground"].outputs[0].data)[0].BoundBox
        for b in (blk.BoundBox for blk in blocks):   # every block stands on the ground plate
            self.assertTrue(ground.XMin <= b.XMin and b.XMax <= ground.XMax
                            and ground.YMin <= b.YMin and b.YMax <= ground.YMax)
            self.assertAlmostEqual(b.ZMin, ground.ZMax, places=6)

    def test_woven_threads_alternate_and_never_touch(self):
        from katydid import showcase
        c = self.build(showcase.build_weave)
        n = int(c["threads"].value)
        warp, weft = list(c["warp"].outputs[0].data), list(c["weft"].outputs[0].data)
        self.assertEqual((len(warp), len(weft)), (n, n))
        # corners and edges too: free thread ends once dived into the crossing threads
        for i, j in ((0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1), (n - 1, 2), (3, 4)):
            self.assertGreater(warp[i].distToShape(weft[j])[0], 0.05, (i, j))
        # over, under, over: neighbouring crossings on one warp thread swap sides
        pts = list(c["warp_pts"].outputs[0].data.branches())[2][1]
        signs = [p.Point.z > 0 for p in pts]
        self.assertTrue(all(a != b for a, b in zip(signs, signs[1:])))

    def test_torus_knot(self):
        from katydid import showcase
        c = self.build(showcase.build_knot)
        curve = list(c["curve"].outputs[0].data)[0]
        tube = list(c["tube"].outputs[0].data)[0]
        self.assertTrue(curve.isClosed() and tube.isValid())
        r = c["thick"].value
        self.assertAlmostEqual(tube.Volume, math.pi * r * r * curve.Length, delta=0.005 * tube.Volume)
        # it loops q times through the hole: z = r sin(q t) has q peaks
        # (not zero crossings: with 240 points z lands exactly on 0)
        z = [v.Point.z for v in c["pts"].outputs[0].data]
        peaks = sum(1 for i in range(len(z)) if z[i - 1] < z[i] >= z[(i + 1) % len(z)])
        self.assertEqual(peaks, int(c["q"].value))

    def test_pipe_along_a_closed_3d_curve_is_valid(self):
        # A closed rail that is not flat: one sweep did not close on itself (invalid).
        pts = [V((30 + 12 * math.cos(3 * t)) * math.cos(2 * t), (30 + 12 * math.cos(3 * t)) * math.sin(2 * t),
                 12 * math.sin(3 * t)) for t in [2 * math.pi * k / 120 for k in range(120)]]
        rail = lib.Interpolate().solve_instance(pts, True)
        tube = lib.Pipe().solve_instance(rail, 2.0)
        self.assertTrue(tube.isValid())
        self.assertAlmostEqual(tube.Volume, math.pi * 4 * rail.Length, delta=0.005 * tube.Volume)

    def test_boolean_never_passes_on_a_broken_solid_silently(self):
        # The NX session's tube wall: two Pipes on a circle, cut by 72 short cylinders
        # standing on the outer surface, 3 mm deep, several on the tube's seams.
        # OpenCascade returned -10 mm^3 and an invalid solid with no error.
        rail = lib.Circle().solve_instance(40.0, 0.0)
        tube, inner = lib.Pipe().solve_instance(rail, 9.0), lib.Pipe().solve_instance(rail, 7.5)
        wall = lib.Difference().solve_instance(tube, [inner])
        # The NX cutters themselves (tests/data): a regular grid of similar cylinders
        # gave a valid cut, so the fixture is what reproduces the failure.
        here = os.path.dirname(os.path.abspath(__file__))
        cutters = Part.read(os.path.join(here, "data", "tube_cutters.brep")).Solids
        expected = wall.Volume - sum(wall.common(t).Volume for t in cutters)
        diff = lib.Difference()
        result = diff.solve_instance(wall, cutters)
        good = result.isValid() and abs(result.Volume - expected) < 1e-3 * expected
        self.assertTrue(good or diff.state == "warning", (round(result.Volume, 1), round(expected, 1),
                                                          result.isValid(), diff.state))

    def test_twisted_lobed_ring(self):
        from katydid import showcase
        c = self.build(showcase.build_ring)
        ring = list(c["ring"].outputs[0].data)[0]
        self.assertTrue(ring.isValid())
        self.assertTrue(ring.isClosed())   # a closed loft of closed sections: no free edges
        # each section's distance from the ring's core circle swings between a(1 - d) and a(1 + d)
        a, d, R = c["a"].value, c["depth"].value, c["R"].value
        for _, pts in list(c["pts"].outputs[0].data.branches())[:3]:
            dist = [math.hypot(math.hypot(p.Point.x, p.Point.y) - R, p.Point.z) for p in pts]
            self.assertAlmostEqual(max(dist), a * (1 + d), delta=0.02 * a)
            self.assertAlmostEqual(min(dist), a * (1 - d), delta=0.02 * a)

    def test_frame_tunnel(self):
        from katydid import showcase
        c = self.build(showcase.build_frames)
        n = int(c["frames"].value)
        frames = list(c["tunnel"].outputs[0].data)
        self.assertEqual(len(frames), n)
        base = list(c["frame"].outputs[0].data)[0].Volume
        mid = n // 2
        size = 1 + c["swell"].value * math.sin(math.pi * mid / n)
        self.assertAlmostEqual(frames[mid].Volume, base * size ** 3, delta=1e-6 * base)
        self.assertAlmostEqual(frames[mid].BoundBox.Center.y, mid * c["spacing"].value, places=6)

    def test_hypar_members_lie_on_the_membrane(self):
        from katydid import showcase
        c = self.build(showcase.build_hypar)
        m = int(c["members"].value)
        self.assertEqual(len(list(c["rot1"].outputs[0].data)), 4 * (m + 1))
        membrane = list(c["membrane"].outputs[0].data)[0]
        # a hyperbolic paraboloid is doubly ruled: the second family, built between the
        # other pair of edges, lies on the ruled surface of the first
        for line in list(c["fam2"].outputs[0].data)[::4]:
            mid = line.valueAt((line.FirstParameter + line.LastParameter) / 2)
            self.assertLess(membrane.distToShape(Part.Vertex(mid))[0], 1e-6)

    def test_slatted_ceiling(self):
        from katydid import showcase
        c = self.build(showcase.build_slats)
        slats = list(c["slat"].outputs[0].data)
        self.assertEqual(len(slats), int(c["slats"].value))
        for s in slats:
            self.assertTrue(s.isValid() and s.Volume > 0)
            self.assertAlmostEqual(s.BoundBox.XLength, c["thick"].value, places=6)

    def test_contour_through_mesh_vertex_rows_is_one_curve(self):
        # The NX canopy: at whole-number offsets the plane ran through rows of mesh
        # vertices and the section came out as 3-10 pieces with extra loops
        # (115 mm of curve where the exact cut is 96 mm).
        prof = [V(0, 0, 0), V(16, 0, 22), V(12, 0, 44), V(30, 0, 62), V(58, 0, 70)]
        curve = lib.Interpolate().solve_instance([Part.Vertex(p) for p in prof], False)
        mirror = lib.Mirror().solve_instance(curve, (14, 45, 0), (0, 1, 0))
        mid = lib.EvaluateCurve().solve_instance(curve, 0.5)[0].Point
        middle = lib.Interpolate().solve_instance([V(14, 45, 0), V(mid.x, 45, mid.z), V(44, 45, 84)], False)
        surface = lib.Loft().solve_instance([curve, middle, mirror], False)
        contour = lib.Contour()
        for y in (25.0, 30.0, 45.0, 65.0):
            curves = contour.solve_instance(surface, (0, 1, 0), y)
            exact = surface.slice(V(0, 1, 0), y)
            self.assertEqual(len(curves), len(exact), y)
            self.assertAlmostEqual(curves[0].Length, exact[0].Length, delta=0.002 * exact[0].Length)

    def test_carved_monolith(self):
        from katydid import showcase
        c = self.build(showcase.build_monolith)
        carved = list(c["carved"].outputs[0].data)[0]
        block = list(c["block"].outputs[0].data)[0]
        spheres = list(c["voids_at"].outputs[0].data)
        self.assertTrue(carved.isValid())
        self.assertEqual(len(carved.Solids), 1)   # no loose shards at the default settings
        self.assertEqual(len(spheres), int(c["voids"].value))
        removed = block.common(spheres[0].multiFuse(spheres[1:])).Volume   # independent: fuse first
        self.assertAlmostEqual(carved.Volume, block.Volume - removed, delta=1e-3 * block.Volume)
        tight = carved.optimalBoundingBox()
        self.assertLessEqual(tight.XLength, c["w"].value + 1e-6)
        # the biggest void is the one nearest the attractor
        radii = list(c["remap"].outputs[0].data)
        dists = list(c["dist"].outputs[0].data)
        self.assertAlmostEqual(radii[dists.index(min(dists))], c["large"].value, places=9)

    def test_flange_and_its_tolerance_zones(self):
        from katydid import showcase
        c = self.build(showcase.build_flange)
        n, t, R = int(c["bolts"].value), c["t"].value, c["R"].value
        actual, pos, scale = c["actual"].value, c["pos"].value, c["scale"].value
        flange = list(c["flange"].outputs[0].data)[0]
        expected = math.pi * t * (R ** 2 - n * (actual / 2) ** 2 - 8.0 ** 2)
        self.assertTrue(flange.isValid())
        self.assertAlmostEqual(flange.Volume, expected, delta=1e-6 * expected)
        # total position tolerance = stated + bonus (actual - MMC) at MMC; zones drawn x scale
        zones = list(c["zones"].outputs[0].data)
        self.assertEqual(len(zones), n)
        r_zone = next(f.Surface.Radius for f in zones[0].Faces if hasattr(f.Surface, "Radius"))
        self.assertAlmostEqual(r_zone, (pos + actual - 9.0) * scale / 2, places=9)
        # gauge pins at the holes' virtual condition, MMC - tolerance
        pin = list(c["pins"].outputs[0].data)[0]
        r_pin = next(f.Surface.Radius for f in pin.Faces if hasattr(f.Surface, "Radius"))
        self.assertAlmostEqual(2 * r_pin, 9.0 - pos, places=9)

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
