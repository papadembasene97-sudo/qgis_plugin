"""
Exemple complet d'utilisation du module IA de CheminerIndus
"""

import sys
import os

# Ajout du chemin du module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.pollution_predictor import PollutionPredictor, VisitOptimizer
from ai.network_visualizer_3d import NetworkVisualizer3D
from ai.training_data_generator import generate_synthetic_training_data, save_training_data


def example_1_train_model():
    """Exemple 1: Entraîner un modèle depuis zéro"""
    print("=" * 80)
    print("EXEMPLE 1: Entraînement d'un modèle IA")
    print("=" * 80)
    
    # Génération de données synthétiques pour la démo
    print("\n📊 Génération de 300 échantillons d'entraînement...")
    training_data = generate_synthetic_training_data(nb_samples=300)
    
    # Sauvegarde (optionnel)
    save_training_data(training_data, 'demo_training_data.json')
    
    # Création et entraînement du modèle
    print("\n🤖 Création du prédicteur...")
    predictor = PollutionPredictor()
    
    print("\n🚀 Entraînement du modèle...")
    predictor.train(training_data, validation_split=0.2)
    
    # Sauvegarde du modèle
    model_path = 'pollution_model_demo.pkl'
    predictor.save_model(model_path)
    
    print(f"\n✅ Modèle sauvegardé: {model_path}")
    print("\nVous pouvez maintenant utiliser ce modèle pour faire des prédictions !")
    
    return predictor


def example_2_make_predictions(predictor):
    """Exemple 2: Faire des prédictions avec le modèle"""
    print("\n" + "=" * 80)
    print("EXEMPLE 2: Prédictions de pollution")
    print("=" * 80)
    
    # Simulation d'un nouveau nœud à analyser
    node_data = {
        'id': 'test_node_1',
        'x': 500.0,
        'y': 500.0,
        'elevation': 100.0
    }
    
    upstream_data = [
        {
            'diametre': 400,
        '_pente': 0.004,  # Pente faible !
        'zmont': 102.0,
        'zaval': 100.0,
            'longueur': 50.0,
            'type_reseau': 'EU',
            'materiau': 'PVC'
        },
        {
            'diametre': 300,
        '_pente': 0.005,
        'zmont': 101.5,
        'zaval': 100.0,
            'longueur': 30.0,
            'type_reseau': 'EU',
            'materiau': 'Béton'
        }
    ]
    
    downstream_data = [
        {
            'diametre': 600,  # Augmentation de diamètre
        '_pente': 0.008,
        'zmont': 100.0,
        'zaval': 96.0,
            'longueur': 50.0,
            'type_reseau': 'EU',
            'materiau': 'Béton'
        }
    ]
    
    historical_visits = [
        {
            'node_id': 'nearby_node_1',
            'polluted': True,  # Pollution dans le voisinage !
            'date': '2025-11-15T10:00:00',
            'x': 480.0,
            'y': 490.0
        },
        {
            'node_id': 'nearby_node_2',
            'polluted': True,
            'date': '2025-11-20T14:30:00',
            'x': 510.0,
            'y': 505.0
        }
    ]
    
    # Prédiction
    print("\n🔮 Analyse du nœud test_node_1...")
    print(f"   - Altitude: {node_data['elevation']}m")
    print(f"   - {len(upstream_data)} branches amont")
    print(f"   - {len(downstream_data)} branche(s) aval")
    print(f"   - {len(historical_visits)} visites dans le voisinage")
    
    probability = predictor.predict_pollution_probability(
        node_data=node_data,
        upstream_data=upstream_data,
        downstream_data=downstream_data,
        historical_visits=historical_visits
    )
    
    risk_level = predictor._get_risk_level(probability)
    
    print(f"\n📊 Résultat:")
    print(f"   - Probabilité de pollution: {probability*100:.1f}%")
    print(f"   - Niveau de risque: {risk_level}")
    
    if risk_level in ['CRITIQUE', 'ÉLEVÉ']:
        print(f"   ⚠️  Visite recommandée en priorité !")
    elif risk_level == 'MOYEN':
        print(f"   ⚠️  Surveiller ce nœud")
    else:
        print(f"   ✅ Risque faible")
    
    return probability, risk_level


