# SPDX-License-Identifier: LGPL-2.1-or-later
"""Transient viewport preview: Coin3D nodes in the active 3D view.

Nothing is written to the FreeCAD document; baking does that.
"""

from __future__ import annotations

import FreeCAD
import FreeCADGui
from pivy import coin

RED = (0.80, 0.10, 0.08)
GREEN = (0.30, 0.78, 0.10)
EDGE = {RED: (0.35, 0.02, 0.02), GREEN: (0.10, 0.35, 0.02)}


class Preview:
    def __init__(self):
        try:  # pay the one-off import when the canvas opens, not on the first solve
            import MeshPart  # noqa: F401
        except ImportError:
            pass
        self.root = coin.SoSeparator()
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE  # never steals FreeCAD selection
        self.root.addChild(pick)
        self.content = coin.SoSeparator()
        self.root.addChild(self.content)
        self.enabled = True
        self._doc = None
        self._scenegraph = None

    def _attach(self) -> bool:
        gdoc = FreeCADGui.ActiveDocument
        if gdoc is None:
            return False
        name = gdoc.Document.Name
        if name != self._doc:
            self.detach()
            self._scenegraph = gdoc.ActiveView.getSceneGraph()
            self._scenegraph.addChild(self.root)
            self._doc = name
        return True

    def detach(self):
        if self._scenegraph is not None and self._doc in FreeCAD.listDocuments():
            self._scenegraph.removeChild(self.root)
        self.forget()

    def forget(self):
        """Drop the scene graph without touching it (its document is closing)."""
        self.content.removeAllChildren()
        self._scenegraph, self._doc = None, None

    def update(self, normal: list, selected: list) -> None:
        self.content.removeAllChildren()
        if not self.enabled or not (normal or selected) or not self._attach():
            return
        for shapes, colour in ((normal, RED), (selected, GREEN)):
            if shapes:
                self.content.addChild(_mesh_node(shapes, colour))


def _triangulate(shapes, tol):
    """Preview-quality (vertices, triangles) for shapes with faces.

    MeshPart with FreeCAD's display angle, on NEW shapes as a canvas update
    produces them: a r=42 sphere 16 ms (Shape.tessellate: 8000 triangles, ~130 ms,
    whatever the tolerance); 100 extruded tubes 73 ms (tessellate: 152 ms).
    Measure on fresh shapes: OCCT caches a shape's triangulation, and a profile
    that re-meshes the same shapes once made tessellate look 3x faster than it is.
    """
    import Part
    compound = Part.makeCompound(shapes)
    try:
        import MeshPart
    except ImportError:
        return compound.tessellate(tol)
    mesh = MeshPart.meshFromShape(Shape=compound, LinearDeflection=tol,
                                  AngularDeflection=_angle(compound), Relative=False)
    return mesh.Topology


CURVED_FACES = 24   # above this many, mesh curved faces coarser (28 woven pipes must qualify)


def _angle(compound) -> float:
    """Angular deflection for the preview: 0.5 rad normally, 1.0 rad when there
    are many curved faces. Measured on fresh shapes: 400 spheres 953 -> 302 ms,
    28 woven pipes 2106 -> 1110 ms, a lattice of 57 pipes 798 -> 337 ms. Flat
    faces do not depend on it, and baked objects keep FreeCAD's own quality."""
    curved = sum(1 for f in compound.Faces if f.Surface.TypeId != "Part::GeomPlane")
    return 1.0 if curved > CURVED_FACES else 0.5


def _polylines(shapes, tol):
    """Discretised edges as (points, counts) for an SoLineSet."""
    points, counts = [], []

    def add(item):
        try:
            pts = item.discretize(Deflection=tol)
        except Exception:  # degenerate edges, e.g. sphere poles
            return
        if len(pts) > 1:
            points.extend((v.x, v.y, v.z) for v in pts)
            counts.append(len(pts))

    for shape in shapes:
        if shape.ShapeType == "Wire":
            # One call per wire, not per edge: a traced contour is thousands of tiny
            # segments (the wave example: 4,100 edges in 55 wires, 0.16 s -> 0.02 s).
            add(shape)
        else:
            for edge in shape.Edges:
                add(edge)
    return points, counts


def _flat(colour, width=None, point=None, nodes=()):
    """Unlit, opaque styling for lines and points."""
    sep = coin.SoSeparator()
    light = coin.SoLightModel()
    light.model = coin.SoLightModel.BASE_COLOR
    mat = coin.SoMaterial()
    mat.diffuseColor.setValue(*colour)
    style = coin.SoDrawStyle()
    if width:
        style.lineWidth = width
    if point:
        style.pointSize = point
    for node in (light, mat, style, *nodes):
        sep.addChild(node)
    return sep


def _coords(points):
    c = coin.SoCoordinate3()
    c.point.setValues(0, len(points), points)
    return c


def _mesh_node(shapes, colour) -> coin.SoSeparator:
    """Grasshopper-style preview: translucent faces with dark outlines, curves
    as thick lines in the preview colour, points as dots."""
    import Part
    shapes = [s for s in shapes if not s.isNull()]
    faced = [s for s in shapes if s.Faces]
    curves = [s for s in shapes if not s.Faces and s.Edges]
    vertices = [s for s in shapes if s.ShapeType == "Vertex"]
    whole = Part.makeCompound(shapes)
    tol = max(whole.BoundBox.DiagonalLength * 0.002, 0.01)
    sep = coin.SoSeparator()

    if faced:
        # One meshing call per group is ~40% cheaper than one per shape
        # (measured: 4 boxes, 5.3 ms -> 3.1 ms; tests/preview_profile.py).
        verts, tris = _triangulate(faced, tol)
        index = []
        for a, b, c in tris:
            index.extend((a, b, c, -1))
        hints = coin.SoShapeHints()
        hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
        hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE  # two-sided lighting
        mat = coin.SoMaterial()
        mat.diffuseColor.setValue(*colour)
        mat.emissiveColor.setValue(colour[0] * 0.25, colour[1] * 0.25, colour[2] * 0.25)
        mat.transparency.setValue(0.45)
        faces = coin.SoIndexedFaceSet()
        faces.coordIndex.setValues(0, len(index), index)
        for node in (hints, mat, _coords([(v.x, v.y, v.z) for v in verts]), faces):
            sep.addChild(node)
        pts, counts = _polylines(faced, tol)
        if counts:
            lines = coin.SoLineSet()
            lines.numVertices.setValues(0, len(counts), counts)
            sep.addChild(_flat(EDGE[colour], width=1.5, nodes=(_coords(pts), lines)))

    if curves:
        pts, counts = _polylines(curves, tol)
        if counts:
            lines = coin.SoLineSet()
            lines.numVertices.setValues(0, len(counts), counts)
            sep.addChild(_flat(colour, width=2.5, nodes=(_coords(pts), lines)))

    if vertices:
        dots = coin.SoPointSet()
        sep.addChild(_flat(colour, point=6, nodes=(
            _coords([(v.Point.x, v.Point.y, v.Point.z) for v in vertices]), dots)))
    return sep
