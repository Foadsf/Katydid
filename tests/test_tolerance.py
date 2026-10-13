# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tolerance analysis against the textbooks' worked numbers. Run: python tests/test_tolerance.py

Fixtures (numbers only, from the worked examples):
  Fischer, Mechanical Tolerance Stackup and Analysis, 2nd ed. (2011):
    Examples 4.1-4.4 (equal-bilateral conversion), Figures 8.9-8.14
    (statistical chain), Figure 8.15 (report form), Example 8.1 (pin groove).
  Cogorno, Geometric Dimensioning and Tolerancing for Mechanical Design,
    3rd ed. (2020), Table 3-2 (bonus tolerance).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from katydid import components as lib  # noqa: E402
from katydid.engine import Graph  # noqa: E402
from katydid.tolerance import (Dim, bonus, boundaries, mean_std, monte_carlo, outside,  # noqa: E402
                               position_to_plus_minus, stack)


def sym(nominal, tol, sign=1, dist="normal"):
    return Dim(nominal, tol, -tol, sign, dist)


FIG_8_9 = [sym(56.5, 1.5), sym(11, 1, -1), sym(17.5, 0.5, -1), sym(16.5, 0.5, -1)]
FIG_8_15_TOLS = [0.5, 0.29, 0, 0.2, 0, 0, 0.665, 0.225, 0.1, 0, 0, 0.5, 0.15]


class EqualBilateral(unittest.TestCase):
    def test_fischer_examples_4_1_to_4_4(self):
        cases = [((10.0, 0.0, -0.45), (9.775, 0.225)),    # limits 10.00 / 9.55
                 ((8.50, 0.25, -0.10), (8.575, 0.175)),
                 ((8.50, 0.25, 0.0), (8.625, 0.125)),
                 ((8.50, 0.0, -0.25), (8.375, 0.125))]
        for (n, up, lo), (mean, tol) in cases:
            d = Dim(n, up, lo)
            self.assertAlmostEqual(d.mean, mean)
            self.assertAlmostEqual(d.tol, tol)


class FischerStackups(unittest.TestCase):
    def test_figures_8_9_to_8_14(self):
        r = stack(FIG_8_9, 1.5)
        self.assertAlmostEqual(r.nominal, 11.5)
        self.assertAlmostEqual(r.worst_case, 3.5)                       # Fig 8.11: ±3.5
        self.assertEqual(round(r.rss, 2), 1.94)                         # Fig 8.12: ±1.94
        self.assertEqual([round(v, 2) for v in r.limits("rss")], [9.56, 13.44])   # Fig 8.13
        # Fig 8.14 multiplies the ROUNDED 1.94 by 1.5 (= ±2.91, limits 8.59 / 14.41).
        # Exactly it is 2.9047; the book's figure is within its own rounding of RSS.
        self.assertLessEqual(abs(r.adjusted - 2.91), 1.5 * 0.005)
        self.assertLessEqual(abs(r.limits("adjusted")[0] - 8.59), 1.5 * 0.005 + 0.005)
        self.assertLessEqual(abs(r.limits("adjusted")[1] - 14.41), 1.5 * 0.005 + 0.005)

    def test_figure_8_15_report(self):
        dims = [Dim(0.0, t, -t) for t in FIG_8_15_TOLS]
        dims[2] = sym(8.5, 0.0)          # line 3: +8.5
        dims[10] = sym(6.0, 0.0, -1)     # line 11: -6.0
        r = stack(dims, 1.5)
        self.assertAlmostEqual(r.nominal, 2.5)
        self.assertEqual(round(r.worst_case, 4), 2.6300)
        self.assertEqual([round(v, 4) for v in r.limits("worst")], [-0.13, 5.13])
        self.assertEqual(round(r.rss, 4), 1.0721)
        self.assertEqual([round(v, 4) for v in r.limits("rss")], [1.4279, 3.5721])
        self.assertEqual(round(r.adjusted, 4), 1.6082)
        self.assertEqual([round(v, 4) for v in r.limits("adjusted")], [0.8918, 4.1082])
        shares = [round(100 * s) for s in r.contributions]
        self.assertEqual(shares, [19, 11, 0, 8, 0, 0, 25, 9, 4, 0, 0, 19, 6])  # "Percent Contrib"

    def test_example_8_1_pin_groove(self):
        r = stack([sym(45, 0.5), sym(30, 0.2, -1), sym(13.2, 0.5, -1)], 1.5)
        self.assertAlmostEqual(r.nominal, 1.8)
        self.assertAlmostEqual(r.worst_case, 1.2)
        self.assertEqual([round(v, 1) for v in r.limits("worst")], [0.6, 3.0])
        # The book prints RSS ±0.74: sqrt(0.54) = 0.7348 rounded UP, the conservative
        # direction, in this hand-worked example (its spreadsheet report, Fig 8.15,
        # rounds to nearest instead: 1.07213 -> 1.0721).
        self.assertAlmostEqual(r.rss, math.sqrt(0.54))
        self.assertEqual(math.ceil(r.rss * 100) / 100, 0.74)
        self.assertEqual(round(r.adjusted, 1), 1.1)
        self.assertEqual([round(v, 1) for v in r.limits("adjusted")], [0.7, 2.9])

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            Dim(10, -0.2, 0.1)
        with self.assertRaises(ValueError):
            Dim(10, 0.1, -0.1, distribution="lognormal")
        with self.assertRaises(ValueError):
            stack([], 1.5)
        with self.assertRaises(ValueError):
            stack(FIG_8_9, 0.5)


