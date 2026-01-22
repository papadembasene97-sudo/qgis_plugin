# -*- coding: utf-8 -*-
# cheminer_indus/gui/pv_conformite_tab.py

from __future__ import annotations

from typing import Dict, List, Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QSpinBox, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox
)
from qgis.PyQt.QtCore import QUrl


class PVConformiteTab(QWidget):
    """Onglet PV Conformité avec analyse Industriels + PV."""

    def __init__(self, main_dock, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_dock = main_dock

        self._last_indus_data: Dict[str, Dict[str, str]] = {}
        self._last_pv_data: Dict[str, Dict[str, str]] = {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("🏠 Analyse Industrielle + Conformité PV")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        desc = QLabel(
            "Analysez les industriels connectés et les PV non conformes\n"
            "sur un cheminement de réseau EU/EP."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        config_group = QGroupBox("⚙️ Configuration de l'analyse")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(6)

        steps = QLabel(
            "1. Réalisez un cheminement depuis l'onglet Cheminement\n"
            "2. Cliquez sur \"Analyser\" pour détecter les industriels et PV non conformes"
        )
        steps.setWordWrap(True)
        config_layout.addWidget(steps)

        distance_layout = QHBoxLayout()
        distance_layout.addWidget(QLabel("Distance de recherche PV :"))
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(1, 500)
        self.distance_spin.setValue(15)
        self.distance_spin.setSuffix(" m")
        distance_layout.addWidget(self.distance_spin)
        distance_layout.addStretch()
        config_layout.addLayout(distance_layout)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type de réseau :"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Tous", "EU", "EP", "Unitaire"])
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        config_layout.addLayout(type_layout)

        self.analyze_btn = QPushButton("🔍 Analyser le cheminement")
        self.analyze_btn.clicked.connect(self._on_analyze)
        config_layout.addWidget(self.analyze_btn)

        self.status_label = QLabel("Aucune analyse effectuée")
        self.status_label.setStyleSheet("color: #666;")
        config_layout.addWidget(self.status_label)

        layout.addWidget(config_group)

        tables_layout = QHBoxLayout()

        self.indus_table = self._create_table_group("🏭 Industriels connectés")
        tables_layout.addWidget(self.indus_table["group"])

        self.pv_table = self._create_table_group("🏠 PV non conformes")
        tables_layout.addWidget(self.pv_table["group"])

        layout.addLayout(tables_layout)

        actions_group = QGroupBox("🧹 Actions")
        actions_layout = QHBoxLayout(actions_group)

        btn_export = QPushButton("📊 Exporter en CSV")
        btn_export.clicked.connect(self._on_export_csv)
        actions_layout.addWidget(btn_export)

        btn_visualize = QPushButton("🗺️ Visualiser sur la carte")
        btn_visualize.clicked.connect(self._on_visualize_map)
        actions_layout.addWidget(btn_visualize)

        btn_report = QPushButton("🧾 Générer un rapport")
        btn_report.clicked.connect(self._on_generate_report)
        actions_layout.addWidget(btn_report)

        btn_clear = QPushButton("🧼 Nettoyer la carte")
        btn_clear.clicked.connect(self._on_clear_map)
        actions_layout.addWidget(btn_clear)

        layout.addWidget(actions_group)

    def _create_table_group(self, title: str) -> Dict[str, object]:
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)

        table = QTableWidget()
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        group_layout.addWidget(table)

        btn_layout = QHBoxLayout()
        btn_zoom = QPushButton("🔍 Zoomer")
        btn_zoom.clicked.connect(lambda: self._on_zoom(table))
        btn_layout.addWidget(btn_zoom)

        btn_designate = QPushButton("🎯 Désigner comme pollueur")
        btn_designate.clicked.connect(lambda: self._on_designate(table))
        btn_layout.addWidget(btn_designate)

        if "PV" in title:
            btn_osmose = QPushButton("🔗 Voir dans OSMOSE")
            btn_osmose.clicked.connect(lambda: self._on_open_osmose(table))
            btn_layout.addWidget(btn_osmose)

        group_layout.addLayout(btn_layout)
        return {"group": group, "table": table}

    def _on_analyze(self):
        start_id = (self.main_dock.id_input.text() or "").strip() if self.main_dock.id_input else ""
        if not start_id:
            QMessageBox.warning(
                self,
                "ID manquant",
                "Veuillez saisir un ID ouvrage dans l'onglet Cheminement."
            )
            return

        pv_layer = self.main_dock.pv_combo.currentData() if self.main_dock.pv_combo else None
        if not pv_layer or not pv_layer.isValid():
            QMessageBox.warning(
                self,
                "Couche PV manquante",
                "Veuillez sélectionner une couche PV dans l'onglet Paramètres."
            )
            return
        self.main_dock.pv_layer = pv_layer
        try:
            from ..core.pv_service import PVService
            canal_layer = self.main_dock.canal_combo.currentData() if self.main_dock.canal_combo else None
            if canal_layer and canal_layer.isValid():
                self.main_dock.pv_svc = PVService(pv_layer, canal_layer)
        except Exception:
            self.main_dock.pv_svc = None

        filters = {"category": "", "function": ""}
        type_val = self.type_combo.currentText()
        if type_val == "EU":
            filters["category"] = "02"
        elif type_val == "EP":
            filters["category"] = "01"
        elif type_val == "Unitaire":
            filters["category"] = "03"

        self.main_dock._trace_for_industrials(
            start_id=start_id,
            filters=filters,
            pv_distance=float(self.distance_spin.value())
        )

        self._last_indus_data = self.main_dock._last_indus_data or {}
        self._last_pv_data = self.main_dock._last_pv_data or {}

        self._refresh_tables()

        self.status_label.setText(
            f"Industriels : {len(self._last_indus_data)} | "
            f"PV non conformes : {len(self._last_pv_data)}"
        )

    def _refresh_tables(self):
        self._refresh_indus_table()
        self._refresh_pv_table()

    def _refresh_indus_table(self):
        table = self.indus_table["table"]
        table.setRowCount(0)
        table.setColumnCount(0)

        if not self._last_indus_data:
            return

        all_fields = set()
        for row in self._last_indus_data.values():
            all_fields.update(row.keys())

        preferred = ["id", "Nom", "Activite", "Adresse", "Commune", "distance"]
        ordered_fields = [f for f in preferred if f in all_fields]
        remaining = sorted(f for f in all_fields if f not in ordered_fields)
        ordered_fields += remaining

        table.setColumnCount(len(ordered_fields))
        table.setHorizontalHeaderLabels(ordered_fields)

        for row_idx, (ind_id, row) in enumerate(self._last_indus_data.items()):
            table.insertRow(row_idx)
            for col_idx, field in enumerate(ordered_fields):
                val = str(row.get(field, "") or "")
                item = QTableWidgetItem(val)
                if col_idx == 0:
                    item.setData(Qt.UserRole, ind_id)
                table.setItem(row_idx, col_idx, item)

        table.resizeColumnsToContents()

    def _refresh_pv_table(self):
        table = self.pv_table["table"]
        table.setRowCount(0)
        table.setColumnCount(0)

        if not self._last_pv_data:
            return

        columns = [
            ("num_pv", "N° PV"),
            ("adresse", "Adresse"),
            ("commune", "Commune"),
            ("eu_vers_ep", "EU→EP"),
            ("ep_vers_eu", "EP→EU"),
            ("canal", "Canal"),
            ("distance", "Distance (m)")
        ]

        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels([label for _, label in columns])

        for row_idx, (pv_id, pv) in enumerate(self._last_pv_data.items()):
            table.insertRow(row_idx)
            for col_idx, (key, _) in enumerate(columns):
                val = str(pv.get(key, "") or "")
                item = QTableWidgetItem(val)
                if col_idx == 0:
                    item.setData(Qt.UserRole, pv_id)
                table.setItem(row_idx, col_idx, item)

        table.resizeColumnsToContents()

    def _selected_id(self, table: QTableWidget) -> Optional[str]:
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        if item:
            return str(item.data(Qt.UserRole) or item.text()).strip()
        return None

    def _on_zoom(self, table: QTableWidget):
        item_id = self._selected_id(table)
        if not item_id:
            return
        if table is self.indus_table["table"]:
            self.main_dock._zoom_to_industrial(item_id)
        else:
            self.main_dock._zoom_to_pv(item_id)

    def _on_designate(self, table: QTableWidget):
        item_id = self._selected_id(table)
        if not item_id:
            return
        if table is self.indus_table["table"]:
            self.main_dock._designate_industrial(item_id)
        else:
            self.main_dock._designate_pv(item_id)

    def _on_open_osmose(self, table: QTableWidget):
        item_id = self._selected_id(table)
        if not item_id:
            return

        pv = self._last_pv_data.get(item_id, {})
        url = pv.get("lien_osmose") or pv.get("url_osmose") or pv.get("lien") or ""
        if not url:
            QMessageBox.information(self, "OSMOSE", "Aucun lien OSMOSE disponible.")
            return
        QDesktopServices.openUrl(QUrl(url))

    def _on_export_csv(self):
        if self.main_dock.industrial_dock:
            self.main_dock.industrial_dock._export_indus_csv()
            if hasattr(self.main_dock.industrial_dock, "_export_pv_csv"):
                self.main_dock.industrial_dock._export_pv_csv()
            return
        QMessageBox.information(self, "Export CSV", "Aucune donnée à exporter.")

    def _on_visualize_map(self):
        if self.main_dock.canvas:
            self.main_dock.canvas.refresh()

    def _on_generate_report(self):
        self.main_dock._make_report_with_wait()

    def _on_clear_map(self):
        self.main_dock._reset()
