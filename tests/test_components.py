# SPDX-License-Identifier: LGPL-2.1-or-later
"""Headless tests for the non-geometry components and the formula evaluator.
Run: python tests/test_components.py"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from katydid import components as lib  # noqa: E402
from katydid.engine import Component, Graph  # noqa: E402
from katydid.expr import ExpressionError, evaluate  # noqa: E402
from katydid.tree import Tree  # noqa: E402


class Source(Component):
    nickname = "Src"

    def __init__(self, tree):
        self.tree = tree
        super().__init__()

    def setup(self):
        self.add_output("Out", "O")

    def compute(self):
        self.outputs[0].data = Tree(self.tree)


def solve_with(comp, *trees):
    """Wire one Source per tree into comp's first inputs, solve, return outputs."""
    g = Graph()
    g.add(comp)
    for i, tree in enumerate(trees):
        src = g.add(Source(tree))
        g.connect(src.outputs[0], comp.inputs[i])
    g.solve()
    return comp


class Formulas(unittest.TestCase):
    def test_arithmetic_functions_and_variables(self):
        self.assertAlmostEqual(evaluate("x*2 + sin(y)", x=3, y=math.pi / 2), 7.0)
        self.assertAlmostEqual(evaluate("sqrt(x**2 + y**2)", x=3, y=4), 5.0)
        self.assertAlmostEqual(evaluate("-pi % 3"), -math.pi % 3)
        self.assertEqual(evaluate("max(x, y, 2)", x=1, y=0), 2.0)

    def test_anything_beyond_arithmetic_is_refused(self):
        attacks = ["__import__('os').system('calc')", "x.__class__", "().__class__",
                   "[c for c in ()]", "lambda: 1", "open('f')", "'text'", "x if y else z",
                   "eval('1')", "getattr(x, 'real')", "sin.__self__", "True", "x == 1"]
        for text in attacks:
            with self.subTest(text=text), self.assertRaises(ExpressionError):
                evaluate(text, x=1, y=1, z=1)

    def test_runaway_and_bad_maths_are_errors_not_hangs(self):
        for text in ("10**10**10", "1/0", "sqrt(-1)", "", "x" * 600):
            with self.subTest(text=text[:20]), self.assertRaises(ExpressionError):
                evaluate(text, x=1)

    def test_expression_component_marks_error(self):
        comp = lib.Expression()
        comp.inputs[0].default = "__import__('os')"
        g = Graph()
        g.add(comp)
        g.solve()
        self.assertEqual(comp.state, "error")
        self.assertTrue(any("Not allowed" in m for m in comp.messages), comp.messages)


class MathsAndLists(unittest.TestCase):
    def test_range_includes_both_ends(self):
        self.assertEqual(lib.Range().solve_instance(0.0, 1.0, 4), [0.0, 0.25, 0.5, 0.75, 1.0])

    def test_remap(self):
        self.assertEqual(lib.Remap().solve_instance(5.0, 0.0, 10.0, 100.0, 200.0), 150.0)
        with self.assertRaises(ValueError):
            lib.Remap().solve_instance(5.0, 1.0, 1.0, 0.0, 1.0)

    def test_bounds_per_branch(self):
        comp = solve_with(lib.Bounds(), {(0,): [3.0, -1.0, 7.0], (1,): [2.0]})
        self.assertEqual(comp.outputs[0].data.branches(), [((0,), [-1.0]), ((1,), [2.0])])
        self.assertEqual(list(comp.outputs[1].data), [7.0, 2.0])

    def test_list_item_wraps_by_default(self):
        comp = lib.ListItem()
        self.assertEqual(comp.solve_instance(["a", "b", "c"], 4, True), "b")
        self.assertEqual(comp.solve_instance(["a", "b", "c"], -1, False), "c")
        with self.assertRaises(IndexError):
            comp.solve_instance(["a"], 3, False)

    def test_cull_pattern_repeats(self):
        comp = solve_with(lib.CullPattern(), {(0,): list("abcdef")}, {(0,): [True, False, False]})
        self.assertEqual(list(comp.outputs[0].data), ["a", "d"])

    def test_shift_list(self):
        self.assertEqual(lib.ShiftList().solve_instance([1, 2, 3, 4], 1, True), [2, 3, 4, 1])
        self.assertEqual(lib.ShiftList().solve_instance([1, 2, 3, 4], -1, True), [4, 1, 2, 3])
        self.assertEqual(lib.ShiftList().solve_instance([1, 2, 3, 4], 2, False), [3, 4])

    def test_list_length_of_each_branch(self):
        comp = solve_with(lib.ListLength(), {(0,): [1, 2, 3], (1,): [9]})
        self.assertEqual(list(comp.outputs[0].data), [3.0, 1.0])

    def test_every_component_constructs_and_has_unique_names(self):
        names = [cls.__name__ for cls in lib.REGISTRY]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreaterEqual(len(names), 40)
        for cls in lib.REGISTRY:
            comp = cls()
            self.assertIn(cls.category, lib.CATEGORIES, cls.__name__)
            self.assertTrue(comp.outputs or cls is lib.Panel, cls.__name__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