class MonteCarloTests(unittest.TestCase):
    PATHS = (True, False)  # numpy and the pure-Python fallback

    def test_normal_spread_matches_rss_over_three(self):
        for path in self.PATHS:
            with self.subTest(numpy=path):
                values = monte_carlo(FIG_8_9, 40000, seed=7, use_numpy=path)
                m, s = mean_std(values)
                self.assertAlmostEqual(m, 11.5, delta=0.02)
                self.assertAlmostEqual(s, math.sqrt(3.75) / 3, delta=0.02 * math.sqrt(3.75) / 3)

    def test_uniform_and_triangular_spread_and_repeatability(self):
        for path in self.PATHS:
            for dist, var_factor in (("uniform", 3), ("triangular", 6)):  # var = t^2/3, t^2/6
                with self.subTest(numpy=path, dist=dist):
                    dims = [sym(d.nominal, d.tol, d.sign, dist) for d in FIG_8_9]
                    a = monte_carlo(dims, 40000, seed=3, use_numpy=path)
                    self.assertEqual(a[:5], monte_carlo(dims, 40000, seed=3, use_numpy=path)[:5])
                    expected = math.sqrt(sum(d.tol ** 2 for d in dims) / var_factor)
                    self.assertAlmostEqual(mean_std(a)[1], expected, delta=0.02 * expected)
                    self.assertEqual(outside(a, 11.5 - 3.5, 11.5 + 3.5), 0.0)  # never past worst case

    def test_out_of_spec_at_rss_limits_is_about_0_27_percent(self):
        for path in self.PATHS:
            with self.subTest(numpy=path):
                values = monte_carlo(FIG_8_9, 40000, seed=11, use_numpy=path)
                frac = outside(values, 11.5 - math.sqrt(3.75), 11.5 + math.sqrt(3.75))
                self.assertGreater(frac, 0.0015)   # 3-sigma two-sided: 0.27 %
                self.assertLess(frac, 0.0040)


