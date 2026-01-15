# -*- coding: utf-8 -*-
# cheminer_indus/core/selection.py

from __future__ import annotations
from typing import Optional

from qgis.PyQt.QtCore import pyqtSignal, QObject, QPoint
from qgis.gui import QgsMapTool
from qgis.core import (
    QgsPointXY,
    QgsGeometry,
    QgsFeatureRequest,
    QgsVectorLayer,
    QgsRectangle,
    QgsProject,
)

class _BasePickTool(QgsMapTool):
    """
    Map tool générique pour cliquer un objet d'une couche vectorielle et
    émettre un signal avec la valeur de l'attribut id_field.
    """

    # On garde le nom EXACT attendu par main_dock : featureIdentified (str)
    featureIdentified = pyqtSignal(str)

    def __init__(self, canvas, layer: QgsVectorLayer, id_field: str):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer: QgsVectorLayer = layer
        self.id_field: str = id_field

        # tolérance de recherche (pixels)
        self._tol_px = 6

        # fallback si le champ demandé n'existe pas
        self._fallback_fields = [id_field, 'idouvrage', 'id_ouvrage', 'id', 'ID', 'Id']

    # ------------------------------
    # Utilitaires
    # ------------------------------
    def _map_point_from_event(self, e) -> QgsPointXY:
        p: QPoint = e.pos()
        return self.canvas.getCoordinateTransform().toMapCoordinates(p.x(), p.y())

    def _search_rect(self, center: QgsPointXY) -> QgsRectangle:
        """Rectangle de recherche (tolérance en px -> unités carte)"""
        mupp = self.canvas.mapSettings().mapUnitsPerPixel()
        tol = max(self._tol_px * mupp, 0.01)
        return QgsRectangle(center.x() - tol, center.y() - tol,
                            center.x() + tol, center.y() + tol)

    def _best_id_field(self) -> Optional[str]:
        """Renvoie le premier champ existant parmi les candidats."""
        if not self.layer or not self.layer.isValid():
            return None
        names = set(self.layer.fields().names())
        for c in self._fallback_fields:
            if c in names:
                return c
        return None

    # ------------------------------
    # Événement de clic
    # ------------------------------
    def canvasReleaseEvent(self, e):
        if not self.layer or not self.layer.isValid():
            return

        map_pt = self._map_point_from_event(e)
        rect   = self._search_rect(map_pt)

        req = QgsFeatureRequest().setFilterRect(rect)
        # limiter pour aller vite
        req.setLimit(50)

        best_feat = None
        best_dist = None

        for f in self.layer.getFeatures(req):
            g = f.geometry()
            if not g or g.isEmpty():
                continue
            try:
                # distance au clic
                d = g.distance(QgsGeometry.fromPointXY(map_pt))
            except Exception:
                continue
            if best_dist is None or d < best_dist:
                best_feat = f
                best_dist = d

        if best_feat is None:
            return

        # champ d'identifiant
        fld = self._best_id_field()
        if not fld:
            return

        try:
            val = best_feat[fld]
            if val is None:
                return
            self.featureIdentified.emit(str(val))
        except Exception:
            return


class MapSelectionTool(_BasePickTool):
    """
    Outil de sélection pour les OUVRAGES (par défaut id_field='idouvrage').
    Usage dans main_dock :
        self.tool_select = MapSelectionTool(self.canvas, self.ouvr_layer, id_field='idouvrage')
        self.tool_select.featureIdentified.connect(self._on_select)
    """
    def __init__(self, canvas, layer: QgsVectorLayer, id_field: str = 'idouvrage'):
        super().__init__(canvas, layer, id_field)


class AstreintSelectionTool(_BasePickTool):
    """
    Outil de sélection pour la couche d'Astreinte-Exploit (par défaut id_field='id').
    Usage dans main_dock :
        self.tool_astreint = AstreintSelectionTool(self.canvas, self.astreint_layer, id_field='id')
        self.tool_astreint.featureIdentified.connect(self._on_astreint)
    """
    def __init__(self, canvas, layer: QgsVectorLayer, id_field: str = 'id'):
        super().__init__(canvas, layer, id_field)
