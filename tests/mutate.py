# SPDX-License-Identifier: LGPL-2.1-or-later
"""Negative controls: break one rule at a time in a copy and confirm a test fails.

    python -I tests/mutate.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUTATIONS = [
    ("list output path ignores the iteration", "katydid/engine.py",
     "out.data.extend(path + (iteration,), value)", "out.data.extend(path, value)"),
    ("paths come from the last input", "katydid/engine.py",
     "master = next(i for i, _ in matched if len(branches[i]) == count)",
     "master = [i for i, _ in matched if len(branches[i]) == count][-1]"),
    ("simplify keeps shared indices", "katydid/tree.py",
     "while shared < shortest - 1 and", "while False and"),
    ("short trees do not repeat their last branch", "katydid/engine.py",
     "branches[i][min(b, len(branches[i]) - 1)][1]", "(branches[i][b][1] if b < len(branches[i]) else [])"),
    ("input modifiers are ignored", "katydid/engine.py",
     "return tree.mapped(param.modifier, param.reverse)", "return tree"),
    ("worst case takes the largest tolerance", "katydid/tolerance.py",
     "wc = sum(d.tol for d in dims)", "wc = max(d.tol for d in dims)"),
    ("RSS forgets the square root", "katydid/tolerance.py",
     "rss = math.sqrt(sum(d.tol ** 2 for d in dims))", "rss = sum(d.tol ** 2 for d in dims)"),
    ("equal-bilateral mean ignores asymmetry", "katydid/tolerance.py",
     "return self.nominal + (self.upper + self.lower) / 2", "return self.nominal"),
    ("hole virtual condition adds the tolerance", "katydid/tolerance.py",
     "vc, rc = mmc - geometric, lmc + geometric + size_tol",
     "vc, rc = mmc + geometric, lmc + geometric + size_tol"),
    ("LMC modifier measures from MMC", "katydid/tolerance.py",
     "b = abs(actual - lmc)", "b = abs(actual - mmc)"),
]
TESTS = ["tests/test_tree.py", "tests/test_engine.py", "tests/test_document.py",
         "tests/test_components.py", "tests/test_tolerance.py", "tests/test_geom2d.py"]


def run_suite(root):
    failed = False
    for t in TESTS:
        r = subprocess.run([sys.executable, "-I", os.path.join(root, t)], capture_output=True, text=True)
        failed |= r.returncode != 0
    return failed


def main():
    ignore = shutil.ignore_patterns("__pycache__", ".git")
    control = tempfile.mkdtemp(prefix="katydid_ctl_")
    shutil.copytree(ADDON, control, dirs_exist_ok=True, ignore=ignore)
    if run_suite(control):
        print("CONTROL FAILED: the unmutated copy does not pass; mutations prove nothing")
        return 3
    caught = 0
    for label, rel, old, new in MUTATIONS:
        root = tempfile.mkdtemp(prefix="katydid_mut_")
        shutil.copytree(ADDON, root, dirs_exist_ok=True, ignore=ignore)
        path = os.path.join(root, rel)
        src = open(path, encoding="utf-8").read()
        if old not in src:
            print(f"STALE   {label}: pattern not found")
            continue
        open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
        hit = run_suite(root)
        caught += hit
        print(f"{'caught ' if hit else 'MISSED '} {label}")
        shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(control, ignore_errors=True)
    print(f"{caught}/{len(MUTATIONS)} mutations caught (control clean)")
    return 0 if caught == len(MUTATIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