class GDT(unittest.TestCase):
    def test_cogorno_table_3_2(self):
        hole = [(.505, .000, .005), (.506, .001, .006), (.507, .002, .007),
                (.508, .003, .008), (.509, .004, .009), (.510, .005, .010)]
        for actual, b, total in hole:
            got = bonus(actual, .505, .510, .005)
            self.assertAlmostEqual(got[0], b)
            self.assertAlmostEqual(got[1], total)
        pin = [(.510, .000, .005), (.507, .003, .008), (.505, .005, .010)]
        for actual, b, total in pin:
            got = bonus(actual, .510, .505, .005)
            self.assertAlmostEqual(got[0], b)
            self.assertAlmostEqual(got[1], total)
        self.assertEqual(bonus(.508, .505, .510, .005, "RFS"), (0.0, .005))
        # LMC modifier (Cogorno's definition; no printed table): the tolerance applies
        # at LMC and the bonus grows as the size departs from LMC toward MMC.
        self.assertEqual([round(v, 6) for v in bonus(.510, .505, .510, .005, "LMC")], [0.0, .005])
        self.assertEqual([round(v, 6) for v in bonus(.506, .505, .510, .005, "LMC")], [.004, .009])
        with self.assertRaises(ValueError):
            bonus(.520, .505, .510, .005)

    def test_virtual_and_resultant_condition_formulas(self):
        # Cogorno's formulas applied to the Table 3-2 features (values computed here).
        h = boundaries(.505, .510, .005, internal=True)
        self.assertAlmostEqual(h["virtual"], .500)    # MMC - tol
        self.assertAlmostEqual(h["resultant"], .520)  # LMC + tol + size tol
        p = boundaries(.510, .505, .005, internal=False)
        self.assertAlmostEqual(p["virtual"], .515)    # MMC + tol
        self.assertAlmostEqual(p["resultant"], .495)  # LMC - tol - size tol
        self.assertEqual((h["inner"], h["outer"]), (h["virtual"], h["resultant"]))
        self.assertEqual((p["inner"], p["outer"]), (p["resultant"], p["virtual"]))
        with self.assertRaises(ValueError):
            boundaries(.510, .505, .005, internal=True)

    def test_position_to_plus_minus(self):
        self.assertEqual(position_to_plus_minus(0.4, 0.3), (0.2, 0.15))


class Components(unittest.TestCase):
    def test_dimension_and_stackup_components_on_figure_8_9(self):
        g = Graph()
        stack_c = g.add(lib.StackUp())
        for d in FIG_8_9:
            dc = g.add(lib.Dimension())
            for p, v in zip(dc.inputs, (d.nominal, d.upper, d.lower, float(d.sign), "normal", "")):
                p.default = v
            g.connect(dc.outputs[0], stack_c.inputs[0])
        g.solve()
        out = [list(o.data)[0] if o.access == "item" else list(o.data) for o in stack_c.outputs]
        self.assertAlmostEqual(out[0], 11.5)
        self.assertAlmostEqual(out[1], 3.5)
        self.assertEqual(round(out[2], 2), 1.94)
        self.assertEqual((out[4], out[5]), (8.0, 15.0))
        self.assertTrue(any("Worst case" in line for line in out[8]))

    def test_stackup_demo_solves(self):
        from katydid import demo

        class FakeScene:
            def __init__(self):
                self.graph = Graph()

            def add_component(self, comp, pos, centre=False):
                self.graph.add(comp)

            def rebuild_wires(self):
                pass

            def request_solve(self):
                pass

        s = FakeScene()
        c = demo.build_stackup(s)
        s.graph.solve()
        bad = {x.nickname: x.messages for x in s.graph.components if x.state != "ok"}
        self.assertEqual(bad, {})
        self.assertEqual(round(list(c["stack"].outputs[2].data)[0], 2), 1.94)
        pct = list(c["mc"].outputs[2].data)[0]
        # limits 10..13 are ±1.5 = 2.32 sigma (sigma = RSS/3): ~2.0 % two-sided
        self.assertAlmostEqual(pct, 2.0, delta=0.6)
        self.assertEqual(len(list(c["mc"].outputs[3].data)), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
