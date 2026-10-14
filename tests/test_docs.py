# SPDX-License-Identifier: LGPL-2.1-or-later
"""Every showcase example appears everywhere it is listed by hand: the home
page strip, the gallery, the tutorials page, the README and the Examples menu.
Run: python tests/test_docs.py"""

import os
import re
import unittest

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ADDON, rel), encoding="utf-8") as fh:
        return fh.read()


def showcase_keys():
    src = read("katydid/showcase.py")
    table = src[src.index("SHOWCASE = {"):]
    return re.findall(r'"(\w+)": build_\w+', table)


class ShowcaseListings(unittest.TestCase):
    def setUp(self):
        self.keys = showcase_keys()

    def test_keys_found(self):
        self.assertGreater(len(self.keys), 20)

    def test_every_example_is_listed(self):
        pages = {rel: read(rel) for rel in ("docs/index.adoc", "docs/gallery.adoc", "docs/tutorials.adoc",
                                            "README.md")}
        menu = read("katydid/gui.py")
        for key in self.keys:
            for rel, text in pages.items():
                self.assertTrue(f"{key}-render.png" in text, f"{key} is missing from {rel}")
            self.assertTrue(f'"{key}")' in menu, f"{key} is missing from the Examples menu")
            self.assertTrue(os.path.exists(os.path.join(ADDON, "docs", f"tutorial-{key}.adoc")), key)
            self.assertTrue(os.path.exists(os.path.join(ADDON, "docs", "images", f"{key}-render.png")), key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
