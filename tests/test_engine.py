# SPDX-License-Identifier: LGPL-2.1-or-later
"""Headless engine tests. Run with any Python 3.9+:  python tests/test_engine.py"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from katydid.components import NumberSlider, Series  # noqa: E402
from katydid.engine import ERROR, OK, WARNING, Component, Graph  # noqa: E402


class Add(Component):
    nickname = "Add"
    calls = 0

    def setup(self):
        self.add_input("A", "A")
        self.add_input("B", "B", default=0.0)
        self.add_output("R", "R")

    def solve_instance(self, a, b):
        type(self).calls += 1
        return a + b


class Fail(Component):
    def setup(self):
        self.add_input("X", "X")
        self.add_output("Y", "Y")

    def solve_instance(self, x):
        if x < 0:
            raise ValueError("negative")
        return x


class EngineTests(unittest.TestCase):
    def setUp(self):
        Add.calls = 0
        self.g = Graph()

    def test_wire_carries_data_and_default_fills_unwired_input(self):
        s = self.g.add(NumberSlider(3, 0, 10))
        a = self.g.add(Add())
        self.assertTrue(self.g.connect(s.outputs[0], a.inputs[0]))
        self.g.solve()
        self.assertEqual(list(a.outputs[0].data), [3.0])
        self.assertEqual(a.state, OK)

    def test_missing_input_is_a_warning_not_an_error(self):
        a = self.g.add(Add())
        self.g.solve()
        self.assertEqual(a.state, WARNING)
        self.assertEqual(list(a.outputs[0].data), [])

    def test_exception_marks_error_and_other_iterations_survive(self):
        ser = self.g.add(Series())
        ser.inputs[0].default = -1.0  # -1, 0, 1
        ser.inputs[2].default = 3.0
        f = self.g.add(Fail())
        self.g.connect(ser.outputs[0], f.inputs[0])
        self.g.solve()
        self.assertEqual(f.state, ERROR)
        self.assertEqual(list(f.outputs[0].data), [0.0, 1.0])
        self.assertIn("negative", f.messages)

    def test_longest_list_matching_repeats_last_item(self):
        ser = self.g.add(Series())  # 0..9
        one = self.g.add(NumberSlider(100, 0, 1000))
        a = self.g.add(Add())
        self.g.connect(ser.outputs[0], a.inputs[0])
        self.g.connect(one.outputs[0], a.inputs[1])
        self.g.solve()
        self.assertEqual(list(a.outputs[0].data), [100.0 + i for i in range(10)])

    def test_cycles_and_wrong_direction_are_refused(self):
        a, b = self.g.add(Add()), self.g.add(Add())
        self.assertTrue(self.g.connect(a.outputs[0], b.inputs[0]))
        self.assertFalse(self.g.connect(b.outputs[0], a.inputs[0]))   # loop
        self.assertFalse(self.g.connect(a.outputs[0], a.inputs[0]))   # self
        self.assertFalse(self.g.connect(b.inputs[0], a.inputs[1]))    # input to input
        self.assertFalse(self.g.connect(a.outputs[0], b.inputs[0]))   # duplicate

    def test_only_downstream_of_a_change_is_recomputed(self):
        s1 = self.g.add(NumberSlider(1, 0, 10))
        s2 = self.g.add(NumberSlider(2, 0, 10))
        a1, a2 = self.g.add(Add()), self.g.add(Add())
        self.g.connect(s1.outputs[0], a1.inputs[0])
        self.g.connect(s2.outputs[0], a2.inputs[0])
        self.g.solve()
        Add.calls = 0
        s1.set_value(5)
        solved = self.g.solve()
        self.assertEqual(set(solved), {s1, a1})
        self.assertEqual(Add.calls, 1)
        self.assertEqual(list(a1.outputs[0].data), [5.0])
        self.assertEqual(list(a2.outputs[0].data), [2.0])

    def test_solve_order_follows_dependencies_not_insertion(self):
        a2 = self.g.add(Add())
        a1 = self.g.add(Add())
        s = self.g.add(NumberSlider(4, 0, 10))
        self.g.connect(s.outputs[0], a1.inputs[0])
        self.g.connect(a1.outputs[0], a2.inputs[0])
        self.g.solve()
        self.assertEqual(list(a2.outputs[0].data), [4.0])

    def test_disconnect_expires_and_empties_downstream(self):
        s = self.g.add(NumberSlider(4, 0, 10))
        a = self.g.add(Add())
        self.g.connect(s.outputs[0], a.inputs[0])
        self.g.solve()
        self.g.disconnect(s.outputs[0], a.inputs[0])
        self.g.solve()
        self.assertEqual(a.state, WARNING)
        self.assertEqual(list(a.outputs[0].data), [])

    def test_slider_clamps_and_rounds(self):
        s = NumberSlider(5, 1, 8, 0)
        s.set_value(3.6)
        self.assertEqual(s.value, 4)
        s.set_value(99)
        self.assertEqual(s.value, 8)

    def test_remove_component_detaches_wires(self):
        s = self.g.add(NumberSlider(4, 0, 10))
        a = self.g.add(Add())
        self.g.connect(s.outputs[0], a.inputs[0])
        self.g.remove(s)
        self.assertEqual(a.inputs[0].sources, [])
        self.assertEqual(self.g.wires(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
