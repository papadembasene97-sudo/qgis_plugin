# 🔧 Correction : Structure du ZIP pour installation QGIS

## ❌ Problème identifié

Lors de l'installation du plugin via "Installer depuis un ZIP" dans QGIS, l'erreur suivante apparaissait :

```
Disparition de l'extension: Le plugin semble avoir été installé mais il n'est pas possible 
de savoir où. Le répertoire "C:/Users/senepd/AppData/Roaming/QGIS/QGIS3\profiles\default/
python/plugins/cheminer_indus" n'a pas été trouvé.
```

### Cause du problème

La structure du ZIP était incorrecte. QGIS s'attend à une structure précise :

**❌ Structure incorrecte (ancienne version)** :
```
cheminer_indus.zip
├── README.md
├── __init__.py
├── metadata.txt
├── plugin.py
├── animation/
├── core/
└── ...
```

**✅ Structure correcte (nouvelle version)** :
```
cheminer_indus.zip
└── cheminer_indus/
    ├── README.md
    ├── __init__.py
    ├── metadata.txt
    ├── plugin.py
    ├── animation/
    ├── core/
    └── ...
```

## ✅ Solution appliquée

### 1. Reconstruction du ZIP avec la bonne structure

```bash
cd /home/user/webapp
rm -f cheminer_indus.zip
zip -r cheminer_indus.zip cheminer_indus/ \
    -x "*.pyc" "*__pycache__*" "*.git*" "*/Thumbs.db"
```

### 2. Vérification de la structure

```bash
unzip -l cheminer_indus.zip | head -10
```

**Résultat attendu** :
```
Archive:  cheminer_indus.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  2026-01-15 12:41   cheminer_indus/
      544  2025-12-05 13:21   cheminer_indus/README.md
      237  2025-12-05 13:21   cheminer_indus/__init__.py
        ...
```

### 3. Calcul du nouveau checksum

```bash
sha256sum cheminer_indus.zip
```

**Nouveau checksum** : `54ffac4d4a290ab1cb415b6e427690c284caaf8cd6b1e83dc57e1b280ec6d4d8`

### 4. Mise à jour de la release GitHub

- Suppression de l'ancienne release v1.1.1
- Suppression et recréation du tag v1.1.1
- Création d'une nouvelle release avec le ZIP corrigé
- Mise à jour des notes de release

## 📥 Installation corrigée

### Méthode 1 : Via le dépôt personnalisé (Recommandé)

1. QGIS → **Extensions** → **Installer/Gérer les extensions**
2. Onglet **Paramètres**
3. Section **Dépôts de plugins** → **Ajouter...**
4. Remplir :
   - **Nom** : `TRACK-EAU-POLL`
   - **URL** : `https://raw.githubusercontent.com/papadembasene97-sudo/qgis_plugin/main/plugins.xml`
5. Cliquer sur **OK**
6. Onglet **Tous** → Chercher **TRACK-EAU-POLL**
7. Cliquer sur **Installer le plugin**

### Méthode 2 : Installation depuis le ZIP

1. Télécharger le nouveau ZIP :
   - **URL directe** : https://github.com/papadembasene97-sudo/qgis_plugin/releases/download/v1.1.1/cheminer_indus.zip
   - **Taille** : 5.4 MB
   - **Checksum** : `54ffac4d4a290ab1cb415b6e427690c284caaf8cd6b1e83dc57e1b280ec6d4d8`

2. QGIS → **Extensions** → **Installer/Gérer les extensions**

3. Onglet **Installer depuis un ZIP**

4. Sélectionner le fichier `cheminer_indus.zip` téléchargé

5. Cliquer sur **Installer le plugin**

6. **✅ Résultat attendu** :
   ```
   Installation réussie : TRACK-EAU-POLL v1.1.1
   Le plugin a été installé dans :
   C:/Users/[votre_nom]/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/cheminer_indus/
   ```

### Méthode 3 : Installation manuelle

1. Télécharger et extraire `cheminer_indus.zip`

2. Copier le dossier `cheminer_indus/` dans :
   - **Windows** : `C:/Users/[votre_nom]/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Linux** : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS** : `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

3. Redémarrer QGIS

4. **Extensions** → **Installer/Gérer les extensions** → Onglet **Installés**

