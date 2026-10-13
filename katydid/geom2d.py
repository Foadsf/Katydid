# SPDX-License-Identifier: LGPL-2.1-or-later
"""Planar helpers: Voronoi cells by half-plane clipping, random points with
Lloyd relaxation. Pure Python (no numpy or scipy), so it is tested headless.

A Voronoi cell of a site is the part of the boundary rectangle closer to that
site than to any other: the rectangle clipped by the perpendicular bisector of
the site and each other site. That is O(n^2) clips, which is quick for the few
hundred cells a canvas definition uses, and every cell comes out closed,
convex and inside the rectangle.
"""

from __future__ import annotations

import random

Point = tuple[float, float]


def clip(polygon: list[Point], a: float, b: float, c: float) -> list[Point]:
    """Keep the part of a convex polygon where a*x + b*y <= c."""
    out: list[Point] = []
    n = len(polygon)
    for i in range(n):
        p, q = polygon[i], polygon[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def voronoi_cells(sites: list[Point], xmin: float, ymin: float, xmax: float, ymax: float) -> list[list[Point]]:
    """One counter-clockwise polygon per site (an empty list for a duplicate site)."""
    if xmax <= xmin or ymax <= ymin:
        raise ValueError("The boundary rectangle has no area")
    rect = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
    cells = []
    for i, (px, py) in enumerate(sites):
        cell = rect
        for j, (qx, qy) in enumerate(sites):
            if i == j:
                continue
            if (qx, qy) == (px, py):
                if j < i:  # the first copy of a duplicated site keeps the cell
                    cell = []
                    break
                continue
            # points nearer p than q:  (q - p) . x <= (|q|^2 - |p|^2) / 2
            cell = clip(cell, qx - px, qy - py, (qx * qx + qy * qy - px * px - py * py) / 2)
            if not cell:
                break
        cells.append(cell)
    return cells


def area(polygon: list[Point]) -> float:
    """Signed area (positive when counter-clockwise)."""
    s = 0.0
    n = len(polygon)
    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return s / 2


def centroid(polygon: list[Point]) -> Point:
    a = area(polygon)
    if abs(a) < 1e-15:
        xs, ys = zip(*polygon)
        return sum(xs) / len(xs), sum(ys) / len(ys)
    cx = cy = 0.0
    n = len(polygon)
    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    return cx / (6 * a), cy / (6 * a)


def populate(count: int, xmin: float, ymin: float, xmax: float, ymax: float,
             seed: int = 1, relax: int = 0) -> list[Point]:
    """Random points in a rectangle; each relaxation step moves every point to
    the centroid of its Voronoi cell (Lloyd), spreading them more evenly."""
    if count < 1:
        raise ValueError("Count must be at least 1")
    rng = random.Random(int(seed))
    pts = [(rng.uniform(xmin, xmax), rng.uniform(ymin, ymax)) for _ in range(int(count))]
    for _ in range(max(int(relax), 0)):
        cells = voronoi_cells(pts, xmin, ymin, xmax, ymax)
        pts = [centroid(c) if len(c) >= 3 else p for p, c in zip(pts, cells)]
    return pts


def regular_polygon(radius: float, sides: int, rotation_deg: float = 0.0) -> list[Point]:
    import math
    if sides < 3:
        raise ValueError("A polygon needs at least 3 sides")
    if radius <= 0:
        raise ValueError("Radius must be positive")
    r0 = math.radians(rotation_deg)
    return [(radius * math.cos(r0 + 2 * math.pi * k / sides), radius * math.sin(r0 + 2 * math.pi * k / sides))
            for k in range(int(sides))]
