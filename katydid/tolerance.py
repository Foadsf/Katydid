# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tolerance analysis: linear stack-ups and GD&T size boundaries. Pure Python.

Stack-ups follow B. R. Fischer, Mechanical Tolerance Stackup and Analysis,
2nd ed. (2011), ch. 7-8: every dimension is converted to equal-bilateral form,
the nominal is the positive total minus the negative total, the worst-case
tolerance is the sum of tolerances, the RSS tolerance is the root of the sum
of their squares, and the adjusted RSS multiplies that by a factor (1.5 in
his examples). Monte Carlo treats each tolerance as k standard deviations
(k = 3 by default) of a normal distribution, or as the half-width of a uniform
or triangular one.

GD&T boundaries follow G. R. Cogorno, Geometric Dimensioning and Tolerancing
for Mechanical Design, 3rd ed. (2020), ch. 3, for features toleranced at MMC.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

DISTRIBUTIONS = ("normal", "uniform", "triangular")


@dataclass(frozen=True)
class Dim:
    """One dimension in a stack: nominal with upper/lower deviations (lower is
    negative for a minus tolerance) and its direction in the chain (+1 / -1)."""

    nominal: float
    upper: float
    lower: float
    sign: int = 1
    distribution: str = "normal"
    name: str = ""

    def __post_init__(self):
        if self.upper < self.lower:
            raise ValueError("Upper deviation is below the lower deviation")
        if self.sign not in (1, -1):
            raise ValueError("Direction must be +1 or -1")
        if self.distribution not in DISTRIBUTIONS:
            raise ValueError(f"Distribution must be one of {', '.join(DISTRIBUTIONS)}")

    @property
    def mean(self) -> float:
        """Equal-bilateral nominal (Fischer ch. 4): 10 +0.2/-0.1 -> 10.05."""
        return self.nominal + (self.upper + self.lower) / 2

    @property
    def tol(self) -> float:
        """Equal-bilateral tolerance: 10 +0.2/-0.1 -> +/-0.15."""
        return (self.upper - self.lower) / 2

    def __str__(self):
        sign = "+" if self.sign > 0 else "-"
        if abs(self.upper + self.lower) < 1e-12:
            body = f"{self.nominal:g} ±{self.upper:g}"
        else:
            body = f"{self.nominal:g} {self.upper:+g}/{self.lower:+g}"
        label = f"{self.name}: " if self.name else ""
        return f"{label}{sign}{body}"


@dataclass(frozen=True)
class StackResult:
    nominal: float
    worst_case: float
    rss: float
    adjusted: float
    factor: float
    contributions: tuple  # worst-case share of each line, 0..1

    def limits(self, method: str) -> tuple[float, float]:
        t = {"worst": self.worst_case, "rss": self.rss, "adjusted": self.adjusted}[method]
        return self.nominal - t, self.nominal + t


def stack(dims, factor: float = 1.5) -> StackResult:
    if not dims:
        raise ValueError("A stack needs at least one dimension")
    if factor < 1:
        raise ValueError("The RSS adjustment factor must be at least 1")
    nominal = sum(d.sign * d.mean for d in dims)
    wc = sum(d.tol for d in dims)
    rss = math.sqrt(sum(d.tol ** 2 for d in dims))
    shares = tuple(d.tol / wc if wc else 0.0 for d in dims)
    return StackResult(nominal, wc, rss, rss * factor, factor, shares)


def report(dims, result: StackResult, digits: int = 4) -> list[str]:
    """Fischer-style report lines: each dimension with its share, then results."""
    f = f".{digits}f"
    lines = [f"{i + 1:>2}  {str(d):<28} ±{d.tol:{f}}  {share:4.0%}"
             for i, (d, share) in enumerate(zip(dims, result.contributions))]
    lines.append(f"Nominal            {result.nominal:{f}}")
    for label, method, tol in (("Worst case", "worst", result.worst_case),
                               ("RSS", "rss", result.rss),
                               (f"Adj. RSS x{result.factor:g}", "adjusted", result.adjusted)):
        lo, hi = result.limits(method)
        lines.append(f"{label:<17}  ±{tol:{f}}   {lo:{f}} .. {hi:{f}}")
    return lines


