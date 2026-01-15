# 🤖 Scripts d'entraînement IA - CheminerIndus

Scripts Python pour entraîner et tester le modèle de prédiction de pollution pour le plugin QGIS CheminerIndus.

---

## 📁 Fichiers

| Fichier | Description |
|---------|-------------|
| `entrainer_modele_ia.py` | Script d'entraînement du modèle IA |
| `tester_predictions_ia.py` | Script de test et visualisation des prédictions |
| `donnees_ia.csv` | Données d'entraînement exportées depuis PostgreSQL |

---

## 🚀 Installation rapide

### 1. Installer les dépendances Python

```bash
pip install pandas scikit-learn joblib
```

### 2. Exporter les données depuis PostgreSQL

```sql
COPY (
    SELECT 
        pollution_detectee_label,
        nb_canalisations,
        diametre_moyen,
        diametre_max,
        diametre_min,
        variation_diametres,
        pente_moyenne,
        pente_max,
        pente_min,
        longueur_cumul_amont,
        longueur_moyenne,
        age_moyen_reseau,
        nb_ep,
        nb_eu,
        nb_unitaire,
        nb_inversions_ep_dans_eu,
        nb_inversions_eu_dans_ep,
        nb_inversions_total,
        nb_industriels,
        nb_industriels_risque_pollution,
        nb_industriels_risque_graisse,
        nb_industriels_risque_hydrocarbure,
        nb_industriels_risque_chimique,
        nb_industriels_icpe,
        nb_visites_total,
        nb_pollutions,
        nb_pollutions_graisse,
        nb_pollutions_hydrocarbure,
        nb_debordements,
        nb_interventions_eu,
        nb_interventions_ep,
        nb_interventions_voirie,
        jours_depuis_derniere_visite,
        freq_interventions_par_an,
        score_risque_calcule
    FROM cheminer_indus.donnees_entrainement_ia
) TO 'P:/BASES_SIG/ProjetQGIS/model_ia/donnees_ia.csv' 
WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',');
```

⚠️ **Important** : Remplacer le chemin `P:/BASES_SIG/ProjetQGIS/model_ia/` par votre propre chemin.

### 3. Configurer les scripts

Ouvrir `entrainer_modele_ia.py` et modifier la ligne 18 :

```python
# ⚠️ MODIFIER CE CHEMIN SELON VOTRE INSTALLATION
DOSSIER_DONNEES = 'P:/BASES_SIG/ProjetQGIS/model_ia'
```

Faire la même chose dans `tester_predictions_ia.py` ligne 11.

---

## 📊 Utilisation

### Étape 1 : Entraîner le modèle

```bash
python entrainer_modele_ia.py
```

**Résultat attendu** :

```
============================================================
🚀 ENTRAÎNEMENT MODÈLE IA - CHEMINER INDUS v1.2.1
============================================================

📂 Chargement des données depuis : P:/BASES_SIG/.../donnees_ia.csv
✓ 820 exemples chargés

============================================================
📊 ANALYSE DES DONNÉES
============================================================

📋 Colonnes disponibles (34) :
   1. pollution_detectee_label
   2. nb_canalisations
   3. diametre_moyen
   ...

📈 Répartition des classes :
   Pollution détectée   :  287 ( 35.0%)
   Pas de pollution     :  533 ( 65.0%)

🔧 Préparation des données...
✓ 33 features préparées

🔀 Séparation train/test (80/20)...
✓ Train: 656 | Test: 164

🎓 Entraînement du modèle Random Forest...
✓ Entraînement terminé

============================================================
🎯 ÉVALUATION DU MODÈLE
============================================================

🎯 Précision globale : 87.2%

📊 Rapport de classification :
                       precision    recall  f1-score   support

Pas de pollution (0)      0.91      0.93      0.92       107
Pollution détectée (1)    0.85      0.82      0.84        57

⭐ Top 10 des features les plus importantes :
   1. nb_pollutions                       : 18.3%
   2. nb_inversions_total                 : 12.7%
   3. nb_industriels_risque_pollution     : 10.2%
   ...

💾 Modèle sauvegardé : .../modele_pollution_2026.pkl
✓ Métadonnées sauvegardées : .../modele_metadata.pkl
📄 Génération du rapport : .../rapport_entrainement.txt
✓ Rapport généré

============================================================
🎉 ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS !
============================================================
```

**Fichiers générés** :
- `modele_pollution_2026.pkl` : Le modèle entraîné
- `modele_metadata.pkl` : Métadonnées (features, précision, date)
- `rapport_entrainement.txt` : Rapport détaillé

---

### Étape 2 : Tester les prédictions

```bash
python tester_predictions_ia.py
```

**Résultat attendu** :

```
============================================================
🔮 TEST DES PRÉDICTIONS - CHEMINER INDUS v1.2.1
============================================================

📂 Chargement du modèle : .../modele_pollution_2026.pkl
✓ Modèle chargé
   - Date d'entraînement : 2026-01-15 14:30:45
   - Précision : 87.2%
   - Features : 33

🔮 Prédiction en cours sur 820 nœuds...
✓ Prédictions terminées

============================================================
📊 ANALYSE DES PRÉDICTIONS
============================================================

📈 Répartition des prédictions :
   Pollution détectée    :  294 ( 35.9%)
   Pas de pollution      :  526 ( 64.1%)

🎯 Niveaux de risque :
   CRITIQUE (≥80%)       :   42 nœuds 🔴
   ÉLEVÉ (60-79%)        :   89 nœuds 🟠
   MOYEN (40-59%)        :  163 nœuds 🟡
   FAIBLE (<40%)         :  526 nœuds 🟢

⚠️  TOP 20 NŒUDS À RISQUE CRITIQUE
============================================================

Rang  ID Nœud         Proba    Niveau          Inversions   Industriels  Historique
----------------------------------------------------------------------------------------------------
1     OUV_A42          94.3%  CRITIQUE 🔴     3            2            5
2     OUV_B17          91.8%  CRITIQUE 🔴     2            3            4
3     OUV_C08          88.5%  CRITIQUE 🔴     1            2            6
...

💾 Sauvegarde des prédictions : .../predictions_resultats.csv
✓ 820 prédictions sauvegardées
```

