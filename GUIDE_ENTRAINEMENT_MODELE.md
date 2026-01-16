# 📚 Guide d'entraînement du modèle IA CheminerIndus

## 🎯 Objectif du modèle

Le modèle IA apprend à **prédire la probabilité de pollution** dans les nœuds du réseau d'assainissement en analysant :
- La **topologie** du réseau (connectivité, position)
- Les **caractéristiques physiques** (diamètre, pente, longueur)
- L'**historique des visites** (pollutions précédentes)
- Les **facteurs temporels** (saison, jour, heure)

---

## 📊 Données nécessaires pour l'entraînement

### 1️⃣ Couche de canalisations (OBLIGATOIRE)

**Nom de la couche** : Canalisations / Réseau / Canal

**Champs requis ou recommandés** :

| Champ | Type | Obligatoire | Description | Exemple |
|-------|------|-------------|-------------|---------|
| `id` ou `idcanal` | String/Integer | ✅ OUI | Identifiant unique de la canalisation | "CAN_001" |
| `diameter` ou `diametre` | Integer | ⭐ Recommandé | Diamètre en mm | 300 |
| `length` ou `longueur` | Float | ⭐ Recommandé | Longueur en mètres | 45.5 |
| `slope` ou `pente` | Float | ⭐ Recommandé | Pente en % ou m/m | 0.02 |
| `zamont` | Float | ⭐ Recommandé | Altitude amont en m | 152.3 |
| `zaval` | Float | ⭐ Recommandé | Altitude aval en m | 151.4 |
| `type_reseau` ou `typreseau` | String | ⭐ Recommandé | Type : EU, EP, Unitaire | "EU" |
| `material` ou `materiau` | String | ⚙️ Optionnel | Matériau de la canalisation | "PVC", "Béton" |
| `date_pose` | Date | ⚙️ Optionnel | Date de pose | "2015-03-20" |

**Note** : Le modèle s'adapte aux champs disponibles. Plus vous avez de champs, meilleure sera la précision.

---

### 2️⃣ Données historiques de visites (OBLIGATOIRE pour entraînement réel)

**Option A : Couche de visites existante**

Créez une couche vectorielle **Points** avec les nœuds visités :

| Champ | Type | Obligatoire | Description | Exemple |
|-------|------|-------------|-------------|---------|
| `node_id` ou `id_noeud` | String | ✅ OUI | ID du nœud visité | "NOE_042" |
| `polluted` ou `pollue` | Boolean/Integer | ✅ OUI | 1 si pollué, 0 sinon | 1 |
| `date_visite` | Date | ⭐ Recommandé | Date de la visite | "2024-06-15" |
| `pollution_level` ou `niveau_pollution` | Integer | ⚙️ Optionnel | Niveau 0-10 | 7 |
| `type_pollution` | String | ⚙️ Optionnel | Type de pollution | "Industrielle" |

**Exemple de données** :
```
node_id    | polluted | date_visite | pollution_level
-----------|----------|-------------|----------------
NOE_042    | 1        | 2024-06-15  | 8
NOE_137    | 0        | 2024-06-15  | 0
NOE_221    | 1        | 2024-07-03  | 6
NOE_089    | 0        | 2024-07-03  | 0
```

**Option B : Utiliser les données synthétiques (pour test)**

Si vous n'avez pas encore d'historique, le plugin peut **générer des données synthétiques** pour tester le modèle. Ces données simulent des pollutions basées sur :
- Proximité des industriels
- Diamètre faible
- Pente faible
- Âge du réseau

---

## 🚀 Comment entraîner le modèle

### Méthode 1 : Via l'interface graphique (RECOMMANDÉ)

#### Avec des données réelles

1. **Préparer vos données** :
   - Couche de canalisations chargée dans QGIS
   - Couche de visites chargée dans QGIS (avec champ `polluted`)

2. **Ouvrir CheminerIndus** :
   - Cliquer sur l'icône du plugin
   - Aller dans l'onglet **"🤖 IA"**

3. **Sélectionner les couches** :
   - Onglet **"COUCHES"** → Sélectionner votre couche de canalisations

4. **Entraîner** :
   - Revenir dans l'onglet **"🤖 IA"**
   - Cliquer sur **"⚙️ Entraîner le modèle"**
   - Choisir où sauvegarder le modèle (ex: `modele_pollution_2024.pkl`)
   - Attendre 2-5 minutes (selon la taille du réseau)

5. **Vérification** :
   - Le statut passe de ❌ à ✅
   - Message : "Modèle entraîné et sauvegardé avec succès !"

