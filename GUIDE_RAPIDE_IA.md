# 🚀 Guide rapide : IA + Visualisation 3D

## 📋 Vue d'ensemble

Deux nouvelles fonctionnalités majeures ajoutées à CheminerIndus :

### 1. 🤖 IA de Prédiction de Pollution
- **Prédit** où la pollution va apparaître AVANT de faire les visites
- **Optimise** vos parcours terrain (gain de temps)
- **Apprend** de vos visites passées

### 2. 🎨 Visualisation 3D des Réseaux
- **Affiche** le réseau en 3D avec profondeurs réelles
- **Détecte** automatiquement les zones complexes (réseaux entremêlés)
- **Coloration** par diamètre, pente, élévation ou type

---

## ⚡ Installation express

```bash
# Dans votre environnement QGIS Python
pip install scikit-learn numpy matplotlib pyvista
```

Si `pyvista` pose problème, juste :
```bash
pip install scikit-learn numpy matplotlib
```

---

## 🎯 Utilisation en 3 étapes

### ÉTAPE 1 : Entraîner le modèle IA (une seule fois)

**Option A : Avec vos données réelles**

1. Dans QGIS, ouvrir CheminerIndus
2. Onglet **"IA"** (nouveau !)
3. Cliquer **"📂 Charger historique des visites"**
4. Sélectionner votre fichier JSON d'historique
5. Cliquer **"🚀 Entraîner le modèle"**
6. Attendre 1-2 minutes
7. **"💾 Sauvegarder modèle"** → `mon_modele.pkl`

**Option B : Test avec données synthétiques**

```bash
cd cheminer_indus/ai/
python training_data_generator.py
# Génère training_data_synthetic.json
```

Puis charger ce fichier dans l'interface.

---

### ÉTAPE 2 : Prédire les pollutions

1. Charger votre modèle (si pas déjà fait)
2. Cliquer **"🔥 Rechercher les points chauds"**
3. Ajuster le seuil (ex: 60% = points à 60%+ de pollution)
4. Voir les résultats dans le tableau
5. **"🗺️ Optimiser le parcours"** pour avoir l'ordre de visite idéal

**Résultat** :
```
Nœud_123    92.3%    CRITIQUE    Ø400mm    → Visiter en priorité !
Nœud_456    78.1%    ÉLEVÉ       Ø300mm    → Visiter aujourd'hui
Nœud_789    65.4%    ÉLEVÉ       Ø500mm    → Visiter cette semaine
...
```

---

### ÉTAPE 3 : Visualiser en 3D

1. **Sélectionner** les canalisations dans QGIS (ou toutes si aucune sélection)
2. Onglet **"IA"** → Section **Visualisation 3D**
3. Choisir coloration : `diameter`, `slope`, `elevation` ou `type`
4. Cocher **"Mettre en évidence zones complexes"**
5. Ajuster seuils :
   - **Densité** : 5 canaux (combien de canaux = zone complexe)
   - **Rayon** : 50m (dans quel rayon chercher)
6. Cliquer **"🌐 Visualiser réseau 3D"**

**Zones complexes détectées automatiquement** :
- 🔴 Sphères rouges = zones à problème
- Score de complexité calculé
- Évaluation du risque (FAIBLE → CRITIQUE)

---

## 💡 Cas d'usage concrets

### Cas 1 : "Je cherche où il y a de la pollution"

```
1. Charger mon modèle IA (déjà entraîné)
2. Rechercher points chauds (seuil 60%)
3. Top 10 des nœuds à risque s'affichent
4. Je pars visiter ces 10 nœuds en priorité
```

**Gain** : Au lieu de 50 visites aléatoires, je cible les 10 vraiment à risque !

---

### Cas 2 : "J'ai une zone avec plein de réseaux superposés"

```
1. Sélectionner la zone dans QGIS
2. Visualiser en 3D
3. Voir les profondeurs (Z) de chaque canalisation
4. Identifier les zones complexes (sphères rouges)
5. Exporter le rapport JSON
```

**Gain** : Je vois enfin en 3D comment les réseaux s'entremêlent !

---

### Cas 3 : "Je veux optimiser ma tournée de la semaine"

```
1. Prédire les pollutions
2. Optimiser le parcours
3. L'IA me donne l'ordre optimal : plus proches + plus à risque
4. Je suis le plan suggéré
```

