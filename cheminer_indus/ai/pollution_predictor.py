"""
Module d'intelligence artificielle pour prédiction de pollution
Utilise les données historiques de visites pour optimiser les recherches
"""

import numpy as np
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. ML features disabled.")


class PollutionPredictor:
    """
    Prédicteur de pollution basé sur Machine Learning
    
    Utilise les données historiques pour prédire la probabilité de pollution
    sur chaque nœud/branche du réseau
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialise le prédicteur
        
        Args:
            model_path: Chemin vers un modèle pré-entraîné (optionnel)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required for AI features. Install with: pip install scikit-learn")
        
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
    
    def extract_features(self, 
                        node_data: Dict,
                        upstream_data: List[Dict],
                        downstream_data: List[Dict],
                        historical_visits: List[Dict]) -> np.ndarray:
        """
        Extrait les features pour le Machine Learning
        
        Args:
            node_data: Données du nœud actuel
            upstream_data: Données des branches amont
            downstream_data: Données des branches aval
            historical_visits: Historique des visites précédentes
            
        Returns:
            Array numpy des features
        """
        features = []
        
        # === FEATURES DU NŒUD ===
        features.append(node_data.get('elevation', 0))  # Altitude
        features.append(node_data.get('x', 0))  # Coordonnée X
        features.append(node_data.get('y', 0))  # Coordonnée Y
        
        # === FEATURES AMONT (moyennes) ===
        if upstream_data:
            avg_diameter_up = np.mean([b.get('diametre', 300) for b in upstream_data])
            avg_slope_up = np.mean([b.get('pente', 0.005) for b in upstream_data])
            avg_z_amont = np.mean([b.get('z_amont', 0) for b in upstream_data])
            avg_z_aval = np.mean([b.get('z_aval', 0) for b in upstream_data])
            total_length_up = sum([b.get('longueur', 0) for b in upstream_data])
            nb_branches_up = len(upstream_data)
            
            # Types de réseau amont (EU=1, EP=2, Mixte=3)
            type_codes = {'EU': 1, 'EP': 2, 'Mixte': 3, 'UNITAIRE': 3}
            avg_type_up = np.mean([type_codes.get(b.get('type_reseau', 'EU'), 1) 
                                   for b in upstream_data])
            
            # Matériaux amont (encodage)
            material_codes = {'PVC': 1, 'Fonte': 2, 'Béton': 3, 'Grès': 4, 'PE': 5}
            avg_material_up = np.mean([material_codes.get(b.get('materiau', 'PVC'), 1) 
                                       for b in upstream_data])
        else:
            avg_diameter_up = 0
            avg_slope_up = 0
            avg_z_amont = 0
            avg_z_aval = 0
            total_length_up = 0
            nb_branches_up = 0
            avg_type_up = 0
            avg_material_up = 0
        
        features.extend([
            avg_diameter_up,
            avg_slope_up,
            avg_z_amont,
            avg_z_aval,
            total_length_up,
            nb_branches_up,
            avg_type_up,
            avg_material_up
        ])
        
        # === FEATURES AVAL (moyennes) ===
        if downstream_data:
            avg_diameter_down = np.mean([b.get('diametre', 300) for b in downstream_data])
            avg_slope_down = np.mean([b.get('pente', 0.005) for b in downstream_data])
            nb_branches_down = len(downstream_data)
        else:
            avg_diameter_down = 0
            avg_slope_down = 0
            nb_branches_down = 0
        
        features.extend([
            avg_diameter_down,
            avg_slope_down,
            nb_branches_down
        ])
        
        # === FEATURES TOPOLOGIQUES ===
        # Ratio diamètres amont/aval (indication de réduction)
        diameter_ratio = avg_diameter_up / avg_diameter_down if avg_diameter_down > 0 else 1.0
        features.append(diameter_ratio)
        
        # Différence de pente (indication de changement brutal)
        slope_diff = abs(avg_slope_up - avg_slope_down)
        features.append(slope_diff)
        
        # Complexité du nœud (nombre total de branches)
        node_complexity = nb_branches_up + nb_branches_down
        features.append(node_complexity)
        
        # === FEATURES HISTORIQUES ===
        if historical_visits:
            # Nombre de visites précédentes sur ce nœud
            nb_visits = len([v for v in historical_visits 
                           if v.get('node_id') == node_data.get('id')])
            
            # Nombre de fois où pollution détectée
            nb_polluted = len([v for v in historical_visits 
                             if v.get('node_id') == node_data.get('id') 
                             and v.get('polluted', False)])
            
            # Taux de pollution historique
            pollution_rate = nb_polluted / nb_visits if nb_visits > 0 else 0
            
            # Jours depuis dernière visite
            last_visits = [v for v in historical_visits 
                          if v.get('node_id') == node_data.get('id')]
            if last_visits:
                last_visit_date = max([v.get('date', datetime.min) for v in last_visits])
                days_since_visit = (datetime.now() - last_visit_date).days
            else:
                days_since_visit = 9999  # Jamais visité
            
            # Pollution dans le voisinage (nœuds proches)
            nearby_polluted = len([v for v in historical_visits
                                  if v.get('polluted', False)
                                  and self._is_nearby(node_data, v, radius=100)])
            
        else:
            nb_visits = 0
            nb_polluted = 0
            pollution_rate = 0
            days_since_visit = 9999
            nearby_polluted = 0
        
        features.extend([
            nb_visits,
            nb_polluted,
            pollution_rate,
            days_since_visit,
            nearby_polluted
        ])
        
        # === FEATURES TEMPORELLES ===
        now = datetime.now()
        month = now.month  # Saisonnalité
        day_of_week = now.weekday()
        
        features.extend([
            month,
            day_of_week
        ])
        
        return np.array(features)
    
    def _is_nearby(self, node1: Dict, node2: Dict, radius: float = 100) -> bool:
        """Vérifie si deux nœuds sont proches"""
        x1, y1 = node1.get('x', 0), node1.get('y', 0)
        x2, y2 = node2.get('x', 0), node2.get('y', 0)
        distance = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        return distance <= radius
    
    def prepare_training_data(self, historical_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prépare les données d'entraînement à partir de l'historique
        
        Args:
            historical_data: Liste des visites historiques avec contexte
            
        Returns:
            X (features), y (labels: 0=non pollué, 1=pollué)
        """
        X_list = []
        y_list = []
        
        for visit in historical_data:
            features = self.extract_features(
                node_data=visit.get('node_data', {}),
                upstream_data=visit.get('upstream_data', []),
                downstream_data=visit.get('downstream_data', []),
                historical_visits=visit.get('historical_context', [])
            )
            
            label = 1 if visit.get('polluted', False) else 0
            
            X_list.append(features)
            y_list.append(label)
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        return X, y
    
    def train(self, historical_data: List[Dict], validation_split: float = 0.2):
        """
        Entraîne le modèle sur les données historiques
        
        Args:
            historical_data: Données d'entraînement
            validation_split: Proportion des données pour validation
        """
        print(f"🤖 Préparation des données d'entraînement ({len(historical_data)} visites)...")
        X, y = self.prepare_training_data(historical_data)
        
        # Normalisation
        X_scaled = self.scaler.fit_transform(X)
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        print(f"📊 Entraînement : {len(X_train)} échantillons")
        print(f"📊 Validation : {len(X_test)} échantillons")
        print(f"📊 Distribution : {np.sum(y_train)} pollués / {len(y_train)} total")
        
        # Entraînement
        print("🚀 Entraînement du modèle...")
        self.model.fit(X_train, y_train)
        
        # Évaluation
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\n✅ Modèle entraîné avec succès !")
        print(f"📈 Précision : {accuracy*100:.2f}%")
        print("\n📊 Rapport détaillé :")
        print(classification_report(y_test, y_pred, target_names=['Non pollué', 'Pollué']))
        
        # Feature importance
        feature_importance = self.model.feature_importances_
        print("\n🔍 Top 5 des features les plus importantes :")
        top_indices = np.argsort(feature_importance)[-5:][::-1]
        for idx in top_indices:
            print(f"  - Feature {idx}: {feature_importance[idx]:.4f}")
        
        self.is_trained = True
    
    def predict_pollution_probability(self, 
                                     node_data: Dict,
                                     upstream_data: List[Dict],
                                     downstream_data: List[Dict],
                                     historical_visits: List[Dict]) -> float:
        """
        Prédit la probabilité de pollution pour un nœud
        
        Returns:
            Probabilité entre 0 et 1
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet. Call train() first.")
        
        features = self.extract_features(
            node_data, upstream_data, downstream_data, historical_visits
        )
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Prédiction de probabilité
        proba = self.model.predict_proba(features_scaled)[0][1]  # Proba classe 1 (pollué)
        
        return proba
    
    def get_pollution_hotspots(self,
                               nodes: List[Dict],
                               get_context_fn,
                               threshold: float = 0.6) -> List[Dict]:
        """
        Identifie les points chauds de pollution
        
        Args:
            nodes: Liste de tous les nœuds
            get_context_fn: Fonction pour obtenir le contexte d'un nœud
            threshold: Seuil de probabilité pour considérer un hotspot
            
        Returns:
            Liste des hotspots triée par probabilité décroissante
        """
        hotspots = []
        
        for node in nodes:
            context = get_context_fn(node)
            
            proba = self.predict_pollution_probability(
                node_data=node,
                upstream_data=context['upstream'],
                downstream_data=context['downstream'],
                historical_visits=context['history']
            )
            
            if proba >= threshold:
                hotspots.append({
                    'node': node,
                    'probability': proba,
                    'risk_level': self._get_risk_level(proba),
                    'context': context
                })
        
        # Tri par probabilité décroissante
        hotspots.sort(key=lambda x: x['probability'], reverse=True)
        
        return hotspots
    
    def _get_risk_level(self, probability: float) -> str:
        """Détermine le niveau de risque"""
        if probability >= 0.8:
            return 'CRITIQUE'
        elif probability >= 0.6:
            return 'ÉLEVÉ'
        elif probability >= 0.4:
            return 'MOYEN'
        else:
            return 'FAIBLE'
    
    def save_model(self, path: str):
        """Sauvegarde le modèle entraîné"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"💾 Modèle sauvegardé : {path}")
    
    def load_model(self, path: str):
        """Charge un modèle pré-entraîné"""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.is_trained = model_data['is_trained']
        
        print(f"📂 Modèle chargé : {path}")
        print(f"   Entraîné le : {model_data.get('saved_at', 'unknown')}")

    # ------------------------------------------------------------------
    # Compatibilité avec l'onglet IA (GUI)
    # ------------------------------------------------------------------
    def predict_pollution(self, canal_layer):
        """
        Prédiction simplifiée sur une couche de canalisations.
        Retourne une liste [(id, proba, niveau_risque), ...]
        """
        if not canal_layer or not canal_layer.isValid():
            return []

        predictions = []

        for feat in canal_layer.getFeatures():
            fid = feat.id()
            diameter = feat.attribute("diametre") or feat.attribute("diam") or 0
            slope = feat.attribute("pente") or 0
            typ = feat.attribute("typreseau") or feat.attribute("type_reseau") or ""

            score = 20
            try:
                slope_val = float(slope)
                if slope_val <= 0.003:
                    score += 30
                elif slope_val <= 0.006:
                    score += 15
            except Exception:
                pass

            try:
                diam_val = float(diameter)
                if diam_val <= 200:
                    score += 10
                elif diam_val <= 300:
                    score += 5
            except Exception:
                pass

            if str(typ).strip() in ("02", "EU"):
                score += 10

            score = min(100, max(0, score))
            risk = self._get_risk_level(score / 100.0)
            predictions.append((str(fid), score, risk))

        return predictions

    def get_hotspots(self, predictions: List[Tuple[str, float, str]], threshold: float = 70.0):
        """Filtre les points chauds à partir de la liste prédite."""
        if not predictions:
            return []
        filtered = [p for p in predictions if p[1] >= threshold]
        return sorted(filtered, key=lambda x: x[1], reverse=True)

    def optimize_visit_tour(self, hotspots: List[Tuple[str, float, str]],
                            start_point=None, max_visits_per_day: int = 20):
        """
        Optimisation simple par ordre décroissant de risque.
        Retourne un dict {jour: [(id, score), ...]}
        """
        if not hotspots:
            return {}

        ordered = [(h[0], h[1]) for h in hotspots]
        tour = {}
        day = 1
        for i in range(0, len(ordered), max_visits_per_day):
            tour[day] = ordered[i:i + max_visits_per_day]
            day += 1
        return tour


