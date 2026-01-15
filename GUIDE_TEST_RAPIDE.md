# 🧪 Guide de test rapide - CheminerIndus v1.1.1

## 🎯 Objectif

Tester rapidement le plugin CheminerIndus avec la structure ZIP corrigée dans QGIS.

---

## 📥 Étape 1 : Téléchargement

### Option A : Téléchargement direct du ZIP
```
https://github.com/papadembasene97-sudo/qgis_plugin/releases/download/v1.1.1/cheminer_indus.zip
```

### Option B : Via la page de release
1. Aller sur : https://github.com/papadembasene97-sudo/qgis_plugin/releases/tag/v1.1.1
2. Cliquer sur `cheminer_indus.zip` (5.4 MB)

---

## 🔧 Étape 2 : Installation dans QGIS

### Méthode recommandée : Installer depuis un ZIP

1. **Ouvrir QGIS**
2. Menu **Extensions** → **Installer/Gérer les extensions**
3. Cliquer sur l'onglet **Installer depuis un ZIP**
4. Cliquer sur **...** pour sélectionner le fichier
5. Naviguer vers le fichier `cheminer_indus.zip` téléchargé
6. Cliquer sur **Installer le plugin**

**✅ Message attendu** :
```
Installation réussie : CheminerIndus v1.1.1
```

**❌ Si vous voyez cette erreur** :
```
Disparition de l'extension: Le plugin semble avoir été installé mais...
```
→ Vous avez l'ancienne version du ZIP. Téléchargez à nouveau depuis la release v1.1.1.

---

## ✅ Étape 3 : Vérification de l'installation

### 3.1 Vérifier dans le gestionnaire d'extensions

1. **Extensions** → **Installer/Gérer les extensions**
2. Onglet **Installés**
3. Chercher **CheminerIndus** dans la liste
4. **✅ Résultat attendu** : Le plugin apparaît avec la version 1.1.1

### 3.2 Vérifier l'interface

1. Le dock **CheminerIndus** doit apparaître automatiquement
2. **Si le dock n'apparaît pas** :
   - Menu **Extensions** → **CheminerIndus** → Cliquer pour afficher le dock

3. **✅ Vérifier les onglets** :
   - CHEMINEMENT
   - VISITE-INDUS
   - ACTIONS
   - COUCHES

### 3.3 Vérifier dans la console Python

1. **Extensions** → **Console Python**
2. Copier-coller ce code :

```python
# Test 1 : Import du plugin
try:
    from cheminer_indus import CheminerIndusPlugin
    print("✅ Plugin principal importé avec succès")
except Exception as e:
    print(f"❌ Erreur import plugin : {e}")

# Test 2 : Import de l'interface
try:
    from cheminer_indus.gui.main_dock import MainDock
    print("✅ Interface principale importée avec succès")
except Exception as e:
    print(f"❌ Erreur import interface : {e}")

# Test 3 : Import des optimisations
try:
    from cheminer_indus.gui.main_dock_optimized import OptimizedNodeOps
    print("✅ Module d'optimisation importé avec succès")
except Exception as e:
    print(f"❌ Erreur import optimisations : {e}")

# Test 4 : Vérification des modules core
try:
    from cheminer_indus.core.tracer import NetworkTracer
    from cheminer_indus.core.industrials import IndustrialsService
    from cheminer_indus.core.diagnostics import Diagnostics
    print("✅ Modules core importés avec succès")
except Exception as e:
    print(f"❌ Erreur import modules core : {e}")

print("\n✅ Tous les tests d'import réussis !")
```

**✅ Résultat attendu** :
```
✅ Plugin principal importé avec succès
✅ Interface principale importée avec succès
✅ Module d'optimisation importé avec succès
✅ Modules core importés avec succès

✅ Tous les tests d'import réussis !
```

---

## 🗂️ Étape 4 : Vérifier le dossier d'installation

### Windows
```cmd
dir "C:\Users\[VOTRE_NOM]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus"
```

### Linux
```bash
ls -la ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/cheminer_indus/
```

### macOS
```bash
ls -la ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/cheminer_indus/
```

**✅ Fichiers attendus** :
```
cheminer_indus/
├── __init__.py
├── metadata.txt
├── plugin.py
├── README.md
├── animation/
│   ├── __init__.py
│   └── flow_animator.py
├── core/
│   ├── __init__.py
│   ├── tracer.py
│   ├── industrials.py
│   ├── diagnostics.py
│   ├── selection.py
│   └── ...
├── gui/
│   ├── __init__.py
│   ├── main_dock.py
│   ├── main_dock_optimized.py
│   ├── industrial_dock.py
│   └── diagnostics_dock.py
├── icons/
├── fonts/
├── report/
│   ├── pdf_generator.py
│   └── photos.py
└── utils/
```

