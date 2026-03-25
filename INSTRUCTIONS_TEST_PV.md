# 🧪 INSTRUCTIONS DE TEST - Module PV Conformité

## 🎯 Comment tester le module PV maintenant

### Pré-requis

✅ QGIS 3.x installé  
✅ Plugin TRACK-EAU-POLL chargé  
✅ Connexion PostgreSQL configurée dans QGIS  
✅ Base de données avec la table `exploit.PV_CONFORMITE`  

---

## 📋 Test 1 : Chargement de la couche PV_CONFORMITE

### Méthode automatique (recommandée)

```python
# Dans la console Python de QGIS
from cheminer_indus.core.postgres_connector import PostgreSQLConnector

# Initialiser le connecteur
connector = PostgreSQLConnector()

# Auto-détection de la connexion
connector.auto_detect_connection()

# Charger toutes les couches
layers = connector.load_cheminer_indus_layers()

# Vérifier que PV_CONFORMITE est chargée
if 'pv_conformite' in layers:
    print(f"✅ PV Conformité chargée : {layers['pv_conformite'].featureCount()} PV")
else:
    print("❌ PV Conformité non chargée")
```

### Méthode manuelle

```
1. QGIS → Couche → Ajouter une couche → Ajouter une couche PostGIS
2. Sélectionner votre connexion PostgreSQL
3. Schema : exploit
4. Table : PV_CONFORMITE
5. Utiliser l'option "Créer une géométrie depuis lat/lon"
6. Ajouter
```

**Résultat attendu :** Couche "PV Conformité" avec 10 694 points

---

## 📋 Test 2 : Statistiques sur les PV

```python
# Charger le script de test
exec(open('/home/user/webapp/test_pv_analyzer.py').read())

# Afficher les statistiques
stats_pv_conformite()
```

**Résultat attendu :**
```
📊 STATISTIQUES PV_CONFORMITE
Total PV : 10694
✅ Conformes : 7396 (69.2%)
❌ Non conformes : 3298 (30.8%)
⚠️ Inversions EU → EP : 54 (0.5%)
⚠️ Inversions EP → EU : 391 (3.7%)

Top 10 communes :
  1. GOUSSAINVILLE : 1787 PV
  2. SARCELLES : 1454 PV
  ...
```

---

## 📋 Test 3 : Module PVAnalyzer complet

```python
# Tester le module complet
test_pv_analyzer()
```

**Résultat attendu :**
```
🧪 TEST MODULE PVANALYZER

1️⃣ Chargement des couches...
✅ Couche PV chargée : 10694 PV
✅ Couche Canalisations chargée : XXXX canalisations

2️⃣ Initialisation PVAnalyzer...
✅ PVAnalyzer initialisé (distance buffer : 15.0m)

3️⃣ Simulation d'un cheminement...
✅ 50 canalisations dans le cheminement simulé

4️⃣ Recherche des PV non conformes...
🔍 Recherche de PV non conformes à 15.0m du cheminement...
  ✓ PV trouvé : 9 allée des Tournelles, LE THILLAY (distance: 12.3m)
  ✓ PV trouvé : 1 Rue Berthier, BOUFFEMONT (distance: 8.7m)
  ...

✅ X PV non conformes trouvés

5️⃣ Test de l'exclusion de branches...
   PV avant exclusion : X
   PV après exclusion : Y
   PV exclus : X-Y

6️⃣ Test de désignation d'un PV comme pollueur...
✅ PV désigné comme pollueur avec succès !

📍 Informations du PV pollueur :
   Type : PV non conforme
   Adresse : 9 allée des Tournelles
   Commune : LE THILLAY
   ...

✅ TESTS TERMINÉS
```

---

## 📋 Test 4 : Intégration manuelle dans un cheminement

### Étape 1 : Préparer un cheminement

```python
from qgis.core import QgsProject
from cheminer_indus.core.pv_analyzer import PVAnalyzer

# 1. Charger les couches
canal_layer = QgsProject.instance().mapLayersByName('Canalisations')[0]
pv_layer = QgsProject.instance().mapLayersByName('PV Conformité')[0]

# 2. Initialiser PVAnalyzer
pv_analyzer = PVAnalyzer(pv_layer)

print(f"✅ PVAnalyzer initialisé avec {pv_layer.featureCount()} PV")
```

### Étape 2 : Simuler un cheminement

```python
# Prendre 100 canalisations au hasard
canalisations_features = []
for i, feat in enumerate(canal_layer.getFeatures()):
    if i >= 100:
        break
    canalisations_features.append(feat)

print(f"✅ Cheminement simulé : {len(canalisations_features)} canalisations")
```

### Étape 3 : Chercher les PV

```python
# Chercher les PV non conformes
pv_list = pv_analyzer.find_pv_near_path(canalisations_features, 'EU')

print(f"\n✅ {len(pv_list)} PV non conformes trouvés :")

for i, pv in enumerate(pv_list[:5], 1):
    print(f"  {i}. {pv['adresse']}, {pv['commune']}")
    print(f"     Conforme: {pv['conforme']}")
    print(f"     EU→EP: {pv['eu_vers_ep']} | EP→EU: {pv['ep_vers_eu']}")
    print(f"     Distance: {pv['distance']:.1f}m")
```

### Étape 4 : Désigner un PV comme pollueur

