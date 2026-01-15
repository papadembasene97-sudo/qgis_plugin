# -*- coding: utf-8 -*-
# cheminer_indus/animation/flow_animator.py

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple

from qgis.PyQt.QtCore import QTimer, QObject
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsVectorLayer, QgsGeometry, QgsWkbTypes, QgsPointXY
from qgis.gui import QgsRubberBand

from ..utils.geom_utils import safe_interpolate_point, calculate_angle, create_arrow_geometry


class FlowAnimator(QObject):
    """
    Flèches animées sur les entités sélectionnées.

    - Couleurs configurables: set_colors(ep, eu, def)
    - Règles d’espacement: set_spacing_rules(short_max, short_arrows, long_min, long_arrows)
        * longueur < short_max  -> short_arrows (nb de flèches)
        * longueur >= long_min  -> long_arrows  (nb de flèches)
        * sinon -> interpolation linéaire entre short_arrows et long_arrows
    - Pause automatique pendant la navigation (pan/zoom) sur la carte,
      reprise automatique (debounce) dès que l’on s’arrête de naviguer.
    """

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas

        # Couches sources (uniquement linéaires seront utilisées)
        self.layers: List[QgsVectorLayer] = []

        # Eléments animés (un item = un triangle/arrow animé le long d'une géométrie)
        self.items: List[Dict[str, Any]] = []

        # Timer d’animation
        self.timer: Optional[QTimer] = None

        # Timer de reprise après navigation (debounce)
        self._resume_timer: Optional[QTimer] = None

        # Etat navigation
        self._nav_paused: bool = False

        # Echelle
        self._mupp = None  # mapUnitsPerPixel (pour adapter la taille/ vitesse)

        # Vitesse en pixels par tick (tick ~ 40ms)
        self._px_speed = 10.0

        # Couleurs (défauts, modifiables via set_colors)
        # EP = 01 (bleu), EU = 02 (brun), Défaut = rouge (selon demande)
        self.col_ep  = QColor("#0066FF")
        self.col_eu  = QColor("#7A3B00")
        self.col_def = QColor("#6B686852")

        # Règles d’espacement (défaut)
        self._short_max = 35.0
        self._short_ar  = (3,)
        self._long_min  = 35.0
        self._long_ar   = (5,)

        # Connexions aux signaux du canvas pour pause/reprise auto
        try:
            # Appelé à chaque changement d'emprise (pan/zoom)
            self.canvas.extentsChanged.connect(self._on_canvas_extents_changed)
        except Exception:
            # Au cas où un canvas custom n’expose pas le signal
            pass

    # ---------------------------
    # Configuration
    # ---------------------------
    def set_spacing_rules(
        self,
        short_max: float,
        short_arrows: Tuple[int, ...],
        long_min: float,
        long_arrows: Tuple[int, ...]
    ):
        self._short_max = float(short_max)
        self._short_ar  = tuple(short_arrows) if short_arrows else (3,)
        self._long_min  = float(long_min)
        self._long_ar   = tuple(long_arrows) if long_arrows else (5,)

    def set_colors(
        self,
        col_ep: Optional[QColor] = None,
        col_eu: Optional[QColor] = None,
        col_def: Optional[QColor] = None
    ):
        """Met à jour les couleurs et reconstruit les items pour appliquer la nouvelle palette."""
        if col_ep is not None:
            self.col_ep = QColor(col_ep)
        if col_eu is not None:
            self.col_eu = QColor(col_eu)
        if col_def is not None:
            self.col_def = QColor(col_def)

        # Rebuild pour recalculer la couleur de chaque item selon _color_for(...)
        self._rebuild_items()
        self.canvas.refresh()

    def setLayers(self, layers: List[QgsVectorLayer]):
        """Définit les couches sources (les non valides seront ignorées)."""
        self.layers = [l for l in (layers or []) if l and l.isValid()]

    def set_speed(self, px_per_tick: float):
        """Vitesse en pixels d’écran par tick (>= 2.0)."""
        self._px_speed = max(2.0, float(px_per_tick))

    # ---------------------------
    # Cycle de vie
    # ---------------------------
    def start(self):
        """Démarre l'animation (ou redémarre proprement)."""
        self.stop()  # stop propre si déjà lancé
        self._rebuild_items()
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(80)  # ~25 FPS
        self._nav_paused = False  # on part actif

    def stop(self):
        """Arrête l'animation et nettoie les RubberBands."""
        # Stop timers
        if self.timer:
            try:
                self.timer.stop()
                self.timer.timeout.disconnect(self._tick)
            except Exception:
                pass
            self.timer.deleteLater()
            self.timer = None

        if self._resume_timer:
            try:
                self._resume_timer.stop()
            except Exception:
                pass
            self._resume_timer.deleteLater()
            self._resume_timer = None

        # Supprime les RB
        for it in self.items:
            try:
                it["rb"].reset()
            except Exception:
                pass
        self.items = []
        self.canvas.refresh()

    # ---------------------------
    # Navigation (pause auto)
    # ---------------------------
    def _on_canvas_extents_changed(self):
        """
        Appelé à chaque changement d'emprise (panning/zoom).
        On met en pause l'animation et on programme une reprise
        immédiate dès que la navigation cesse pendant un court
        délai (debounce).
        """
        # Pause immédiate
        self._pause_for_navigation()

        # (Re)programme une reprise après un court délai (p.ex. 250 ms)
        if not self._resume_timer:
            self._resume_timer = QTimer()
            self._resume_timer.setSingleShot(True)
            self._resume_timer.timeout.connect(self._resume_after_navigation)

        # Redémarre le compte à rebours (debounce)
        try:
            self._resume_timer.start(250)
        except Exception:
            pass

    def _pause_for_navigation(self):
        """Met l'animation en pause sans détruire les items (effet visuel OFF)."""
        if self._nav_paused:
            return
        self._nav_paused = True

        # Couper le timer pour stopper le _tick()
        if self.timer and self.timer.isActive():
            self.timer.stop()

        # Option: masquer visuellement les flèches pendant le pan/zoom (pour plus de fluidité)
        for it in self.items:
            try:
                it["rb"].reset()
            except Exception:
                pass
        self.canvas.refresh()

    def _resume_after_navigation(self):
        """Relance l'animation une fois le pan/zoom terminé (debounce écoulé)."""
        self._nav_paused = False

        # Re-calcul MUPP et rebuild à la reprise, car l’échelle a probablement changé.
        self._rebuild_items()

        # Relancer le timer
        if self.timer and not self.timer.isActive():
            try:
                self.timer.start(40)
            except Exception:
                pass
        self.canvas.refresh()

    # ---------------------------
    # Logique interne
    # ---------------------------
    def _color_for(self, layer: QgsVectorLayer, feat) -> QColor:
        """
        Renvoie la couleur selon attribut réseau et/ou nom de couche.
        - 02 -> EU (col_eu)
        - 01 ou 03 -> EP (col_ep)
        - fossé/cours d'eau -> EP
        - sinon -> col_def
        """
        try:
            names = feat.fields().names()
        except Exception:
            names = []
        tfield = "typreseau" if "typreseau" in names else ("type_reseau" if "type_reseau" in names else None)
        code = str(feat[tfield]) if (tfield and feat[tfield] is not None) else None

        if code == "02":
            return self.col_eu
        if code in ("01", "03"):
            return self.col_ep

        lname = layer.name().lower()
        if "fosse" in lname or "cours" in lname:
            return self.col_ep

        return self.col_def

    def _choose_nb(self, L: float) -> int:
        """Détermine le nombre d’items (flèches) à instancier selon la longueur."""
        if L < self._short_max:
            return max(self._short_ar)
        if L >= self._long_min:
            return max(self._long_ar)
        # Zone intermédiaire -> interpolation
        a = max(self._short_ar)
        b = max(self._long_ar)
        ratio = 0.0
        if self._long_min > self._short_max:
            ratio = (L - self._short_max) / (self._long_min - self._short_max)
            ratio = max(0.0, min(1.0, ratio))
        return int(round(a + ratio * (b - a))) or 1

    def _rebuild_items(self):
        """Reconstruit tous les items (taille, couleur, espacement) à partir des entités sélectionnées."""
        # Nettoyage précédent
        for it in self.items:
            try:
                it["rb"].reset()
            except Exception:
                pass
        self.items = []

        if not self.layers:
            return

        # Taille des flèches en unités cartes (fonction du MUPP)
        self._mupp = self.canvas.mapSettings().mapUnitsPerPixel()
        size = max(4.0 * self._mupp, 1.0)

        # Parcours des couches
        for layer in self.layers:
            try:
                if layer.geometryType() != QgsWkbTypes.LineGeometry:
                    continue
            except Exception:
                continue

            # On ne prend que les entités SÉLECTIONNÉES
            feats = layer.getSelectedFeatures()
            for f in feats:
                geom: QgsGeometry = f.geometry()
                if not geom or geom.isEmpty():
                    continue
                L = float(geom.length() or 0.0)
                if L <= 0.0:
                    continue

                nb = self._choose_nb(L)
                color = self._color_for(layer, f)
                spacing = L / float(nb)

                # Crée 'nb' items répartis régulièrement
                for k in range(nb):
                    rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
                    rb.setColor(color)
                    rb.setFillColor(color)
                    rb.setWidth(1)

                    self.items.append({
                        "layer": layer,
                        "geom": geom,      # on conserve la géométrie QGIS
                        "length": L,
                        "offset": k * spacing,
                        "spacing": spacing,
                        "rb": rb,
                        "size": size,
                    })

    def _tick(self):
        """Une étape d’animation: avance les offsets, redessine les triangles."""
        if not self.items:
            return

        # Si on a changé d’échelle (MUPP), rebuild pour garder la bonne taille
        mupp_now = self.canvas.mapSettings().mapUnitsPerPixel()
        if self._mupp is None or abs(mupp_now - self._mupp) > 1e-9:
            self._rebuild_items()
            return

        # Avancée par tick (en unités carte)
        step = self._px_speed * mupp_now
        redraw = False

        for it in self.items:
            geom: QgsGeometry = it["geom"]
            L = it["length"]

            # Nouvelle position
            it["offset"] = (it["offset"] + step) % L

            # Point/angle sur la géométrie
            p = safe_interpolate_point(geom, it["offset"])
            if not p:
                continue
            angle = calculate_angle(geom, it["offset"])

            # Triangle (flèche)
            tri = create_arrow_geometry(QgsPointXY(p.x(), p.y()), angle, it["size"])
            try:
                it["rb"].setToGeometry(tri, it["layer"])
                redraw = True
            except Exception:
                continue

        if redraw:
            self.canvas.refresh()
