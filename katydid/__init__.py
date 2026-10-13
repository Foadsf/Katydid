# SPDX-License-Identifier: LGPL-2.1-or-later
"""Katydid: a Grasshopper-style visual programming canvas for FreeCAD."""

import os

__version__ = "0.1.0"

_RESOURCES = os.path.join(os.path.dirname(__file__), "resources")


def resource(name: str) -> str:
    return os.path.join(_RESOURCES, name)
