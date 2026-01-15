# -*- coding: utf-8 -*-
# cheminer_indus/gui/industrial_dock.py

from __future__ import annotations

from typing import Dict, Callable, Optional, List

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QAbstractItemView,
    QHeaderView, QFileDialog, QMessageBox, QFrame, QGroupBox
)


class _FieldList(QListWidget):
    """
    QListWidget avec glisser-déposer entre listes.
    - Move entre 2 listes de même type
    - Pas de doublons côté destination
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def dropEvent(self, event):
        source = event.source()
        # Drop interne (réorganisation dans la même liste)
        if source is self:
            super().dropEvent(event)
            return

        # Drop depuis une autre liste : on "déplace" les items sélectionnés
        if isinstance(source, QListWidget):
            texts = [it.text() for it in source.selectedItems()]
            # Ajouter sans doublons
            for txt in texts:
                if not any(self.item(i).text() == txt for i in range(self.count())):
                    self.addItem(txt)
            # Supprimer de la liste source
            # (on supprime à l'envers pour ne pas décaler les indices)
            rows = sorted([source.row(it) for it in source.selectedItems()], reverse=True)
            for row in rows:
                source.takeItem(row)
            event.accept()
        else:
            super().dropEvent(event)


class IndustrialDock(QDockWidget):
    """
    Dock listant les industriels connectés avec :
    - Tableau des résultats
    - Recherche multi-champs (zone "Champs filtrés")
    - Critères multiples séparés par des virgules
    - Boutons Zoom / Désigner / Rafraîchir / Export CSV
    - Méthode exclude_ids pour exclure certains industriels du tableau

    UI "futuriste" :
    - Palette bleue claire, pas de fond noir
    - 2 colonnes de champs : disponibles / filtrés
      avec glisser-déposer + double-clic.
    """

    def __init__(self, parent=None):
        super().__init__("Industriels connectés", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        base = QWidget(self)
        base.setObjectName("IndustrialBase")
        self.setWidget(base)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # ------------------------------------------------------------------
        # STYLES (palette bleue, aucun noir)
        # ------------------------------------------------------------------
        base.setStyleSheet("""
        QWidget#IndustrialBase {
            background-color: #f4f7fb;
        }
        QLabel {
            color: #12355b;
            font-weight: 600;
        }
        QGroupBox {
            border: 1px solid #c3d4f4;
            border-radius: 4px;
            margin-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            color: #0f2f5b;
            font-weight: 600;
        }
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #b7c9e8;
            border-radius: 3px;
            padding: 3px 5px;
            color: #102a43;
        }
        QListWidget {
            background-color: #ffffff;
            border: 1px solid #b7c9e8;
            border-radius: 3px;
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
        QHeaderView::section {
            background-color: #d6e4ff;
            color: #102a43;
            padding: 3px;
            border: 0px;
            border-right: 1px solid #b0c4ef;
        }
        QPushButton {
            background-color: #1f6feb;
            color: #ffffff;
            border-radius: 3px;
            padding: 4px 10px;
            border: 0px;
        }
        QPushButton:hover {
            background-color: #1554b3;
        }
        QPushButton:disabled {
            background-color: #a9c4f5;
            color: #e5ecff;
        }
        """)

        # ------------------------------------------------------------------
        # Zone de filtres : 2 colonnes + critère
        # ------------------------------------------------------------------
        filter_group = QGroupBox("Filtrage des industriels")
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setContentsMargins(6, 6, 6, 6)
        filter_layout.setSpacing(4)

        # Ligne des listes de champs
        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(8)

        # Colonne gauche : champs disponibles
        col_left = QVBoxLayout()
        lbl_avail = QLabel("Champs disponibles")
        self.available_fields = _FieldList()
        self.available_fields.setMinimumHeight(80)
        col_left.addWidget(lbl_avail)
        col_left.addWidget(self.available_fields)

        # Colonne droite : champs utilisés pour le filtrage
        col_right = QVBoxLayout()
        lbl_filter = QLabel("Champs filtrés")
        self.filter_fields = _FieldList()
        self.filter_fields.setMinimumHeight(80)
        col_right.addWidget(lbl_filter)
        col_right.addWidget(self.filter_fields)

        # Petite colonne centrale avec boutons de transfert
        col_mid = QVBoxLayout()
        col_mid.setSpacing(4)
        col_mid.addStretch()

        btn_to_filter = QPushButton("▶")
        btn_to_filter.setToolTip("Ajouter aux champs filtrés")
        btn_to_filter.setMaximumWidth(32)
        btn_to_filter.clicked.connect(self._move_selected_to_filter)

        btn_to_avail = QPushButton("◀")
        btn_to_avail.setToolTip("Retirer des champs filtrés")
        btn_to_avail.setMaximumWidth(32)
        btn_to_avail.clicked.connect(self._move_selected_to_available)

        col_mid.addWidget(btn_to_filter)
        col_mid.addWidget(btn_to_avail)
        col_mid.addStretch()

        lists_layout.addLayout(col_left, 3)
        lists_layout.addLayout(col_mid, 0)
        lists_layout.addLayout(col_right, 3)

        filter_layout.addLayout(lists_layout)

        # Double-clic pour déplacer d'une liste à l'autre
        self.available_fields.itemDoubleClicked.connect(self._on_double_click_available)
        self.filter_fields.itemDoubleClicked.connect(self._on_double_click_filter)

        # Ligne de saisie des critères
        crit_layout = QHBoxLayout()
        crit_layout.setSpacing(4)
        crit_layout.addWidget(QLabel("Valeurs :"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Critères séparés par des virgules (ex : peinture, solvants)"
        )
        crit_layout.addWidget(self.search_edit, 1)

        btn_filter = QPushButton("Filtrer")
        btn_filter.clicked.connect(self._apply_filter)
        crit_layout.addWidget(btn_filter)

        btn_reset = QPushButton("Réinitialiser")
        btn_reset.clicked.connect(self._reset_filter)
        crit_layout.addWidget(btn_reset)

        filter_layout.addLayout(crit_layout)

        layout.addWidget(filter_group)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # ------------------------------------------------------------------
        # Tableau des industriels
        # ------------------------------------------------------------------
        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # ------------------------------------------------------------------
        # Boutons d'action
        # ------------------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_zoom = QPushButton("Zoom")
        self.btn_zoom.clicked.connect(self._on_zoom)
        btn_layout.addWidget(self.btn_zoom)

        self.btn_designate = QPushButton("Désigner pollueur")
        self.btn_designate.clicked.connect(self._on_designate)
        btn_layout.addWidget(self.btn_designate)

        self.btn_refresh = QPushButton("Rafraîchir")
        self.btn_refresh.clicked.connect(self._on_refresh)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("Exporter CSV")
        self.btn_export.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.btn_export)

        layout.addLayout(btn_layout)

        # ------------------------------------------------------------------
        # Callbacks externes
        # ------------------------------------------------------------------
        self._cb_zoom: Optional[Callable[[str], None]] = None
        self._cb_designate: Optional[Callable[[str], None]] = None
        self._cb_refresh: Optional[Callable[[], None]] = None

        # Données
        self._raw_data: Dict[str, Dict[str, str]] = {}
        self._visible_data: Dict[str, Dict[str, str]] = {}
        self._all_fields: List[str] = []

    # ----------------------------------------------------------------------
    # API callbacks (utilisées par main_dock)
    # ----------------------------------------------------------------------
    def on_zoom_request(self, cb: Callable[[str], None]):
        """cb(ind_id: str)"""
        self._cb_zoom = cb

    def on_designate_request(self, cb: Callable[[str], None]):
        """cb(ind_id: str)"""
        self._cb_designate = cb

    def on_refresh_request(self, cb: Callable[[], None]):
        """cb()"""
        self._cb_refresh = cb

    # ----------------------------------------------------------------------
    # Injection de données
    # ----------------------------------------------------------------------
    def set_data(self, data: Dict[str, Dict[str, str]]):
        """
        data : { id_indus: {colonne: valeur, ...}, ... }
        """
        self._raw_data = data or {}
        self._visible_data = dict(self._raw_data)

        # Construire la liste des champs à partir des clés présentes
        all_fields = set()
        for row in self._raw_data.values():
            all_fields.update(row.keys())

        # Ordre optimisé : id, Nom, Activite, Produits, Risques, Adresse, puis le reste
        preferred = ["id", "Nom", "Activite", "Produits", "Risques", "Adresse"]
        ordered: List[str] = [f for f in preferred if f in all_fields]
        remaining = sorted(f for f in all_fields if f not in ordered)
        self._all_fields = ordered + remaining

        # Si aucun champ, on vide le tableau et les listes
        if not self._all_fields:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.available_fields.clear()
            self.filter_fields.clear()
            self.setWindowTitle("Industriels connectés (0)")
            return

        # Colonnes du tableau
        self.table.setColumnCount(len(self._all_fields))
        self.table.setHorizontalHeaderLabels(self._all_fields)

        # Remplir les listes de champs
        self.available_fields.clear()
        self.filter_fields.clear()

        # Par défaut, on met dans "champs filtrés" les colonnes les plus parlantes
        default_filter = [f for f in ("Nom", "Activite", "Produits", "Risques", "Adresse") if f in self._all_fields]

        for f in self._all_fields:
            if f in default_filter:
                self.filter_fields.addItem(QListWidgetItem(f))
            else:
                self.available_fields.addItem(QListWidgetItem(f))

        # Remplir le tableau
        self._refresh_table()

    # ----------------------------------------------------------------------
    # Affichage du tableau à partir de _visible_data
    # ----------------------------------------------------------------------
    def _refresh_table(self):
        self.table.setRowCount(0)

        if not self._visible_data:
            self.setWindowTitle("Industriels connectés (0)")
            return

        for row_idx, (ind_id, row) in enumerate(self._visible_data.items()):
            self.table.insertRow(row_idx)
            for col_idx, field in enumerate(self._all_fields):
                val = str(row.get(field, "") or "")
                item = QTableWidgetItem(val)
                # On stocke l'ID industriel dans la première colonne (UserRole),
                # même si le champ 'id' n'est pas la première colonne logique.
                if col_idx == 0:
                    item.setData(Qt.UserRole, ind_id)
                self.table.setItem(row_idx, col_idx, item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.setWindowTitle(
            "Industriels connectés ({})".format(len(self._visible_data))
        )

    # ----------------------------------------------------------------------
    # Utilitaires de sélection
    # ----------------------------------------------------------------------
    def _selected_industrial_id(self) -> Optional[str]:
        row = self.table.currentRow()
        if row < 0 or self.table.columnCount() == 0:
            return None
        first_item = self.table.item(row, 0)
        if not first_item:
            return None
        ind_id = first_item.data(Qt.UserRole)
        return str(ind_id) if ind_id is not None else None

    # ----------------------------------------------------------------------
    # Boutons : Zoom / Désigner / Rafraîchir
    # ----------------------------------------------------------------------
    def _on_zoom(self):
        ind_id = self._selected_industrial_id()
        if ind_id and self._cb_zoom:
            self._cb_zoom(ind_id)

    def _on_designate(self):
        ind_id = self._selected_industrial_id()
        if ind_id and self._cb_designate:
            self._cb_designate(ind_id)

    def _on_refresh(self):
        """
        Laisse la logique de rafraîchissement au main_dock / service industriel.
        """
        if self._cb_refresh:
            self._cb_refresh()

    # ----------------------------------------------------------------------
    # Mouvements entre listes de champs
    # ----------------------------------------------------------------------
    def _move_selected_to_filter(self):
        items = self.available_fields.selectedItems()
        if not items:
            return
        texts = [it.text() for it in items]
        # Ajouter dans filter_fields sans doublon
        for txt in texts:
            if not any(self.filter_fields.item(i).text() == txt for i in range(self.filter_fields.count())):
                self.filter_fields.addItem(QListWidgetItem(txt))
        # Retirer de available_fields
        rows = sorted([self.available_fields.row(it) for it in items], reverse=True)
        for r in rows:
            self.available_fields.takeItem(r)

    def _move_selected_to_available(self):
        items = self.filter_fields.selectedItems()
        if not items:
            return
        texts = [it.text() for it in items]
        # Ajouter dans available_fields sans doublon
        for txt in texts:
            if not any(self.available_fields.item(i).text() == txt for i in range(self.available_fields.count())):
                self.available_fields.addItem(QListWidgetItem(txt))
        # Retirer de filter_fields
        rows = sorted([self.filter_fields.row(it) for it in items], reverse=True)
        for r in rows:
            self.filter_fields.takeItem(r)

    def _on_double_click_available(self, item: QListWidgetItem):
        if not item:
            return
        txt = item.text()
        # Ajouter à filter_fields si pas déjà présent
        if not any(self.filter_fields.item(i).text() == txt for i in range(self.filter_fields.count())):
            self.filter_fields.addItem(QListWidgetItem(txt))
        # Retirer de available_fields
        row = self.available_fields.row(item)
        self.available_fields.takeItem(row)

    def _on_double_click_filter(self, item: QListWidgetItem):
        if not item:
            return
        txt = item.text()
        # Ajouter à available_fields si pas déjà présent
        if not any(self.available_fields.item(i).text() == txt for i in range(self.available_fields.count())):
            self.available_fields.addItem(QListWidgetItem(txt))
        # Retirer de filter_fields
        row = self.filter_fields.row(item)
        self.filter_fields.takeItem(row)

    # ----------------------------------------------------------------------
    # Filtrage : champs de la colonne "champs filtrés" + critères séparés par virgules
    # ----------------------------------------------------------------------
    def _apply_filter(self):
        if not self._raw_data:
            return

        text = (self.search_edit.text() or "").strip()
        if not text:
            self._visible_data = dict(self._raw_data)
            self._refresh_table()
            return

        # Critères séparés par virgules
        tokens = [t.strip() for t in text.split(",") if t.strip()]
        if not tokens:
            self._visible_data = dict(self._raw_data)
            self._refresh_table()
            return

        # Champs utilisés pour le filtrage = liste de droite.
        selected_fields = [self.filter_fields.item(i).text() for i in range(self.filter_fields.count())]
        if not selected_fields:
            # Si aucun champ filtré, on utilise tous les champs
            selected_fields = list(self._all_fields)

        def row_match(row: Dict[str, str]) -> bool:
            """
            Match OR global :
            - pour chaque token
            - pour chaque champ sélectionné
            si token dans valeur champ => ligne retenue
            """
            for token in tokens:
                tok = token.lower()
                for field in selected_fields:
                    val = str(row.get(field, "") or "").lower()
                    if tok in val:
                        return True
            return False

        filtered = {
            ind_id: row
            for ind_id, row in self._raw_data.items()
            if row_match(row)
        }
        self._visible_data = filtered
        self._refresh_table()

    def _reset_filter(self):
        self.search_edit.clear()
        # On remet tous les champs dans "disponibles" et on remet le jeu par défaut dans "filtrés"
        all_fields = list(self._all_fields)
        self.available_fields.clear()
        self.filter_fields.clear()

        default_filter = [f for f in ("Nom", "Activite", "Produits", "Risques", "Adresse") if f in all_fields]
        for f in all_fields:
            if f in default_filter:
                self.filter_fields.addItem(QListWidgetItem(f))
            else:
                self.available_fields.addItem(QListWidgetItem(f))

        self._visible_data = dict(self._raw_data)
        self._refresh_table()

    # ----------------------------------------------------------------------
    # Exclusion d'IDs (utilisé par la logique de visite dans main_dock)
    # ----------------------------------------------------------------------
    def exclude_ids(self, ids: List[str]):
        """
        Exclut du tableau les industriels dont l'ID figure dans ids.
        ids : liste de chaînes (id_industriel)
        """
        if not ids:
            return
        sids = set(str(i) for i in ids)

        self._raw_data = {
            k: v for k, v in self._raw_data.items()
            if str(k) not in sids
        }
        self._visible_data = {
            k: v for k, v in self._visible_data.items()
            if str(k) not in sids
        }
        self._refresh_table()

    # ----------------------------------------------------------------------
    # Export CSV de la vue filtrée
    # ----------------------------------------------------------------------
    def _export_csv(self):
        if not self._visible_data:
            QMessageBox.information(self, "Export CSV", "Aucun industriel à exporter.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les industriels",
            "",
            "Fichier CSV (*.csv)"
        )
        if not path:
            return

        try:
            import csv
            # BOM UTF-8 pour meilleure compatibilité Excel
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                # En-têtes
                writer.writerow(self._all_fields)
                # Lignes
                for _, row in self._visible_data.items():
                    vals = [str(row.get(field, "") or "") for field in self._all_fields]
                    writer.writerow(vals)

            QMessageBox.information(
                self, "Export CSV", "Export réalisé :\n{}".format(path)
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export CSV", "Erreur lors de l'export : {}".format(e)
            )