def example_3_optimize_route(predictor):
    """Exemple 3: Optimiser un parcours de visite"""
    print("\n" + "=" * 80)
    print("EXEMPLE 3: Optimisation de parcours")
    print("=" * 80)
    
    # Point de départ
    start_node = {
        'id': 'depot',
        'x': 0.0,
        'y': 0.0
    }
    
    # Génération de nœuds candidats à visiter
    print("\n📍 Génération de 15 nœuds candidats...")
    candidate_nodes = []
    
    for i in range(15):
        import random
        candidate_nodes.append({
            'id': f'candidate_{i}',
            'x': random.uniform(50, 950),
            'y': random.uniform(50, 950),
            'elevation': random.uniform(80, 120)
        })
    
    # Fonction contexte simplifiée pour la démo
    def get_context_fn(node):
        import random
        return {
            'upstream': [{
                'diametre': random.choice([300, 400, 500]),
                '_pente': random.uniform(0.003, 0.015),
                'zmont': node['elevation'] + random.uniform(0.5, 2),
                'zaval': node['elevation'],
                'longueur': random.uniform(20, 80),
                'type_reseau': 'EU',
                'materiau': 'PVC'
            } for _ in range(random.randint(1, 3))],
            'downstream': [{
                'diametre': random.choice([400, 500, 600]),
                '_pente': random.uniform(0.005, 0.02),
                'zmont': node['elevation'],
                'zaval': node['elevation'] - random.uniform(0.5, 3),
                'longueur': random.uniform(30, 100),
                'type_reseau': 'EU',
                'materiau': 'Béton'
            }],
            'history': []
        }
    
    # Optimisation
    print("\n🗺️  Optimisation du parcours...")
    optimizer = VisitOptimizer(predictor)
    
    optimized_route = optimizer.suggest_visit_order(
        start_node=start_node,
        candidate_nodes=candidate_nodes,
        get_context_fn=get_context_fn,
        max_distance=1500
    )
    
    # Affichage des résultats
    print(f"\n📋 Parcours optimisé (Top 10):")
    print(f"{'Rang':<6} {'Nœud':<15} {'Proba':<10} {'Distance':<10} {'Score':<10} {'Risque'}")
    print("-" * 80)
    
    for i, node_info in enumerate(optimized_route[:10], 1):
        print(f"{i:<6} {node_info['node']['id']:<15} "
              f"{node_info['pollution_probability']*100:>6.1f}% "
              f"{node_info['distance']:>8.0f}m "
              f"{node_info['score']:>8.1f} "
              f"{node_info['risk_level']}")
    
    return optimized_route


