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


def _triangulate(shape, tol):
    """Preview-quality triangles. Shape.tessellate() ignores the tolerance on curved
    faces (a r=42 sphere is 8000 triangles, ~130 ms, at any tolerance); MeshPart
    with FreeCAD's display angle gives 1484 triangles in ~16 ms."""
    try:
        import MeshPart
    except ImportError:
        return shape.tessellate(tol)
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=tol,
                                  AngularDeflection=0.5, Relative=False)
    return mesh.Topology


def _mesh_node(shapes, colour) -> coin.SoSeparator:
    import Part
    shapes = [s for s in shapes if not s.isNull()]
    # One meshing call for the whole group is ~40% cheaper than one per shape
    # (measured: 4 boxes, 5.3 ms -> 3.1 ms; tests/preview_profile.py).
    compound = Part.makeCompound(shapes)
    tol = max(compound.BoundBox.DiagonalLength * 0.002, 0.01)
    verts, tris = _triangulate(compound, tol)
    points = [(v.x, v.y, v.z) for v in verts]
    index = []
    for a, b, c in tris:
        index.extend((a, b, c, -1))
    edge_points, edge_counts = [], []
    for shape in shapes:
        for edge in shape.Edges:
            try:
                pts = edge.discretize(Deflection=tol)
            except Exception:  # degenerate edges, e.g. sphere poles
                continue
            if len(pts) > 1:
                edge_points.extend((v.x, v.y, v.z) for v in pts)
                edge_counts.append(len(pts))

    sep = coin.SoSeparator()
    hints = coin.SoShapeHints()
    hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
    hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE  # two-sided lighting
    mat = coin.SoMaterial()
    mat.diffuseColor.setValue(*colour)
    mat.emissiveColor.setValue(colour[0] * 0.25, colour[1] * 0.25, colour[2] * 0.25)
    mat.transparency.setValue(0.45)
    coords = coin.SoCoordinate3()
    coords.point.setValues(0, len(points), points)
    faces = coin.SoIndexedFaceSet()
    faces.coordIndex.setValues(0, len(index), index)
    for node in (hints, mat, coords, faces):
        sep.addChild(node)

    if edge_counts:
        edges = coin.SoSeparator()
        light = coin.SoLightModel()
        light.model = coin.SoLightModel.BASE_COLOR
        emat = coin.SoMaterial()
        emat.diffuseColor.setValue(*EDGE[colour])
        style = coin.SoDrawStyle()
        style.lineWidth = 1.5
        ecoords = coin.SoCoordinate3()
        ecoords.point.setValues(0, len(edge_points), edge_points)
        lines = coin.SoLineSet()
        lines.numVertices.setValues(0, len(edge_counts), edge_counts)
        for node in (light, emat, style, ecoords, lines):
            edges.addChild(node)
        sep.addChild(edges)
    return sep
