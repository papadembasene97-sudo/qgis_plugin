# -*- coding: utf-8 -*-
# cheminer_indus/gui/diagnostics_dock.py

from __future__ import annotations
from typing import Dict, List, Tuple

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton
)


class DiagnosticsDock(QDockWidget):
    """
    Affiche un tableau regroupant :
    - INVERSIONS
    - RÉDUCTIONS DE DIAMÈTRE

    Colonnes affichées :
        Rubrique | Infos | Entité (cachée)
    """

    def __init__(self, parent=None):
        super().__init__("Diagnostics réseau", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        base = QWidget()
        self.setWidget(base)
        v = QVBoxLayout(base)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Rubrique", "Infos", "Entité"])
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setColumnHidden(2, True)  # colonne ENTITÉ cachée
        v.addWidget(self.table)

        h = QHBoxLayout()
        self.btn_zoom = QPushButton("Zoom")
        self.btn_refresh = QPushButton("Rafraîchir")
        h.addWidget(self.btn_zoom)
        h.addWidget(self.btn_refresh)
        v.addLayout(h)

        self.btn_zoom.clicked.connect(self._on_zoom)
        self.btn_refresh.clicked.connect(self._on_refresh)

        self._cb_zoom = None
        self._cb_refresh = None
        self._layers = {}
        self._results = {}

    # ----------------------------------------------------------------------
    # API externe
    # ----------------------------------------------------------------------
    def set_results(self, results, canal_layer, ouvr_layer):
        self._results = results or {}
        self._layers = {
            "canal": canal_layer.name() if canal_layer else "",
            "ouvr": ouvr_layer.name() if ouvr_layer else ""
        }
        self._fill()

    def on_zoom_request(self, callback):
        self._cb_zoom = callback

    def on_refresh_request(self, callback):
        self._cb_refresh = callback

    # ----------------------------------------------------------------------
    # Remplissage du tableau
    # ----------------------------------------------------------------------
    def _fill(self):
        self.table.setRowCount(0)

        # ---- INVERSIONS ----
        for (fid_c, info, fid_o) in self._results.get("INVERSIONS", []):
            r = self.table.rowCount()
            self.table.insertRow(r)

            self.table.setItem(r, 0, QTableWidgetItem("INVERSIONS"))
            self.table.setItem(r, 1, QTableWidgetItem(info))

            ent = QTableWidgetItem(f"{self._layers.get('canal', '')}:{fid_c}")
            ent.setData(Qt.UserRole, (self._layers.get("canal", ""), fid_c))
            self.table.setItem(r, 2, ent)

        # ---- RÉDUCTIONS ----
        for (fid_c, info, fid_o) in self._results.get("REDUCTIONS", []):
            r = self.table.rowCount()
            self.table.insertRow(r)

            self.table.setItem(r, 0, QTableWidgetItem("RÉDUCTION DE DIAMÈTRE"))
            self.table.setItem(r, 1, QTableWidgetItem(info))

            ent = QTableWidgetItem(f"{self._layers.get('canal', '')}:{fid_c}")
            ent.setData(Qt.UserRole, (self._layers.get("canal", ""), fid_c))
            self.table.setItem(r, 2, ent)

        self.table.resizeColumnsToContents()

    # ----------------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------------
    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        ent = self.table.item(row, 2)
        return ent.data(Qt.UserRole) if ent else None

    def _on_zoom(self):
        sel = self._selected()
        if sel and self._cb_zoom:
            layer_name, fid = sel
            self._cb_zoom(layer_name, int(fid))

    def _on_refresh(self):
        if self._cb_refresh:
            self._cb_refresh()
