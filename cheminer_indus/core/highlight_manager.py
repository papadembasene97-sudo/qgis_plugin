# -*- coding: utf-8 -*-
# cheminer_indus/core/highlight_manager.py

from __future__ import annotations
from typing import Optional

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsFillSymbol, QgsSingleSymbolRenderer
)
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapCanvas


class HighlightManager:
    """
    Gestionnaire d'affichage du contour (bassin de collecte) dans une couche
    MÉMOIRE unique "BASSIN_COLLECTE (temp)".

    ⚙️ Rôle : il n'effectue AUCUN calcul géométrique (concave hull, etc.)
    Il se contente d'INSÉRER dans une couche mémoire le polygone qu'on lui
    transmet (déjà calculé à partir des canalisations ET des fossés).
    """

    LAYER_NAME = "BASSIN_COLLECTE (temp)"  # nom unique dans le projet

    def __init__(self, canvas: QgsMapCanvas):
        self.canvas = canvas
        self._layer: Optional[QgsVectorLayer] = None

    # ------------------------------------------------------------------
    # Couche mémoire : création si absente, sinon réutilisation
    # ------------------------------------------------------------------
    def _ensure_layer(self, outline_width_mm: float = 1.2) -> QgsVectorLayer:
        """
        Garantit l'existence d'une couche mémoire polygonale pour le bassin.
        - Cherche d'abord une couche EXISTANTE dans le projet portant LAYER_NAME
          (pour éviter toute recréation inutile).
        - Si absente, la crée une fois, la stylise (trait blanc, remplissage transparent),
          et l'ajoute au projet.

        outline_width_mm : épaisseur du trait (mm). Laisse 1.2 pour le rendu recommandé.
        """
        # 1) Réutiliser une couche déjà présente dans le projet (si on l'a ajoutée
        #    précédemment et que self._layer a été perdu, par exemple après reload).
        if self._layer is None:
            for lyr in QgsProject.instance().mapLayers().values():
                if isinstance(lyr, QgsVectorLayer) and lyr.name() == self.LAYER_NAME and lyr.isValid():
                    self._layer = lyr
                    break

        # 2) Si on n'a toujours rien : créer la couche mémoire
        if not self._layer or not self._layer.isValid():
            vdef = "Polygon?crs=EPSG:2154"
            self._layer = QgsVectorLayer(vdef, self.LAYER_NAME, "memory")

            # Style : contour blanc 100 %, remplissage transparent
            outline = QColor(255, 255, 255)
            fill = QColor(255, 255, 255, 0)  # alpha 0 = transparent

            # On crée le symbole de remplissage avec trait seul (remplissage transparent)
            fsym = QgsFillSymbol.createSimple({
                'outline_color': f'{outline.red()},{outline.green()},{outline.blue()}',
                'outline_width': str(outline_width_mm),
                'color': f'{fill.red()},{fill.green()},{fill.blue()},{fill.alpha()}',
                'style': 'no'  # pas de motif de remplissage
            })
            self._layer.setRenderer(QgsSingleSymbolRenderer(fsym))

            QgsProject.instance().addMapLayer(self._layer)

        return self._layer

    # ------------------------------------------------------------------
    # API d'affichage
    # ------------------------------------------------------------------
    def show_polygon(self, geom: Optional[QgsGeometry], outline_width_mm: float = 1.2):
        """
        Affiche le polygone 'geom' dans la couche mémoire de bassin.
        - 'geom' doit être une géométrie de type POLYGON/MULTIPOLYGON (ex: concave hull).
        - 'outline_width_mm' permet d'épaissir le trait si nécessaire.

        📌 NOTE : Si vous avez calculé le contour à partir des canalisations ET des fossés
                  (côté MainDock/concave_envelope_from_selected), il sera affiché tel quel.
        """
        lyr = self._ensure_layer(outline_width_mm)
        prov = lyr.dataProvider()

        # On repart proprement (un seul polygone à afficher)
        prov.truncate()

        if geom and not geom.isEmpty():
            f = QgsFeature()
            f.setGeometry(geom)
            prov.addFeatures([f])

        lyr.triggerRepaint()
        self.canvas.refresh()

    def clear(self):
        """Efface le bassin affiché (la couche reste dans le projet)."""
        if not self._layer or not self._layer.isValid():
            # Chercher si une couche existe malgré tout dans le projet
            for lyr in QgsProject.instance().mapLayers().values():
                if isinstance(lyr, QgsVectorLayer) and lyr.name() == self.LAYER_NAME and lyr.isValid():
                    self._layer = lyr
                    break
        if self._layer and self._layer.isValid():
            try:
                self._layer.dataProvider().truncate()
                self._layer.triggerRepaint()
            except Exception:
                pass
        self.canvas.refresh()

    # ------------------------------------------------------------------
    # Optionnel : accès direct à la couche (pour debug/paramétrage avancé)
    # ------------------------------------------------------------------
    def layer(self) -> Optional[QgsVectorLayer]:
        """
        Retourne la couche mémoire du bassin si elle existe (ou None si jamais affichée).
        Utile si vous voulez modifier manuellement le style depuis le code appelant.
        """
        return self._layer
