# 🤖 Module IA - CheminerIndus

## Vue d'ensemble

Ce module ajoute des capacités d'**Intelligence Artificielle** au plugin CheminerIndus pour :

1. **Prédire les zones de pollution** avant même de faire les visites terrain
2. **Optimiser les parcours de visite** en priorisant les nœuds à risque
3. **Visualiser en 3D** les réseaux complexes avec détection automatique des zones problématiques

---

## 🎯 Fonctionnalités

### 1. Prédiction de pollution par Machine Learning

**Comment ça marche ?**

Le modèle IA apprend depuis votre historique de visites et identifie les **patterns** qui conduisent à la pollution :

- Réductions de diamètre
- Pentes faibles
- Proximité d'industriels
- Historique de pollution dans le voisinage
- Configuration topologique du réseau

**Features utilisées** (27 au total):
- Altitude du nœud
- Coordonnées X, Y
- Diamètres moyens amont/aval
- Pentes moyennes amont/aval
- Nombre de branches amont/aval
- Types de réseau (EU/EP/Mixte)
- Matériaux
- Ratio diamètres (détection réductions)
- Différence de pentes
- Complexité du nœud
- **Historique**: nombre de visites, taux de pollution, jours depuis dernière visite
- Pollution dans le voisinage
- Saisonnalité (mois, jour de semaine)

**Résultats** :
- Probabilité de pollution pour chaque nœud (0-100%)
- Niveau de risque (FAIBLE, MOYEN, ÉLEVÉ, CRITIQUE)
- Points chauds identifiés automatiquement

---

### 2. Optimisation des parcours

**Algorithme** :
- Score composite : `pollution_proba × 100 - (distance / distance_max) × 20`
- Favorise les nœuds à forte probabilité ET proches
- Génère un plan multi-jours optimisé

**Avantages** :
- ✅ Gain de temps terrain (visites ciblées)
- ✅ Détection précoce des pollutions
- ✅ Moins de kilomètres parcourus

---

### 3. Visualisation 3D des réseaux

**Détection automatique des zones complexes** :
- Seuil configurable (ex: 5 canaux dans un rayon de 50m)
- Score de complexité basé sur:
  - Nombre de canalisations
  - Différence d'altitude (z_range)
  - Variance des diamètres

**Visualisations disponibles** :
- 🌐 **Vue 3D interactive** (PyVista) - rotations, zoom, etc.
- 📊 **Profil en long** - vue de côté du réseau
- 🎨 **Coloration par critère** :
  - Diamètre
  - Pente
  - Élévation (Z)
  - Type de réseau (EU/EP)

**Export** :
- JSON des zones complexes avec statistiques
- Rapport d'évaluation des risques

---

## 📦 Installation des dépendances

```bash
# ML et analyse de données
pip install scikit-learn numpy

# Visualisation 3D (optionnel mais recommandé)
pip install pyvista matplotlib

# Si pyvista ne fonctionne pas, matplotlib seul suffit
pip install matplotlib
```

---

## 🚀 Guide d'utilisation

### Étape 1 : Préparer les données d'entraînement

#### Option A : Depuis votre historique réel

```python
from cheminer_indus.ai.training_data_generator import convert_visits_to_training_data, save_training_data

# Convertir vos visites
training_data = convert_visits_to_training_data(
    visits_history=your_visits_history,
    canal_layer=your_canal_layer,
    ouvr_layer=your_ouvr_layer
)

# Sauvegarder
save_training_data(training_data, 'my_training_data.json')
```

#### Option B : Données synthétiques pour tester

```bash
cd cheminer_indus/ai/
python training_data_generator.py
```

Cela génère `training_data_synthetic.json` avec 200 échantillons.

---

### Étape 2 : Entraîner le modèle

#### Via l'interface graphique (recommandé)

1. Ouvrir l'onglet **"IA"** dans CheminerIndus
2. Cliquer sur **"📂 Charger historique des visites"**
3. Sélectionner votre fichier JSON
4. Cliquer sur **"🚀 Entraîner le modèle"**
5. Attendre la fin (quelques secondes à quelques minutes selon le volume)
6. Sauvegarder le modèle avec **"💾 Sauvegarder modèle"**

#### Via code Python

```python
from cheminer_indus.ai.pollution_predictor import PollutionPredictor
from cheminer_indus.ai.training_data_generator import load_training_data

# Charger les données
training_data = load_training_data('my_training_data.json')

# Créer et entraîner
predictor = PollutionPredictor()
predictor.train(training_data, validation_split=0.2)

# Sauvegarder
predictor.save_model('pollution_model.pkl')
```

**Résultats attendus** :
```
📊 Entraînement : 160 échantillons
📊 Validation : 40 échantillons
📊 Distribution : 48 pollués / 160 total
🚀 Entraînement du modèle...

✅ Modèle entraîné avec succès !
📈 Précision : 87.50%

📊 Rapport détaillé :
              precision    recall  f1-score   support

 Non pollué       0.91      0.89      0.90        28
     Pollué       0.80      0.83      0.82        12

    accuracy                           0.88        40
```

---

### Étape 3 : Faire des prédictions

#### Rechercher les points chauds

```python
from cheminer_indus.ai.pollution_predictor import PollutionPredictor

# Charger le modèle
predictor = PollutionPredictor(model_path='pollution_model.pkl')

# Prédire
hotspots = predictor.get_pollution_hotspots(
    nodes=all_nodes,
    get_context_fn=your_context_function,
    threshold=0.6  # Seuil 60%
)

# Résultats
for hotspot in hotspots[:10]:  # Top 10
    print(f"Nœud {hotspot['node']['id']}: {hotspot['probability']*100:.1f}% - {hotspot['risk_level']}")
```

