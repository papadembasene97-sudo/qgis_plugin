# 🏠 Module PV de Conformité - TRACK-EAU-POLL v1.2.3

## 📋 Vue d'ensemble

Le **module PV de Conformité** permet de :
- ✅ Détecter automatiquement les PV (Points de Visite) non conformes le long d'un cheminement
- ✅ Désigner un PV comme origine de pollution (comme pour les industriels)
- ✅ Calculer le parcours Amont → Aval depuis un PV
- ✅ Générer un rapport PDF complet avec toutes les informations
- ✅ Gérer l'exclusion dynamique des PV lors de la désélection de branches

---

## 🎯 Qu'est-ce qu'un PV de conformité ?

Un **PV (Point de Visite)** est un contrôle réalisé sur une **maison** ou un **établissement industriel** pour vérifier que :
- ✅ Les **eaux usées (EU)** vont bien dans le **réseau EU**
- ✅ Les **eaux pluviales (EP)** vont bien dans le **réseau EP**

### Champs importants de la table `exploit.PV_CONFORMITE`

| Champ | Description | Valeurs possibles |
|-------|-------------|-------------------|
| `conforme` | Conformité générale | `Oui` / `Non` |
| `eu_vers_ep` | EU → EP (inversion) | `Oui` / `Non` |
| `ep_vers_eu` | EP → EU (inversion) | `Oui` / `Non` |
| `num_pv` | Numéro du PV | Ex: `GH.15.11.012` |
| `date_pv` | Date du contrôle | Ex: `2015/11/18` |
| `adresse` | Adresse du PV | Ex: `9 allée des Tournelles` |
| `commune` | Commune | Ex: `LE THILLAY` |
| `lien_osmose` | Lien vers OSMOSE | URL |

---

## 🔍 Détection des PV lors du cheminement

### Distance de recherche : **15 mètres**

Lors du calcul d'un cheminement Aval → Amont à partir d'un ouvrage pollué, le plugin :

1. **Trace toutes les canalisations** en amont
2. **Crée un buffer de 15 mètres** autour de chaque canalisation
3. **Cherche les PV non conformes** dans ces buffers (`conforme = 'Non'`)
4. **Rattache chaque PV** à la canalisation la plus proche
5. **Affiche la liste** des PV trouvés avec leurs détails

### Exemple de sortie console

```
🔍 Recherche de PV non conformes à 15.0m du cheminement...
  ✓ PV trouvé : 9 allée des Tournelles, LE THILLAY (distance: 12.3m)
  ✓ PV trouvé : 1 Rue Berthier, BOUFFEMONT (distance: 8.7m)
  ✓ PV trouvé : 5 allée Paul Cézanne, SAINT-BRICE (distance: 14.1m)

✅ 23 PV non conformes trouvés au total
```

---

## 🎨 Interface utilisateur

### Onglet "Analyse Industrielle + Conformité"

```
┌──────────────────────────────────────────────────────────────┐
│  🏭 ANALYSE INDUSTRIELLE + CONFORMITÉ                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 RÉSULTATS :                                              │
│  ├─ Canalisations analysées : 142                           │
│  ├─ Industriels connectés   : 8                             │
│  └─ PV non conformes        : 23                            │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  🏭 INDUSTRIELS CONNECTÉS :                                  │
│  │ ✅ [Usine X] - Risque graisse                            │
│  │    [🎯 Désigner comme pollueur]                         │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ⚠️ PV NON CONFORMES :                                      │
│  │ ⚠️ [9 allée des Tournelles, LE THILLAY]                 │
│  │    EU→EP: Non | EP→EU: Oui ⚠️ (INVERSION)              │
│  │    [🎯 Désigner comme pollueur] ← NOUVEAU               │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  🎯 POLLUEUR DÉSIGNÉ :                                      │
│  │ Type : [PV non conforme]                                 │
│  │ Adresse : 9 allée des Tournelles, LE THILLAY           │
│  │ Problème : EP → EU (inversion)                          │
│  │                                                          │
│  │ [▶ Calculer le cheminement Amont → Aval]               │
│  │ [📥 Générer le rapport d'enquête]                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🗑️ Exclusion de branches

### Comportement identique aux industriels

Quand l'utilisateur **exclut une branche** du cheminement :

1. **Les industriels de cette branche** sont retirés de la liste ✅
2. **Les PV de cette branche** sont AUSSI retirés de la liste 🆕

### Exemple

**Avant exclusion :**
```
Canalisations : 142
Industriels   : 8
PV non conformes : 23
```

**Après exclusion de la branche NOE_137 :**
```
Canalisations : 98 (−44)
Industriels   : 5 (−3)     ← Usine Z exclue
PV non conformes : 15 (−8)  ← 8 PV de la branche exclus
```

---

## 📄 Rapport PDF enrichi

### Sections du rapport pour un PV pollueur

#### 1️⃣ **Origine de la pollution**
```
Type : PV non conforme
Adresse : 9 allée des Tournelles
Commune : LE THILLAY
N° PV : GH.15.11.012
Date contrôle : 18/11/2015
```

#### 2️⃣ **Non-conformités détectées**
```
• Conformité générale : NON ❌
• EU vers EP : NON
• EP vers EU : OUI ⚠️ (INVERSION)
• Surface EP déclarée : 0 m²
• Nombre de chambres : Non renseigné
```

#### 3️⃣ **Lien OSMOSE**
```
https://si.siah-croult.org/gestion-pv/pv/?action=voir&id=14
```

#### 4️⃣ **Parcours (Amont → Aval)**
```
Depuis le PV vers l'ouvrage pollué
Distance totale : 0.8 km
Nombre de tronçons : 11
Ouvrages traversés : 6
```

#### 5️⃣ **Photos Street View**
Photos de la maison/adresse du PV

#### 6️⃣ **Autres PV non conformes sur le parcours** 🆕
```
• 1 Rue Berthier, BOUFFEMONT
  ⚠️ Inversion EP → EU détectée
