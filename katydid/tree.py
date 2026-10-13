# SPDX-License-Identifier: LGPL-2.1-or-later
"""Data trees: ordered branches of items, each addressed by a path like {0;1}.

Pure Python. Iterating a Tree yields every item in path order, len() counts
items, and tree[i] indexes that flattened sequence, so code that only needs
"the data" can treat a tree like a list.
"""

from __future__ import annotations

from typing import Iterable, Iterator

Path = tuple[int, ...]

FLATTEN, GRAFT, SIMPLIFY = "flatten", "graft", "simplify"
MODIFIERS = (FLATTEN, GRAFT, SIMPLIFY)


def format_path(path: Path) -> str:
    return "{" + ";".join(str(i) for i in path) + "}"


class Tree:
    def __init__(self, branches: dict[Path, list] | None = None):
        self._branches: dict[Path, list] = {}
        for path, items in (branches or {}).items():
            self._branches[tuple(path)] = list(items)

    @classmethod
    def from_list(cls, items: Iterable, path: Path = (0,)) -> "Tree":
        return cls({path: list(items)})

    # building ---------------------------------------------------------------
    def branch(self, path: Path) -> list:
        """The branch at path, created empty if missing."""
        return self._branches.setdefault(tuple(path), [])

    def append(self, path: Path, item) -> None:
        self.branch(path).append(item)

    def extend(self, path: Path, items: Iterable) -> None:
        self.branch(path).extend(items)

    def merge(self, other: "Tree") -> None:
        """Append other's branches; items under the same path are concatenated."""
        for path, items in other.branches():
            self.extend(path, items)

    # reading ----------------------------------------------------------------
    def paths(self) -> list[Path]:
        return sorted(self._branches)

    def branches(self) -> list[tuple[Path, list]]:
        return [(p, self._branches[p]) for p in self.paths()]

    @property
    def branch_count(self) -> int:
        return len(self._branches)

    def __iter__(self) -> Iterator:
        for _, items in self.branches():
            yield from items

    def __len__(self) -> int:
        return sum(len(items) for items in self._branches.values())

    def __getitem__(self, index: int):
        return list(self)[index]

    def __bool__(self) -> bool:
        return len(self) > 0

    def __eq__(self, other) -> bool:
        return isinstance(other, Tree) and self.branches() == other.branches()

    def __repr__(self) -> str:
        inner = ", ".join(f"{format_path(p)}: {len(i)}" for p, i in self.branches())
        return f"<Tree {inner}>"

    def describe(self) -> str:
        n, b = len(self), self.branch_count
        return f"{n} item{'s' * (n != 1)} in {b} branch{'es' * (b != 1)}"

    # the three path operations ------------------------------------------------
    def flatten(self) -> "Tree":
        """All items, in path order, in the single branch {0}."""
        return Tree({(0,): list(self)})

    def graft(self) -> "Tree":
        """Every item into its own branch: {A} item i -> {A;i}. Empty branches stay."""
        out = Tree()
        for path, items in self.branches():
            if not items:
                out.branch(path)
            for i, item in enumerate(items):
                out.append(path + (i,), item)
        return out

    def simplify(self) -> "Tree":
        """Drop empty branches, then the leading path indices shared by every
        branch, keeping at least the last index so each path stays valid."""
        branches = [(p, i) for p, i in self.branches() if i]
        if not branches:
            return Tree()
        paths = [p for p, _ in branches]
        shortest = min(len(p) for p in paths)
        shared = 0
        while shared < shortest - 1 and len({p[shared] for p in paths}) == 1:
            shared += 1
        out = Tree()
        for path, items in branches:
            out.extend(path[shared:], items)
        return out

    def reverse(self) -> "Tree":
        """Reverse the order of items within each branch."""
        return Tree({p: list(reversed(i)) for p, i in self.branches()})

    def mapped(self, modifier: str | None, reverse: bool = False) -> "Tree":
        tree = self
        if modifier == FLATTEN:
            tree = tree.flatten()
        elif modifier == GRAFT:
            tree = tree.graft()
        elif modifier == SIMPLIFY:
            tree = tree.simplify()
        return tree.reverse() if reverse else tree