**Exemple de sortie** :
```
Nœud node_42: 92.3% - CRITIQUE
Nœud node_17: 87.1% - CRITIQUE
Nœud node_89: 78.5% - ÉLEVÉ
Nœud node_33: 74.2% - ÉLEVÉ
Nœud node_56: 68.9% - ÉLEVÉ
...
```

#### Optimiser un parcours

```python
from cheminer_indus.ai.pollution_predictor import VisitOptimizer

optimizer = VisitOptimizer(predictor)

# Ordre optimal de visite
visit_plan = optimizer.suggest_visit_order(
    start_node=my_start_node,
    candidate_nodes=nodes_to_visit,
    get_context_fn=your_context_function,
    max_distance=1000  # metres
)

# Plan multi-jours
multi_day_plan = optimizer.optimize_multi_day_plan(
    all_nodes=all_nodes,
    get_context_fn=your_context_function,
    days=5,
    nodes_per_day=10
)
```

---

### Étape 4 : Visualiser en 3D

#### Détecter les zones complexes

```python
from cheminer_indus.ai.network_visualizer_3d import NetworkVisualizer3D

viz = NetworkVisualizer3D(use_pyvista=True)

# Détecter
complex_zones = viz.detect_complex_zones(
    canal_features=your_canal_features,
    density_threshold=5,  # 5 canaux min
    radius=50  # dans un rayon de 50m
)

# Afficher
for zone in complex_zones:
    print(f"Zone @ ({zone['center'][0]:.0f}, {zone['center'][1]:.0f})")
    print(f"  - {zone['nb_canals']} canalisations")
    print(f"  - Diamètres: {zone['min_diameter']}-{zone['max_diameter']}mm")
    print(f"  - Dénivelé: {zone['z_range']:.2f}m")
    print(f"  - Score complexité: {zone['complexity_score']:.1f}")
    print(f"  - Risque: {zone.get('risk_assessment', 'N/A')}")
```

#### Visualiser le réseau

```python
# Vue 3D interactive
viz.visualize_network_3d(
    canal_features=your_canal_features,
    color_by='diameter',  # ou 'slope', 'elevation', 'type'
    show_labels=True,
    highlight_complex=True
)

# Profil en long
viz.create_profile_view(
    canal_features=your_canal_features,
    output_path='profile.png'  # Optionnel
)

# Export zones complexes
viz.export_complex_zones_report(
    complex_zones=complex_zones,
    output_path='zones_complexes.json'
)
```

---

## 📊 Format des données

### Format d'entrée (training data)

```json
{
  "node_data": {
    "id": "node_123",
    "x": 456789.5,
    "y": 6543210.2,
    "elevation": 125.3
  },
  "upstream_data": [
    {
      "diametre": 400,
      "pente": 0.008,
      "z_amont": 127.5,
      "z_aval": 125.3,
      "longueur": 45.2,
      "type_reseau": "EU",
      "materiau": "PVC"
    }
  ],
  "downstream_data": [...],
  "historical_context": [
    {
      "node_id": "node_100",
      "polluted": true,
      "date": "2025-10-15T14:30:00",
      "x": 456750.0,
      "y": 6543200.0
    }
  ],
  "polluted": true,
  "date": "2025-12-01T10:15:00"
}
```

### Format de sortie (prédictions)

```json
{
  "node": {...},
  "probability": 0.892,
  "risk_level": "CRITIQUE",
  "context": {...}
}
```

---

## 🎓 Améliorer les performances du modèle

### 1. Collectez plus de données

Plus vous avez de visites historiques, meilleur sera le modèle :
- **Minimum** : 100 visites
- **Recommandé** : 500+ visites
- **Idéal** : 1000+ visites

### 2. Équilibrez les classes

Si vous avez beaucoup plus de nœuds non-pollués que pollués :
- Utilisez un échantillonnage stratifié
- Augmentez le poids des cas pollués
- Générez des données synthétiques pour la classe minoritaire

### 3. Ajustez les hyperparamètres

```python
from sklearn.ensemble import GradientBoostingClassifier

predictor.model = GradientBoostingClassifier(
    n_estimators=200,  # Plus d'arbres
    learning_rate=0.05,  # Apprentissage plus lent mais plus précis
    max_depth=7,  # Arbres plus profonds
    min_samples_split=5,
    random_state=42
)
```

### 4. Ajoutez des features

Modifiez `extract_features()` pour ajouter :
- Présence d'industriels proches
- Âge des canalisations
- Matériau spécifique
- Historique de débordements
- Données météo

---

## 🐛 Dépannage

### Erreur : "scikit-learn not available"
```bash
pip install scikit-learn
```

### Erreur : "PyVista not available"
```bash
pip install pyvista
# OU si ça ne fonctionne pas
pip install matplotlib  # Fallback
```

### Le modèle prédit toujours la même classe
- **Cause** : Déséquilibre des classes
- **Solution** : Collectez plus de données ou utilisez l'échantillonnage

### La visualisation 3D ne s'affiche pas
- Vérifiez que PyVista est installé
- Utilisez `use_pyvista=False` pour fallback vers Matplotlib

---

## 📈 Améliorations futures

- [ ] Deep Learning (réseaux de neurones)
- [ ] Intégration données météo temps réel
- [ ] Prédiction de débit
- [ ] Détection d'anomalies non supervisée
- [ ] API REST pour prédictions en ligne
- [ ] Dashboard de monitoring temps réel

---

## 📞 Support

Pour toute question sur le module IA :
- **GitHub Issues** : https://github.com/papadembasene97-sudo/qgis_plugin/issues
- **Email** : papademba.sene97@gmail.com

---

## 📄 Licence

Ce module fait partie de CheminerIndus et est distribué sous la même licence que le plugin principal.

---

**Bon cheminement intelligent ! 🤖🚀**
