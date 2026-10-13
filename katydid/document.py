# SPDX-License-Identifier: LGPL-2.1-or-later
"""Save and load a canvas definition as plain JSON.

The JSON is stored on a document object (see feature.py), so a definition
lives inside the FreeCAD file's Document.xml. Pure Python: no FreeCAD or Qt.

Format, version 1:
    {"format": "katydid", "version": 1,
     "components": [{"id", "type", "nickname", "x", "y", "preview",
                     "inputs": [nicknames], "outputs": [nicknames],
                     "defaults": [per-input default], "state": {...}}],
     "wires": [[source id, output index, target id, input index]]}
"""

from __future__ import annotations

import json

from . import components as lib
from .engine import ERROR, Component, Graph

FORMAT = "katydid"
VERSION = 1
_SCALARS = (int, float, str, bool, type(None))


class Missing(Component):
    """Stands in for a component type this version does not know, and saves
    its original record unchanged so nothing is lost on the next save."""

    name = "Missing component"
    nickname = "?"
    category = "Params"
    description = "Placeholder for an unknown component type"

    def __init__(self, record: dict):
        self.record = dict(record)
        super().__init__()
        self.nickname = record.get("nickname") or "?"

    def setup(self):
        for n in self.record.get("inputs", []):
            self.add_input(n, n, optional=True)
        for n in self.record.get("outputs", []):
            self.add_output(n, n)

    def compute(self):
        self.state = ERROR
        self.messages = [f"Component type '{self.record.get('type')}' is not available"]
        for out in self.outputs:
            out.data = []


def dump(graph: Graph, positions: dict | None = None) -> dict:
    positions = positions or {}
    ids = {c: i for i, c in enumerate(graph.components, 1)}
    records = []
    for c in graph.components:
        if isinstance(c, Missing):
            rec = dict(c.record)
        else:
            rec = {"type": type(c).__name__, "nickname": c.nickname, "preview": c.preview,
                   "inputs": [p.nickname for p in c.inputs],
                   "outputs": [p.nickname for p in c.outputs],
                   "defaults": [p.default if isinstance(p.default, _SCALARS) else None
                                for p in c.inputs]}
            state = c.write_state()
            if state:
                rec["state"] = state
        x, y = positions.get(c, (rec.get("x", 0.0), rec.get("y", 0.0)))
        rec.update(id=ids[c], x=round(float(x), 2), y=round(float(y), 2))
        records.append(rec)
    wires = [[ids[s.owner], s.owner.outputs.index(s), ids[d.owner], d.owner.inputs.index(d)]
             for s, d in graph.wires()]
    return {"format": FORMAT, "version": VERSION, "components": records, "wires": wires}


def dumps(graph: Graph, positions: dict | None = None) -> str:
    return json.dumps(dump(graph, positions), separators=(",", ":"), ensure_ascii=False)


def build(graph: Graph, data) -> tuple[dict, list[str]]:
    """Add a definition's components and wires to graph.

    Returns ({component: (x, y)}, warnings). Unknown types become Missing
    placeholders; wires that no longer fit are skipped with a warning.
    """
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("Not a Katydid definition")
    warnings = []
    if data.get("version", 0) > VERSION:
        warnings.append(f"Definition version {data['version']} is newer than this Katydid "
                        f"({VERSION}); loading what it understands")
    by_id, positions = {}, {}
    for rec in data.get("components", []):
        try:
            cls = lib.by_name(rec["type"])
        except KeyError:
            comp = Missing(rec)
            warnings.append(f"Unknown component type '{rec.get('type')}' kept as a placeholder")
        else:
            comp = cls()
            comp.nickname = rec.get("nickname", comp.nickname)
            comp.preview = bool(rec.get("preview", True))
            for p, value in zip(comp.inputs, rec.get("defaults", [])):
                if value is not None:
                    p.default = value
            comp.read_state(rec.get("state", {}))
        graph.add(comp)
        by_id[rec.get("id")] = comp
        positions[comp] = (float(rec.get("x", 0)), float(rec.get("y", 0)))
    for wire in data.get("wires", []):
        try:
            a, ai, b, bi = wire
            out, inp = by_id[a].outputs[ai], by_id[b].inputs[bi]
        except (KeyError, IndexError, TypeError, ValueError):
            warnings.append(f"Skipped invalid wire {wire}")
            continue
        if not graph.connect(out, inp):
            warnings.append(f"Skipped wire {wire}: it would not connect")
    return positions, warnings
