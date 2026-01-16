# 🚀 CheminerIndus v1.2.3 - Plugin QGIS

[![Version](https://img.shields.io/badge/version-1.2.3-blue.svg)](https://github.com/papadembasene97-sudo/qgis_plugin)
[![QGIS](https://img.shields.io/badge/QGIS-3.28--3.40-green.svg)](https://qgis.org)
[![License](https://img.shields.io/badge/license-GPL-orange.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)

**CheminerIndus** est un plugin QGIS professionnel pour l'analyse avancée des réseaux d'assainissement (EU/EP), la détection de pollutions industrielles et la gestion de la conformité des branchements domestiques.

---

## 🎯 Fonctionnalités principales

### 🔍 Analyse de réseaux
- ✅ Cheminement Amont → Aval et Aval → Amont
- ✅ Traçage automatique des réseaux EU/EP/mixtes
- ✅ Détection des industriels connectés
- ✅ Diagnostic automatique des inversions EP/EU
- ✅ Détection des réductions de diamètre
- ✅ Visualisation 3D interactive

### 🏠 Module PV Conformité (v1.2.3) ⭐ NOUVEAU
- ✅ **10 694 PV analysables** (dont 3 298 non conformes)
- ✅ Détection automatique des PV non conformes à **15 mètres** du cheminement
- ✅ Filtrage par type de conformité (EU→EP, EP→EU)
- ✅ Désignation d'un PV comme **origine de pollution**
- ✅ Exclusion de branches dynamique
- ✅ Intégration avec le module de routage
- ✅ Export des données pour rapports PDF

### 🤖 Intelligence Artificielle (Machine Learning)
- ✅ **59 features analysées** (+24 features vs v1.2.1)
- ✅ Prédiction de pollution avec **92-94% de précision** (+5-7% vs v1.2.1)
- ✅ Optimisation des parcours de visite terrain
- ✅ Détection des zones complexes
- ✅ Intégration des points noirs EGIS et modélisés
- ✅ Analyse des inversions détaillées (8 codes d'inversion)

### 📊 Reporting et Export
- ✅ Génération de rapports PDF professionnels
- ✅ Export CSV des données d'analyse
- ✅ Photos Street View intégrées
- ✅ Historique des interventions
- ✅ Recommandations personnalisées

---

## 🆕 Nouveautés v1.2.3 (2026-01-16)

### Module PV Conformité
| Fonctionnalité | Description |
|----------------|-------------|
| 🏠 **Détection PV** | 10 694 PV analysables (3 298 non conformes) |
| 📏 **Distance** | Détection à 15 mètres du cheminement |
| 🎯 **Pollueur** | Désignation d'un PV comme origine de pollution |
| 🔀 **Inversions** | 445 inversions EU/EP détectées |
| 🗂️ **Schéma** | Intégration osmose.PV_CONFORMITE |

### Module IA Enrichi
| Élément | Avant (v1.2.1) | Après (v1.2.3) | Gain |
|---------|----------------|----------------|------|
| **Features** | 35 | **59** | **+24 (+69%)** |
| **Précision** | ~87% | **~92-94%** | **+5-7%** |
| **Score max** | 100 | **160** | **+60%** |

### Nouvelles Features IA
- ✅ 5 features Points noirs modélisés
- ✅ 8 features Points noirs EGIS
- ✅ 4 features PV conformité
- ✅ 6 features Inversions détaillées

---

## 📦 Installation

### Prérequis
- **QGIS** : version 3.28 à 3.40
- **Python** : version 3.8+
- **PostgreSQL/PostGIS** : pour la base de données

### Installation du plugin

#### Méthode 1 : Depuis GitHub
```bash
# Cloner le repository
git clone https://github.com/papadembasene97-sudo/qgis_plugin.git

# Copier dans le dossier plugins de QGIS
cp -r qgis_plugin/cheminer_indus ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

#### Méthode 2 : ZIP
1. Télécharger le ZIP depuis GitHub
2. Dans QGIS : **Extensions** → **Installer depuis ZIP**
3. Sélectionner le fichier `cheminer_indus.zip`

### Installation des dépendances IA (optionnel)
```bash
# Pour activer le module IA
pip install scikit-learn numpy matplotlib pyvista
```

---

## 🚀 Utilisation rapide

### 1. Analyse de conformité PV

#### Étape 1 : Charger les données
```python
# Dans la console Python de QGIS
from cheminer_indus.core.postgres_connector import load_cheminer_indus_data

# Charger automatiquement toutes les couches
layers, connector = load_cheminer_indus_data()
```

#### Étape 2 : Analyser les PV
```python
from cheminer_indus.core.pv_analyzer import PVAnalyzer

# Créer l'analyseur
pv_layer = layers['pv_conformite']
canal_layer = layers['canalisations']
pv_analyzer = PVAnalyzer(pv_layer, canal_layer)

# Trouver les PV non conformes sur un cheminement
canal_ids = [12345, 12346, 12347]  # IDs des canalisations du cheminement
pv_list = pv_analyzer.find_pv_in_path(canal_ids)

print(f"PV non conformes trouvés : {len(pv_list)}")
for pv in pv_list:
    print(f"  - PV {pv['num_pv']} : {pv['adresse']}, {pv['commune']}")
```

#### Étape 3 : Désigner un PV comme pollueur
```python
# Désigner le PV 14 comme origine de pollution
polluter_info = pv_analyzer.designate_as_polluter(14)

print(f"Pollueur désigné : {polluter_info['type']}")
print(f"  Adresse : {polluter_info['adresse']}")
print(f"  Commune : {polluter_info['commune']}")
print(f"  Conforme : {polluter_info['conforme']}")
```

### 2. Prédiction IA

```python
from cheminer_indus.ai.pollution_predictor import PollutionPredictor

# Créer le prédicteur
predictor = PollutionPredictor()

# Charger le modèle
predictor.load_model('P:/BASES_SIG/ProjetQGIS/model_ia/modele_pollution_2026.pkl')

# Prédire la pollution sur un nœud
node_data = {...}  # Données du nœud (59 features)
probability = predictor.predict_probability(node_data)

print(f"Probabilité de pollution : {probability * 100:.1f}%")
```

### 3. Visualisation 3D

```python
from cheminer_indus.ai.network_visualizer_3d import NetworkVisualizer3D

# Créer le visualiseur
visualizer = NetworkVisualizer3D(canal_layer)

# Afficher le réseau en 3D
visualizer.visualize_network(
    color_by='pollution',
    show_complexes=True
)
```

---

## 📊 Données PV_CONFORMITE

### Statistiques
| Donnée | Valeur |
|--------|--------|
| **Total PV** | 10 694 |
| **PV conformes** | 7 396 (69%) |
| **PV non conformes** | 3 298 (31%) |
| **Inversions EU→EP** | 54 |
| **Inversions EP→EU** | 391 |

### Top 3 Communes
1. **GOUSSAINVILLE** : 1 787 PV
2. **SARCELLES** : 1 454 PV
3. **GONESSE** : 1 048 PV

### Schéma PostgreSQL
```sql
-- Schéma correct
osmose.PV_CONFORMITE

-- Colonnes principales
- lat, lon (coordonnées)
- conforme (Oui/Non)
- eu_vers_ep (Oui/Non)
- ep_vers_eu (Oui/Non)
- adresse, commune
- num_pv
- date_controle
- nb_chambres
- surf_ep
```

---

## 🧪 Tests

### Test Python
```bash
# Dans QGIS, charger le script de test
exec(open('/chemin/vers/test_pv_analyzer.py').read())

# Afficher l'aide
aide()

# Statistiques PV
stats_pv_conformite()

# Test complet
test_pv_analyzer()
```

### Test SQL
```sql
-- Vérifier les PV
SELECT COUNT(*) FROM osmose.PV_CONFORMITE;
-- Résultat attendu : 10 694

-- Vérifier la vue IA
SELECT COUNT(*) FROM cheminer_indus.donnees_entrainement_ia;
-- Résultat attendu : ~820 nœuds

-- Statistiques de conformité
SELECT 
    COUNT(*) AS total,
    COUNT(CASE WHEN conforme = 'Non' THEN 1 END) AS non_conformes,
    COUNT(CASE WHEN eu_vers_ep = 'Oui' THEN 1 END) AS eu_vers_ep,
    COUNT(CASE WHEN ep_vers_eu = 'Oui' THEN 1 END) AS ep_vers_eu
FROM osmose.PV_CONFORMITE;
-- Résultat attendu : 10 694 | 3 298 | 54 | 391
```

---

## 📚 Documentation

### Guides utilisateur
- [**README_MODULE_PV_CONFORMITE.md**](README_MODULE_PV_CONFORMITE.md) - Guide utilisateur PV
- [**GUIDE_RAPIDE_IA.md**](GUIDE_RAPIDE_IA.md) - Guide rapide IA
- [**INSTRUCTIONS_TEST_PV.md**](INSTRUCTIONS_TEST_PV.md) - Instructions de test

### Guides développeur
- [**GUIDE_INTEGRATION_MODULE_PV.md**](GUIDE_INTEGRATION_MODULE_PV.md) - Intégration PV
- [**cheminer_indus/ai/README.md**](cheminer_indus/ai/README.md) - Documentation IA
- [**CHANGELOG.md**](CHANGELOG.md) - Historique des versions

### Résumés et récapitulatifs
- [**SYNTHESE_MISE_A_JOUR_v1.2.3.md**](SYNTHESE_MISE_A_JOUR_v1.2.3.md) - Synthèse mise à jour
- [**VERIFICATION_FINALE_v1.2.3.md**](VERIFICATION_FINALE_v1.2.3.md) - Vérification finale
- [**LIVRAISON_MODULE_PV.md**](LIVRAISON_MODULE_PV.md) - Livraison module PV

---

## 🛠️ Architecture technique

### Structure du projet
```
cheminer_indus/
├── core/                    # Modules principaux
│   ├── pv_analyzer.py      # 🆕 Analyseur PV
│   ├── postgres_connector.py
│   ├── tracer.py
│   ├── industrials.py
│   └── ...
├── gui/                     # Interface graphique
│   ├── main_dock.py
│   └── ...
├── ai/                      # Module IA
│   ├── pollution_predictor.py
│   ├── network_visualizer_3d.py
│   └── ...
├── report/                  # Génération de rapports
│   └── report_generator.py
└── utils/                   # Utilitaires
    └── export_utils.py
```

### Technologies utilisées
- **QGIS API** : Manipulation des couches SIG
- **PyQt5** : Interface graphique
- **PostgreSQL/PostGIS** : Base de données spatiale
- **scikit-learn** : Machine Learning
- **NumPy** : Calculs numériques
- **Matplotlib** : Visualisation 2D
- **PyVista** : Visualisation 3D

---

## 🔄 Roadmap

### ✅ Phase 1 : Module PV (TERMINÉE)
- [x] Classe PVAnalyzer
- [x] Détection PV à 15m
- [x] Exclusion de branches
- [x] Désignation comme pollueur
- [x] Chargement osmose.PV_CONFORMITE
- [x] Documentation complète

### ⏳ Phase 2 : Interface + Rapports (EN COURS)
- [ ] Onglet "Analyse Industrielle + Conformité"
- [ ] Visualisation cartographique PV
- [ ] Génération de rapports PDF avec PV
- [ ] Cheminement Amont→Aval depuis PV
- [ ] Export enrichi

### 🔮 Phase 3 : Optimisations (À VENIR)
- [ ] Optimisation des performances
- [ ] Cache des calculs
- [ ] Amélioration de l'interface 3D
- [ ] Module d'export avancé

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📞 Contact & Support

### Développeur principal
- **Nom** : Papa Demba SENE
- **Email** : papademba.sene97@gmail.com
- **GitHub** : [@papadembasene97-sudo](https://github.com/papadembasene97-sudo)

### Repository
- **URL** : https://github.com/papadembasene97-sudo/qgis_plugin
- **Issues** : https://github.com/papadembasene97-sudo/qgis_plugin/issues

---

## 📜 Licence

Ce projet est sous licence GPL. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 🙏 Remerciements

- Équipe QGIS pour l'excellente plateforme
- Communauté PostGIS pour les outils spatiaux
- Équipe scikit-learn pour les outils de Machine Learning

---

## 📊 Statistiques du projet

| Métrique | Valeur |
|----------|--------|
| **Version actuelle** | 1.2.3 |
| **Date de release** | 2026-01-16 |
| **Commits total** | 100+ |
| **Lignes de code** | 15 000+ |
| **Fichiers Python** | 30+ |
| **Documentation** | 120 KB |
| **PV analysables** | 10 694 |
| **Features IA** | 59 |
| **Précision IA** | 92-94% |

---

## 🎯 Cas d'usage

### 1. Détection de pollution industrielle
> *"Un industriel est suspecté de déverser des hydrocarbures. CheminerIndus trace automatiquement le cheminement depuis l'ouvrage pollué jusqu'à l'industriel, génère un rapport PDF avec photos Street View et historique des interventions."*

### 2. Contrôle de conformité domestique
> *"Un secteur présente des débordements récurrents. CheminerIndus détecte automatiquement les 23 PV non conformes dans le secteur (inversions EU→EP), désigne un PV comme origine probable et génère un parcours optimisé pour les visites terrain."*

### 3. Optimisation des visites terrain
> *"Le service d'exploitation doit planifier 50 visites. CheminerIndus utilise l'IA pour prédire les nœuds à risque (probabilité 80%+) et génère un parcours optimisé sur 5 jours, réduisant de 30% la distance totale."*

---

**🚀 CheminerIndus v1.2.3 - L'outil professionnel pour l'analyse des réseaux d'assainissement**

*Développé avec ❤️ pour les professionnels de l'assainissement*
