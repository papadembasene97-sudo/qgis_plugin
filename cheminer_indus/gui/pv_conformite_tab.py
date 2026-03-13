# -*- coding: utf-8 -*-
# cheminer_indus/gui/pv_conformite_tab.py

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QDesktopServices, QColor
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QScrollArea, QSizePolicy
)
from qgis.PyQt.QtCore import QUrl

from ..utils.qt_compat import QT_ALIGN_CENTER, QT_USER_ROLE


class PVConformiteTab(QWidget):
    """Onglet PV Conformité avec analyse PV."""

    def __init__(self, main_dock, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_dock = main_dock

        self._last_pv_data: Dict[str, Dict[str, str]] = {}
        self._visible_pv_data: Dict[str, Dict[str, str]] = {}

        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        scroll.setWidget(content)

        layout = QVBoxLayout(content)

        self.title_label = QLabel("🏠 Analyse Conformité PV")
        self.title_label.setAlignment(QT_ALIGN_CENTER)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.title_label)

        self.desc_label = QLabel(
            "Analysez les PV conformes et non conformes\n"
            "sur un cheminement de réseau EU/EP."
        )
        self.desc_label.setAlignment(QT_ALIGN_CENTER)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        self.config_group = QGroupBox("⚙️ Configuration de l'analyse")
        config_layout = QVBoxLayout(self.config_group)
        config_layout.setSpacing(6)

        self.steps_label = QLabel(
            "1. Réalisez un cheminement depuis l'onglet Cheminement\n"
            "2. Cliquez sur \"Analyser\" pour détecter les PV"
        )
        self.steps_label.setWordWrap(True)
        config_layout.addWidget(self.steps_label)

        distance_layout = QHBoxLayout()
        self.distance_label = QLabel("Distance de recherche PV :")
        distance_layout.addWidget(self.distance_label)
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(1, 500)
        self.distance_spin.setValue(15)
        self.distance_spin.setSuffix(" m")
        distance_layout.addWidget(self.distance_spin)
        distance_layout.addStretch()
        config_layout.addLayout(distance_layout)

        self.analyze_btn = QPushButton("🔍 Analyser le cheminement")
        self.analyze_btn.clicked.connect(self._on_analyze)
        config_layout.addWidget(self.analyze_btn)

        self.status_label = QLabel("Aucune analyse effectuée")
        self.status_label.setStyleSheet("color: #666;")
        config_layout.addWidget(self.status_label)

        layout.addWidget(self.config_group)

        self.pv_table = self._create_table_group("🏠 PV détectés")
        layout.addWidget(self.pv_table["group"])

        self.actions_group = QGroupBox("🧹 Actions")
        actions_layout = QHBoxLayout(self.actions_group)

        self.btn_export = QPushButton("📊 Exporter en CSV")
        self.btn_export.clicked.connect(self._on_export_csv)
        actions_layout.addWidget(self.btn_export)

        self.btn_report = QPushButton("🧾 Générer un rapport")
        self.btn_report.clicked.connect(self._on_generate_report)
        actions_layout.addWidget(self.btn_report)

        self.btn_clear = QPushButton("🧼 Nettoyer la carte")
        self.btn_clear.clicked.connect(self._on_clear_map)
        actions_layout.addWidget(self.btn_clear)

        layout.addWidget(self.actions_group)
        layout.addStretch()

    def _create_table_group(self, title: str) -> Dict[str, object]:
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)

        search_layout = QHBoxLayout()
        self.search_label = QLabel("Recherche :")
        search_layout.addWidget(self.search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrer sur toutes les colonnes...")
        self.search_input.textChanged.connect(self._apply_search)
        search_layout.addWidget(self.search_input, 1)
        group_layout.addLayout(search_layout)

        table = QTableWidget()
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        group_layout.addWidget(table)

        btn_layout = QHBoxLayout()
        self.btn_zoom = QPushButton("🔍 Zoomer")
        self.btn_zoom.clicked.connect(lambda: self._on_zoom(table))
        btn_layout.addWidget(self.btn_zoom)

        self.btn_designate = QPushButton("🎯 Désigner comme pollueur")
        self.btn_designate.clicked.connect(lambda: self._on_designate(table))
        btn_layout.addWidget(self.btn_designate)

        if "PV" in title:
            self.btn_osmose = QPushButton("🔗 Voir dans OSMOSE")
            self.btn_osmose.clicked.connect(lambda: self._on_open_osmose(table))
            btn_layout.addWidget(self.btn_osmose)

        group_layout.addLayout(btn_layout)
        return {"group": group, "table": table, "search": self.search_input}

    def _on_analyze(self):
        self.main_dock._run_with_wait_cursor(
            self._do_analyze,
            process_key="pv_analyze",
            label="Analyse PV en cours..."
        )

    def _do_analyze(self):
        nodes = getattr(self.main_dock, "_last_trace_nodes", None) or set()
        if not nodes:
            QMessageBox.warning(
                self,
                "Cheminement manquant",
                "Veuillez d'abord effectuer un cheminement depuis l'onglet Cheminement."
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

        pv_details = {}
        if self.main_dock.pv_svc:
            pv_ids = self.main_dock.pv_svc.connected_ids_from_nodes(
                nodes,
                distance=float(self.distance_spin.value()),
                include_conformes=True
            )
            pv_details = self.main_dock.pv_svc.fetch_many(
                pv_ids,
                include_conformes=True
            )
            for pv_id in pv_details:
                distance = self.main_dock.pv_svc.get_distance_to_network(pv_id)
                if distance is not None:
                    pv_details[pv_id]["distance"] = str(distance)

        self._last_pv_data = self._annotate_pv_data(pv_details)
        self._visible_pv_data = dict(self._last_pv_data)
        self._apply_search()

        self.status_label.setText(
            f"PV détectés : {len(self._last_pv_data)}"
        )

    def _refresh_tables(self):
        self._refresh_pv_table()

    def _apply_search(self):
        pv_query = self.pv_table["search"].text().strip().lower()
        if not pv_query:
            self._visible_pv_data = dict(self._last_pv_data)
        else:
            self._visible_pv_data = {
                k: v for k, v in self._last_pv_data.items()
                if any(pv_query in str(val).lower() for val in v.values())
            }
        self._refresh_tables()

    def _refresh_pv_table(self):
        table = self.pv_table["table"]
        table.setRowCount(0)
        table.setColumnCount(0)

        if not self._visible_pv_data:
            return
        all_fields = set()
        for row in self._visible_pv_data.values():
            all_fields.update(row.keys())
        preferred = [
            "num_pv",
            "adresse",
            "commune",
            "conforme",
            "type_visite",
            "date_pv",
            "eu_vers_ep",
            "ep_vers_eu",
            "distance"
        ]
        ordered_fields = [f for f in preferred if f in all_fields]
        ordered_fields += sorted(f for f in all_fields if f not in ordered_fields)

        table.setColumnCount(len(ordered_fields))
        table.setHorizontalHeaderLabels(ordered_fields)

        for row_idx, (pv_id, pv) in enumerate(self._visible_pv_data.items()):
            table.insertRow(row_idx)
            for col_idx, key in enumerate(ordered_fields):
                val = str(pv.get(key, "") or "")
                item = QTableWidgetItem(val)
                if col_idx == 0:
                    item.setData(QT_USER_ROLE, pv_id)
                table.setItem(row_idx, col_idx, item)
                self._apply_pv_cell_style(item, key)

        table.resizeColumnsToContents()

    def _annotate_pv_data(self, pv_details: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        if not pv_details:
            return {}

        pv_layer = self.main_dock.pv_layer
        if not pv_layer or not pv_layer.isValid():
            return pv_details

        pv_ids = set(pv_details.keys())
        pv_meta: Dict[str, Tuple[Optional[datetime], Optional[object]]] = {}
        id_field = None
        for field_name in ["id", "num_pv", "ID", "NUM_PV"]:
            if pv_layer.fields().indexOf(field_name) >= 0:
                id_field = field_name
                break

        if id_field is None:
            return pv_details

        for feat in pv_layer.getFeatures():
            pv_id = feat.attribute(id_field)
            if pv_id is None:
                continue
            pv_id_str = str(pv_id)
            if pv_id_str not in pv_ids:
                continue
            date_value = None
            for date_field in ["date_pv", "DATE_PV", "date", "date_visite"]:
                if feat.fields().indexOf(date_field) >= 0:
                    date_value = feat.attribute(date_field)
                    break
            pv_meta[pv_id_str] = (
                self._parse_date(date_value),
                feat.geometry()
            )

        overlap_groups = self._build_overlap_groups(pv_meta)
        annotated = dict(pv_details)
        for pv_id, row in annotated.items():
            row["conforme"] = self._format_conforme(row)

        for group in overlap_groups:
            dates = [(pv_id, pv_meta[pv_id][0]) for pv_id in group]
            dates = [(pv_id, dt) for pv_id, dt in dates if dt is not None]
            if not dates:
                continue
            dates.sort(key=lambda x: x[1])
            earliest = dates[0][1]
            latest_id, latest_dt = dates[-1]
            if (latest_dt - earliest).days >= 7:
                annotated[latest_id]["type_visite"] = "Contre-visite"
                for pv_id, _ in dates[:-1]:
                    annotated[pv_id]["type_visite"] = "Visite"

        for pv_id, row in annotated.items():
            row.setdefault("type_visite", "Visite")
        return annotated

    def _build_overlap_groups(
        self,
        pv_meta: Dict[str, Tuple[Optional[datetime], Optional[object]]]
    ) -> List[List[str]]:
        ids = list(pv_meta.keys())
        if len(ids) < 2:
            return []

        from qgis.core import QgsSpatialIndex, QgsFeature

        index = QgsSpatialIndex()
        geom_cache: Dict[str, object] = {}
        id_map: Dict[int, str] = {}
        for idx, (pv_id, (_, geom)) in enumerate(pv_meta.items(), start=1):
            if not geom:
                continue
            geom_cache[pv_id] = geom
            feat = QgsFeature()
            feat.setId(idx)
            feat.setGeometry(geom)
            index.addFeature(feat)
            id_map[idx] = pv_id

        parent = {pv_id: pv_id for pv_id in geom_cache}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for pv_id, geom in geom_cache.items():
            candidate_ids = index.intersects(geom.boundingBox())
            for cand_id in candidate_ids:
                other_id = id_map.get(cand_id)
                if not other_id or other_id == pv_id:
                    continue
                other_geom = geom_cache.get(other_id)
                if other_geom and geom.intersects(other_geom):
                    union(pv_id, other_id)

        groups: Dict[str, List[str]] = {}
        for pv_id in geom_cache:
            root = find(pv_id)
            groups.setdefault(root, []).append(pv_id)
        return [g for g in groups.values() if len(g) > 1]

    def _parse_date(self, value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        sval = str(value).strip()
        if not sval:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(sval, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(sval)
        except ValueError:
            return None

    def _format_conforme(self, row: Dict[str, str]) -> str:
        for field_name in ["conforme", "conformite", "conformité", "conform"]:
            for key in row.keys():
                if key.lower() != field_name:
                    continue
                sval = str(row.get(key) or "").strip().lower()
                if sval in ("oui", "yes", "true", "1"):
                    return "Oui"
                if sval:
                    return "Non"
        return "Inconnu"

    def _apply_pv_cell_style(self, item: QTableWidgetItem, field: str) -> None:
        text = (item.text() or "").strip().lower()
        if field == "conforme":
            if text == "oui":
                item.setBackground(QColor("#d5f5e3"))
            elif text == "non":
                item.setBackground(QColor("#f9d6d5"))
            else:
                item.setBackground(QColor("#f0f0f0"))
        elif field == "type_visite":
            if "contre" in text:
                item.setBackground(QColor("#d6eaf8"))
            else:
                item.setBackground(QColor("#fcf3cf"))

    def _selected_id(self, table: QTableWidget) -> Optional[str]:
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        if item:
            return str(item.data(QT_USER_ROLE) or item.text()).strip()
        return None

    def _on_zoom(self, table: QTableWidget):
        item_id = self._selected_id(table)
        if not item_id:
            return
        self.main_dock._zoom_to_pv(item_id)

    def _on_designate(self, table: QTableWidget):
        item_id = self._selected_id(table)
        if not item_id:
            return
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
        if self.main_dock.industrial_dock and hasattr(self.main_dock.industrial_dock, "_export_pv_csv"):
            self.main_dock.industrial_dock._export_pv_csv()
            return
        QMessageBox.information(self, "Export CSV", "Aucune donnée PV à exporter.")

    def _on_visualize_map(self):
        if self.main_dock.canvas:
            self.main_dock.canvas.refresh()

    def _on_generate_report(self):
        self.main_dock._make_report_with_wait()

    def _on_clear_map(self):
        self.main_dock._reset()

    def exclude_pv_ids(self, pv_ids: List[str]):
        if not pv_ids:
            return
        removed = False
        for pid in pv_ids:
            if pid in self._last_pv_data:
                self._last_pv_data.pop(pid, None)
                removed = True
        if removed:
            self._visible_pv_data = dict(self._last_pv_data)
            self._refresh_tables()
            self.status_label.setText(f"PV détectés : {len(self._last_pv_data)}")

    def set_pv_data(self, pv_details: Dict[str, Dict[str, str]]):
        self._last_pv_data = self._annotate_pv_data(pv_details or {})
        self._visible_pv_data = dict(self._last_pv_data)
        self._refresh_tables()
        self.status_label.setText(f"PV détectés : {len(self._last_pv_data)}")

    def set_language(self, lang: str):
        translations = {
            "fr": {
                "title": "🏠 Analyse Conformité PV",
                "desc": "Analysez les PV conformes et non conformes\nsur un cheminement de réseau EU/EP.",
                "config": "⚙️ Configuration de l'analyse",
                "steps": "1. Réalisez un cheminement depuis l'onglet Cheminement\n2. Cliquez sur \"Analyser\" pour détecter les PV",
                "distance": "Distance de recherche PV :",
                "analyze": "🔍 Analyser le cheminement",
                "status": "Aucune analyse effectuée",
                "pv_group": "🏠 PV détectés",
                "actions": "🧹 Actions",
                "export": "📊 Exporter en CSV",
                "report": "🧾 Générer un rapport",
                "clear": "🧼 Nettoyer la carte",
                "search": "Recherche :",
                "search_placeholder": "Filtrer sur toutes les colonnes...",
                "zoom": "🔍 Zoomer",
                "designate": "🎯 Désigner comme pollueur",
                "osmose": "🔗 Voir dans OSMOSE",
            },
            "en": {
                "title": "🏠 PV Compliance Analysis",
                "desc": "Analyze compliant and non-compliant PVs\non a EU/EP network trace.",
                "config": "⚙️ Analysis settings",
                "steps": "1. Run a trace from the Trace tab\n2. Click \"Analyze\" to detect PVs",
                "distance": "PV search distance:",
                "analyze": "🔍 Analyze trace",
                "status": "No analysis performed",
                "pv_group": "🏠 PV detected",
                "actions": "🧹 Actions",
                "export": "📊 Export CSV",
                "report": "🧾 Generate report",
                "clear": "🧼 Clear map",
                "search": "Search:",
                "search_placeholder": "Filter across all columns...",
                "zoom": "🔍 Zoom",
                "designate": "🎯 Designate polluter",
                "osmose": "🔗 Open in OSMOSE",
            },
        }
        tr = translations.get(lang, translations["fr"])
        if self.title_label:
            self.title_label.setText(tr["title"])
        if self.desc_label:
            self.desc_label.setText(tr["desc"])
        if self.config_group:
            self.config_group.setTitle(tr["config"])
        if self.steps_label:
            self.steps_label.setText(tr["steps"])
        if self.distance_label:
            self.distance_label.setText(tr["distance"])
        if self.analyze_btn:
            self.analyze_btn.setText(tr["analyze"])
        if self.status_label and not self._last_pv_data:
            self.status_label.setText(tr["status"])
        if self.pv_table:
            self.pv_table["group"].setTitle(tr["pv_group"])
        if self.actions_group:
            self.actions_group.setTitle(tr["actions"])
        if self.btn_export:
            self.btn_export.setText(tr["export"])
        if self.btn_report:
            self.btn_report.setText(tr["report"])
        if self.btn_clear:
            self.btn_clear.setText(tr["clear"])
        if self.search_label:
            self.search_label.setText(tr["search"])
        if self.search_input:
            self.search_input.setPlaceholderText(tr["search_placeholder"])
        if self.btn_zoom:
            self.btn_zoom.setText(tr["zoom"])
        if self.btn_designate:
            self.btn_designate.setText(tr["designate"])
        if hasattr(self, "btn_osmose") and self.btn_osmose:
            self.btn_osmose.setText(tr["osmose"])
