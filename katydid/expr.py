# SPDX-License-Identifier: LGPL-2.1-or-later
"""A safe arithmetic evaluator for the Expression component.

Formulas live in saved files that people share, so they are never handed to
eval(): they are parsed, checked node by node against a whitelist, and walked.
Allowed: numbers, the variables x, y, z, the constants pi, e and tau,
+ - * / // % **, unary minus, and the math functions in FUNCTIONS.
"""

from __future__ import annotations

import ast
import math
import operator

FUNCTIONS = {name: getattr(math, name) for name in (
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh",
    "sqrt", "exp", "log", "log10", "floor", "ceil", "degrees", "radians", "hypot")}
FUNCTIONS.update(abs=abs, min=min, max=max, round=round)
CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}
VARIABLES = ("x", "y", "z")
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
MAX_POWER = 1000  # 10**10**10 would hang the solver


class ExpressionError(ValueError):
    pass


def compile_formula(text: str) -> ast.Expression:
    """Parse and validate; raises ExpressionError naming what is not allowed."""
    if not isinstance(text, str) or not text.strip():
        raise ExpressionError("Empty formula")
    if len(text) > 500:
        raise ExpressionError("Formula is too long")
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"Syntax error: {exc.msg}") from None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.Load)) or type(node) in _BIN or type(node) in _UNARY:
            continue
        if isinstance(node, (ast.BinOp, ast.UnaryOp)):
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            continue
        if isinstance(node, ast.Name) and (node.id in VARIABLES or node.id in CONSTANTS
                                           or node.id in FUNCTIONS):
            continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in FUNCTIONS and not node.keywords:
            continue
        what = getattr(node, "id", None) or getattr(node, "attr", None) or type(node).__name__
        raise ExpressionError(f"Not allowed in a formula: {what}")
    return tree


def evaluate(text: str, **values) -> float:
    tree = compile_formula(text)

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in CONSTANTS:
                return CONSTANTS[node.id]
            if node.id in VARIABLES:
                return values.get(node.id, 0.0)
            raise ExpressionError(f"{node.id} is a function, not a value")
        if isinstance(node, ast.UnaryOp):
            return _UNARY[type(node.op)](walk(node.operand))
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER:
                raise ExpressionError("Exponent is too large")
            return _BIN[type(node.op)](left, right)
        if isinstance(node, ast.Call):
            return FUNCTIONS[node.func.id](*(walk(a) for a in node.args))
        raise ExpressionError(f"Not allowed in a formula: {type(node).__name__}")

    try:
        result = walk(tree)
    except ExpressionError:
        raise
    except (ZeroDivisionError, OverflowError, TypeError, ValueError) as exc:  # e.g. sqrt(-1)
        raise ExpressionError(str(exc)) from None
    if isinstance(result, complex):
        raise ExpressionError("Result is not a real number")
    return float(result)
