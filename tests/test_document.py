# SPDX-License-Identifier: LGPL-2.1-or-later
"""Headless tests for the saved definition format. Run: python tests/test_document.py"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from katydid import document  # noqa: E402
from katydid.components import Addition, NumberSlider, Panel, Series  # noqa: E402
from katydid.engine import ERROR, Graph  # noqa: E402


def sample():
    g = Graph()
    s = g.add(NumberSlider(7.5, 0, 20, 1))
    s.nickname = "Width"
    ser = g.add(Series())
    ser.inputs[0].default = 5.0          # Start, set without a wire
    add = g.add(Addition())
    add.preview = False
    pan = g.add(Panel())
    g.connect(s.outputs[0], ser.inputs[1])
    g.connect(ser.outputs[0], add.inputs[0])
    g.connect(s.outputs[0], add.inputs[1])
    g.connect(add.outputs[0], pan.inputs[0])
    positions = {s: (-100, 20), ser: (50.5, 0), add: (200, 10), pan: (350, 0)}
    return g, positions


class DocumentTests(unittest.TestCase):
    def test_round_trip_is_identical_and_solves_the_same(self):
        g, pos = sample()
        g.solve()
        text = document.dumps(g, pos)
        g2 = Graph()
        pos2, warnings = document.build(g2, text)
        self.assertEqual(warnings, [])
        self.assertEqual(document.dumps(g2, pos2), text)
        g2.solve()
        self.assertEqual(g2.components[2].outputs[0].data, g.components[2].outputs[0].data)
        self.assertEqual(g2.components[3].text_lines, g.components[3].text_lines)

    def test_slider_state_defaults_preview_and_nickname_survive(self):
        g, pos = sample()
        g2 = Graph()
        document.build(g2, document.dumps(g, pos))
        s, ser, add, _ = g2.components
        self.assertEqual((s.value, s.minimum, s.maximum, s.decimals, s.nickname),
                         (7.5, 0, 20, 1, "Width"))
        self.assertEqual(ser.inputs[0].default, 5.0)
        self.assertFalse(add.preview)

    def test_point_defaults_round_trip_as_tuples(self):
        from katydid.components import CircleCNR
        g = Graph()
        c = g.add(CircleCNR())
        c.inputs[0].default = (1.0, 2.0, 3.0)
        g2 = Graph()
        document.build(g2, document.dumps(g))
        self.assertEqual(g2.components[0].inputs[0].default, (1.0, 2.0, 3.0))

    def test_value_dialog_parsing(self):
        from katydid.canvas import format_value, parse_value, value_kind
        self.assertEqual(value_kind((0.0, 0.0, 1.0)), "point")
        self.assertEqual(value_kind(True), "bool")
        self.assertIsNone(value_kind(None))
        self.assertEqual(parse_value("point", "1, 2;3"), (1.0, 2.0, 3.0))
        self.assertEqual(format_value("point", (1.0, 2.5, 0.0)), "1, 2.5, 0")
        self.assertIs(parse_value("bool", "false"), False)
        for kind, text in (("point", "1, 2"), ("number", "abc"), ("bool", "maybe")):
            with self.assertRaises(ValueError):
                parse_value(kind, text)

    def test_inputs_without_default_declare_a_kind_and_it_persists(self):
        from katydid.canvas import param_kind
        from katydid.components import BonusTolerance, Distance, MonteCarlo, Move
        self.assertEqual(param_kind(BonusTolerance().inputs[1]), "number")   # MMC
        self.assertEqual(param_kind(Distance().inputs[0]), "point")
        self.assertEqual(param_kind(MonteCarlo().inputs[4]), "number")       # LSL
        self.assertIsNone(param_kind(Move().inputs[0]))                      # geometry: wire it
        g = Graph()
        b = g.add(BonusTolerance())
        b.inputs[1].default = 0.505
        g2 = Graph()
        document.build(g2, document.dumps(g))
        self.assertEqual(g2.components[0].inputs[1].default, 0.505)

    def test_unknown_type_is_kept_with_its_wires(self):
        g, pos = sample()
        data = document.dump(g, pos)
        data["components"][2]["type"] = "FutureThing"
        data["components"][2]["state"] = {"secret": 42}
        g2 = Graph()
        pos2, warnings = document.build(g2, data)
        missing = g2.components[2]
        self.assertIsInstance(missing, document.Missing)
        self.assertTrue(any("FutureThing" in w for w in warnings))
        g2.solve()
        self.assertEqual(missing.state, ERROR)
        again = document.dump(g2, pos2)
        self.assertEqual(again["components"][2]["type"], "FutureThing")
        self.assertEqual(again["components"][2]["state"], {"secret": 42})
        self.assertEqual(sorted(again["wires"]), sorted(data["wires"]))

    def test_bad_wires_are_skipped_with_warnings(self):
        g, pos = sample()
        data = document.dump(g, pos)
        data["wires"] += [[1, 5, 2, 0], [99, 0, 1, 0], "junk", [3, 0, 1, 0]]
        g2 = Graph()
        _, warnings = document.build(g2, data)
        self.assertEqual(len(g2.wires()), 4)
        self.assertEqual(len(warnings), 4)

    def test_rejects_foreign_json_and_warns_on_newer_version(self):
        with self.assertRaises(ValueError):
            document.build(Graph(), json.dumps({"format": "other"}))
        data = document.dump(sample()[0])
        data["version"] = document.VERSION + 1
        _, warnings = document.build(Graph(), data)
        self.assertTrue(any("newer" in w for w in warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