class VisitOptimizer:
    """
    Optimiseur de parcours de visite
    Utilise les prédictions IA pour suggérer l'ordre optimal de visite
    """
    
    def __init__(self, predictor: PollutionPredictor):
        self.predictor = predictor
    
    def suggest_visit_order(self,
                           start_node: Dict,
                           candidate_nodes: List[Dict],
                           get_context_fn,
                           max_distance: float = 1000) -> List[Dict]:
        """
        Suggère l'ordre optimal de visite des nœuds
        
        Args:
            start_node: Nœud de départ
            candidate_nodes: Nœuds candidats à visiter
            get_context_fn: Fonction pour obtenir le contexte
            max_distance: Distance maximale acceptable (m)
            
        Returns:
            Liste ordonnée des nœuds à visiter avec scores
        """
        scored_nodes = []
        
        for node in candidate_nodes:
            context = get_context_fn(node)
            
            # Probabilité de pollution
            pollution_proba = self.predictor.predict_pollution_probability(
                node_data=node,
                upstream_data=context['upstream'],
                downstream_data=context['downstream'],
                historical_visits=context['history']
            )
            
            # Distance depuis le départ
            distance = self._calculate_distance(start_node, node)
            
            # Score composite (favorise haute proba et faible distance)
            # Score = pollution_proba * 100 - (distance / max_distance) * 20
            score = pollution_proba * 100 - (distance / max_distance) * 20
            
            scored_nodes.append({
                'node': node,
                'pollution_probability': pollution_proba,
                'distance': distance,
                'score': score,
                'risk_level': self.predictor._get_risk_level(pollution_proba)
            })
        
        # Tri par score décroissant
        scored_nodes.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_nodes
    
    def _calculate_distance(self, node1: Dict, node2: Dict) -> float:
        """Calcule la distance entre deux nœuds"""
        x1, y1 = node1.get('x', 0), node1.get('y', 0)
        x2, y2 = node2.get('x', 0), node2.get('y', 0)
        return np.sqrt((x2-x1)**2 + (y2-y1)**2)
    
    def optimize_multi_day_plan(self,
                                all_nodes: List[Dict],
                                get_context_fn,
                                days: int = 5,
                                nodes_per_day: int = 10) -> Dict:
        """
        Optimise un plan de visite sur plusieurs jours
        
        Returns:
            Plan jour par jour avec nœuds prioritaires
        """
        # Prédire pour tous les nœuds
        hotspots = self.predictor.get_pollution_hotspots(
            all_nodes, get_context_fn, threshold=0.3
        )
        
        # Répartition sur les jours
        plan = {}
        for day in range(1, days + 1):
            start_idx = (day - 1) * nodes_per_day
            end_idx = start_idx + nodes_per_day
            
            day_nodes = hotspots[start_idx:end_idx]
            
            plan[f"Jour {day}"] = {
                'nodes': day_nodes,
                'total_nodes': len(day_nodes),
                'avg_probability': np.mean([n['probability'] for n in day_nodes]) if day_nodes else 0,
                'critical_nodes': len([n for n in day_nodes if n['risk_level'] == 'CRITIQUE'])
            }
        
        return plan
