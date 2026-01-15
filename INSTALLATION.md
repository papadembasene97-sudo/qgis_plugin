# 📥 Guide d'Installation - CheminerIndus via QGIS

## 🎯 Méthode 1 : Installation directe via dépôt QGIS (RECOMMANDÉ)

Cette méthode permet d'installer et de mettre à jour automatiquement le plugin depuis QGIS.

### Étapes détaillées

#### 1️⃣ Ouvrir le gestionnaire d'extensions QGIS

Dans QGIS :
- Menu **Extensions** → **Installer/Gérer les extensions**

#### 2️⃣ Accéder aux paramètres

Dans la fenêtre qui s'ouvre :
- Cliquer sur l'onglet **Paramètres** (en haut)

#### 3️⃣ Ajouter le dépôt personnalisé

Dans la section "Dépôts de plugins" :
- Cliquer sur le bouton **Ajouter...**
- Remplir les champs :

```
Nom : CheminerIndus
URL  : https://raw.githubusercontent.com/papadembasene97-sudo/qgis_plugin/main/plugins.xml
```

- Cocher la case **Activé**
- Cliquer sur **OK**

#### 4️⃣ Installer le plugin

- Retourner sur l'onglet **Tous** (en haut)
- Dans la barre de recherche, taper : `CheminerIndus`
- Sélectionner le plugin **CheminerIndus**
- Cliquer sur **Installer le plugin**

#### 5️⃣ Vérification

- Une fois installé, le plugin apparaît dans :
  - Menu **Extensions** → **CheminerIndus**
  - Barre d'outils (icône du plugin)

---

## 🔧 Méthode 2 : Installation depuis un fichier ZIP

### Option A : Télécharger depuis GitHub Releases

#### 1️⃣ Télécharger le ZIP

Aller sur : https://github.com/papadembasene97-sudo/qgis_plugin/releases/latest

- Télécharger le fichier **cheminer_indus.zip**

#### 2️⃣ Installer dans QGIS

Dans QGIS :
- Menu **Extensions** → **Installer/Gérer les extensions**
- Onglet **Installer depuis un ZIP**
- Cliquer sur **...** et sélectionner le fichier `cheminer_indus.zip`
- Cliquer sur **Installer le plugin**

### Option B : Téléchargement direct du code

```bash
# Télécharger directement depuis GitHub
https://github.com/papadembasene97-sudo/qgis_plugin/releases/download/v1.1.1/cheminer_indus.zip
```

Puis suivre l'étape 2️⃣ ci-dessus.

---

## 🛠️ Méthode 3 : Installation manuelle (Développeurs)

### Via Git Clone

```bash
# Linux / Mac
cd ~/.qgis3/python/plugins/
git clone https://github.com/papadembasene97-sudo/qgis_plugin.git cheminer_indus

# Windows
cd %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
git clone https://github.com/papadembasene97-sudo/qgis_plugin.git cheminer_indus
```

### Extraction manuelle

1. Télécharger : https://github.com/papadembasene97-sudo/qgis_plugin/archive/refs/heads/main.zip
2. Extraire l'archive
3. Renommer le dossier en `cheminer_indus`
4. Copier dans le répertoire des plugins QGIS :

**Linux / Mac** :
```
~/.qgis3/python/plugins/cheminer_indus/
```

**Windows** :
```
C:\Users\[VOTRE_UTILISATEUR]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cheminer_indus\
```

5. Redémarrer QGIS
6. Activer le plugin dans **Extensions** → **Installer/Gérer les extensions** → **Installées**

---

## ✅ Vérification de l'installation

### Après installation réussie, vous devriez voir :

1. **Dans le menu** :
   - Extensions → CheminerIndus

2. **Dans la barre d'outils** :
   - Icône du plugin (logo CheminerIndus)

3. **En cliquant sur l'icône** :
   - Ouverture du dock "CHEMINEMENT RESEAUX"
   - Splash screen animé (3 secondes)

### Test rapide

1. Cliquer sur l'icône CheminerIndus
2. Le dock principal doit s'ouvrir avec 4 onglets :
   - CHEMINEMENT
   - VISITE-INDUS
   - ACTIONS
   - COUCHES

---

## 🔄 Mise à jour du plugin

### Si installé via dépôt (Méthode 1)

Les mises à jour sont automatiques !

1. **Extensions** → **Installer/Gérer les extensions**
2. Onglet **Mises à jour disponibles**
3. Si une nouvelle version est disponible, cliquer sur **Mettre à jour le plugin**

### Si installé via ZIP ou manuellement

1. Désinstaller l'ancienne version
2. Réinstaller la nouvelle version en suivant la méthode choisie

---

## 📋 Prérequis

| Élément | Requis |
|---------|--------|
| **QGIS version** | 3.28 minimum, 3.40 maximum |
| **Python** | 3.9+ (inclus avec QGIS) |
| **Système** | Windows, Linux, macOS |
| **Connexion Internet** | Pour installation via dépôt uniquement |

---

## 🐛 Résolution de problèmes

### Le plugin n'apparaît pas après installation

1. Vérifier que le plugin est activé :
   - **Extensions** → **Installer/Gérer les extensions** → **Installées**
   - Cocher **CheminerIndus**

2. Redémarrer QGIS

### Erreur lors de l'installation via dépôt

1. Vérifier la connexion Internet
2. Vérifier l'URL du dépôt :
   ```
   https://raw.githubusercontent.com/papadembasene97-sudo/qgis_plugin/main/plugins.xml
   ```
3. Essayer la méthode d'installation via ZIP

### Erreur "Module non trouvé"

Le plugin nécessite QGIS 3.28 minimum. Vérifier votre version :
- **Aide** → **À propos**

### Erreur d'import

1. Vérifier que le dossier du plugin s'appelle bien `cheminer_indus`
2. Vérifier la structure du dossier :
   ```
   cheminer_indus/
   ├── __init__.py
   ├── plugin.py
   ├── metadata.txt
   ├── animation/
   ├── core/
   ├── gui/
   ├── ...
   ```

---

## 📞 Support

### Signaler un bug
https://github.com/papadembasene97-sudo/qgis_plugin/issues

### Documentation
- [Guide d'optimisations](https://github.com/papadembasene97-sudo/qgis_plugin/blob/main/OPTIMISATIONS.md)
- [Tests de performance](https://github.com/papadembasene97-sudo/qgis_plugin/blob/main/TESTS_PERFORMANCE.md)

### Contact
📧 Email : papademba.sene97@gmail.com

---

## 🎉 Installation réussie !

Une fois installé, vous pouvez :
- ✅ Cheminer les réseaux d'assainissement
- ✅ Détecter les industriels connectés
- ✅ Effectuer des diagnostics automatiques
- ✅ Générer des rapports PDF professionnels
- ✅ Bénéficier des optimisations de performance (85-90% plus rapide)

**Bon cheminement ! 🚀⚡**
