# -*- coding: utf-8 -*-
# cheminer_indus/gui/industrial_dock_v2.py

"""
Dock avec onglets séparés pour Industriels et PV
Version 2.0 avec QTabWidget
"""

from __future__ import annotations

from typing import Dict, Callable, Optional, List

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QLineEdit, QTabWidget, QMessageBox, QFileDialog
)


class IndustrialDockV2(QDockWidget):
    """
    Dock avec onglets séparés pour Industriels et PV
    - Onglet 1 : 🏭 Industriels connectés
    - Onglet 2 : 🏠 PV non conformes
    """

    def __init__(self, parent=None):
        super().__init__("Analyses", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Widget de base
        base = QWidget(self)
        base.setObjectName("IndustrialBaseV2")
        self.setWidget(base)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Styles
        base.setStyleSheet("""
        QWidget#IndustrialBaseV2 {
            background-color: #f4f7fb;
        }
        QTabWidget::pane {
            border: 1px solid #c3d4f4;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #e9f1ff;
            color: #12355b;
            padding: 8px 16px;
            border: 1px solid #c3d4f4;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            font-weight: 600;
        }
        QTabBar::tab:hover {
            background-color: #d6e4ff;
        }
        QLabel {
            color: #12355b;
            font-weight: 600;
        }
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #b7c9e8;
            border-radius: 3px;
            padding: 3px 5px;
            color: #102a43;
        }
        QTableWidget {
            background-color: #ffffff;
            alternate-background-color: #e9f1ff;
            gridline-color: #c0d3f2;
            color: #102a43;
            selection-background-color: #c7defe;
            selection-color: #102a43;
        }
        QPushButton {
            background-color: #1f6feb;
            color: #ffffff;
            border-radius: 3px;
            padding: 6px 12px;
            border: 0px;
        }
        QPushButton:hover {
            background-color: #1554b3;
        }
        """)

        # QTabWidget principal
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Créer les onglets
        self._create_indus_tab()
        self._create_pv_tab()

        # Données
        self._raw_indus_data = {}
        self._visible_indus_data = {}
        self._raw_pv_data = {}
        self._visible_pv_data = {}

        # Callbacks
        self._cb_zoom_indus = None
        self._cb_designate_indus = None
        self._cb_zoom_pv = None
        self._cb_designate_pv = None
        self._cb_refresh = None

    def _create_indus_tab(self):
        """Crée l'onglet Industriels"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Recherche
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Recherche :"))
        self.indus_search = QLineEdit()
        self.indus_search.setPlaceholderText("Nom, activité, adresse...")
        self.indus_search.textChanged.connect(self._filter_indus)
        search_layout.addWidget(self.indus_search, 1)
        layout.addLayout(search_layout)

        # Tableau
        self.indus_table = QTableWidget()
        self.indus_table.setAlternatingRowColors(True)
        self.indus_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.indus_table)

        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        btn_zoom_indus = QPushButton("🔍 Zoom")
        btn_zoom_indus.clicked.connect(self._on_zoom_indus)
        btn_layout.addWidget(btn_zoom_indus)

        btn_designate_indus = QPushButton("🎯 Désigner comme pollueur")
        btn_designate_indus.clicked.connect(self._on_designate_indus)
        btn_layout.addWidget(btn_designate_indus)

        btn_refresh = QPushButton("🔄 Rafraîchir")
        btn_refresh.clicked.connect(self._on_refresh)
        btn_layout.addWidget(btn_refresh)

        btn_export_indus = QPushButton("📊 Export CSV")
        btn_export_indus.clicked.connect(self._export_indus_csv)
        btn_layout.addWidget(btn_export_indus)

        layout.addLayout(btn_layout)

        self.tab_widget.addTab(tab, "🏭 Industriels (0)")

    def _create_pv_tab(self):
        """Crée l'onglet PV"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Recherche
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Recherche :"))
        self.pv_search = QLineEdit()
        self.pv_search.setPlaceholderText("N° PV, adresse, commune...")
        self.pv_search.textChanged.connect(self._filter_pv)
        search_layout.addWidget(self.pv_search, 1)
        layout.addLayout(search_layout)

        # Tableau
        self.pv_table = QTableWidget()
        self.pv_table.setAlternatingRowColors(True)
        self.pv_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.pv_table)

        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        btn_zoom_pv = QPushButton("🔍 Zoom")
        btn_zoom_pv.clicked.connect(self._on_zoom_pv)
        btn_layout.addWidget(btn_zoom_pv)

        btn_designate_pv = QPushButton("🎯 Désigner comme pollueur")
        btn_designate_pv.clicked.connect(self._on_designate_pv)
        btn_layout.addWidget(btn_designate_pv)

        btn_osmose = QPushButton("🔗 Lien OSMOSE")
        btn_osmose.clicked.connect(self._open_osmose)
        btn_layout.addWidget(btn_osmose)

        btn_export_pv = QPushButton("📊 Export CSV")
        btn_export_pv.clicked.connect(self._export_pv_csv)
        btn_layout.addWidget(btn_export_pv)

        layout.addLayout(btn_layout)

        self.tab_widget.addTab(tab, "🏠 PV non conformes (0)")

    # ------------------------------------------------------------------
    # API Callbacks
    # ------------------------------------------------------------------
    def on_zoom_indus_request(self, cb: Callable[[str], None]):
        """cb(ind_id: str)"""
        self._cb_zoom_indus = cb

    def on_designate_indus_request(self, cb: Callable[[str], None]):
        """cb(ind_id: str)"""
        self._cb_designate_indus = cb

    def on_zoom_pv_request(self, cb: Callable[[str], None]):
        """cb(pv_id: str)"""
        self._cb_zoom_pv = cb

    def on_designate_pv_request(self, cb: Callable[[str], None]):
        """cb(pv_id: str)"""
        self._cb_designate_pv = cb

    def on_refresh_request(self, cb: Callable[[], None]):
        """cb()"""
        self._cb_refresh = cb

    # ------------------------------------------------------------------
    # Gestion données Industriels
    # ------------------------------------------------------------------
    def set_indus_data(self, data: Dict[str, Dict[str, str]]):
        """Définit les données industriels"""
        self._raw_indus_data = data or {}
        self._visible_indus_data = dict(self._raw_indus_data)
        self._refresh_indus_table()
        self._update_tab_titles()

    def exclude_indus_ids(self, ids: List[str]):
        """Exclut des industriels du tableau"""
        if not ids:
            return
        sids = set(str(i) for i in ids)
        self._raw_indus_data = {
            k: v for k, v in self._raw_indus_data.items()
            if str(k) not in sids
        }
        self._visible_indus_data = {
            k: v for k, v in self._visible_indus_data.items()
            if str(k) not in sids
        }
        self._refresh_indus_table()
        self._update_tab_titles()

    def _refresh_indus_table(self):
        """Rafraîchit le tableau industriels"""
        self.indus_table.setRowCount(0)
        self.indus_table.setColumnCount(0)

        if not self._visible_indus_data:
            return

        # Extraire tous les champs
        all_fields = set()
        for row in self._visible_indus_data.values():
            all_fields.update(row.keys())

        # Ordre préféré
        preferred = ["id", "Nom", "Activite", "Produits", "Risques", "Adresse"]
        ordered_fields = [f for f in preferred if f in all_fields]
        remaining = sorted(f for f in all_fields if f not in ordered_fields)
        ordered_fields += remaining

        # Créer les colonnes
        self.indus_table.setColumnCount(len(ordered_fields))
        self.indus_table.setHorizontalHeaderLabels(ordered_fields)

        # Remplir les lignes
        for row_idx, (ind_id, row) in enumerate(self._visible_indus_data.items()):
            self.indus_table.insertRow(row_idx)
            risk_color = self._risk_color_for_row(row)
            for col_idx, field in enumerate(ordered_fields):
                val = str(row.get(field, "") or "")
                item = QTableWidgetItem(val)
                if col_idx == 0:
                    item.setData(Qt.UserRole, ind_id)
                if risk_color:
                    item.setBackground(risk_color)
                self.indus_table.setItem(row_idx, col_idx, item)

        self.indus_table.resizeColumnsToContents()

    def _risk_color_for_row(self, row: Dict[str, str]) -> Optional[QColor]:
        risques = str(row.get("Risques", row.get("risques", "")) or "").lower()
        if not risques.strip():
            return None

        if any(token in risques for token in ("pollution", "déversement", "deversement", "rejet")):
            return QColor("#f5b7b1")
        if any(token in risques for token in ("hydrocarbure", "huile")):
            return QColor("#f9e79f")
        if "graisse" in risques:
            return QColor("#fcf3cf")
        if any(token in risques for token in ("chimique", "solvant")):
            return QColor("#d7bde2")
        return QColor("#fadbd8")

    def _filter_indus(self):
        """Filtre les industriels selon la recherche"""
        query = self.indus_search.text().strip().lower()
        if not query:
            self._visible_indus_data = dict(self._raw_indus_data)
        else:
            self._visible_indus_data = {
                k: v for k, v in self._raw_indus_data.items()
                if any(query in str(val).lower() for val in v.values())
            }
        self._refresh_indus_table()
        self._update_tab_titles()

    # ------------------------------------------------------------------
    # Gestion données PV
    # ------------------------------------------------------------------
    def set_pv_data(self, pv_data: List[Dict]):
        """Définit les données PV"""
        self._raw_pv_data = {}
        if pv_data:
            for pv in pv_data:
                pv_id = str(pv.get('id', pv.get('num_pv', '')))
                if pv_id:
                    self._raw_pv_data[pv_id] = pv
        self._visible_pv_data = dict(self._raw_pv_data)
        self._refresh_pv_table()
        self._update_tab_titles()

    def exclude_pv_ids(self, pv_ids: List[str]):
        """Exclut des PV du tableau"""
        if not pv_ids:
            return
        spv = set(str(i) for i in pv_ids)
        self._raw_pv_data = {
            k: v for k, v in self._raw_pv_data.items()
            if str(k) not in spv
        }
        self._visible_pv_data = {
            k: v for k, v in self._visible_pv_data.items()
            if str(k) not in spv
        }
        self._refresh_pv_table()
        self._update_tab_titles()

    def _refresh_pv_table(self):
        """Rafraîchit le tableau PV"""
        self.pv_table.setRowCount(0)
        self.pv_table.setColumnCount(0)

        if not self._visible_pv_data:
            return

        # Colonnes PV
        columns = ["id", "num_pv", "adresse", "commune", "eu_vers_ep", "ep_vers_eu", "date_pv", "lien_osmose"]
        self.pv_table.setColumnCount(len(columns))
        self.pv_table.setHorizontalHeaderLabels(columns)

        # Remplir
        for row_idx, (pv_id, pv) in enumerate(self._visible_pv_data.items()):
            self.pv_table.insertRow(row_idx)
            for col_idx, col in enumerate(columns):
                val = str(pv.get(col, "") or "")
                item = QTableWidgetItem(val)
                if col_idx == 0:
                    item.setData(Qt.UserRole, pv_id)
                self.pv_table.setItem(row_idx, col_idx, item)

        self.pv_table.resizeColumnsToContents()

    def _filter_pv(self):
        """Filtre les PV selon la recherche"""
        query = self.pv_search.text().strip().lower()
        if not query:
            self._visible_pv_data = dict(self._raw_pv_data)
        else:
            self._visible_pv_data = {
                k: v for k, v in self._raw_pv_data.items()
                if any(query in str(val).lower() for val in v.values())
            }
        self._refresh_pv_table()
        self._update_tab_titles()

    # ------------------------------------------------------------------
    # Actions boutons
    # ------------------------------------------------------------------
    def _on_zoom_indus(self):
        """Zoom sur un industriel"""
        row = self.indus_table.currentRow()
        if row < 0:
            return
        item = self.indus_table.item(row, 0)
        if item and self._cb_zoom_indus:
            ind_id = item.data(Qt.UserRole)
            self._cb_zoom_indus(ind_id)

    def _on_designate_indus(self):
        """Désigner un industriel comme pollueur"""
        row = self.indus_table.currentRow()
        if row < 0:
            return
        item = self.indus_table.item(row, 0)
        if item and self._cb_designate_indus:
            ind_id = item.data(Qt.UserRole)
            self._cb_designate_indus(ind_id)

    def _on_zoom_pv(self):
        """Zoom sur un PV"""
        row = self.pv_table.currentRow()
        if row < 0:
            return
        item = self.pv_table.item(row, 0)
        if item and self._cb_zoom_pv:
            pv_id = item.data(Qt.UserRole)
            self._cb_zoom_pv(pv_id)

    def _on_designate_pv(self):
        """Désigner un PV comme pollueur"""
        row = self.pv_table.currentRow()
        if row < 0:
            return
        item = self.pv_table.item(row, 0)
        if item and self._cb_designate_pv:
            pv_id = item.data(Qt.UserRole)
            self._cb_designate_pv(pv_id)

    def _open_osmose(self):
        """Ouvrir le lien OSMOSE du PV sélectionné"""
        row = self.pv_table.currentRow()
        if row < 0:
            return
        item = self.pv_table.item(row, 0)
        if item:
            pv_id = item.data(Qt.UserRole)
            pv = self._visible_pv_data.get(pv_id)
            if pv:
                lien = pv.get('lien_osmose', '')
                if lien:
                    import webbrowser
                    webbrowser.open(lien)
                else:
                    QMessageBox.information(self, "OSMOSE", "Aucun lien OSMOSE disponible.")

    def _on_refresh(self):
        """Rafraîchir les données"""
        if self._cb_refresh:
            self._cb_refresh()

    def _export_indus_csv(self):
        """Export CSV industriels"""
        if not self._visible_indus_data:
            QMessageBox.information(self, "Export CSV", "Aucun industriel à exporter.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Exporter industriels", "", "CSV (*.csv)")
        if not path:
            return
        
        try:
            import csv
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                # Extraire champs
                all_fields = set()
                for row in self._visible_indus_data.values():
                    all_fields.update(row.keys())
                ordered_fields = sorted(all_fields)
                
                writer = csv.writer(f, delimiter=";")
                writer.writerow(ordered_fields)
                for _, row in self._visible_indus_data.items():
                    vals = [str(row.get(field, "") or "") for field in ordered_fields]
                    writer.writerow(vals)
            QMessageBox.information(self, "Export CSV", f"Export réalisé :\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export CSV", f"Erreur : {e}")

    def _export_pv_csv(self):
        """Export CSV PV"""
        if not self._visible_pv_data:
            QMessageBox.information(self, "Export CSV", "Aucun PV à exporter.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PV", "", "CSV (*.csv)")
        if not path:
            return
        
        try:
            import csv
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                columns = ["id", "num_pv", "adresse", "commune", "eu_vers_ep", "ep_vers_eu", "date_pv", "lien_osmose"]
                writer = csv.writer(f, delimiter=";")
                writer.writerow(columns)
                for _, pv in self._visible_pv_data.items():
                    vals = [str(pv.get(col, "") or "") for col in columns]
                    writer.writerow(vals)
            QMessageBox.information(self, "Export CSV", f"Export réalisé :\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export CSV", f"Erreur : {e}")

    def _update_tab_titles(self):
        """Met à jour les titres des onglets avec les compteurs"""
        nb_indus = len(self._visible_indus_data)
        nb_pv = len(self._visible_pv_data)
        self.tab_widget.setTabText(0, f"🏭 Industriels ({nb_indus})")
        self.tab_widget.setTabText(1, f"🏠 PV non conformes ({nb_pv})")

    # ------------------------------------------------------------------
    # Compatibilité avec l'ancien IndustrialDock
    # ------------------------------------------------------------------
    def set_data(self, data: Dict[str, Dict[str, str]]):
        """Compatibilité : set_data appelle set_indus_data"""
        self.set_indus_data(data)

    def exclude_ids(self, ids: List[str]):
        """Compatibilité : exclude_ids appelle exclude_indus_ids"""
        self.exclude_indus_ids(ids)
