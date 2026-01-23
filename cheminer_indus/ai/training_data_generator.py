"""
Utilitaire pour générer des données d'entraînement depuis l'historique de visites
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict

from qgis.core import QgsExpression, QgsFeatureRequest
import random


def convert_visits_to_training_data(visits_history: List[Dict], 
                                    canal_layer,
                                    ouvr_layer) -> List[Dict]:
    """
    Convertit l'historique des visites en données d'entraînement pour l'IA
    
    Args:
        visits_history: Liste des visites (format interne du plugin)
        canal_layer: Couche des canalisations QGIS
        ouvr_layer: Couche des ouvrages QGIS
        
    Returns:
        Liste de données formatées pour l'entraînement
    """
    training_data = []

    def _ouvrage_z(node_id: str):
        if not node_id or not ouvr_layer:
            return 0
        try:
            expr = QgsExpression(f"trim(\"idouvrage\") = '{str(node_id).replace(\"'\", \"''\")}'")
            req = QgsFeatureRequest(expr)
            for feat in ouvr_layer.getFeatures(req):
                if feat.fields().indexOf('z') >= 0:
                    val = feat.attribute('z')
                    return val if val is not None else 0
        except Exception:
            return 0
        return 0
    
    for visit in visits_history:
        node_id = visit.get('node_id')
        polluted = visit.get('polluted', False)
        visit_date = visit.get('date', datetime.now())
        
        # Récupération du nœud (ouvrage)
        node_feature = ouvr_layer.getFeature(node_id)
        
        if not node_feature:
            continue
        
        node_geom = node_feature.geometry()
        node_point = node_geom.asPoint()
        
        node_data = {
            'id': node_id,
            'x': node_point.x(),
            'y': node_point.y(),
            'elevation': node_feature.attribute('altitude') or 0
        }
        
        # Recherche des branches amont
        upstream_data = []
        expr = f"trim(idnterm) = '{node_id}'"
        canal_layer.selectByExpression(expr)
        
        for canal_feat in canal_layer.selectedFeatures():
            z_amont = canal_feat.attribute('zmont')
            if z_amont is None or z_amont == "":
                z_amont = canal_feat.attribute('zamont')
            z_aval = canal_feat.attribute('zaval')
            if z_aval is None or z_aval == "":
                z_aval = canal_feat.attribute('zaval')
            if z_amont in (None, ""):
                z_amont = _ouvrage_z(canal_feat.attribute('idnini'))
            if z_aval in (None, ""):
                z_aval = _ouvrage_z(canal_feat.attribute('idnterm'))
            upstream_data.append({
                'diametre': canal_feat.attribute('diametre') or 300,
                'pente': canal_feat.attribute('pente') or 0.005,
                'z_amont': z_amont or 0,
                'z_aval': z_aval or 0,
                'longueur': canal_feat.geometry().length(),
                'type_reseau': canal_feat.attribute('type_reseau') or 'EU',
                'materiau': canal_feat.attribute('materiau') or 'PVC'
            })
        
        # Recherche des branches aval
        downstream_data = []
        expr = f"trim(idnini) = '{node_id}'"
        canal_layer.selectByExpression(expr)
        
        for canal_feat in canal_layer.selectedFeatures():
            z_amont = canal_feat.attribute('zmont')
            if z_amont is None or z_amont == "":
                z_amont = canal_feat.attribute('zamont')
            z_aval = canal_feat.attribute('zaval')
            if z_aval is None or z_aval == "":
                z_aval = canal_feat.attribute('zaval')
            if z_amont in (None, ""):
                z_amont = _ouvrage_z(canal_feat.attribute('idnini'))
            if z_aval in (None, ""):
                z_aval = _ouvrage_z(canal_feat.attribute('idnterm'))
            downstream_data.append({
                'diametre': canal_feat.attribute('diametre') or 300,
                'pente': canal_feat.attribute('pente') or 0.005,
                'z_amont': z_amont or 0,
                'z_aval': z_aval or 0,
                'longueur': canal_feat.geometry().length(),
                'type_reseau': canal_feat.attribute('type_reseau') or 'EU',
                'materiau': canal_feat.attribute('materiau') or 'PVC'
            })
        
        # Contexte historique (visites précédentes)
        historical_context = [
            {
                'node_id': v.get('node_id'),
                'polluted': v.get('polluted', False),
                'date': v.get('date', datetime.now())
            }
            for v in visits_history
            if v.get('date', datetime.now()) < visit_date
        ]
        
        # Ajout de l'échantillon
        training_sample = {
            'node_data': node_data,
            'upstream_data': upstream_data,
            'downstream_data': downstream_data,
            'historical_context': historical_context,
            'polluted': polluted,
            'date': visit_date.isoformat() if isinstance(visit_date, datetime) else visit_date
        }
        
        training_data.append(training_sample)
    
    canal_layer.removeSelection()
    
    return training_data


def generate_synthetic_training_data(nb_samples: int = 100) -> List[Dict]:
    """
    Génère des données synthétiques pour tester l'IA
    (À utiliser uniquement pour le développement/test)
    """
    import numpy as np
    
    training_data = []
    base_date = datetime.now() - timedelta(days=365)
    
    for i in range(nb_samples):
        # Simulation d'un nœud
        node_data = {
            'id': f'node_{i}',
            'x': random.uniform(0, 1000),
            'y': random.uniform(0, 1000),
            'elevation': random.uniform(50, 150)
        }
        
        # Simulation branches amont (1 à 4)
        nb_upstream = random.randint(1, 4)
        upstream_data = []
        
        for j in range(nb_upstream):
            upstream_data.append({
                'diametre': random.choice([200, 300, 400, 500, 600]),
                'pente': random.uniform(0.002, 0.02),
                'z_amont': node_data['elevation'] + random.uniform(0.5, 3),
                'z_aval': node_data['elevation'],
                'longueur': random.uniform(10, 100),
                'type_reseau': random.choice(['EU', 'EP', 'Mixte']),
                'materiau': random.choice(['PVC', 'Fonte', 'Béton'])
            })
        
        # Simulation branches aval (1 à 2)
        nb_downstream = random.randint(1, 2)
        downstream_data = []
        
        for j in range(nb_downstream):
            downstream_data.append({
                'diametre': random.choice([300, 400, 500, 600, 800]),
                'pente': random.uniform(0.002, 0.02),
                'z_amont': node_data['elevation'],
                'z_aval': node_data['elevation'] - random.uniform(0.5, 3),
                'longueur': random.uniform(10, 100),
                'type_reseau': random.choice(['EU', 'EP', 'Mixte']),
                'materiau': random.choice(['PVC', 'Fonte', 'Béton'])
            })
        
        # Simulation historique (0 à 5 visites précédentes)
        nb_history = random.randint(0, 5)
        historical_context = []
        
        for j in range(nb_history):
            historical_context.append({
                'node_id': f'node_{random.randint(0, i)}',
                'polluted': random.random() > 0.7,  # 30% de pollution
                'date': (base_date + timedelta(days=j*30)).isoformat(),
                'x': node_data['x'] + random.uniform(-50, 50),
                'y': node_data['y'] + random.uniform(-50, 50)
            })
        
        # Logique de pollution (règles simplifiées)
        # Plus de probabilité si:
        # - Réduction de diamètre importante
        # - Pente faible
        # - Historique de pollution dans le voisinage
        
        avg_diameter_up = np.mean([u['diametre'] for u in upstream_data])
        avg_diameter_down = np.mean([d['diametre'] for d in downstream_data])
        diameter_reduction = avg_diameter_up > avg_diameter_down * 1.2
        
        low_slope = np.mean([u['pente'] for u in upstream_data]) < 0.005
        
        nearby_polluted = len([h for h in historical_context if h['polluted']])
        
        # Calcul probabilité
        pollution_score = 0
        if diameter_reduction:
            pollution_score += 0.3
        if low_slope:
            pollution_score += 0.2
        pollution_score += nearby_polluted * 0.1
        
        polluted = random.random() < pollution_score
        
        training_sample = {
            'node_data': node_data,
            'upstream_data': upstream_data,
            'downstream_data': downstream_data,
            'historical_context': historical_context,
            'polluted': polluted,
            'date': (base_date + timedelta(days=i*3)).isoformat()
        }
        
        training_data.append(training_sample)
    
    return training_data


def save_training_data(data: List[Dict], output_path: str):
    """Sauvegarde les données d'entraînement"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Données d'entraînement sauvegardées: {output_path}")
    print(f"   Nombre d'échantillons: {len(data)}")
    print(f"   Pollués: {sum(1 for d in data if d['polluted'])}")


def load_training_data(input_path: str) -> List[Dict]:
    """Charge les données d'entraînement"""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📂 Données d'entraînement chargées: {input_path}")
    print(f"   Nombre d'échantillons: {len(data)}")
    
    return data


if __name__ == '__main__':
    # Exemple: générer des données synthétiques pour test
    print("🤖 Génération de données d'entraînement synthétiques...")
    
    synthetic_data = generate_synthetic_training_data(nb_samples=200)
    save_training_data(synthetic_data, 'training_data_synthetic.json')
    
    print("\n✅ Données générées avec succès !")
    print("   Vous pouvez maintenant les utiliser pour entraîner le modèle IA")