• 5 allée Paul Cézanne, SAINT-BRICE
Total : 2 PV non conformes
```

#### 7️⃣ **Industriels sur le parcours** 🆕
```
• Usine X - Risque graisse
• Entreprise Y - ICPE
Total : 2 industriels
```

#### 8️⃣ **Recommandations** 🆕
```
1. Effectuer une visite sur place
2. Vérifier le raccordement EU/EP avec caméra
3. Faire une mise en conformité si besoin
4. Contrôler les autres PV proches (< 100m)
5. Planifier un nouveau contrôle dans 6 mois
```

---

## 📊 Export CSV

### Format du CSV avec PV pollueur

```csv
type_origine,id_origine,adresse_origine,commune_origine,type_element,id_element,nom_element,adresse_element,commune_element,conforme,eu_vers_ep,ep_vers_eu,distance_km
PV,14,9 allée des Tournelles,LE THILLAY,PV,14,Particulier,9 allée des Tournelles,LE THILLAY,Non,Non,Oui,0.0
PV,14,9 allée des Tournelles,LE THILLAY,Canalisation,idcanal_12345,,,,,,,0.15
PV,14,9 allée des Tournelles,LE THILLAY,Ouvrage,NOE_042,,,,,,,0.15
PV,14,9 allée des Tournelles,LE THILLAY,PV,1575,Particulier,1 Rue Berthier,BOUFFEMONT,Non,Non,Non,0.32
PV,14,9 allée des Tournelles,LE THILLAY,Industriel,42,Usine X,12 Rue...,SARCELLES,,,,,0.45
```

---

## 🔧 Architecture technique

### Fichiers créés/modifiés

```
cheminer_indus/
├── core/
│   ├── pv_analyzer.py          # 🆕 Module d'analyse des PV
│   └── tracer.py               # Mise à jour pour intégration PV
├── gui/
│   └── industrial_tab.py       # 🆕 Interface d'analyse industrielle
└── report/
    └── report_generator.py     # 🆕 Génération rapports PV
```

### Classe `PVAnalyzer`

```python
class PVAnalyzer:
    """Analyse les PV de conformité le long d'un cheminement"""
    
    # Méthodes principales
    def find_pv_near_path(canalisations, network_type)
        # Trouve les PV à 15m du cheminement
    
    def update_after_exclusion(canalisations_exclues)
        # Retire les PV des branches exclues
    
    def designate_as_polluter(pv_id)
        # Désigne un PV comme origine de pollution
    
    def get_polluter_info()
        # Retourne les infos complètes du PV pollueur