#### Avec des données synthétiques (test)

Si vous n'avez pas de couche de visites :

1. Le plugin **génère automatiquement** des données d'entraînement
2. Environ **1000 exemples synthétiques** sont créés
3. Le modèle s'entraîne sur ces données simulées
4. ⚠️ **Précision réduite** mais permet de tester le système

---

### Méthode 2 : Via code Python (avancé)

#### A. Avec vos vraies données

```python
from cheminer_indus.ai import PollutionPredictor

# 1. Récupérer les couches
canal_layer = QgsProject.instance().mapLayersByName("Canalisations")[0]
visite_layer = QgsProject.instance().mapLayersByName("Visites")[0]

# 2. Créer le prédicteur
predictor = PollutionPredictor()

# 3. Entraîner avec vos données historiques
predictor.train_from_historical_data(
    canal_layer=canal_layer,
    visite_layer=visite_layer,
    node_id_field='id_noeud',      # Nom du champ ID nœud
    polluted_field='pollue'         # Nom du champ pollution (0/1)
)

# 4. Sauvegarder le modèle
predictor.save_model("/chemin/vers/modele_pollution.pkl")

print("✅ Modèle entraîné et sauvegardé avec succès !")
```

#### B. Avec des données synthétiques

```python
from cheminer_indus.ai import PollutionPredictor
from cheminer_indus.ai import TrainingDataGenerator

# 1. Récupérer la couche de canalisations
canal_layer = QgsProject.instance().mapLayersByName("Canalisations")[0]

# 2. Générer des données d'entraînement synthétiques
generator = TrainingDataGenerator(canal_layer)
X_train, y_train = generator.generate_training_data(
    n_samples=1000,           # Nombre d'exemples
    pollution_rate=0.15       # 15% de nœuds pollués
)

# 3. Créer et entraîner le prédicteur
predictor = PollutionPredictor()
predictor.train(X_train, y_train)

# 4. Sauvegarder
predictor.save_model("/chemin/vers/modele_test.pkl")

print(f"✅ Modèle entraîné sur {len(X_train)} exemples synthétiques")
```

---

## 📊 Les 27 features analysées par le modèle

Le modèle analyse automatiquement ces caractéristiques :

### 🔗 Topologie du réseau (8 features)
1. **Degré du nœud** : Nombre de canalisations connectées
2. **Distance réseau amont** : Distance totale vers l'amont (m)
3. **Distance réseau aval** : Distance totale vers l'aval (m)
4. **Centralité** : Position dans le réseau (0-1)
5. **Profondeur dans le réseau** : Niveau hiérarchique
6. **Nombre de nœuds amont** : Nœuds en amont
7. **Nombre de nœuds aval** : Nœuds en aval
8. **Densité locale** : Densité du réseau autour du nœud

### 📏 Caractéristiques physiques (10 features)
9. **Diamètre moyen** : Diamètre des canalisations connectées (mm)
10. **Diamètre min** : Plus petit diamètre (mm)
11. **Diamètre max** : Plus grand diamètre (mm)
12. **Écart-type diamètre** : Variabilité des diamètres
13. **Longueur totale** : Somme des longueurs connectées (m)
14. **Pente moyenne** : Pente moyenne (%)
15. **Pente min** : Pente minimale (%)
16. **Pente max** : Pente maximale (%)
17. **Altitude** : Altitude du nœud (m)
18. **Type de réseau** : EU (0), EP (1), Unitaire (2)

### 📅 Facteurs temporels (4 features)
19. **Mois** : 1-12 (saison)
20. **Jour de la semaine** : 1-7
21. **Heure** : 0-23
22. **Est week-end** : 0 ou 1

### 🏭 Proximité industrielle (3 features)
23. **Nombre d'industriels proches** : Dans un rayon de 500m
24. **Distance au plus proche industriel** : En mètres
25. **Industriels en amont** : Nombre en amont hydraulique

### 📜 Historique (2 features)
26. **Pollutions précédentes** : Nombre de fois pollué
27. **Jours depuis dernière pollution** : Nombre de jours

---

## 📈 Évaluation de la performance du modèle

Après l'entraînement, vous pouvez évaluer le modèle :

```python
from cheminer_indus.ai import PollutionPredictor

# Charger le modèle
predictor = PollutionPredictor()
predictor.load_model("/chemin/vers/modele.pkl")

# Évaluer sur des données de test
X_test, y_test = ...  # Vos données de test
accuracy = predictor.evaluate(X_test, y_test)

print(f"Précision du modèle : {accuracy * 100:.1f}%")
```

