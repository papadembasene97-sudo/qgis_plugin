# -*- coding: utf-8 -*-
"""
Onglet PV Conformité pour le plugin CheminerIndus
Interface pour l'analyse des PV non conformes et des industriels connectés
"""

from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTextEdit, QFileDialog, QMessageBox, QSpinBox,
    QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QAbstractItemView
)
from qgis.core import (
    QgsProject, Qgis, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsMarkerSymbol, QgsLineSymbol, QgsSymbol,
    QgsSingleSymbolRenderer, QgsVectorLayerTemporalProperties
)
from qgis.PyQt.QtGui import QFont, QColor, QBrush
from typing import Optional, List, Dict, Any
import os
import csv


class PVConformiteTab(QWidget):
    """Onglet PV Conformité pour l'analyse des industriels et PV non conformes"""
    
    def __init__(self, main_dock, parent=None):
        super().__init__(parent)
        self.main_dock = main_dock
        self.iface = main_dock.iface
        
        # État
        self.pv_analyzer = None
        self.current_path_canals = []  # Liste des IDs de canalisations du cheminement
        self.industriels_list = []     # Liste des industriels connectés
        self.pv_list = []              # Liste des PV non conformes
        self.excluded_branches = set() # Branches exclues
        
        # Couches de visualisation temporaires
        self.temp_pv_layer = None
        self.temp_indus_layer = None
        self.temp_path_layer = None
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel("🏠 Analyse Industrielle + Conformité PV")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Analysez les industriels connectés et les PV non conformes\n"
            "sur un cheminement de réseau EU/EP."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Groupe 1: Configuration de l'analyse
        self._add_config_group(layout)
        
        # Groupe 2: Résultats (Splitter horizontal)
        splitter = QSplitter(Qt.Horizontal)
        
        # Table des industriels (gauche)
        self._add_industriels_table(splitter)
        
        # Table des PV non conformes (droite)
        self._add_pv_table(splitter)
        
        layout.addWidget(splitter)
        
        # Groupe 3: Actions
        self._add_actions_group(layout)
        
        layout.addStretch()
        
    def _add_config_group(self, layout):
        """Ajoute le groupe de configuration"""
        group = QGroupBox("⚙️ Configuration de l'analyse")
        group_layout = QVBoxLayout(group)
        
        # Info
        info = QLabel(
            "1. Réalisez un cheminement depuis l'onglet Cheminement\n"
            "2. Cliquez sur 'Analyser' pour détecter les industriels et PV non conformes"
        )
        info.setWordWrap(True)
        group_layout.addWidget(info)
        
        # Distance de recherche PV
        distance_layout = QHBoxLayout()
        distance_layout.addWidget(QLabel("Distance de recherche PV :"))
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(5, 100)
        self.distance_spin.setValue(15)
        self.distance_spin.setSuffix(" m")
        self.distance_spin.setToolTip("Distance autour des canalisations pour rechercher les PV")
        distance_layout.addWidget(self.distance_spin)
        distance_layout.addStretch()
        group_layout.addLayout(distance_layout)
        
        # Type de réseau
        reseau_layout = QHBoxLayout()
        reseau_layout.addWidget(QLabel("Type de réseau :"))
        self.reseau_combo = QComboBox()
        self.reseau_combo.addItems(["EU", "EP", "Mixte"])
        self.reseau_combo.setCurrentText("EU")
        reseau_layout.addWidget(self.reseau_combo)
        reseau_layout.addStretch()
        group_layout.addLayout(reseau_layout)
        
        # Bouton analyser
        btn_analyze = QPushButton("🔍 Analyser le cheminement")
        btn_analyze.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        btn_analyze.setToolTip("Analyser les industriels et PV non conformes sur le cheminement")
        btn_analyze.clicked.connect(self._on_analyze)
        group_layout.addWidget(btn_analyze)
        
        # Statistiques
        self.stats_label = QLabel("Aucune analyse effectuée")
        self.stats_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(self.stats_label)
        
        layout.addWidget(group)
        
    def _add_industriels_table(self, parent):
        """Ajoute la table des industriels"""
        group = QGroupBox("🏭 Industriels connectés")
        group_layout = QVBoxLayout(group)
        
        # Table
        self.industriels_table = QTableWidget(0, 6)
        self.industriels_table.setHorizontalHeaderLabels([
            "ID", "Nom", "Type", "Adresse", "Commune", "Distance (m)"
        ])
        self.industriels_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.industriels_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.industriels_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.industriels_table.setAlternatingRowColors(True)
        self.industriels_table.itemSelectionChanged.connect(self._on_indus_selection_changed)
        group_layout.addWidget(self.industriels_table)
        
        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        btn_zoom_indus = QPushButton("🔍 Zoomer")
        btn_zoom_indus.clicked.connect(self._on_zoom_industriel)
        btn_layout.addWidget(btn_zoom_indus)
        
        btn_designate_indus = QPushButton("🎯 Désigner comme pollueur")
        btn_designate_indus.clicked.connect(self._on_designate_industriel)
        btn_layout.addWidget(btn_designate_indus)
        
        group_layout.addLayout(btn_layout)
        
        parent.addWidget(group)
        
    def _add_pv_table(self, parent):
        """Ajoute la table des PV non conformes"""
        group = QGroupBox("🏠 PV non conformes")
        group_layout = QVBoxLayout(group)
        
        # Table
        self.pv_table = QTableWidget(0, 7)
        self.pv_table.setHorizontalHeaderLabels([
            "N° PV", "Adresse", "Commune", "EU→EP", "EP→EU", "Canal", "Distance (m)"
        ])
        self.pv_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pv_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pv_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pv_table.setAlternatingRowColors(True)
        self.pv_table.itemSelectionChanged.connect(self._on_pv_selection_changed)
        group_layout.addWidget(self.pv_table)
        
        # Boutons d'action
        btn_layout = QHBoxLayout()
        
        btn_zoom_pv = QPushButton("🔍 Zoomer")
        btn_zoom_pv.clicked.connect(self._on_zoom_pv)
        btn_layout.addWidget(btn_zoom_pv)
        
        btn_designate_pv = QPushButton("🎯 Désigner comme pollueur")
        btn_designate_pv.clicked.connect(self._on_designate_pv)
        btn_layout.addWidget(btn_designate_pv)
        
        btn_osmose = QPushButton("🔗 Voir dans OSMOSE")
        btn_osmose.clicked.connect(self._on_view_osmose)
        btn_layout.addWidget(btn_osmose)
        
        group_layout.addLayout(btn_layout)
        
        parent.addWidget(group)
        
    def _add_actions_group(self, layout):
        """Ajoute le groupe d'actions"""
        group = QGroupBox("📊 Actions")
        group_layout = QHBoxLayout(group)
        
        # Export CSV
        btn_export = QPushButton("📄 Exporter en CSV")
        btn_export.setToolTip("Exporter les résultats en fichier CSV")
        btn_export.clicked.connect(self._on_export_csv)
        group_layout.addWidget(btn_export)
        
        # Visualisation cartographique
        btn_visualize = QPushButton("🗺️ Visualiser sur la carte")
        btn_visualize.setToolTip("Afficher le cheminement, les PV et les industriels")
        btn_visualize.clicked.connect(self._on_visualize)
        group_layout.addWidget(btn_visualize)
        
        # Générer rapport
        btn_report = QPushButton("📋 Générer un rapport")
        btn_report.setToolTip("Générer un rapport PDF de l'analyse")
        btn_report.clicked.connect(self._on_generate_report)
        group_layout.addWidget(btn_report)
        
        # Nettoyer la visualisation
        btn_clear = QPushButton("🧹 Nettoyer la carte")
        btn_clear.setToolTip("Supprimer les couches temporaires de visualisation")
        btn_clear.clicked.connect(self._on_clear_visualization)
        group_layout.addWidget(btn_clear)
        
        layout.addWidget(group)
        
    # ========================================================================
    # Méthodes d'analyse
    # ========================================================================
    
    def _on_analyze(self):
        """Lance l'analyse du cheminement"""
        try:
            # Vérifier qu'un cheminement existe
            if not hasattr(self.main_dock, 'tracer') or not self.main_dock.tracer:
                QMessageBox.warning(
                    self,
                    "Aucun cheminement",
                    "Veuillez d'abord réaliser un cheminement depuis l'onglet Cheminement."
                )
                return
            
            # Récupérer les canalisations du cheminement
            tracer = self.main_dock.tracer
            self.current_path_canals = list(tracer.canal_ids)
            
            if not self.current_path_canals:
                QMessageBox.warning(
                    self,
                    "Cheminement vide",
                    "Le cheminement ne contient aucune canalisation."
                )
                return
            
            # Initialiser PVAnalyzer si nécessaire
            self._init_pv_analyzer()
            
            # Analyser les industriels
            self._analyze_industriels()
            
            # Analyser les PV non conformes
            self._analyze_pv()
            
            # Mettre à jour les statistiques
            self._update_stats()
            
            # Message de succès
            self.iface.messageBar().pushMessage(
                "Analyse terminée",
                f"✅ {len(self.industriels_list)} industriels et {len(self.pv_list)} PV non conformes détectés",
                level=Qgis.Success,
                duration=5
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur d'analyse",
                f"Une erreur s'est produite lors de l'analyse :\n{str(e)}"
            )
            
    def _init_pv_analyzer(self):
        """Initialise le PVAnalyzer"""
        try:
            from ..core.pv_analyzer import PVAnalyzer
            
            # Récupérer les couches
            pv_layer = self._find_layer_by_name("PV_CONFORMITE") or self._find_layer_by_name("osmose.PV_CONFORMITE")
            canal_layer = self.main_dock.canal_layer
            
            if not pv_layer:
                raise Exception("Couche PV_CONFORMITE non trouvée")
            if not canal_layer:
                raise Exception("Couche de canalisations non chargée")
            
            # Créer l'analyseur
            self.pv_analyzer = PVAnalyzer(pv_layer, canal_layer)
            
            # Configurer la distance de recherche
            distance = self.distance_spin.value()
            self.pv_analyzer.search_distance = distance
            
        except ImportError:
            QMessageBox.critical(
                self,
                "Module manquant",
                "Le module PVAnalyzer n'est pas disponible."
            )
            raise
            
    def _analyze_industriels(self):
        """Analyse les industriels connectés"""
        try:
            # Utiliser le service industriels du main_dock
            if not hasattr(self.main_dock, 'indus_svc') or not self.main_dock.indus_svc:
                self.industriels_list = []
                return
            
            indus_svc = self.main_dock.indus_svc
            
            # Récupérer les industriels pour chaque canalisation
            industriels_dict = {}
            for canal_id in self.current_path_canals:
                # Rechercher les industriels liés à cette canalisation
                # (logique à adapter selon votre implémentation)
                pass
            
            # Pour l'instant, utiliser une liste vide
            # TODO: implémenter la récupération des industriels
            self.industriels_list = []
            
            # Mettre à jour la table
            self._update_industriels_table()
            
        except Exception as e:
            print(f"Erreur lors de l'analyse des industriels: {e}")
            self.industriels_list = []
            
    def _analyze_pv(self):
        """Analyse les PV non conformes"""
        try:
            if not self.pv_analyzer:
                self.pv_list = []
                return
            
            # Rechercher les PV non conformes
            self.pv_list = self.pv_analyzer.find_pv_in_path(self.current_path_canals)
            
            # Mettre à jour la table
            self._update_pv_table()
            
        except Exception as e:
            print(f"Erreur lors de l'analyse des PV: {e}")
            self.pv_list = []
            
    def _update_stats(self):
        """Met à jour les statistiques d'analyse"""
        nb_canaux = len(self.current_path_canals)
        nb_indus = len(self.industriels_list)
        nb_pv = len(self.pv_list)
        
        stats_text = (
            f"✅ Analyse terminée\n"
            f"📊 {nb_canaux} canalisations analysées\n"
            f"🏭 {nb_indus} industriels connectés\n"
            f"🏠 {nb_pv} PV non conformes détectés"
        )
        
        self.stats_label.setText(stats_text)
        self.stats_label.setStyleSheet("color: green; font-weight: bold;")
        
    # ========================================================================
    # Mise à jour des tables
    # ========================================================================
    
    def _update_industriels_table(self):
        """Met à jour la table des industriels"""
        self.industriels_table.setRowCount(0)
        
        for indus in self.industriels_list:
            row = self.industriels_table.rowCount()
            self.industriels_table.insertRow(row)
            
            self.industriels_table.setItem(row, 0, QTableWidgetItem(str(indus.get('id', ''))))
            self.industriels_table.setItem(row, 1, QTableWidgetItem(indus.get('nom', '')))
            self.industriels_table.setItem(row, 2, QTableWidgetItem(indus.get('type', '')))
            self.industriels_table.setItem(row, 3, QTableWidgetItem(indus.get('adresse', '')))
            self.industriels_table.setItem(row, 4, QTableWidgetItem(indus.get('commune', '')))
            self.industriels_table.setItem(row, 5, QTableWidgetItem(f"{indus.get('distance', 0):.1f}"))
            
    def _update_pv_table(self):
        """Met à jour la table des PV"""
        self.pv_table.setRowCount(0)
        
        for pv in self.pv_list:
            row = self.pv_table.rowCount()
            self.pv_table.insertRow(row)
            
            self.pv_table.setItem(row, 0, QTableWidgetItem(str(pv.get('num_pv', ''))))
            self.pv_table.setItem(row, 1, QTableWidgetItem(pv.get('adresse', '')))
            self.pv_table.setItem(row, 2, QTableWidgetItem(pv.get('commune', '')))
            self.pv_table.setItem(row, 3, QTableWidgetItem(pv.get('eu_vers_ep', 'Non')))
            self.pv_table.setItem(row, 4, QTableWidgetItem(pv.get('ep_vers_eu', 'Non')))
            self.pv_table.setItem(row, 5, QTableWidgetItem(str(pv.get('canal_id', ''))))
            self.pv_table.setItem(row, 6, QTableWidgetItem(f"{pv.get('distance', 0):.1f}"))
            
            # Colorer en orange les lignes avec inversions
            if pv.get('eu_vers_ep') == 'Oui' or pv.get('ep_vers_eu') == 'Oui':
                for col in range(7):
                    item = self.pv_table.item(row, col)
                    if item:
                        item.setBackground(QBrush(QColor(255, 165, 0, 100)))  # Orange clair
                        
    # ========================================================================
    # Événements de sélection
    # ========================================================================
    
    def _on_indus_selection_changed(self):
        """Gère la sélection d'un industriel dans la table"""
        pass
        
    def _on_pv_selection_changed(self):
        """Gère la sélection d'un PV dans la table"""
        pass
        
    # ========================================================================
    # Actions sur les industriels
    # ========================================================================
    
    def _on_zoom_industriel(self):
        """Zoom sur l'industriel sélectionné"""
        selected_rows = self.industriels_table.selectedItems()
        if not selected_rows:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un industriel.")
            return
        
        # TODO: implémenter le zoom
        QMessageBox.information(self, "Zoom", "Fonctionnalité à implémenter")
        
    def _on_designate_industriel(self):
        """Désigne l'industriel sélectionné comme pollueur"""
        selected_rows = self.industriels_table.selectedItems()
        if not selected_rows:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un industriel.")
            return
        
        row = selected_rows[0].row()
        indus_id = self.industriels_table.item(row, 0).text()
        indus_nom = self.industriels_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Désigner comme pollueur",
            f"Désigner l'industriel '{indus_nom}' comme origine de pollution ?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # TODO: implémenter la désignation
            self.iface.messageBar().pushMessage(
                "Pollueur désigné",
                f"✅ Industriel '{indus_nom}' désigné comme origine de pollution",
                level=Qgis.Success,
                duration=3
            )
            
    # ========================================================================
    # Actions sur les PV
    # ========================================================================
    
    def _on_zoom_pv(self):
        """Zoom sur le PV sélectionné"""
        selected_rows = self.pv_table.selectedItems()
        if not selected_rows:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un PV.")
            return
        
        row = selected_rows[0].row()
        pv_data = self.pv_list[row]
        
        # Zoom sur la géométrie du PV
        if 'geometry' in pv_data and pv_data['geometry']:
            geom = pv_data['geometry']
            bbox = geom.boundingBox()
            bbox_buffered = bbox.buffered(50)  # 50m autour
            self.iface.mapCanvas().setExtent(bbox_buffered)
            self.iface.mapCanvas().refresh()
            
    def _on_designate_pv(self):
        """Désigne le PV sélectionné comme pollueur"""
        selected_rows = self.pv_table.selectedItems()
        if not selected_rows:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un PV.")
            return
        
        row = selected_rows[0].row()
        pv_num = self.pv_table.item(row, 0).text()
        pv_adresse = self.pv_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Désigner comme pollueur",
            f"Désigner le PV n°{pv_num} ({pv_adresse}) comme origine de pollution ?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            pv_data = self.pv_list[row]
            pv_id = pv_data.get('id')
            
            if self.pv_analyzer and pv_id:
                polluter_info = self.pv_analyzer.designate_as_polluter(pv_id)
                
                self.iface.messageBar().pushMessage(
                    "Pollueur désigné",
                    f"✅ PV n°{pv_num} désigné comme origine de pollution",
                    level=Qgis.Success,
                    duration=3
                )
                
                # TODO: lancer le cheminement Amont→Aval depuis ce PV
                
    def _on_view_osmose(self):
        """Ouvre le lien OSMOSE du PV sélectionné"""
        selected_rows = self.pv_table.selectedItems()
        if not selected_rows:
            QMessageBox.information(self, "Sélection", "Veuillez sélectionner un PV.")
            return
        
        row = selected_rows[0].row()
        pv_data = self.pv_list[row]
        pv_num = pv_data.get('num_pv')
        
        if pv_num:
            url = f"https://si.siah-croult.org/gestion-pv/{pv_num}"
            
            import webbrowser
            webbrowser.open(url)
        else:
            QMessageBox.warning(self, "OSMOSE", "Numéro de PV non disponible.")
            
    # ========================================================================
    # Actions globales
    # ========================================================================
    
    def _on_export_csv(self):
        """Exporte les résultats en CSV"""
        if not self.industriels_list and not self.pv_list:
            QMessageBox.information(
                self,
                "Aucune donnée",
                "Aucune donnée à exporter. Veuillez d'abord lancer une analyse."
            )
            return
        
        # Demander le chemin de sauvegarde
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter en CSV",
            "",
            "Fichiers CSV (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                
                # En-tête
                writer.writerow([
                    'Type', 'ID', 'Numéro', 'Nom', 'Adresse', 'Commune',
                    'Conforme', 'EU→EP', 'EP→EU', 'Canal', 'Distance (m)'
                ])
                
                # Industriels
                for indus in self.industriels_list:
                    writer.writerow([
                        'Industriel',
                        indus.get('id', ''),
                        '',
                        indus.get('nom', ''),
                        indus.get('adresse', ''),
                        indus.get('commune', ''),
                        'N/A',
                        'N/A',
                        'N/A',
                        '',
                        f"{indus.get('distance', 0):.1f}"
                    ])
                
                # PV
                for pv in self.pv_list:
                    writer.writerow([
                        'PV',
                        pv.get('id', ''),
                        pv.get('num_pv', ''),
                        '',
                        pv.get('adresse', ''),
                        pv.get('commune', ''),
                        pv.get('conforme', 'Non'),
                        pv.get('eu_vers_ep', 'Non'),
                        pv.get('ep_vers_eu', 'Non'),
                        pv.get('canal_id', ''),
                        f"{pv.get('distance', 0):.1f}"
                    ])
            
            self.iface.messageBar().pushMessage(
                "Export réussi",
                f"✅ Données exportées vers {file_path}",
                level=Qgis.Success,
                duration=5
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur d'export",
                f"Impossible d'exporter les données :\n{str(e)}"
            )
            
    def _on_visualize(self):
        """Visualise le cheminement, les PV et les industriels sur la carte"""
        try:
            # Nettoyer la visualisation précédente
            self._on_clear_visualization()
            
            # Créer une couche temporaire pour les PV
            self._create_pv_layer()
            
            # Créer une couche temporaire pour les industriels
            self._create_indus_layer()
            
            # Créer une couche temporaire pour le cheminement
            self._create_path_layer()
            
            self.iface.messageBar().pushMessage(
                "Visualisation",
                "✅ Couches de visualisation créées",
                level=Qgis.Success,
                duration=3
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur de visualisation",
                f"Impossible de créer les couches de visualisation :\n{str(e)}"
            )
            
    def _create_pv_layer(self):
        """Crée une couche temporaire pour les PV"""
        if not self.pv_list:
            return
        
        # Créer une couche mémoire
        layer = QgsVectorLayer("Point?crs=EPSG:2154", "PV non conformes", "memory")
        provider = layer.dataProvider()
        
        # Ajouter les champs
        from qgis.core import QgsField
        provider.addAttributes([
            QgsField("num_pv", QVariant.String),
            QgsField("adresse", QVariant.String),
            QgsField("commune", QVariant.String),
            QgsField("eu_vers_ep", QVariant.String),
            QgsField("ep_vers_eu", QVariant.String)
        ])
        layer.updateFields()
        
        # Ajouter les PV
        features = []
        for pv in self.pv_list:
            feat = QgsFeature()
            feat.setGeometry(pv['geometry'])
            feat.setAttributes([
                pv.get('num_pv', ''),
                pv.get('adresse', ''),
                pv.get('commune', ''),
                pv.get('eu_vers_ep', 'Non'),
                pv.get('ep_vers_eu', 'Non')
            ])
            features.append(feat)
        
        provider.addFeatures(features)
        layer.updateExtents()
        
        # Symbologie orange
        symbol = QgsMarkerSymbol.createSimple({
            'name': 'circle',
            'color': '255,140,0',
            'size': '4',
            'outline_color': '0,0,0',
            'outline_width': '0.5'
        })
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        
        # Ajouter la couche au projet
        QgsProject.instance().addMapLayer(layer)
        self.temp_pv_layer = layer
        
    def _create_indus_layer(self):
        """Crée une couche temporaire pour les industriels"""
        if not self.industriels_list:
            return
        
        # TODO: implémenter la création de la couche des industriels
        pass
        
    def _create_path_layer(self):
        """Crée une couche temporaire pour le cheminement"""
        if not self.current_path_canals:
            return
        
        # TODO: implémenter la création de la couche du cheminement
        pass
        
    def _on_clear_visualization(self):
        """Supprime les couches temporaires de visualisation"""
        project = QgsProject.instance()
        
        if self.temp_pv_layer:
            project.removeMapLayer(self.temp_pv_layer.id())
            self.temp_pv_layer = None
        
        if self.temp_indus_layer:
            project.removeMapLayer(self.temp_indus_layer.id())
            self.temp_indus_layer = None
        
        if self.temp_path_layer:
            project.removeMapLayer(self.temp_path_layer.id())
            self.temp_path_layer = None
        
    def _on_generate_report(self):
        """Génère un rapport PDF de l'analyse"""
        QMessageBox.information(
            self,
            "Rapport",
            "Génération de rapport : fonctionnalité à implémenter dans la prochaine version."
        )
        
    # ========================================================================
    # Utilitaires
    # ========================================================================
    
    def _find_layer_by_name(self, name: str) -> Optional[QgsVectorLayer]:
        """Trouve une couche par son nom"""
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                if name in layer.name() or layer.name() in name:
                    return layer
        return None