def example_4_visualize_3d():
    """Exemple 4: Visualisation 3D"""
    print("\n" + "=" * 80)
    print("EXEMPLE 4: Visualisation 3D des réseaux")
    print("=" * 80)
    
    # Génération d'un réseau synthétique
    import random
    import numpy as np
    
    print("\n🌐 Génération d'un réseau synthétique (50 canalisations)...")
    
    canal_features = []
    
    # Génération de plusieurs zones avec densités variables
    zones = [
        {'center_x': 250, 'center_y': 250, 'nb_canals': 20, 'z_base': 100},
        {'center_x': 750, 'center_y': 250, 'nb_canals': 15, 'z_base': 90},
        {'center_x': 500, 'center_y': 700, 'nb_canals': 15, 'z_base': 85}
    ]
    
    canal_id = 0
    for zone in zones:
        for _ in range(zone['nb_canals']):
            x1 = zone['center_x'] + random.uniform(-50, 50)
            y1 = zone['center_y'] + random.uniform(-50, 50)
            
            angle = random.uniform(0, 2 * np.pi)
            length = random.uniform(20, 80)
            x2 = x1 + length * np.cos(angle)
            y2 = y1 + length * np.sin(angle)
            
            z1 = zone['z_base'] + random.uniform(-2, 2)
            pente = random.uniform(0.003, 0.015)
            z2 = z1 - length * pente
            
            canal_features.append({
                'id': canal_id,
                'geometry': {'coordinates': [[x1, y1], [x2, y2]]},
                'diametre': random.choice([200, 300, 400, 500, 600]),
                '_pente': pente,
                'zmont': z1,
                'zaval': z2,
                'longueur': length,
                'type_reseau': random.choice(['EU', 'EP', 'Mixte']),
                'materiau': random.choice(['PVC', 'Fonte', 'Béton'])
            })
            canal_id += 1
    
    # Détection des zones complexes
    print("\n🔍 Détection des zones complexes...")
    viz = NetworkVisualizer3D(use_pyvista=False)  # Matplotlib pour compatibilité
    
    complex_zones = viz.detect_complex_zones(
        canal_features,
        density_threshold=5,
        radius=60
    )
    
    # Affichage des résultats
    print(f"\n📊 Résultat: {len(complex_zones)} zone(s) complexe(s) détectée(s)")
    
    for i, zone in enumerate(complex_zones, 1):
        print(f"\n🔴 Zone {i}:")
        print(f"   - Centre: ({zone['center'][0]:.0f}, {zone['center'][1]:.0f})")
        print(f"   - Nombre de canaux: {zone['nb_canals']}")
        print(f"   - Diamètres: {zone['min_diameter']:.0f} - {zone['max_diameter']:.0f} mm")
        print(f"   - Dénivelé: {zone['z_range']:.2f} m")
        print(f"   - Niveaux verticaux: {zone['nb_vertical_levels']}")
        print(f"   - Score de complexité: {zone['complexity_score']:.1f}")
        print(f"   - Évaluation: {viz._assess_zone_risk(zone)}")
    
    # Génération de la visualisation
    print("\n🎨 Génération de la visualisation 3D...")
    print("   (Une fenêtre va s'ouvrir - fermez-la pour continuer)")
    
    try:
        viz.visualize_network_3d(
            canal_features,
            color_by='diameter',
            show_labels=False,
            highlight_complex=True
        )
    except Exception as e:
        print(f"⚠️  Erreur lors de la visualisation: {e}")
        print("   (Normal si les bibliothèques 3D ne sont pas installées)")
    
    # Profil en long
    print("\n📊 Génération du profil en long...")
    try:
        viz.create_profile_view(
            canal_features,
            output_path='profile_demo.png'
        )
    except Exception as e:
        print(f"⚠️  Erreur lors de la génération du profil: {e}")
    
    # Export zones complexes
    if complex_zones:
        output_path = 'complex_zones_demo.json'
        viz.export_complex_zones_report(complex_zones, output_path)
        print(f"\n💾 Rapport exporté: {output_path}")
    
    return complex_zones


def main():
    """Programme principal - exécute tous les exemples"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "MODULE IA - CHEMINERINDUS" + " " * 34 + "║")
    print("║" + " " * 25 + "EXEMPLES D'UTILISATION" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        # Exemple 1: Entraînement
        predictor = example_1_train_model()
        
        # Exemple 2: Prédictions
        example_2_make_predictions(predictor)
        
        # Exemple 3: Optimisation
        example_3_optimize_route(predictor)
        
        # Exemple 4: Visualisation 3D
        example_4_visualize_3d()
        
        print("\n" + "=" * 80)
        print("✅ TOUS LES EXEMPLES TERMINÉS AVEC SUCCÈS")
        print("=" * 80)
        print("\n📚 Pour plus d'informations, consultez le fichier README.md")
        print("🐛 Pour signaler un bug: https://github.com/papadembasene97-sudo/qgis_plugin/issues")
        print("\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