**Précision attendue** :
- Avec données synthétiques : **70-80%**
- Avec vrais historiques (>500 visites) : **85-90%**
- Avec vrais historiques (>2000 visites) : **90-95%**

---

## 🎯 Recommandations pour un bon entraînement

### ✅ Qualité des données

1. **Minimum recommandé** : 200-500 visites historiques
2. **Idéal** : 1000+ visites sur plusieurs mois
3. **Équilibre** : 10-20% de nœuds pollués (pas trop déséquilibré)
4. **Diversité** : Visites sur différentes saisons/périodes

### ✅ Préparation des données

```sql
-- Exemple : Créer une vue PostgreSQL avec les visites
CREATE VIEW visites_pollution AS
SELECT 
    id_noeud,
    CASE WHEN pollution_detectee THEN 1 ELSE 0 END as pollue,
    date_visite,
    niveau_pollution
FROM historique_visites
WHERE date_visite >= '2023-01-01';
```

### ✅ Mise à jour du modèle

**Réentraînez régulièrement** le modèle :
- Tous les 3-6 mois avec les nouvelles données
- Après des travaux importants sur le réseau
- Après modification du réseau industriel

---

## 🐛 Résolution de problèmes

### Erreur : "Impossible d'importer le module IA"

**Solution** :
```bash
pip install scikit-learn numpy matplotlib pyvista
```

### Erreur : "Couche de visites non trouvée"

**Solution** :
- Créer une couche Points avec les champs requis
- Ou utiliser le mode synthétique (pour test)

### Modèle peu précis (< 70%)

**Causes possibles** :
1. Trop peu de données d'entraînement (< 200 visites)
2. Données déséquilibrées (trop de 0 ou trop de 1)
3. Champs importants manquants (diamètre, pente, etc.)
4. Données synthétiques utilisées

**Solutions** :
1. Collecter plus de visites historiques
2. Rééquilibrer les données
3. Enrichir les attributs de la couche canalisations
4. Utiliser de vraies données de visite

---

## 💡 Exemple complet

### Étape 1 : Préparer les données

```sql
-- Créer une table de visites si elle n'existe pas
CREATE TABLE visites_terrain (
    id SERIAL PRIMARY KEY,
    id_noeud VARCHAR(50),
    date_visite DATE,
    pollue INTEGER,  -- 0 ou 1
    niveau_pollution INTEGER,  -- 0-10
    type_pollution VARCHAR(50),
    observateur VARCHAR(100)
);

-- Insérer des données d'exemple
INSERT INTO visites_terrain (id_noeud, date_visite, pollue, niveau_pollution) VALUES
('NOE_001', '2024-01-15', 0, 0),
('NOE_042', '2024-01-15', 1, 7),
('NOE_089', '2024-02-03', 0, 0),
('NOE_137', '2024-02-03', 1, 8),
...
```

### Étape 2 : Charger dans QGIS

1. Couche → Ajouter une couche → PostgreSQL
2. Charger "Canalisations" et "visites_terrain"

### Étape 3 : Entraîner via l'interface

1. CheminerIndus → Onglet "IA"
2. Cliquer "⚙️ Entraîner le modèle"
3. Sauvegarder : `C:/Modeles/pollution_2024.pkl`
4. ✅ "Modèle entraîné avec succès !"

### Étape 4 : Utiliser pour prédire

1. Cliquer "🎯 Prédire les zones à risque"
2. Les résultats s'affichent :
```
🎯 PRÉDICTION DE POLLUTION
==================================================

Seuil de risque : 70%
Points chauds détectés : 23

Top 10 des zones à risque :
--------------------------------------------------
1. NOE_042 → 94.2% → CRITIQUE
2. NOE_137 → 89.7% → CRITIQUE
3. NOE_221 → 78.3% → ÉLEVÉ
...
```

---

## 📝 Résumé rapide

| Étape | Action | Durée |
|-------|--------|-------|
| 1️⃣ Préparer les données | Créer couche visites avec champ `pollue` | 30 min |
| 2️⃣ Charger dans QGIS | Ajouter couches Canalisations + Visites | 5 min |
| 3️⃣ Ouvrir l'onglet IA | CheminerIndus → "🤖 IA" | 10 sec |
| 4️⃣ Entraîner | Cliquer "⚙️ Entraîner le modèle" | 2-5 min |
| 5️⃣ Prédire | Cliquer "🎯 Prédire les zones à risque" | 30 sec |

---

**🎉 Voilà ! Votre modèle IA est prêt à prédire les pollutions !** 🤖🔍

**Contact** : papademba.sene97@gmail.com
