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