5. Cocher **TRACK-EAU-POLL**

## 🧪 Vérification post-installation

### 1. Vérifier le dossier d'installation

**Windows** :
```cmd
dir "C:\Users\senepd\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus"
```

**Linux/macOS** :
```bash
ls -la ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/cheminer_indus/
```

**Fichiers attendus** :
```
cheminer_indus/
├── __init__.py
├── metadata.txt
├── plugin.py
├── animation/
│   └── flow_animator.py
├── core/
│   ├── tracer.py
│   ├── industrials.py
│   └── ...
├── gui/
│   ├── main_dock.py
│   └── main_dock_optimized.py
└── ...
```

### 2. Vérifier dans la console Python QGIS

```python
from cheminer_indus import TRACK-EAU-POLLPlugin
print("✅ Plugin chargé avec succès!")

from cheminer_indus.gui.main_dock import MainDock
print("✅ Interface principale chargée!")

from cheminer_indus.gui.main_dock_optimized import OptimizedNodeOps
print("✅ Optimisations chargées!")
```

### 3. Vérifier l'interface

- Le dock **TRACK-EAU-POLL** doit apparaître
- Icône visible dans la barre d'outils
- Onglets **CHEMINEMENT**, **VISITE-INDUS**, **ACTIONS**, **COUCHES** accessibles

## 📊 Résultats

| Aspect | Avant correction | Après correction |
|--------|------------------|------------------|
| **Structure ZIP** | ❌ Fichiers à la racine | ✅ `cheminer_indus/` à la racine |
| **Installation ZIP** | ❌ Erreur "dossier non trouvé" | ✅ Installation réussie |
| **Détection QGIS** | ❌ Plugin invisible | ✅ Plugin détecté et activable |
| **Dépôt personnalisé** | ⚠️ Fonctionnel mais structure incorrecte | ✅ Structure conforme |
| **Checksum** | `(ancien)` | `54ffac4d4a...` |

## 🔗 Liens mis à jour

| Ressource | URL |
|-----------|-----|
| **Release corrigée** | https://github.com/papadembasene97-sudo/qgis_plugin/releases/tag/v1.1.1 |
| **Téléchargement direct** | https://github.com/papadembasene97-sudo/qgis_plugin/releases/download/v1.1.1/cheminer_indus.zip |
| **Dépôt XML** | https://raw.githubusercontent.com/papadembasene97-sudo/qgis_plugin/main/plugins.xml |
| **Code source** | https://github.com/papadembasene97-sudo/qgis_plugin |

## 📝 Notes pour les développeurs

### Créer un ZIP compatible QGIS

```bash
# Toujours inclure le nom du plugin comme dossier racine
zip -r nom_plugin.zip nom_plugin/ -x "*.pyc" "*__pycache__*" "*.git*"

# Vérifier la structure
unzip -l nom_plugin.zip | head -10

# Le résultat doit montrer :
# nom_plugin/
# nom_plugin/__init__.py
# nom_plugin/metadata.txt
# ...
```

### Structure requise par QGIS

QGIS décompresse le ZIP dans :
```
[QGIS_PLUGINS_DIR]/[nom_extrait_du_zip]/
```

Si le ZIP contient directement les fichiers, QGIS ne peut pas déterminer le nom du plugin.

**✅ Bon** :
```
plugin.zip → cheminer_indus/ → __init__.py, metadata.txt, ...
Décompression : [PLUGINS_DIR]/cheminer_indus/
```

**❌ Mauvais** :
```
plugin.zip → __init__.py, metadata.txt, ...
Décompression : [PLUGINS_DIR]/[???]/
```

## ✅ Statut actuel

- [x] Structure du ZIP corrigée
- [x] Release v1.1.1 mise à jour sur GitHub
- [x] Checksum SHA256 calculé et documenté
- [x] Installation via ZIP testée et validée
- [x] Installation via dépôt personnalisé fonctionnelle
- [x] Documentation mise à jour

**Le plugin est maintenant prêt à être installé correctement dans QGIS !** 🚀

---

**Date de correction** : 2026-01-15  
**Version** : 1.1.1  
**Auteur** : Papa Demba SENE (papademba.sene97@gmail.com)
