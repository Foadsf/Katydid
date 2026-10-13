# SPDX-License-Identifier: LGPL-2.1-or-later
"""Katydid solver: components, parameters, data trees and expire-then-solve.

Pure Python. Nothing here imports FreeCAD or Qt, so the engine runs and is
tested headless.

Matching rules (our reading of Grasshopper's, not verified against it):
- An input's data is a Tree. Wires into one input merge by path.
- Item and list inputs are matched branch by branch; an input with fewer
  branches repeats its last branch. Output branches take their paths from the
  first input with the most branches.
- Within a branch, item inputs are matched longest-list (the last item repeats);
  a list input receives the whole branch; a tree input receives the whole tree
  and the component solves once.
- An item output collects one value per iteration in the branch's path. A list
  output gets a branch per iteration: the branch path plus the iteration index,
  so dividing three curves in {0} gives {0;0}, {0;1}, {0;2}.
- Flatten, Graft, Simplify and Reverse can be set on any grip: on inputs they
  apply to the collected data, on outputs to the solved data.
"""

from __future__ import annotations

import graphlib
import itertools
import time
from typing import Any, Callable

from .tree import MODIFIERS, Tree

OK, WARNING, ERROR = "ok", "warning", "error"
ITEM, LIST, TREE = "item", "list", "tree"

_ids = itertools.count(1)


class Param:
    """An input or output grip on a component."""

    def __init__(self, owner: "Component", name: str, nickname: str,
                 description: str = "", default: Any = None, optional: bool = False,
                 is_input: bool = True, access: str = ITEM):
        self.owner = owner
        self.name = name
        self.nickname = nickname
        self.description = description
        self.default = default
        self.optional = optional
        self.is_input = is_input
        self.access = access
        self.modifier: str | None = None   # flatten | graft | simplify
        self.reverse = False
        self.sources: list[Param] = []      # inputs only
        self.recipients: list[Param] = []   # outputs only
        self.data = Tree()

    def set_modifier(self, modifier: str | None) -> None:
        if modifier not in (None, *MODIFIERS):
            raise ValueError(f"Unknown modifier {modifier!r}")
        self.modifier = modifier
        self.owner.expire()

    def set_reverse(self, on: bool) -> None:
        self.reverse = bool(on)
        self.owner.expire()

    def __repr__(self) -> str:
        side = "in" if self.is_input else "out"
        return f"<Param {self.owner.nickname}.{self.nickname} ({side})>"


class Component:
    """Base class. Subclasses declare grips in setup() and implement
    solve_instance(), called once per matched set of inputs. Its return value is
    one value per output (a tuple when there are several); a list output
    returns a list."""

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

    def add_input(self, name, nickname, description="", default=None, optional=False,
                  access=ITEM) -> Param:
        p = Param(self, name, nickname, description, default, optional, True, access)
        self.inputs.append(p)
        return p

    def add_output(self, name, nickname, description="", access=ITEM) -> Param:
        p = Param(self, name, nickname, description, is_input=False, access=access)
        self.outputs.append(p)
        return p

    # -- persistence -------------------------------------------------------
    def write_state(self) -> dict:
        """Component-specific settings to save, beyond wires and input defaults."""
        return {}

    def read_state(self, state: dict) -> None:
        """Restore what write_state() returned."""

    # -- solving -----------------------------------------------------------
    def solve_instance(self, *args):
        raise NotImplementedError

    def expire(self) -> None:
        if self.graph is not None:
            self.graph.expire(self)

    def collect(self, param: Param) -> Tree:
        """An input's data: merged sources (or its default), then its modifiers."""
        if param.sources:
            tree = Tree()
            for src in param.sources:
                tree.merge(src.data)
        elif param.default is not None:
            tree = Tree.from_list([param.default])
        else:
            tree = Tree()
        return tree.mapped(param.modifier, param.reverse)

    def run(self) -> None:
        """Solve, then apply the output grips' modifiers."""
        self.state, self.messages = OK, []
        for out in self.outputs:
            out.data = Tree()
        self.compute()
        for out in self.outputs:
            if out.modifier or out.reverse:
                out.data = out.data.mapped(out.modifier, out.reverse)

    def warn_missing(self, trees) -> bool:
        for p, tree in zip(self.inputs, trees):
            if not tree and not p.optional:
                self.state = WARNING
                self.messages.append(f"Input parameter {p.nickname} failed to collect data")
        return self.state == WARNING

    def error(self, exc: Exception) -> None:
        self.state = ERROR
        message = str(exc) or type(exc).__name__
        if message not in self.messages:
            self.messages.append(message)

    def compute(self) -> None:
        trees = [self.collect(p) for p in self.inputs]
        if self.warn_missing(trees):
            return
        matched = [(i, p) for i, p in enumerate(self.inputs) if p.access != TREE]
        if not matched:  # tree access throughout: one solve with whole trees
            self._emit((0,), 0, trees)
            return
        branches = {i: trees[i].branches() or [((0,), [])] for i, _ in matched}
        count = max(len(b) for b in branches.values())
        master = next(i for i, _ in matched if len(branches[i]) == count)
        for b in range(count):
            picked = {i: branches[i][min(b, len(branches[i]) - 1)][1] for i, _ in matched}
            path = branches[master][b][0]
            item_lists = [picked[i] for i, p in matched if p.access == ITEM]
            if any(not picked[i] for i, p in matched if p.access == ITEM and not p.optional):
                for out in self.outputs:  # keep the branch, with nothing in it
                    if out.access == ITEM:
                        out.data.branch(path)
                continue
            iterations = max((len(items) for items in item_lists), default=1) or 1
            for it in range(iterations):
                args = []
                for i, p in enumerate(self.inputs):
                    if p.access == TREE:
                        args.append(trees[i])
                    elif p.access == LIST:
                        args.append(list(picked[i]))
                    else:
                        items = picked[i]
                        args.append(items[min(it, len(items) - 1)] if items else None)
                self._emit(path, it, args)

    def _emit(self, path, iteration, args) -> None:
        try:
            result = self.solve_instance(*args)
        except Exception as exc:  # a failing iteration marks the component, the rest continue
            self.error(exc)
            return
        if len(self.outputs) == 1:
            result = (result,)
        for out, value in zip(self.outputs, result):
            if out.access == LIST:
                out.data.extend(path + (iteration,), value)
            else:
                out.data.append(path, value)

    def shapes(self) -> list:
        """Output items that can be previewed (anything with a BoundBox)."""
        return [item for out in self.outputs for item in out.data
                if hasattr(item, "BoundBox") and hasattr(item, "isNull")]

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
                comp.run()
                comp.expired = False
                solved.append(comp)
        self.last_solve_ms = (time.perf_counter() - t0) * 1000.0
        for listener in self.listeners:
            listener(solved)
        return solved
