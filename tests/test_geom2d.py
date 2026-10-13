# SPDX-License-Identifier: LGPL-2.1-or-later
"""Voronoi, Lloyd relaxation and polygons. Run: python tests/test_geom2d.py"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from katydid.geom2d import area, centroid, clip, populate, regular_polygon, voronoi_cells  # noqa: E402


def inside(poly, p, eps=1e-9):
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (x1 - x0) * (p[1] - y0) - (y1 - y0) * (p[0] - x0) < -eps:
            return False
    return True


class VoronoiTests(unittest.TestCase):
    def setUp(self):
        rng = random.Random(5)
        self.sites = [(rng.uniform(0, 100), rng.uniform(0, 60)) for _ in range(80)]
        self.cells = voronoi_cells(self.sites, 0, 0, 100, 60)

    def test_cells_tile_the_rectangle(self):
        self.assertAlmostEqual(sum(area(c) for c in self.cells), 6000.0, places=6)

    def test_each_site_lies_in_its_own_convex_ccw_cell(self):
        for site, cell in zip(self.sites, self.cells):
            self.assertGreater(area(cell), 0)          # counter-clockwise
            self.assertTrue(inside(cell, site))        # convex and contains its site

    def test_cell_points_are_nearest_to_their_site(self):
        rng = random.Random(9)
        for _ in range(300):
            p = (rng.uniform(0, 100), rng.uniform(0, 60))
            nearest = min(range(len(self.sites)), key=lambda i: math.dist(p, self.sites[i]))
            self.assertTrue(inside(self.cells[nearest], p, eps=1e-7))

    def test_two_sites_split_at_the_bisector(self):
        left, right = voronoi_cells([(2, 5), (8, 5)], 0, 0, 10, 10)
        self.assertAlmostEqual(area(left), 50.0)
        self.assertAlmostEqual(max(x for x, _ in left), 5.0)
        self.assertAlmostEqual(min(x for x, _ in right), 5.0)

    def test_duplicate_sites_do_not_break_the_tiling(self):
        cells = voronoi_cells([(2, 5), (2, 5), (8, 5)], 0, 0, 10, 10)
        self.assertEqual(cells[1], [])
        self.assertAlmostEqual(sum(area(c) for c in cells), 100.0)

    def test_bad_rectangle(self):
        with self.assertRaises(ValueError):
            voronoi_cells([(0, 0)], 0, 0, 0, 10)


class OtherTests(unittest.TestCase):
    def test_clip_half_plane(self):
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]
        self.assertAlmostEqual(area(clip(square, 1, 0, 1)), 2.0)   # x <= 1
        self.assertEqual(clip(square, 1, 0, -1), [])                # x <= -1: nothing

    def test_centroid_of_square_and_triangle(self):
        self.assertEqual(centroid([(0, 0), (2, 0), (2, 2), (0, 2)]), (1.0, 1.0))
        cx, cy = centroid([(0, 0), (3, 0), (0, 3)])
        self.assertAlmostEqual(cx, 1.0)
        self.assertAlmostEqual(cy, 1.0)

    def test_relaxation_spreads_points_evenly(self):
        def spread(pts):
            areas = [area(c) for c in voronoi_cells(pts, 0, 0, 100, 100)]
            m = sum(areas) / len(areas)
            return math.sqrt(sum((a - m) ** 2 for a in areas) / len(areas)) / m
        raw = populate(60, 0, 0, 100, 100, seed=3, relax=0)
        once = populate(60, 0, 0, 100, 100, seed=3, relax=1)
        relaxed = populate(60, 0, 0, 100, 100, seed=3, relax=4)
        # cell sizes get more even with every Lloyd step (measured: 0.68 -> 0.34 after 4)
        self.assertLess(spread(once), spread(raw))
        self.assertLess(spread(relaxed), spread(once))
        self.assertLess(spread(relaxed), 0.6 * spread(raw))
        self.assertEqual(populate(5, 0, 0, 1, 1, seed=2), populate(5, 0, 0, 1, 1, seed=2))
        self.assertTrue(all(0 <= x <= 100 and 0 <= y <= 100 for x, y in relaxed))

    def test_regular_polygon(self):
        hexagon = regular_polygon(10, 6)
        self.assertEqual(len(hexagon), 6)
        self.assertAlmostEqual(area(hexagon), 3 * math.sqrt(3) / 2 * 100)
        with self.assertRaises(ValueError):
            regular_polygon(10, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