**Gain** : Moins de kilomètres + meilleure couverture des points critiques

---

## 📊 Données utilisées par l'IA

### Pour prédire la pollution, l'IA analyse :

**Topologie** :
- Nombre de branches amont/aval
- Diamètres moyens
- Réductions de diamètre (amont > aval)
- Pentes moyennes
- Différences de pente brutales

**Géométrie** :
- Altitudes (z_amont, z_aval)
- Coordonnées X, Y
- Longueurs cumulées

**Historique** :
- Vos visites passées sur ce nœud
- Taux de pollution historique
- Jours depuis dernière visite
- Pollution dans le voisinage (100m)

**Temporel** :
- Mois (saisonnalité)
- Jour de la semaine

**Total : 27 features analysées !**

---

## 🎨 Options de visualisation 3D

### Coloration disponible :

| Critère | Utilité |
|---------|---------|
| **diameter** | Voir les variations de section |
| **slope** | Identifier pentes faibles/fortes |
| **elevation** | Visualiser les profondeurs |
| **type** | Distinguer EU/EP/Mixte |

### Détection zones complexes :

- **Densité** : Nombre de canaux dans un rayon donné
- **Z_range** : Différence d'altitude (superposition verticale)
- **Variance diamètres** : Mélange de sections différentes
- **Score = nb_canaux × z_range × (1 + variance/10000)**

**Exemple** :
```
Zone complexe détectée:
  - 12 canalisations
  - Diamètres: 200mm - 800mm
  - Dénivelé: 4.5m (réseaux sur 3 niveaux)
  - Score: 540 → RISQUE ÉLEVÉ
  - Recommandation: Surveillance renforcée nécessaire
```

---

## 🔧 Paramètres recommandés

### Prédiction de pollution :

- **Seuil** : 60% (bon compromis)
  - 80%+ = très sûr mais peu de résultats
  - 40%+ = beaucoup de résultats mais moins précis

### Zones complexes :

- **Densité urbaine** :
  - Densité: 7-10 canaux
  - Rayon: 30-40m
  
- **Zone péri-urbaine** :
  - Densité: 4-6 canaux
  - Rayon: 50-70m
  
- **Zone rurale** :
  - Densité: 3-4 canaux
  - Rayon: 80-100m

---

## 📈 Améliorer les performances

### Plus de données = meilleur modèle

- **Minimum** : 100 visites historiques
- **Recommandé** : 500+ visites
- **Idéal** : 1000+ visites

### Équilibrer pollution / non-pollution

Si 90% de vos visites = pas de pollution :
- Le modèle apprendra mal
- **Solution** : Générez des données synthétiques pour équilibrer

### Ré-entraîner régulièrement

Chaque trimestre, ré-entraînez avec les nouvelles données !

---

## 🐛 Problèmes courants

### "Module IA non disponible"
```bash
pip install scikit-learn numpy
```

### "PyVista not available"
```bash
pip install pyvista
# OU si échec
pip install matplotlib  # Fallback qui marche toujours
```

### "Le modèle prédit toujours 0%"
- Pas assez de données d'entraînement
- Ou toutes vos visites = pas de pollution
- **Solution** : Ajouter plus de cas de pollution

### "La 3D ne s'affiche pas"
- Vérifier que matplotlib est installé
- Essayer avec `use_pyvista=False`

---

## 📚 Exemples de code

### Tester le module en ligne de commande

```bash
cd cheminer_indus/ai/
python example_usage.py
```

Cela exécute 4 exemples complets :
1. Entraînement d'un modèle
2. Prédictions
3. Optimisation de parcours
4. Visualisation 3D

---

## 🎯 Prochaines étapes

Une fois maîtrisé :
- [ ] Entraîner avec VOS données réelles
- [ ] Comparer prédictions vs réalité terrain
- [ ] Ajuster les seuils selon vos besoins
- [ ] Intégrer dans votre workflow quotidien

---

## 💬 Questions ?

- **Documentation complète** : `cheminer_indus/ai/README.md`
- **Exemples** : `cheminer_indus/ai/example_usage.py`
- **Support** : https://github.com/papadembasene97-sudo/qgis_plugin/issues

---

**Bon cheminement intelligent ! 🤖🚀**