**Fichiers générés** :
- `predictions_resultats.csv` : Toutes les prédictions avec niveaux de risque

---

## 🎯 Utiliser le modèle dans QGIS

### Option 1 : Via l'interface CheminerIndus

1. **Ouvrir QGIS** et charger votre projet
2. **Menu Extensions** → **CheminerIndus**
3. **Onglet "IA"**
4. **Section PRÉDICTION** :
   - Couche à analyser : `raepa_ouvrass_p`
   - Modèle : Cliquer sur 📁 et sélectionner `modele_pollution_2026.pkl`
5. **Cliquer "Prédire les pollutions"**

### Option 2 : Importer les prédictions CSV

1. **Dans QGIS** : Menu **Couche** → **Ajouter une couche** → **Ajouter une couche de texte délimité**
2. **Sélectionner** `predictions_resultats.csv`
3. **Type de géométrie** : Aucune géométrie (table attributaire)
4. **Joindre** avec la couche `raepa_ouvrass_p` via `id_noeud`

---

## 📈 Interpréter les résultats

### Niveaux de risque

| Probabilité | Niveau | Icône | Action recommandée |
|-------------|--------|-------|-------------------|
| ≥ 80% | CRITIQUE | 🔴 | **Visite immédiate** - Risque élevé de pollution |
| 60-79% | ÉLEVÉ | 🟠 | **Visite prioritaire** - À planifier sous 1 mois |
| 40-59% | MOYEN | 🟡 | **Surveillance renforcée** - Visite tous les 3 mois |
| < 40% | FAIBLE | 🟢 | **Routine** - Suivi normal |

### Top features importantes

Les features les plus importantes pour la prédiction sont généralement :

1. **nb_pollutions** : Historique de pollutions détectées
2. **nb_inversions_total** : Nombre d'inversions EP/EU
3. **nb_industriels_risque_pollution** : Industriels à risque connectés
4. **nb_industriels_icpe** : ICPE connectées
5. **jours_depuis_derniere_visite** : Temps écoulé

---

## ⚙️ Paramètres du modèle

Le modèle utilise un **Random Forest** avec ces paramètres :

```python
PARAMETRES_MODELE = {
    'n_estimators': 100,           # 100 arbres de décision
    'max_depth': 15,               # Profondeur max 15
    'min_samples_split': 10,       # Min 10 exemples pour split
    'min_samples_leaf': 5,         # Min 5 exemples par feuille
    'random_state': 42,            # Reproductibilité
    'class_weight': 'balanced',    # Équilibrage auto des classes
    'n_jobs': -1                   # Utiliser tous les CPU
}
```

Pour modifier ces paramètres, éditez la section **CONFIGURATION** de `entrainer_modele_ia.py`.

---

## 🔄 Ré-entraîner le modèle

### Quand ré-entraîner ?

- ✅ Tous les **3-6 mois** (nouvelles données)
- ✅ Après **100+ nouvelles visites**
- ✅ Si le réseau a **significativement changé**
- ✅ Si la **précision diminue** (< 75%)

### Comment ré-entraîner ?

1. **Exporter les nouvelles données** depuis PostgreSQL (requête SQL ci-dessus)
2. **Sauvegarder l'ancien modèle** :
   ```bash
   copy modele_pollution_2026.pkl modele_pollution_2026_backup.pkl
   ```
3. **Lancer l'entraînement** :
   ```bash
   python entrainer_modele_ia.py
   ```
4. **Comparer les performances** (ancien vs nouveau)
5. **Utiliser le meilleur modèle**

---

## ❓ FAQ

### Q1 : Le script plante avec "FileNotFoundError"

**R** : Vérifier que le chemin dans `DOSSIER_DONNEES` est correct et que `donnees_ia.csv` existe.

### Q2 : Précision < 70%

**R** : Vérifier la qualité des données :
```python
# Afficher la répartition des classes
df['pollution_detectee_label'].value_counts()
```
Il faut au moins **20-30% de chaque classe** (OUI et NON).

### Q3 : "InvalidEscapeSequence" sur Windows

**R** : Utiliser des slashes normaux `/` au lieu de backslashes `\` :
```python
# ❌ Incorrect
DOSSIER_DONNEES = 'P:\BASES_SIG\...'

# ✅ Correct
DOSSIER_DONNEES = 'P:/BASES_SIG/...'
```

### Q4 : Le modèle prédit toujours 0 (pas de pollution)

**R** : Les données sont déséquilibrées. Le modèle utilise déjà `class_weight='balanced'`, mais vous pouvez aussi :
- Collecter plus de données de pollution
- Ajuster le seuil de décision (ex: considérer > 40% comme pollution)

### Q5 : Comment utiliser le modèle sur un autre réseau ?

**R** : Le modèle est transférable si les features sont similaires. Assurez-vous que le CSV de prédiction contient les **mêmes 33 colonnes** que l'entraînement.

---

## 📞 Support

- **Email** : papademba.sene97@gmail.com
- **GitHub** : https://github.com/papadembasene97-sudo/qgis_plugin/issues

---

## 📄 Licence

Ces scripts font partie du plugin CheminerIndus. Licence identique au plugin principal.

---

**Version** : 1.2.1  
**Date** : 2026-01-15