```

---

## 📈 Statistiques TRACK-EAU-POLL v1.2.3

### Données PV_CONFORMITE

| Indicateur | Valeur |
|-----------|--------|
| **Total PV** | 10 694 |
| **PV conformes** | 7 396 (69.2%) |
| **PV non conformes** | 3 298 (30.8%) |
| **Inversions EU → EP** | 54 (0.5%) |
| **Inversions EP → EU** | 391 (3.7%) |

### Communes les plus touchées

| Commune | PV non conformes |
|---------|-----------------|
| GOUSSAINVILLE | 538 |
| SARCELLES | 437 |
| GONESSE | 315 |
| LOUVRES | 311 |
| VILLIERS-LE-BEL | 208 |

---

## 🚀 Workflow utilisateur complet

### Scénario : Enquête de pollution depuis un PV

1. **Ouvrage pollué détecté** (ex: `Usr.1348`)
2. **Lancer le cheminement Aval → Amont**
3. **Résultats :**
   - 142 canalisations
   - 8 industriels
   - 23 PV non conformes
4. **Analyser la liste des PV**
5. **Cliquer sur "9 allée des Tournelles" → Désigner comme pollueur**
6. **Calculer le cheminement Amont → Aval** depuis ce PV
7. **Générer le rapport PDF** avec :
   - Parcours du PV vers l'ouvrage
   - Photos Street View du PV
   - Non-conformités détectées
   - Autres PV et industriels sur le parcours
   - Recommandations de mise en conformité
8. **Exporter en CSV** pour analyse externe

---

## ✅ Comparaison des fonctionnalités

| Fonctionnalité | Industriel | PV non conforme |
|---------------|-----------|----------------|
| **Détection lors du cheminement** | ✅ | ✅ 🆕 |
| **Affichage dans la liste** | ✅ | ✅ 🆕 |
| **Exclusion de branches** | ✅ | ✅ 🆕 |
| **Désignation comme pollueur** | ✅ | ✅ 🆕 |
| **Cheminement Amont → Aval** | ✅ | ✅ 🆕 |
| **Rapport PDF** | ✅ | ✅ 🆕 |
| **Photos Street View** | ✅ | ✅ 🆕 |
| **Export CSV** | ✅ | ✅ 🆕 |
| **Visualisation 3D** | ✅ | ✅ 🆕 |

---

## 🎯 Cas d'usage

### 1. Détection d'inversions EP → EU

**Problème :**  
Un ouvrage EU est pollué de manière récurrente après la pluie.

**Solution avec le module PV :**
1. Cheminement amont depuis l'ouvrage
2. Liste des PV avec `ep_vers_eu = 'Oui'`
3. Désigner le PV comme pollueur
4. Rapport PDF avec preuves (photos + historique)
5. Intervention ciblée de mise en conformité

### 2. Enquête de pollution d'origine domestique

**Problème :**  
Pollution détectée, mais aucun industriel en amont.

**Solution avec le module PV :**
1. Cheminement amont
2. 23 PV non conformes détectés
3. Analyse des inversions et non-conformités
4. Désignation du PV le plus proche
5. Rapport avec recommandations de contrôle

---

## 📚 Documentation API

### `PVAnalyzer.find_pv_near_path(canalisations, network_type)`

**Paramètres :**
- `canalisations` : Liste des features de canalisations
- `network_type` : Type de réseau (`'EU'` ou `'EP'`)

**Retour :**
- Liste des PV non conformes trouvés

**Exemple :**
```python
pv_analyzer = PVAnalyzer(pv_layer)
pv_list = pv_analyzer.find_pv_near_path(canalisations, 'EU')
print(f"{len(pv_list)} PV non conformes trouvés")
```

### `PVAnalyzer.designate_as_polluter(pv_id)`

**Paramètres :**
- `pv_id` : ID du PV à désigner

**Retour :**
- `True` si succès, `False` sinon

**Exemple :**
```python
success = pv_analyzer.designate_as_polluter(14)
if success:
    info = pv_analyzer.get_polluter_info()
    print(f"PV pollueur : {info['adresse']}, {info['commune']}")
```

---

## 🐛 Débogage

### Pas de PV détectés ?

**Vérifications :**
1. ✅ Couche `exploit.PV_CONFORMITE` chargée dans QGIS
2. ✅ Champ `conforme` présent avec valeurs `Oui`/`Non`
3. ✅ Géométrie valide (type Point)
4. ✅ Buffer de 15m autour des canalisations

**Console Python (QGIS) :**
```python
pv_layer = QgsProject.instance().mapLayersByName('PV_CONFORMITE')[0]
print(f"PV totaux : {pv_layer.featureCount()}")

# Compter les non conformes
non_conformes = [f for f in pv_layer.getFeatures() if f['conforme'] == 'Non']
print(f"PV non conformes : {len(non_conformes)}")
```

---

## 📞 Support

**Email :** papademba.sene97@gmail.com  
**GitHub :** https://github.com/papadembasene97-sudo/qgis_plugin  
**Documentation :** README_MODULE_PV_CONFORMITE.md  

---

## 🔄 Historique des versions

### v1.2.3 (2026-01-16) 🆕

- ✅ Ajout du module `PVAnalyzer`
- ✅ Détection des PV non conformes à 15m
- ✅ Désignation d'un PV comme pollueur
- ✅ Rapport PDF enrichi avec sections PV
- ✅ Gestion de l'exclusion de branches pour les PV
- ✅ Export CSV avec type d'origine (Industriel/PV)

### v1.2.2 (2026-01-15)

- ✅ Vue matérialisée enrichie (55 features)
- ✅ Gestion des 8 codes d'inversion
- ✅ Connecteur PostgreSQL automatique

---

**TRACK-EAU-POLL v1.2.3** - Module PV de Conformité  
*Détection intelligente des non-conformités domestiques*
