# -*- coding: utf-8 -*-
# cheminer_indus/utils/geom_utils.py

from __future__ import annotations
from typing import Optional, List
import math

from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
    QgsFeatureRequest,
    QgsWkbTypes,
)

# -------------------------------------------------------------------
# Outils d'interpolation / orientation (utilisés par flow_animator)
# -------------------------------------------------------------------

def safe_interpolate_point(geom: QgsGeometry, offset: float) -> Optional[QgsPointXY]:
    """
    Retourne un point interpolé sur une polyligne, ou None si non calculable.
    Protège les erreurs 'Null geometry cannot be converted to a point'.
    """
    if not geom or geom.isEmpty():
        return None
    try:
        length = float(geom.length() or 0.0)
        if length <= 0.0:
            return None
        # borne l'offset
        off = max(0.0, min(offset, length))
        gpt = geom.interpolate(off)
        if not gpt or gpt.isEmpty():
            return None
        return gpt.asPoint()
    except Exception:
        return None


def calculate_angle(geom: QgsGeometry, offset: float) -> float:
    """
    Angle (degrés) de la tangente à la polyline au voisinage d'un offset.
    0° = Est, 90° = Nord (mêmes conventions que atan2).
    """
    if not geom or geom.isEmpty():
        return 0.0
    total = float(geom.length() or 0.0)
    if total <= 0.0:
        return 0.0

    # petit delta (en unités carte) pour l’approx de la tangente
    delta = max(0.001 * total, 0.1)

    p1 = safe_interpolate_point(geom, offset)
    p2 = safe_interpolate_point(geom, min(offset + delta, total))
    if not p1 or not p2:
        return 0.0

    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    if dx == 0.0 and dy == 0.0:
        return 0.0

    return math.degrees(math.atan2(dy, dx))


def create_arrow_geometry(center: QgsPointXY, angle_degrees: float, size: float = 5.0) -> QgsGeometry:
    """
    Construit une petite flèche (triangle) centrée en 'center', orientée selon 'angle_degrees'.
    """
    a = math.radians(angle_degrees)

    # pointe
    p1 = QgsPointXY(center.x() + size * math.cos(a),
                    center.y() + size * math.sin(a))
    # ailes (angle d'ouverture ~ 40° de part et d'autre)
    a2 = a + math.radians(140)
    a3 = a - math.radians(140)
    p2 = QgsPointXY(center.x() + (size * 0.6) * math.cos(a2),
                    center.y() + (size * 0.6) * math.sin(a2))
    p3 = QgsPointXY(center.x() + (size * 0.6) * math.cos(a3),
                    center.y() + (size * 0.6) * math.sin(a3))

    return QgsGeometry.fromPolygonXY([[p1, p2, p3]])

# -------------------------------------------------------------------
# Enveloppe « concave » autour de la sélection (bassin visuel)
# -------------------------------------------------------------------

def _collect_selected_union(layer: Optional[QgsVectorLayer]) -> Optional[QgsGeometry]:
    """
    Union des géométries sélectionnées d'une couche (ligne).
    """
    if not layer or not layer.isValid():
        return None
    fids = layer.selectedFeatureIds()
    if not fids:
        return None

    req = QgsFeatureRequest().setFilterFids(fids)
    union: Optional[QgsGeometry] = None
    for f in layer.getFeatures(req):
        g = f.geometry()
        if not g or g.isEmpty():
            continue
        union = QgsGeometry(g) if union is None else union.combine(g)
    return union


def concave_envelope_from_selected(
    canvas,
    canal_layer: Optional[QgsVectorLayer],
    fosse_layer: Optional[QgsVectorLayer],
    base_px: float = 12.0
) -> Optional[QgsGeometry]:
    """
    Construit un polygone « enveloppe » autour des tronçons sélectionnés,
    en tamponnant légèrement les lignes sélectionnées. L’épaisseur dépend
    de l’échelle (base_px en pixels → unités carte via MUPP).
    """
    try:
        mupp = canvas.mapSettings().mapUnitsPerPixel()
    except Exception:
        mupp = 1.0
    dist = max(base_px * mupp, 0.3)

    geoms: List[QgsGeometry] = []
    g1 = _collect_selected_union(canal_layer)
    if g1:
        geoms.append(g1)
    g2 = _collect_selected_union(fosse_layer)
    if g2:
        geoms.append(g2)

    if not geoms:
        return None

    union = geoms[0]
    for g in geoms[1:]:
        union = union.combine(g)

    try:
        buf = union.buffer(dist, 8)
        if not buf or buf.isEmpty():
            return None
        simp = buf.simplify(dist * 0.4)
        return simp if simp and not simp.isEmpty() else buf
    except Exception:
        # repli minimal : enveloppe convexe
        try:
            hull = union.convexHull()
            return hull if hull and not hull.isEmpty() else None
        except Exception:
            return None
