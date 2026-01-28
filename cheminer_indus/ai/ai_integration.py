"""
Intégration IA dans MainDock
Ajout des fonctionnalités IA au plugin principal
"""

from PyQt5.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
                             QProgressBar, QTextEdit, QGroupBox, QComboBox,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QMessageBox,
                             QFileDialog, QTabWidget, QWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY
import os
import json
from datetime import datetime


class AITrainingThread(QThread):
    """Thread pour l'entraînement du modèle IA (évite de bloquer l'UI)"""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, predictor, historical_data):
        super().__init__()
        self.predictor = predictor
        self.historical_data = historical_data
    
    def run(self):
        try:
            self.progress.emit(10, "Préparation des données...")
            
            # Entraînement
            self.predictor.train(self.historical_data, validation_split=0.2)
            
            self.progress.emit(100, "Entraînement terminé !")
            self.finished.emit(True, "Modèle entraîné avec succès")
            
        except Exception as e:
            self.finished.emit(False, f"Erreur: {str(e)}")


class AIModuleDock(QWidget):
    """
    Widget pour les fonctionnalités IA
    À intégrer dans MainDock comme un nouvel onglet
    """
    
    def __init__(self, parent, main_dock):
        super().__init__(parent)
        self.main_dock = main_dock
        self.predictor = None
        self.optimizer = None
        self.visualizer = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialise l'interface IA"""
        layout = QVBoxLayout()
        
        # === SECTION 1: ENTRAÎNEMENT DU MODÈLE ===
        training_group = QGroupBox("🤖 Entraînement du modèle IA")
        training_layout = QVBoxLayout()
        
        # Bouton charger données historiques
        self.btn_load_history = QPushButton("📂 Charger historique des visites")
        self.btn_load_history.clicked.connect(self._load_historical_data)
        training_layout.addWidget(self.btn_load_history)
        
        # Label statut données
        self.lbl_data_status = QLabel("Aucune donnée chargée")
        training_layout.addWidget(self.lbl_data_status)
        
        # Bouton entraîner
        self.btn_train = QPushButton("🚀 Entraîner le modèle")
        self.btn_train.clicked.connect(self._train_model)
        self.btn_train.setEnabled(False)
        training_layout.addWidget(self.btn_train)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        training_layout.addWidget(self.progress_bar)
        
        # Zone de texte pour logs
        self.txt_training_log = QTextEdit()
        self.txt_training_log.setReadOnly(True)
        self.txt_training_log.setMaximumHeight(150)
        training_layout.addWidget(self.txt_training_log)
        
        # Boutons sauvegarder/charger modèle
        model_buttons = QHBoxLayout()
        self.btn_save_model = QPushButton("💾 Sauvegarder modèle")
        self.btn_save_model.clicked.connect(self._save_model)
        self.btn_save_model.setEnabled(False)
        
        self.btn_load_model = QPushButton("📂 Charger modèle")
        self.btn_load_model.clicked.connect(self._load_model)
        
        model_buttons.addWidget(self.btn_save_model)
        model_buttons.addWidget(self.btn_load_model)
        training_layout.addLayout(model_buttons)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        # === SECTION 2: PRÉDICTIONS ===
        prediction_group = QGroupBox("🔮 Prédictions de pollution")
        prediction_layout = QVBoxLayout()
        
        # Bouton rechercher hotspots
        self.btn_find_hotspots = QPushButton("🔥 Rechercher les points chauds")
        self.btn_find_hotspots.clicked.connect(self._find_pollution_hotspots)
        self.btn_find_hotspots.setEnabled(False)
        prediction_layout.addWidget(self.btn_find_hotspots)
        
        # Seuil de probabilité
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Seuil de probabilité:"))
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.0, 1.0)
        self.spin_threshold.setSingleStep(0.1)
        self.spin_threshold.setValue(0.6)
        self.spin_threshold.setSuffix(" (60%)")
        threshold_layout.addWidget(self.spin_threshold)
        prediction_layout.addLayout(threshold_layout)
        
        # Tableau des hotspots
        self.table_hotspots = QTableWidget()
        self.table_hotspots.setColumnCount(5)
        self.table_hotspots.setHorizontalHeaderLabels([
            "Nœud", "Probabilité", "Risque", "Diamètre", "Action"
        ])
        self.table_hotspots.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_hotspots.setMaximumHeight(200)
        prediction_layout.addWidget(self.table_hotspots)
        
        # Bouton optimiser parcours
        self.btn_optimize_route = QPushButton("🗺️ Optimiser le parcours de visite")
        self.btn_optimize_route.clicked.connect(self._optimize_visit_route)
        self.btn_optimize_route.setEnabled(False)
        prediction_layout.addWidget(self.btn_optimize_route)
        
        prediction_group.setLayout(prediction_layout)
        layout.addWidget(prediction_group)
        
        # === SECTION 3: VISUALISATION 3D ===
        viz3d_group = QGroupBox("🎨 Visualisation 3D")
        viz3d_layout = QVBoxLayout()
        
        # Options de visualisation
        viz_options = QHBoxLayout()
        viz_options.addWidget(QLabel("Colorer par:"))
        self.combo_color_by = QComboBox()
        self.combo_color_by.addItems(['diameter', 'slope', 'elevation', 'type'])
        viz_options.addWidget(self.combo_color_by)
        
        self.chk_highlight_complex = QCheckBox("Mettre en évidence zones complexes")
        self.chk_highlight_complex.setChecked(True)
        viz_options.addWidget(self.chk_highlight_complex)
        
        viz3d_layout.addLayout(viz_options)
        
        # Détection zones complexes
        complex_layout = QHBoxLayout()
        complex_layout.addWidget(QLabel("Seuil densité:"))
        self.spin_density = QSpinBox()
        self.spin_density.setRange(3, 20)
        self.spin_density.setValue(5)
        self.spin_density.setSuffix(" canaux")
        complex_layout.addWidget(self.spin_density)
        
        complex_layout.addWidget(QLabel("Rayon:"))
        self.spin_radius = QSpinBox()
        self.spin_radius.setRange(10, 200)
        self.spin_radius.setValue(50)
        self.spin_radius.setSuffix(" m")
        complex_layout.addWidget(self.spin_radius)
        
        viz3d_layout.addLayout(complex_layout)
        
        # Boutons visualisation
        viz_buttons = QHBoxLayout()
        
        self.btn_viz_3d = QPushButton("🌐 Visualiser réseau 3D")
        self.btn_viz_3d.clicked.connect(self._visualize_3d)
        viz_buttons.addWidget(self.btn_viz_3d)
        
        self.btn_profile = QPushButton("📊 Profil en long")
        self.btn_profile.clicked.connect(self._show_profile)
        viz_buttons.addWidget(self.btn_profile)
        
        viz3d_layout.addLayout(viz_buttons)
        
        # Bouton exporter zones complexes
        self.btn_export_zones = QPushButton("📄 Exporter zones complexes (JSON)")
        self.btn_export_zones.clicked.connect(self._export_complex_zones)
        viz3d_layout.addWidget(self.btn_export_zones)
        
        viz3d_group.setLayout(viz3d_layout)
        layout.addWidget(viz3d_group)
        
        # === SECTION 4: STATISTIQUES ===
        stats_group = QGroupBox("📊 Statistiques IA")
        stats_layout = QVBoxLayout()
        
        self.lbl_stats = QLabel("Aucun modèle chargé")
        stats_layout.addWidget(self.lbl_stats)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _load_historical_data(self):
        """Charge les données historiques depuis un fichier JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Charger historique", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.historical_data = json.load(f)
            
            self.lbl_data_status.setText(
                f"✅ {len(self.historical_data)} visites chargées"
            )
            self.btn_train.setEnabled(True)
            
            self._log(f"Données historiques chargées: {len(self.historical_data)} visites")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les données:\n{str(e)}")
    
    def _train_model(self):
        """Lance l'entraînement du modèle"""
        try:
            from ..ai.pollution_predictor import PollutionPredictor
            
            self.predictor = PollutionPredictor()
            
            # Thread pour ne pas bloquer l'UI
            self.training_thread = AITrainingThread(self.predictor, self.historical_data)
            self.training_thread.progress.connect(self._on_training_progress)
            self.training_thread.finished.connect(self._on_training_finished)
            
            self.progress_bar.setVisible(True)
            self.btn_train.setEnabled(False)
            self._log("🚀 Début de l'entraînement...")
            
            self.training_thread.start()
            
        except ImportError:
            QMessageBox.critical(
                self, "Erreur",
                "Module IA non disponible. Installez scikit-learn:\npip install scikit-learn"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'entraînement:\n{str(e)}")
    
    def _on_training_progress(self, value, message):
        """Mise à jour de la progression"""
        self.progress_bar.setValue(value)
        self._log(message)
    
    def _on_training_finished(self, success, message):
        """Fin de l'entraînement"""
        self.progress_bar.setVisible(False)
        self.btn_train.setEnabled(True)
        
        if success:
            self._log("✅ " + message)
            self.btn_save_model.setEnabled(True)
            self.btn_find_hotspots.setEnabled(True)
            self.btn_optimize_route.setEnabled(True)
            
            QMessageBox.information(self, "Succès", message)
        else:
            self._log("❌ " + message)
            QMessageBox.critical(self, "Erreur", message)
    
    def _save_model(self):
        """Sauvegarde le modèle entraîné"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder modèle", "pollution_model.pkl", "Pickle Files (*.pkl)"
        )
        
        if file_path:
            self.predictor.save_model(file_path)
            self._log(f"💾 Modèle sauvegardé: {file_path}")
            QMessageBox.information(self, "Succès", "Modèle sauvegardé avec succès")
    
    def _load_model(self):
        """Charge un modèle pré-entraîné"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Charger modèle", "", "Pickle Files (*.pkl)"
        )
        
        if not file_path:
            return
        
        try:
            from ..ai.pollution_predictor import PollutionPredictor
            
            self.predictor = PollutionPredictor(model_path=file_path)
            
            self._log(f"📂 Modèle chargé: {file_path}")
            self.btn_find_hotspots.setEnabled(True)
            self.btn_optimize_route.setEnabled(True)
            self.btn_save_model.setEnabled(True)
            
            QMessageBox.information(self, "Succès", "Modèle chargé avec succès")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger le modèle:\n{str(e)}")
    
    def _find_pollution_hotspots(self):
        """Recherche les points chauds de pollution"""
        try:
            # TODO: Implémenter la récupération des nœuds et contexte
            # Pour l'instant, exemple avec données simulées
            
            QMessageBox.information(
                self, "Hotspots",
                "Fonctionnalité en cours d'implémentation.\n"
                "Nécessite l'intégration avec les données QGIS réelles."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la recherche:\n{str(e)}")
    
    def _optimize_visit_route(self):
        """Optimise le parcours de visite"""
        QMessageBox.information(
            self, "Optimisation",
            "Fonctionnalité en cours d'implémentation."
        )
    
    def _visualize_3d(self):
        """Lance la visualisation 3D"""
        try:
            from ..ai.network_visualizer_3d import NetworkVisualizer3D
            
            # Récupération des features
            canal_features = self._get_canal_features()
            
            if not canal_features:
                QMessageBox.warning(self, "Attention", "Aucune canalisation sélectionnée")
                return
            
            # Visualisation
            viz = NetworkVisualizer3D(use_pyvista=True)
            viz.visualize_network_3d(
                canal_features,
                color_by=self.combo_color_by.currentText(),
                show_labels=True,
                highlight_complex=self.chk_highlight_complex.isChecked()
            )
            
        except ImportError as e:
            QMessageBox.critical(
                self, "Erreur",
                f"Bibliothèques 3D non disponibles:\n{str(e)}\n\n"
                "Installez PyVista: pip install pyvista"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la visualisation:\n{str(e)}")
    
    def _show_profile(self):
        """Affiche le profil en long"""
        try:
            from ..ai.network_visualizer_3d import NetworkVisualizer3D
            
            canal_features = self._get_canal_features()
            
            if not canal_features:
                QMessageBox.warning(self, "Attention", "Aucune canalisation sélectionnée")
                return
            
            viz = NetworkVisualizer3D(use_pyvista=False)
            viz.create_profile_view(canal_features)
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération du profil:\n{str(e)}")
    
    def _export_complex_zones(self):
        """Exporte les zones complexes"""
        try:
            from ..ai.network_visualizer_3d import NetworkVisualizer3D
            
            canal_features = self._get_canal_features()
            
            if not canal_features:
                QMessageBox.warning(self, "Attention", "Aucune canalisation sélectionnée")
                return
            
            viz = NetworkVisualizer3D()
            complex_zones = viz.detect_complex_zones(
                canal_features,
                density_threshold=self.spin_density.value(),
                radius=self.spin_radius.value()
            )
            
            if not complex_zones:
                QMessageBox.information(self, "Information", "Aucune zone complexe détectée")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exporter zones complexes", "complex_zones.json", "JSON Files (*.json)"
            )
            
            if file_path:
                viz.export_complex_zones_report(complex_zones, file_path)
                QMessageBox.information(self, "Succès", f"Zones complexes exportées:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export:\n{str(e)}")
    
    def _get_canal_features(self) -> List[Dict]:
        """Récupère les features des canalisations depuis QGIS"""
        canal_layer = self.main_dock.canal_layer
        
        if not canal_layer:
            return []
        
        features = []
        for feature in canal_layer.selectedFeatures() if canal_layer.selectedFeatureCount() > 0 else canal_layer.getFeatures():
            geom = feature.geometry()
            coords = []
            
            if geom.isMultipart():
                for part in geom.asMultiPolyline():
                    coords.extend([[p.x(), p.y()] for p in part])
            else:
                coords = [[p.x(), p.y()] for p in geom.asPolyline()]
            
            feature_dict = {
                'id': feature.id(),
                'geometry': {'coordinates': coords},
                'diametre': feature.attribute('diametre') or 300,
                '_pente': feature.attribute('_pente') or feature.attribute('pente') or 0.005,
                'zmont': feature.attribute('zmont') or feature.attribute('zamont') or 0,
                'zaval': feature.attribute('zaval') or feature.attribute('zaval') or 0,
                'type_reseau': feature.attribute('type_reseau') or 'EU',
                'materiau': feature.attribute('materiau') or 'PVC',
                'longueur': geom.length()
            }
            
            features.append(feature_dict)
        
        return features
    
    def _log(self, message: str):
        """Ajoute un message au log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_training_log.append(f"[{timestamp}] {message}")
