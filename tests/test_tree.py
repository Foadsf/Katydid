# SPDX-License-Identifier: LGPL-2.1-or-later
"""Data tree tests: the tree operations and branch matching. Run: python tests/test_tree.py

These encode our reading of Grasshopper's rules (engine.py docstring); they are
not checked against Grasshopper itself.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from katydid import document  # noqa: E402
from katydid.components import NumberSlider, Panel, Series  # noqa: E402
from katydid.engine import ITEM, LIST, TREE, Component, Graph  # noqa: E402
from katydid.tree import Tree, format_path  # noqa: E402


def paths(tree):
    return [format_path(p) for p in tree.paths()]


class Divide(Component):
    """Stand-in for Divide Curve: one 'curve' (a number) in, a list out."""
    nickname = "Div"

    def setup(self):
        self.add_input("Curve", "C")
        self.add_input("Count", "N", default=3)
        self.add_output("Points", "P", access=LIST)

    def solve_instance(self, curve, n):
        return [f"{curve}.{i}" for i in range(int(n))]


class Join(Component):
    """List access: one output item per branch."""
    nickname = "Join"

    def setup(self):
        self.add_input("Items", "I", access=LIST)
        self.add_output("Joined", "J")

    def solve_instance(self, items):
        return "+".join(str(i) for i in items)


class Pair(Component):
    nickname = "Pair"

    def setup(self):
        self.add_input("A", "A")
        self.add_input("B", "B")
        self.add_output("R", "R")

    def solve_instance(self, a, b):
        return f"{a}{b}"


class Source(Component):
    """Emits a fixed tree."""
    nickname = "Src"

    def __init__(self, tree):
        self.tree = tree
        super().__init__()

    def setup(self):
        self.add_output("Out", "O")

    def compute(self):
        self.outputs[0].data = Tree(self.tree)


class TreeOps(unittest.TestCase):
    def test_flatten_graft_simplify_reverse(self):
        t = Tree({(0, 1): ["c"], (0, 0): ["a", "b"]})
        self.assertEqual(paths(t), ["{0;0}", "{0;1}"])          # paths are sorted
        self.assertEqual(list(t), ["a", "b", "c"])              # items in path order
        self.assertEqual(t.flatten().branches(), [((0,), ["a", "b", "c"])])
        self.assertEqual(paths(t.graft()), ["{0;0;0}", "{0;0;1}", "{0;1;0}"])
        self.assertEqual(paths(t.simplify()), ["{0}", "{1}"])
        self.assertEqual(t.reverse().branches()[0][1], ["b", "a"])

    def test_simplify_keeps_a_valid_path_and_drops_empty_branches(self):
        self.assertEqual(paths(Tree({(0, 0, 0): [1]}).simplify()), ["{0}"])
        t = Tree({(0, 0, 0): [1], (0, 0, 1): [2], (0, 0, 2): [], (0, 1, 0): [3]})
        self.assertEqual(paths(t.simplify()), ["{0;0}", "{0;1}", "{1;0}"])

    def test_merge_concatenates_same_paths(self):
        a = Tree({(0,): [1]})
        a.merge(Tree({(0,): [2], (1,): [3]}))
        self.assertEqual(a.branches(), [((0,), [1, 2]), ((1,), [3])])


class Matching(unittest.TestCase):
    def setUp(self):
        self.g = Graph()

    def wire(self, a, b, ai=0, bi=0):
        self.assertTrue(self.g.connect(a.outputs[ai], b.inputs[bi]))

    def test_list_output_gets_a_branch_per_iteration(self):
        src = self.g.add(Source({(0,): ["x", "y", "z"]}))
        div = self.g.add(Divide())
        self.wire(src, div)
        self.g.solve()
        out = div.outputs[0].data
        self.assertEqual(paths(out), ["{0;0}", "{0;1}", "{0;2}"])
        self.assertEqual(out.branches()[1][1], ["y.0", "y.1", "y.2"])

    def test_list_access_solves_once_per_branch(self):
        src = self.g.add(Source({(0,): ["x", "y"]}))
        div = self.g.add(Divide())
        join = self.g.add(Join())
        self.wire(src, div)
        self.wire(div, join)
        self.g.solve()
        self.assertEqual(join.outputs[0].data.branches(),
                         [((0, 0), ["x.0+x.1+x.2"]), ((0, 1), ["y.0+y.1+y.2"])])

    def test_flatten_on_an_input_joins_all_branches(self):
        src = self.g.add(Source({(0,): ["x", "y"]}))
        div = self.g.add(Divide())
        join = self.g.add(Join())
        self.wire(src, div)
        self.wire(div, join)
        join.inputs[0].set_modifier("flatten")
        self.g.solve()
        self.assertEqual(join.outputs[0].data.branches(), [((0,), ["x.0+x.1+x.2+y.0+y.1+y.2"])])

    def test_graft_on_an_output_and_simplify_on_an_input(self):
        src = self.g.add(Source({(0,): ["x", "y"]}))
        div = self.g.add(Divide())
        div.outputs[0].set_modifier("graft")
        self.wire(src, div)
        self.g.solve()
        self.assertEqual(div.outputs[0].data.branch_count, 6)
        join = self.g.add(Join())
        self.wire(div, join)
        join.inputs[0].set_modifier("simplify")
        self.g.solve()
        self.assertEqual(paths(join.outputs[0].data), ["{0;0}", "{0;1}", "{0;2}",
                                                       "{1;0}", "{1;1}", "{1;2}"])

    def test_fewer_branches_repeat_the_last_branch_and_paths_follow_the_bigger_tree(self):
        a = self.g.add(Source({(0,): ["a"], (1,): ["b"], (2,): ["c"]}))
        b = self.g.add(Source({(5,): ["1", "2"]}))
        pair = self.g.add(Pair())
        self.wire(a, pair, bi=0)
        self.wire(b, pair, bi=1)
        self.g.solve()
        self.assertEqual(pair.outputs[0].data.branches(),
                         [((0,), ["a1", "a2"]), ((1,), ["b1", "b2"]), ((2,), ["c1", "c2"])])

    def test_equal_branch_counts_take_paths_from_the_first_input(self):
        a = self.g.add(Source({(3,): ["a"]}))
        b = self.g.add(Source({(7,): ["b"]}))
        pair = self.g.add(Pair())
        self.wire(a, pair, bi=0)
        self.wire(b, pair, bi=1)
        self.g.solve()
        self.assertEqual(paths(pair.outputs[0].data), ["{3}"])

    def test_tree_access_sees_the_whole_tree(self):
        src = self.g.add(Source({(0, 1): [1.0], (0, 0): [2.0, 3.0]}))
        pan = self.g.add(Panel())
        self.assertEqual(pan.inputs[0].access, TREE)
        self.wire(src, pan)
        self.g.solve()
        self.assertEqual(pan.rows, [("path", "{0;0}"), ("item", 0, "2"), ("item", 1, "3"),
                                    ("path", "{0;1}"), ("item", 0, "1")])

    def test_series_output_is_a_list_branch(self):
        s = self.g.add(NumberSlider(4, 1, 10, 0))
        ser = self.g.add(Series())
        self.wire(s, ser, bi=2)
        self.g.solve()
        self.assertEqual(ser.outputs[0].data.branches(), [((0, 0), [0.0, 1.0, 2.0, 3.0])])
        self.assertEqual(ser.inputs[2].access, ITEM)

    def test_modifiers_survive_save_and_load(self):
        src = self.g.add(Series())
        pan = self.g.add(Panel())
        self.wire(src, pan)
        pan.inputs[0].set_modifier("graft")
        src.outputs[0].set_reverse(True)
        g2 = Graph()
        _, warnings = document.build(g2, document.dumps(self.g))
        self.assertEqual(warnings, [])
        self.assertEqual((g2.components[1].inputs[0].modifier, g2.components[0].outputs[0].reverse),
                         ("graft", True))
        g2.solve()
        self.assertEqual(g2.components[1].text_lines, [f"{float(i):g}" for i in range(9, -1, -1)])
        self.assertEqual(g2.components[1].rows[0], ("path", "{0;0;0}"))
        self.assertEqual(len(g2.components[1].rows), 20)  # 10 one-item branches


if __name__ == "__main__":
    unittest.main(verbosity=2)