---

## 🚀 Étape 5 : Test fonctionnel basique

### Test 1 : Interface

1. Ouvrir le dock CheminerIndus
2. Vérifier que tous les onglets sont accessibles
3. Vérifier que les combos de sélection de couches sont présents

### Test 2 : Couches (si vous avez des données)

1. Charger une couche de canalisations
2. Dans l'onglet **COUCHES**, sélectionner la couche dans le combo **Canalisations**
3. Vérifier que le plugin détecte la couche

### Test 3 : Splash screen

1. Au premier lancement, un splash screen animé doit apparaître
2. Il doit se fermer automatiquement après quelques secondes

---

## 📊 Checklist de validation

- [ ] **Téléchargement** : ZIP téléchargé depuis la release v1.1.1
- [ ] **Installation** : Installation réussie sans erreur "dossier non trouvé"
- [ ] **Gestionnaire** : Plugin visible dans l'onglet "Installés"
- [ ] **Interface** : Dock CheminerIndus visible avec tous les onglets
- [ ] **Console Python** : Tous les imports réussissent
- [ ] **Dossier** : Fichiers présents dans le dossier d'installation
- [ ] **Fonctionnel** : Interface réactive et fonctionnelle

---

## ❌ Dépannage

### Erreur : "Le répertoire ... n'a pas été trouvé"

**Cause** : Ancienne version du ZIP avec structure incorrecte

**Solution** :
1. Désinstaller le plugin : **Extensions** → **Installés** → **Désinstaller**
2. Télécharger **à nouveau** le ZIP depuis : https://github.com/papadembasene97-sudo/qgis_plugin/releases/download/v1.1.1/cheminer_indus.zip
3. Réinstaller

### Le plugin n'apparaît pas dans la liste

**Solution** :
1. **Extensions** → **Installés**
2. Activer l'option **Afficher également les extensions expérimentales**
3. Chercher **CheminerIndus**
4. Cocher la case pour activer

### Erreurs d'import dans la console

**Solution** :
1. Vérifier que QGIS est en version 3.28 ou supérieure
2. Vérifier que Python 3.9+ est installé
3. Consulter les logs : **Extensions** → **Afficher les détails**

### Le dock ne s'affiche pas

**Solution** :
1. Menu **Extensions** → **CheminerIndus** (cliquer pour afficher)
2. Ou : Menu **Vue** → **Panneaux** → Chercher **CheminerIndus**

---

## 📝 Rapport de test

Après avoir testé, merci de reporter :

### ✅ Si tout fonctionne :
- Version de QGIS utilisée
- Système d'exploitation
- Confirmation que l'installation a réussi

### ❌ Si vous rencontrez des problèmes :
- Version de QGIS utilisée
- Système d'exploitation
- Message d'erreur exact
- Capture d'écran si possible

**Créer un rapport sur** : https://github.com/papadembasene97-sudo/qgis_plugin/issues

---

## 🔗 Liens utiles

| Ressource | URL |
|-----------|-----|
| **Release v1.1.1** | https://github.com/papadembasene97-sudo/qgis_plugin/releases/tag/v1.1.1 |
| **Téléchargement ZIP** | https://github.com/papadembasene97-sudo/qgis_plugin/releases/download/v1.1.1/cheminer_indus.zip |
| **Documentation complète** | https://github.com/papadembasene97-sudo/qgis_plugin/blob/main/INSTALLATION.md |
| **Correction ZIP** | https://github.com/papadembasene97-sudo/qgis_plugin/blob/main/CORRECTION_ZIP.md |
| **Signaler un bug** | https://github.com/papadembasene97-sudo/qgis_plugin/issues |

---

## ⏱️ Temps estimé

- **Téléchargement** : 1-2 minutes
- **Installation** : 30 secondes
- **Vérification** : 2-3 minutes
- **Test fonctionnel** : 5 minutes

**Total** : ~10 minutes

---

**Version du guide** : 1.0  
**Date** : 2026-01-15  
**Plugin** : CheminerIndus v1.1.1  
**Auteur** : Papa Demba SENE (papademba.sene97@gmail.com)