# --------------------------------------------------------------------------
# Monte Carlo
# --------------------------------------------------------------------------
def monte_carlo(dims, samples: int = 10000, seed: int = 1, sigmas: float = 3.0,
                use_numpy: bool | None = None) -> list[float]:
    """Assembly results for `samples` random builds. A normal dimension has
    standard deviation tol / sigmas; uniform and triangular span +/- tol.
    numpy is used when available (use_numpy=None) -- the two paths draw
    different random streams, so a seed repeats results only on the same path."""
    if samples < 2:
        raise ValueError("Use at least two samples")
    if sigmas <= 0:
        raise ValueError("Sigmas per tolerance must be positive")
    np = None
    if use_numpy is not False:
        try:
            import numpy as np
        except ImportError:
            if use_numpy:
                raise
    if np is not None:  # ~50x faster; FreeCAD bundles numpy
        rng = np.random.default_rng(int(seed))
        total = np.zeros(int(samples))
        for d in dims:
            if d.distribution == "normal":
                v = rng.normal(d.mean, d.tol / sigmas, int(samples)) if d.tol else np.full(int(samples), d.mean)
            elif d.distribution == "uniform":
                v = rng.uniform(d.mean - d.tol, d.mean + d.tol, int(samples))
            else:
                v = (rng.triangular(d.mean - d.tol, d.mean, d.mean + d.tol, int(samples))
                     if d.tol else np.full(int(samples), d.mean))
            total += d.sign * v
        return total.tolist()
    rng = random.Random(int(seed))
    out = []
    for _ in range(int(samples)):
        total = 0.0
        for d in dims:
            if d.distribution == "normal":
                v = rng.gauss(d.mean, d.tol / sigmas) if d.tol else d.mean
            elif d.distribution == "uniform":
                v = rng.uniform(d.mean - d.tol, d.mean + d.tol)
            else:
                v = rng.triangular(d.mean - d.tol, d.mean + d.tol, d.mean)
            total += d.sign * v
        out.append(total)
    return out


def mean_std(values) -> tuple[float, float]:
    n = len(values)
    m = sum(values) / n
    return m, math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def outside(values, low: float | None, high: float | None) -> float:
    """Fraction of results outside [low, high] (either limit may be None)."""
    bad = sum(1 for v in values if (low is not None and v < low) or (high is not None and v > high))
    return bad / len(values)


def histogram(values, bins: int = 16, width: int = 24) -> list[str]:
    """Text histogram lines, one per bin: lower edge, bar, count."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [f"{lo:9.4g} {'█' * width} {len(values)}"]
    counts = [0] * bins
    for v in values:
        counts[min(int((v - lo) / (hi - lo) * bins), bins - 1)] += 1
    top = max(counts)
    step = (hi - lo) / bins
    return [f"{lo + i * step:9.4g} {'█' * round(c / top * width):<{width}} {c}"
            for i, c in enumerate(counts)]


# --------------------------------------------------------------------------
# GD&T (features of size toleranced at MMC, Cogorno ch. 3)
# --------------------------------------------------------------------------
def bonus(actual: float, mmc: float, lmc: float, geometric: float,
          modifier: str = "MMC") -> tuple[float, float]:
    """(bonus, total tolerance) for an actual mating size between MMC and LMC."""
    if not min(mmc, lmc) - 1e-12 <= actual <= max(mmc, lmc) + 1e-12:
        raise ValueError("Actual size is outside the size limits (between MMC and LMC)")
    modifier = modifier.upper()
    if modifier == "MMC":
        b = abs(actual - mmc)
    elif modifier == "LMC":
        b = abs(actual - lmc)
    elif modifier == "RFS":
        b = 0.0
    else:
        raise ValueError("Modifier must be MMC, LMC or RFS")
    return b, b + geometric


def boundaries(mmc: float, lmc: float, geometric: float, internal: bool = True) -> dict:
    """Virtual and resultant condition and the worst-case inner/outer boundaries
    of a feature of size toleranced at MMC (internal = hole, external = pin)."""
    size_tol = abs(lmc - mmc)
    if internal:
        if mmc > lmc:
            raise ValueError("For a hole, MMC is the smallest size")
        vc, rc = mmc - geometric, lmc + geometric + size_tol
        return {"virtual": vc, "resultant": rc, "inner": vc, "outer": rc}
    if mmc < lmc:
        raise ValueError("For a pin, MMC is the largest size")
    vc, rc = mmc + geometric, lmc - geometric - size_tol
    return {"virtual": vc, "resultant": rc, "inner": rc, "outer": vc}


def position_to_plus_minus(position: float, size_tolerance: float = 0.0) -> tuple[float, float]:
    """Fischer: a diametral position tolerance becomes +/- position/2, and the
    bonus available from a size tolerance becomes +/- size_tolerance/2."""
    return position / 2, size_tolerance / 2
