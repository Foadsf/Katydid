# SPDX-License-Identifier: LGPL-2.1-or-later
"""Katydid solver: components, parameters and expire-then-solve.

Pure Python. Nothing here imports FreeCAD or Qt, so the engine runs and is
tested headless. Data is flat lists for now; data trees replace them later
without changing the component API.
"""

from __future__ import annotations

import graphlib
import itertools
import time
from typing import Any, Callable

OK, WARNING, ERROR = "ok", "warning", "error"

_ids = itertools.count(1)


class Param:
    """An input or output grip on a component."""

    def __init__(self, owner: "Component", name: str, nickname: str,
                 description: str = "", default: Any = None,
                 optional: bool = False, is_input: bool = True):
        self.owner = owner
        self.name = name
        self.nickname = nickname
        self.description = description
        self.default = default
        self.optional = optional
        self.is_input = is_input
        self.sources: list[Param] = []      # inputs only
        self.recipients: list[Param] = []   # outputs only
        self.data: list = []

    def __repr__(self) -> str:
        side = "in" if self.is_input else "out"
        return f"<Param {self.owner.nickname}.{self.nickname} ({side})>"


class Component:
    """Base class. Subclasses declare grips in setup() and implement
    solve_instance(), which is called once per matched set of input items."""

    name = "Component"
    nickname = "Comp"
    category = "Params"
    description = ""

    def __init__(self) -> None:
        self.uid = next(_ids)
        self.inputs: list[Param] = []
        self.outputs: list[Param] = []
        self.expired = True
        self.state = OK
        self.messages: list[str] = []
        self.preview = True
        self.graph: Graph | None = None
        self.nickname = type(self).nickname
        self.setup()

    # -- declaration -------------------------------------------------------
    def setup(self) -> None:
        """Declare inputs and outputs."""

    def add_input(self, name, nickname, description="", default=None,
                  optional=False) -> Param:
        p = Param(self, name, nickname, description, default, optional, True)
        self.inputs.append(p)
        return p

    def add_output(self, name, nickname, description="") -> Param:
        p = Param(self, name, nickname, description, is_input=False)
        self.outputs.append(p)
        return p

    # -- solving -----------------------------------------------------------
    def solve_instance(self, *args):
        raise NotImplementedError

    def expire(self) -> None:
        if self.graph is not None:
            self.graph.expire(self)

    def collect(self, param: Param) -> list:
        if param.sources:
            items: list = []
            for src in param.sources:
                items.extend(src.data)
            return items
        if param.default is not None:
            return [param.default]
        return []

    def compute(self) -> None:
        """Collect inputs, match them longest-list style and solve."""
        self.state, self.messages = OK, []
        for out in self.outputs:
            out.data = []
        lists = [self.collect(p) for p in self.inputs]
        for p, items in zip(self.inputs, lists):
            if not items and not p.optional:
                self.state = WARNING
                self.messages.append(f"Input parameter {p.nickname} failed to collect data")
        if self.state == WARNING:
            return
        count = max((len(items) for items in lists), default=1) if lists else 1
        for i in range(count):
            args = [items[min(i, len(items) - 1)] if items else None for items in lists]
            try:
                result = self.solve_instance(*args)
            except Exception as exc:  # a failing iteration marks the component, the rest continue
                self.state = ERROR
                self.messages.append(str(exc) or type(exc).__name__)
                continue
            if len(self.outputs) == 1:
                result = (result,)
            for out, value in zip(self.outputs, result):
                out.data.append(value)

    def shapes(self) -> list:
        """Output items that can be previewed (anything with tessellate())."""
        return [item for out in self.outputs for item in out.data
                if hasattr(item, "tessellate")]

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.nickname}#{self.uid}>"


class Graph:
    """The document: components, wires and the solver."""

    def __init__(self) -> None:
        self.components: list[Component] = []
        self.listeners: list[Callable[[list[Component]], None]] = []
        self.last_solve_ms = 0.0

    # -- topology ----------------------------------------------------------
    def add(self, comp: Component) -> Component:
        comp.graph = self
        self.components.append(comp)
        comp.expired = True
        return comp

    def remove(self, comp: Component) -> None:
        for p in comp.inputs:
            for src in list(p.sources):
                self.disconnect(src, p)
        for p in comp.outputs:
            for dst in list(p.recipients):
                self.disconnect(p, dst)
        self.components.remove(comp)
        comp.graph = None

    def upstream(self, comp: Component) -> set[Component]:
        return {src.owner for p in comp.inputs for src in p.sources}

    def downstream(self, comp: Component) -> list[Component]:
        seen: list[Component] = []
        stack = [comp]
        while stack:
            c = stack.pop()
            for out in c.outputs:
                for dst in out.recipients:
                    if dst.owner not in seen:
                        seen.append(dst.owner)
                        stack.append(dst.owner)
        return seen

    def can_connect(self, out: Param, inp: Param) -> bool:
        if out.is_input or not inp.is_input or out in inp.sources:
            return False
        # A wire may not close a loop: the source must not depend on the target.
        return out.owner is not inp.owner and out.owner not in self.downstream(inp.owner)

    def connect(self, out: Param, inp: Param) -> bool:
        if not self.can_connect(out, inp):
            return False
        inp.sources.append(out)
        out.recipients.append(inp)
        self.expire(inp.owner)
        return True

    def disconnect(self, out: Param, inp: Param) -> None:
        if out in inp.sources:
            inp.sources.remove(out)
            out.recipients.remove(inp)
            self.expire(inp.owner)

    def wires(self) -> list[tuple[Param, Param]]:
        return [(src, p) for c in self.components for p in c.inputs for src in p.sources]

    # -- solving -----------------------------------------------------------
    def expire(self, comp: Component) -> None:
        comp.expired = True
        for c in self.downstream(comp):
            c.expired = True

    def solve(self) -> list[Component]:
        """Recompute expired components in dependency order."""
        t0 = time.perf_counter()
        sorter = graphlib.TopologicalSorter({c: self.upstream(c) for c in self.components})
        solved = []
        for comp in sorter.static_order():
            if comp.expired:
                comp.compute()
                comp.expired = False
                solved.append(comp)
        self.last_solve_ms = (time.perf_counter() - t0) * 1000.0
        for listener in self.listeners:
            listener(solved)
        return solved