```python
# Prendre le premier PV
if pv_analyzer.pv_actifs:
    premier_pv_id = pv_analyzer.pv_actifs[0]['id']
    
    # Désigner comme pollueur
    success = pv_analyzer.designate_as_polluter(premier_pv_id)
    
    if success:
        info = pv_analyzer.get_polluter_info()
        
        print(f"\n🎯 PV pollueur désigné :")
        print(f"   Adresse : {info['adresse']}")
        print(f"   Commune : {info['commune']}")
        print(f"   Problèmes : {info['problemes_str']}")
```

### Étape 5 : Tester l'exclusion

```python
# Exclure les 20 premières canalisations
canalisations_exclues = [
    feat['idcanal'] if 'idcanal' in feat.fields().names() else feat.id()
    for i, feat in enumerate(canalisations_features)
    if i < 20
]

print(f"\n🗑️ Exclusion de {len(canalisations_exclues)} canalisations...")

nb_avant = pv_analyzer.get_pv_count()
pv_analyzer.update_after_exclusion(canalisations_exclues)
nb_apres = pv_analyzer.get_pv_count()

print(f"   PV avant : {nb_avant}")
print(f"   PV après : {nb_apres}")
print(f"   PV exclus : {nb_avant - nb_apres}")
```

---

## 📋 Test 5 : Vérification de la géométrie

```python
# Vérifier que les PV ont bien une géométrie
pv_layer = QgsProject.instance().mapLayersByName('PV Conformité')[0]

total = 0
avec_geom = 0
sans_geom = 0

for feat in pv_layer.getFeatures():
    total += 1
    geom = feat.geometry()
    
    if geom and not geom.isNull():
        avec_geom += 1
    else:
        sans_geom += 1

print(f"Total PV : {total}")
print(f"Avec géométrie : {avec_geom} ({avec_geom/total*100:.1f}%)")
print(f"Sans géométrie : {sans_geom} ({sans_geom/total*100:.1f}%)")
```

**Résultat attendu :** 100% avec géométrie

---

## 📋 Test 6 : Performance

```python
import time

# Test de performance sur 1000 canalisations
canal_layer = QgsProject.instance().mapLayersByName('Canalisations')[0]
pv_layer = QgsProject.instance().mapLayersByName('PV Conformité')[0]

pv_analyzer = PVAnalyzer(pv_layer)

# Prendre 1000 canalisations
canalisations = []
for i, feat in enumerate(canal_layer.getFeatures()):
    if i >= 1000:
        break
    canalisations.append(feat)

# Mesurer le temps
start = time.time()
pv_list = pv_analyzer.find_pv_near_path(canalisations, 'EU')
elapsed = time.time() - start

print(f"\n⚡ Performance :")
print(f"   Canalisations : {len(canalisations)}")
print(f"   PV trouvés : {len(pv_list)}")
print(f"   Temps : {elapsed:.2f} secondes")
print(f"   Vitesse : {len(canalisations)/elapsed:.0f} canalisations/sec")
```

**Résultat attendu :** < 5 secondes pour 1000 canalisations

---

## 🐛 Débogage

### Problème : Couche PV_CONFORMITE introuvable

**Solution :**
```python
# Lister toutes les couches
from qgis.core import QgsProject

for layer in QgsProject.instance().mapLayers().values():
    print(f"- {layer.name()}")
```

Vérifier que "PV Conformité" ou "PV_CONFORMITE" est dans la liste.

### Problème : Pas de géométrie

**Solution :**
Vérifier que la table PostgreSQL a bien des colonnes `lat` et `lon` :

```sql
SELECT 
    COUNT(*) AS total,
    COUNT(lat) AS avec_lat,
    COUNT(lon) AS avec_lon
FROM exploit."PV_CONFORMITE";
```

### Problème : Aucun PV trouvé

**Solution :**
Vérifier que les PV sont proches des canalisations testées :

```python
# Compter les PV non conformes
pv_layer = QgsProject.instance().mapLayersByName('PV Conformité')[0]

non_conformes = 0
for feat in pv_layer.getFeatures():
    if feat['conforme'] == 'Non':
        non_conformes += 1

print(f"PV non conformes dans la couche : {non_conformes}")
```

Si le nombre est faible, c'est normal qu'aucun ne soit trouvé.

---

## ✅ Checklist de validation

Après avoir exécuté tous les tests, vérifier :

- [ ] Couche PV_CONFORMITE chargée (10 694 PV)
- [ ] Statistiques correctes (3 298 non conformes)
- [ ] Module PVAnalyzer fonctionnel
- [ ] Détection des PV à 15m opérationnelle
- [ ] Exclusion de branches fonctionne
- [ ] Désignation comme pollueur OK
- [ ] Performance acceptable (< 5s pour 1000 canalisations)
- [ ] Géométries valides (100% avec géométrie)

---

## 📞 Support

Si un test échoue, vérifier :

1. **Connexion PostgreSQL** configurée dans QGIS
2. **Table `exploit.PV_CONFORMITE`** existe dans la base
3. **Colonnes `lat` et `lon`** présentes et non NULL
4. **Plugin TRACK-EAU-POLL** chargé et activé
5. **Version QGIS** : 3.16+

**Email :** papademba.sene97@gmail.com  
**Documentation :** README_MODULE_PV_CONFORMITE.md  

---

## 🚀 Prochaine étape après validation

Une fois tous les tests validés, passer au développement de :

1. **Interface graphique** (onglet avec listes)
2. **Rapports PDF** (génération complète)
3. **Cheminement depuis PV** (Amont → Aval)

---

**Module PV Conformité v1.2.3**  
**Tests créés le :** 2026-01-16  
**Statut :** Prêt pour validation
