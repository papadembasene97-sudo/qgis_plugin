# 🔄 Instructions pour recharger le plugin CheminerIndus dans QGIS

## ⚠️ Problème

Les modifications du code Python **ne sont PAS automatiquement rechargées** par QGIS. Il faut forcer le rechargement du plugin.

## ✅ Solution 1 : Plugin Reloader (Recommandé)

### Installation
1. Dans QGIS, aller dans **Extensions** → **Installer/Gérer les extensions**
2. Chercher **Plugin Reloader**
3. Cliquer sur **Installer le plugin**

### Utilisation
1. Cliquer sur l'icône **Plugin Reloader** dans la barre d'outils
2. Sélectionner **CheminerIndus** dans la liste
3. Cliquer sur **Recharger le plugin**
4. ✅ Les modifications sont maintenant actives !

## ✅ Solution 2 : Redémarrage de QGIS (Alternative)

1. **Fermer QGIS complètement**
2. **Copier les fichiers modifiés** vers le dossier du plugin :
   ```
   C:\Users\senepd\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus\
   ```
3. **Rouvrir QGIS**
4. Le plugin est rechargé avec les nouvelles modifications

## ✅ Solution 3 : Réinstallation du plugin

1. Dans QGIS : **Extensions** → **Installer/Gérer les extensions**
2. **Désinstaller** CheminerIndus
3. **Copier** les nouveaux fichiers vers le dossier plugins
4. **Réinstaller** CheminerIndus
5. ✅ Plugin mis à jour !

## 📋 Fichiers modifiés dans ce commit

### Commit `35c4fd9` - Corrections de 3 bugs

#### 1. **cheminer_indus/core/tracer.py**
- **Ligne 82-84** : Ajout attributs `self.canal_ids` et `self.fosse_ids`
- **Ligne 244-246** : Stockage des résultats dans `trace()`
- **Bug résolu** : `'NetworkTracer' object has no attribute 'canal_ids'`

#### 2. **cheminer_indus/gui/ai_tab.py**
- **Ligne 264** : Import de `generate_synthetic_training_data` (fonction)
- **Ligne 267** : Utilisation directe de la fonction
- **Ligne 270** : Appel `predictor.train(training_data)`
- **Ligne 507** : Renommage `visualize_network()` → `visualize_network_3d()`
- **Bugs résolus** :
  - `cannot import name 'TrainingDataGenerator'`
  - `'NetworkVisualizer3D' object has no attribute 'visualize_network'`

## 🧪 Tests après rechargement

### Test 1 : Analyse de cheminement
1. Faire un cheminement depuis l'onglet **Cheminement**
2. Aller dans l'onglet **PV Conformité**
3. Cliquer sur **Analyser le cheminement**
4. ✅ Devrait fonctionner sans erreur `canal_ids`

### Test 2 : Entraînement du modèle IA
1. Aller dans l'onglet **IA**
2. Cliquer sur **Entraîner le modèle**
3. Sélectionner un fichier de sauvegarde
4. ✅ Devrait fonctionner sans erreur `TrainingDataGenerator`

### Test 3 : Visualisation 3D
1. Aller dans l'onglet **IA**
2. Cliquer sur **Visualiser en 3D**
3. ✅ Devrait fonctionner sans erreur `visualize_network`

## 🔗 Pull Request

**PR #2** : https://github.com/papadembasene97-sudo/qgis_plugin/pull/2

**Branch** : `fix/ai-training-data-generator-import`

**Commits** :
- `15e0773` - fix(ai): Corriger l'import TrainingDataGenerator inexistant
- `35c4fd9` - fix(core,gui): Corriger 3 bugs dans le plugin

## 📦 Mise à jour manuelle du plugin

Si vous voulez mettre à jour manuellement sans Git :

### Copier les fichiers modifiés
```bash
# Depuis le dépôt Git cloné
cd /chemin/vers/qgis_plugin

# Copier vers QGIS
cp cheminer_indus/core/tracer.py "C:\Users\senepd\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus\core\"

cp cheminer_indus/gui/ai_tab.py "C:\Users\senepd\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus\gui\"
```

### Vérifier la copie
1. Ouvrir le fichier dans l'éditeur :
   - `C:\Users\senepd\...\cheminer_indus\gui\ai_tab.py`
2. Chercher la ligne 264 :
   ```python
   from ..ai.training_data_generator import generate_synthetic_training_data
   ```
3. ✅ Si vous voyez `generate_synthetic_training_data`, la copie est réussie
4. ❌ Si vous voyez `TrainingDataGenerator`, le fichier n'a pas été copié

## 🆘 En cas de problème persistant

### Vider le cache Python de QGIS
1. Fermer QGIS
2. Supprimer le dossier cache :
   ```
   C:\Users\senepd\AppData\Roaming\QGIS\QGIS3\profiles\default\python\__pycache__
   ```
3. Supprimer les .pyc dans le plugin :
   ```
   C:\Users\senepd\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus\**\__pycache__
   ```
4. Redémarrer QGIS

### Vérifier la version du plugin
Dans la console Python de QGIS :
```python
import cheminer_indus
print(cheminer_indus.__file__)

# Vérifier le contenu du fichier
with open(r"C:\Users\senepd\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus\gui\ai_tab.py", encoding='utf-8') as f:
    content = f.read()
    if 'generate_synthetic_training_data' in content:
        print("✅ Fichier mis à jour !")
    else:
        print("❌ Fichier non mis à jour - Copier manuellement")
```

---

**Date de mise à jour** : 2026-01-19  
**Auteur** : GenSpark AI Developer  
**Version plugin** : v1.2.3+
