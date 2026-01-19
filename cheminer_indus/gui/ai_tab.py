# -*- coding: utf-8 -*-
"""
Onglet IA pour le plugin CheminerIndus
Interface pour la prédiction de pollution et la visualisation 3D
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTextEdit, QFileDialog, QMessageBox, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QProgressBar
)
from qgis.core import QgsProject, Qgis
from qgis.PyQt.QtGui import QFont


class AITab(QWidget):
    """Onglet IA pour prédiction de pollution et visualisation 3D"""
    
    def __init__(self, main_dock, parent=None):
        super().__init__(parent)
        self.main_dock = main_dock
        self.iface = main_dock.iface
        
        # État
        self.model_path = None
        self.predictor = None
        self.visualizer = None
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel("🤖 Intelligence Artificielle")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Module IA pour la prédiction de pollution et l'optimisation\n"
            "des tournées de visite. Nécessite l'entraînement préalable du modèle."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Groupe 1: Entraînement du modèle
        self._add_training_group(layout)
        
        # Groupe 2: Prédiction
        self._add_prediction_group(layout)
        
        # Groupe 3: Visualisation 3D
        self._add_visualization_group(layout)
        
        # Groupe 4: Résultats
        self._add_results_group(layout)
        
        layout.addStretch()
        
    def _add_training_group(self, layout):
        """Ajoute le groupe d'entraînement"""
        group = QGroupBox("📚 Entraînement du modèle")
        group_layout = QVBoxLayout(group)
        
        # Info
        info = QLabel("Entraînez le modèle IA avec vos données historiques de visites.")
        info.setWordWrap(True)
        group_layout.addWidget(info)
        
        # Bouton entraîner
        btn_train = QPushButton("⚙️ Entraîner le modèle")
        btn_train.setToolTip("Entraîner le modèle IA avec les couches sélectionnées")
        btn_train.clicked.connect(self._on_train_model)
        group_layout.addWidget(btn_train)
        
        # Bouton charger modèle existant
        btn_load = QPushButton("📂 Charger un modèle existant")
        btn_load.setToolTip("Charger un modèle IA déjà entraîné")
        btn_load.clicked.connect(self._on_load_model)
        group_layout.addWidget(btn_load)
        
        # Statut du modèle
        self.model_status_label = QLabel("❌ Aucun modèle chargé")
        self.model_status_label.setStyleSheet("color: red; font-weight: bold;")
        group_layout.addWidget(self.model_status_label)
        
        layout.addWidget(group)
        
    def _add_prediction_group(self, layout):
        """Ajoute le groupe de prédiction"""
        group = QGroupBox("🔮 Prédiction de pollution")
        group_layout = QVBoxLayout(group)
        
        # Seuil de risque
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Seuil de risque élevé :"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(70)
        self.threshold_spin.setSuffix(" %")
        threshold_layout.addWidget(self.threshold_spin)
        group_layout.addLayout(threshold_layout)
        
        # Bouton prédire
        btn_predict = QPushButton("🎯 Prédire les zones à risque")
        btn_predict.setToolTip("Analyser le réseau et prédire les zones à risque de pollution")
        btn_predict.clicked.connect(self._on_predict)
        group_layout.addWidget(btn_predict)
        
        # Bouton optimiser parcours
        btn_optimize = QPushButton("🗺️ Optimiser le parcours de visite")
        btn_optimize.setToolTip("Générer un parcours optimisé pour les visites")
        btn_optimize.clicked.connect(self._on_optimize_tour)
        group_layout.addWidget(btn_optimize)
        
        # Nombre de visites par jour
        visits_layout = QHBoxLayout()
        visits_layout.addWidget(QLabel("Visites / jour :"))
        self.visits_per_day = QSpinBox()
        self.visits_per_day.setRange(1, 100)
        self.visits_per_day.setValue(20)
        visits_layout.addWidget(self.visits_per_day)
        group_layout.addLayout(visits_layout)
        
        layout.addWidget(group)
        
    def _add_visualization_group(self, layout):
        """Ajoute le groupe de visualisation 3D"""
        group = QGroupBox("🔮 Visualisation 3D")
        group_layout = QVBoxLayout(group)
        
        # Coloration
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Colorer par :"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["diameter", "slope", "elevation", "type"])
        color_layout.addWidget(self.color_combo)
        group_layout.addLayout(color_layout)
        
        # Mode interactif
        self.interactive_check = QCheckBox("Mode interactif (PyVista)")
        self.interactive_check.setChecked(True)
        self.interactive_check.setToolTip(
            "Cocher pour une visualisation 3D interactive (nécessite PyVista)"
        )
        group_layout.addWidget(self.interactive_check)
        
        # Bouton visualiser
        btn_viz = QPushButton("🌐 Visualiser le réseau en 3D")
        btn_viz.setToolTip("Afficher une représentation 3D du réseau sélectionné")
        btn_viz.clicked.connect(self._on_visualize_3d)
        group_layout.addWidget(btn_viz)
        
        # Bouton zones complexes
        btn_complex = QPushButton("🔍 Détecter les zones complexes")
        btn_complex.setToolTip("Identifier automatiquement les zones avec réseaux entremêlés")
        btn_complex.clicked.connect(self._on_detect_complex_zones)
        group_layout.addWidget(btn_complex)
        
        # Seuil de complexité
        complexity_layout = QHBoxLayout()
        complexity_layout.addWidget(QLabel("Seuil de complexité :"))
        self.complexity_spin = QSpinBox()
        self.complexity_spin.setRange(100, 1000)
        self.complexity_spin.setValue(300)
        complexity_layout.addWidget(self.complexity_spin)
        group_layout.addLayout(complexity_layout)
        
        layout.addWidget(group)
        
    def _add_results_group(self, layout):
        """Ajoute le groupe de résultats"""
        group = QGroupBox("📊 Résultats")
        group_layout = QVBoxLayout(group)
        
        # Zone de texte pour les résultats
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        self.results_text.setPlaceholderText(
            "Les résultats des analyses IA s'afficheront ici..."
        )
        group_layout.addWidget(self.results_text)
        
        # Bouton exporter
        btn_export = QPushButton("💾 Exporter les résultats")
        btn_export.setToolTip("Exporter les résultats en JSON")
        btn_export.clicked.connect(self._on_export_results)
        group_layout.addWidget(btn_export)
        
        layout.addWidget(group)
        
    # ========================================
    # Handlers des boutons
    # ========================================
    
    def _on_train_model(self):
        """Entraîner le modèle IA"""
        try:
            # Récupérer la couche de canalisations depuis le combo box
            canal_layer = None
            if hasattr(self.main_dock, 'canal_combo'):
                canal_layer = self.main_dock.canal_combo.currentData()
            
            # Si pas trouvée dans le combo, essayer l'attribut direct
            if not canal_layer and hasattr(self.main_dock, 'canal_layer'):
                canal_layer = self.main_dock.canal_layer
            
            # Vérifier que la couche est valide
            if not canal_layer or not canal_layer.isValid():
                QMessageBox.warning(
                    self,
                    "Couche manquante",
                    "Veuillez sélectionner une couche de canalisations dans l'onglet COUCHES.\n\n"
                    "La couche doit contenir les canalisations du réseau d'assainissement."
                )
                return
            
            # Import du prédicteur
            try:
                from ..ai.pollution_predictor import PollutionPredictor
            except ImportError as e:
                QMessageBox.critical(
                    self,
                    "Erreur d'import",
                    f"Impossible d'importer le module IA.\n"
                    f"Assurez-vous d'avoir installé les dépendances:\n"
                    f"pip install scikit-learn numpy\n\n"
                    f"Erreur: {str(e)}"
                )
                return
            
            # Demander où sauvegarder le modèle
            model_path, _ = QFileDialog.getSaveFileName(
                self,
                "Sauvegarder le modèle",
                "",
                "Pickle Files (*.pkl)"
            )
            
            if not model_path:
                return
            
            # Créer le prédicteur
            self.predictor = PollutionPredictor()
            
            # Message d'info
            self.iface.messageBar().pushMessage(
                "IA",
                "Entraînement du modèle en cours... Cela peut prendre quelques minutes.",
                level=Qgis.Info,
                duration=5
            )
            
            # Entraîner (générer des données synthétiques pour l'instant)
            from ..ai.training_data_generator import TrainingDataGenerator
            
            generator = TrainingDataGenerator(canal_layer)
            X_train, y_train = generator.generate_training_data(n_samples=1000)
            
            # Entraîner
            self.predictor.train(X_train, y_train)
            
            # Sauvegarder
            self.predictor.save_model(model_path)
            self.model_path = model_path
            
            # Mettre à jour le statut
            self.model_status_label.setText(f"✅ Modèle chargé : {model_path}")
            self.model_status_label.setStyleSheet("color: green; font-weight: bold;")
            
            QMessageBox.information(
                self,
                "Succès",
                f"Modèle entraîné et sauvegardé avec succès !\n\n"
                f"Fichier : {model_path}\n"
                f"Vous pouvez maintenant utiliser la prédiction."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'entraînement du modèle:\n{str(e)}"
            )
            
    def _on_load_model(self):
        """Charger un modèle existant"""
        try:
            model_path, _ = QFileDialog.getOpenFileName(
                self,
                "Charger un modèle",
                "",
                "Pickle Files (*.pkl)"
            )
            
            if not model_path:
                return
            
            # Import
            try:
                from ..ai.pollution_predictor import PollutionPredictor
            except ImportError as e:
                QMessageBox.critical(
                    self,
                    "Erreur d'import",
                    f"Impossible d'importer le module IA.\n{str(e)}"
                )
                return
            
            # Charger
            self.predictor = PollutionPredictor()
            self.predictor.load_model(model_path)
            self.model_path = model_path
            
            # Mettre à jour le statut
            self.model_status_label.setText(f"✅ Modèle chargé : {model_path}")
            self.model_status_label.setStyleSheet("color: green; font-weight: bold;")
            
            QMessageBox.information(
                self,
                "Succès",
                f"Modèle chargé avec succès !\n\nFichier : {model_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors du chargement du modèle:\n{str(e)}"
            )
            
    def _on_predict(self):
        """Prédire les zones à risque"""
        try:
            # Vérifier le modèle
            if not self.predictor:
                QMessageBox.warning(
                    self,
                    "Modèle manquant",
                    "Veuillez d'abord entraîner ou charger un modèle."
                )
                return
            
            # Récupérer la couche de canalisations
            canal_layer = None
            if hasattr(self.main_dock, 'canal_combo'):
                canal_layer = self.main_dock.canal_combo.currentData()
            
            if not canal_layer and hasattr(self.main_dock, 'canal_layer'):
                canal_layer = self.main_dock.canal_layer
            
            # Vérifier que la couche est valide
            if not canal_layer or not canal_layer.isValid():
                QMessageBox.warning(
                    self,
                    "Couche manquante",
                    "Veuillez sélectionner une couche de canalisations dans l'onglet COUCHES."
                )
                return
            
            # Prédire
            self.iface.messageBar().pushMessage(
                "IA",
                "Prédiction en cours...",
                level=Qgis.Info,
                duration=3
            )
            
            predictions = self.predictor.predict_pollution(canal_layer)
            threshold = self.threshold_spin.value()
            hotspots = self.predictor.get_hotspots(predictions, threshold=threshold)
            
            # Afficher les résultats
            results = f"🎯 PRÉDICTION DE POLLUTION\n"
            results += f"={'='*50}\n\n"
            results += f"Seuil de risque : {threshold}%\n"
            results += f"Points chauds détectés : {len(hotspots)}\n\n"
            
            # Top 10
            results += "Top 10 des zones à risque :\n"
            results += "-" * 50 + "\n"
            for i, (node_id, prob, risk) in enumerate(hotspots[:10], 1):
                results += f"{i}. {node_id} → {prob:.1f}% → {risk}\n"
            
            self.results_text.setText(results)
            
            # Sauvegarder pour optimisation
            self._last_hotspots = hotspots
            
            QMessageBox.information(
                self,
                "Prédiction terminée",
                f"{len(hotspots)} zones à risque identifiées !"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de la prédiction:\n{str(e)}"
            )
            
    def _on_optimize_tour(self):
        """Optimiser le parcours de visite"""
        try:
            if not hasattr(self, '_last_hotspots'):
                QMessageBox.warning(
                    self,
                    "Prédiction nécessaire",
                    "Veuillez d'abord effectuer une prédiction."
                )
                return
            
            # Point de départ (centre de la carte)
            extent = self.iface.mapCanvas().extent()
            start_point = (extent.center().x(), extent.center().y())
            
            # Optimiser
            max_visits = self.visits_per_day.value()
            tour = self.predictor.optimize_visit_tour(
                self._last_hotspots,
                start_point=start_point,
                max_visits_per_day=max_visits
            )
            
            # Afficher
            results = f"🗺️ PARCOURS OPTIMISÉ\n"
            results += f"={'='*50}\n\n"
            results += f"Visites par jour : {max_visits}\n"
            results += f"Nombre de jours : {len(tour)}\n\n"
            
            for day, visits in tour.items():
                results += f"\n📅 Jour {day} ({len(visits)} visites) :\n"
                results += "-" * 50 + "\n"
                for i, (node_id, score) in enumerate(visits[:5], 1):
                    results += f"  {i}. {node_id} (score: {score:.1f})\n"
                if len(visits) > 5:
                    results += f"  ... et {len(visits)-5} autres visites\n"
            
            self.results_text.setText(results)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'optimisation:\n{str(e)}"
            )
            
    def _on_visualize_3d(self):
        """Visualiser en 3D"""
        try:
            # Récupérer la couche de canalisations
            canal_layer = None
            if hasattr(self.main_dock, 'canal_combo'):
                canal_layer = self.main_dock.canal_combo.currentData()
            
            if not canal_layer and hasattr(self.main_dock, 'canal_layer'):
                canal_layer = self.main_dock.canal_layer
            
            # Vérifier que la couche est valide
            if not canal_layer or not canal_layer.isValid():
                QMessageBox.warning(
                    self,
                    "Couche manquante",
                    "Veuillez sélectionner une couche de canalisations dans l'onglet COUCHES."
                )
                return
            
            # Import
            try:
                from ..ai.network_visualizer_3d import NetworkVisualizer3D
            except ImportError as e:
                QMessageBox.critical(
                    self,
                    "Erreur d'import",
                    f"Impossible d'importer le visualiseur 3D.\n"
                    f"Assurez-vous d'avoir installé matplotlib:\n"
                    f"pip install matplotlib\n\n"
                    f"Erreur: {str(e)}"
                )
                return
            
            # Créer le visualiseur
            self.visualizer = NetworkVisualizer3D()
            
            # Paramètres
            color_by = self.color_combo.currentText()
            interactive = self.interactive_check.isChecked()
            
            # Visualiser
            self.iface.messageBar().pushMessage(
                "IA",
                "Génération de la visualisation 3D...",
                level=Qgis.Info,
                duration=3
            )
            
            self.visualizer.visualize_network(
                canal_layer,
                color_by=color_by,
                interactive=interactive
            )
            
            self.results_text.setText(
                f"✅ Visualisation 3D générée avec succès !\n\n"
                f"Coloration : {color_by}\n"
                f"Mode : {'Interactif' if interactive else 'Statique'}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de la visualisation 3D:\n{str(e)}"
            )
            
    def _on_detect_complex_zones(self):
        """Détecter les zones complexes"""
        try:
            # Récupérer la couche de canalisations
            canal_layer = None
            if hasattr(self.main_dock, 'canal_combo'):
                canal_layer = self.main_dock.canal_combo.currentData()
            
            if not canal_layer and hasattr(self.main_dock, 'canal_layer'):
                canal_layer = self.main_dock.canal_layer
            
            # Vérifier que la couche est valide
            if not canal_layer or not canal_layer.isValid():
                QMessageBox.warning(
                    self,
                    "Couche manquante",
                    "Veuillez sélectionner une couche de canalisations dans l'onglet COUCHES."
                )
                return
            
            # Import
            try:
                from ..ai.network_visualizer_3d import NetworkVisualizer3D
            except ImportError as e:
                QMessageBox.critical(
                    self,
                    "Erreur d'import",
                    f"Impossible d'importer le visualiseur 3D.\n{str(e)}"
                )
                return
            
            # Créer le visualiseur
            self.visualizer = NetworkVisualizer3D()
            
            # Détecter
            threshold = self.complexity_spin.value()
            complex_zones = self.visualizer.detect_complex_zones(
                canal_layer,
                complexity_threshold=threshold
            )
            
            # Afficher
            results = f"🔍 ZONES COMPLEXES DÉTECTÉES\n"
            results += f"={'='*50}\n\n"
            results += f"Seuil de complexité : {threshold}\n"
            results += f"Zones trouvées : {len(complex_zones)}\n\n"
            
            for zone in complex_zones:
                results += f"\n🎯 Zone #{zone['zone_id']}\n"
                results += "-" * 50 + "\n"
                results += f"Centre : ({zone['center'][0]:.1f}, {zone['center'][1]:.1f})\n"
                results += f"Canalisations : {zone['pipe_count']}\n"
                results += f"Diamètres : {zone['diameter_range']}\n"
                results += f"Dénivelé : {zone['elevation_range']:.1f}m\n"
                results += f"Score : {zone['complexity_score']} → {zone['risk_level']}\n"
            
            self.results_text.setText(results)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de la détection:\n{str(e)}"
            )
            
    def _on_export_results(self):
        """Exporter les résultats"""
        try:
            results = self.results_text.toPlainText()
            if not results:
                QMessageBox.warning(
                    self,
                    "Aucun résultat",
                    "Aucun résultat à exporter."
                )
                return
            
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Exporter les résultats",
                "",
                "Text Files (*.txt)"
            )
            
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(results)
                
                QMessageBox.information(
                    self,
                    "Succès",
                    f"Résultats exportés avec succès !\n\nFichier : {path}"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'export:\n{str(e)}"
            )
