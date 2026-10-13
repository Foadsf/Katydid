# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bake: copy previewed geometry into the FreeCAD document as one undo step."""

from __future__ import annotations

import FreeCAD


def bake(components) -> list:
    doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Katydid")
    baked = []
    doc.openTransaction("Katydid bake")
    try:
        for comp in components:
            for i, shape in enumerate(comp.shapes()):
                obj = doc.addObject("Part::Feature", f"Baked_{comp.nickname}")
                obj.Label = f"{comp.nickname} {i}"
                obj.Shape = shape.copy()
                baked.append(obj)
    finally:
        doc.commitTransaction()
    doc.recompute()
    return baked
