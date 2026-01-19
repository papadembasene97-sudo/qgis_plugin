# 🗺️ Noms de Couches Détectées par CheminerIndus

**Date:** 2026-01-19  
**Version:** 1.3.1

---

## 📋 Table des Matières
1. [Règles de Détection](#règles-de-détection)
2. [Couches Détectées](#couches-détectées)
3. [Exemples de Noms Acceptés](#exemples-de-noms-acceptés)
4. [Problèmes Courants](#problèmes-courants)
5. [Solutions](#solutions)

---

## 🔍 Règles de Détection

Le plugin CheminerIndus détecte automatiquement les couches QGIS en cherchant des **mots-clés** dans le **nom de la couche** (insensible à la casse).

### Méthode de Détection
```python
# Le nom de la couche est converti en minuscules
name = lyr.name().lower()

# Puis on cherche les mots-clés
if "mot_cle" in name:
    # Couche détectée !
```

---

## 🗂️ Couches Détectées

### 1. 🔵 **Canalisations** (`canal_combo`)

**Mot-clé requis :** `canal`

**Exemples de noms acceptés :**
- ✅ `CANALISATIONS`
- ✅ `canal_assainissement`
- ✅ `osmose.CANAL`
- ✅ `Reseau_Canal`
- ✅ `CANAL_EU_EP`
- ❌ `conduites` (pas de "canal")
- ❌ `tuyaux` (pas de "canal")

---

### 2. 🔴 **Ouvrages** (`ouvr_combo`)

**Mots-clés requis :** `ouvr` **OU** `ouvrage`

**Exemples de noms acceptés :**
- ✅ `OUVRAGES`
- ✅ `ouvr_assainissement`
- ✅ `osmose.OUVRAGE`
- ✅ `Reseau_Ouvr`
- ✅ `OUVR_REGARD`
- ❌ `regards` (pas de "ouvr" ou "ouvrage")
- ❌ `bouches` (pas de "ouvr" ou "ouvrage")

---

### 3. 🌊 **Cours d'eau / Fossés** (`fosse_combo`)

**Mots-clés requis :** `cours` **OU** `fosse`

**Exemples de noms acceptés :**
- ✅ `COURS_EAU`
- ✅ `fosses`
- ✅ `cours_deau`
- ✅ `osmose.FOSSE`
- ✅ `Reseau_Fosse`
- ✅ `COURS_NATUREL`
- ❌ `rivieres` (pas de "cours" ou "fosse")
- ❌ `ruisseaux` (pas de "cours" ou "fosse")

---

### 4. 🏭 **Industriels** (`indus_combo`)

**Mots-clés requis :** `indus` **OU** `industriel`

**Exemples de noms acceptés :**
- ✅ `INDUSTRIELS`
- ✅ `indus_raccordes`
- ✅ `osmose.INDUSTRIEL`
- ✅ `Reseau_Indus`
- ✅ `INDUS_POLLUEURS`
- ❌ `usines` (pas de "indus" ou "industriel")
- ❌ `etablissements` (pas de "indus" ou "industriel")

---

### 5. 🔗 **Liaisons Industrielles** (`liaison_combo`)

**Mot-clé requis :** `liaison`

**Exemples de noms acceptés :**
- ✅ `LIAISONS`
- ✅ `liaison_indus`
- ✅ `osmose.LIAISON`
- ✅ `Liaison_Industriels`
- ✅ `LIAISON_RACCORD`
- ❌ `raccordements` (pas de "liaison")
- ❌ `connexions` (pas de "liaison")

---

### 6. ⚠️ **Astreinte-Exploitation** (`astreint_combo`)

**Mots-clés requis :** `astreint` **OU** `astreinte`

**Exemples de noms acceptés :**
- ✅ `ASTREINTE`
- ✅ `astreint_exploit`
- ✅ `osmose.ASTREINTE`
- ✅ `Reseau_Astreint`
- ✅ `ASTREINTE_EXPLOITATION`
- ❌ `exploitation` (pas de "astreint" ou "astreinte")
- ❌ `urgence` (pas de "astreint" ou "astreinte")

---

### 7. 🏠 **PV Conformité** (`pv_combo`)

**Mots-clés requis :** `pv` **ET** (`conform` **OU** `confomit`)

**⚠️ IMPORTANT :** Cette couche nécessite **DEUX mots-clés** dans le nom :
- Le nom doit contenir **"pv"**
- **ET** contenir **"conform"** ou **"confomit"**

**Exemples de noms acceptés :**
- ✅ `PV_CONFORMITE` ← **Recommandé**
- ✅ `osmose.PV_CONFORMITE` ← **Standard**
- ✅ `pv_conformite`
- ✅ `PV_CONFOMITE` ← **Accepté** (faute de frappe courante)
- ✅ `pv_confomite` ← **Accepté**
- ✅ `PV_CONFORM`
- ✅ `pv_conformite_2024`
- ✅ `Controles_PV_Conformite`
- ❌ `PV` (manque "conform")
- ❌ `CONFORMITE` (manque "pv")
- ❌ `POINTS_VERTS` (manque "conform")
- ❌ `PV_CONTROLE` (manque "conform")

---

## 🎯 Exemples de Noms Acceptés

### Nommage Standard (Recommandé)
```
✅ CANALISATIONS
✅ OUVRAGES
✅ COURS_EAU
✅ INDUSTRIELS
✅ LIAISONS
✅ ASTREINTE
✅ PV_CONFORMITE
```

### Nommage Osmose (Recommandé)
```
✅ osmose.CANAL
✅ osmose.OUVRAGE
✅ osmose.FOSSE
✅ osmose.INDUSTRIEL
✅ osmose.LIAISON
✅ osmose.ASTREINTE
✅ osmose.PV_CONFORMITE
```

### Nommage avec Préfixes/Suffixes
```
✅ RESEAU_CANAL_2024
✅ OUVR_ASSAINISSEMENT
✅ INDUS_RACCORDES
✅ PV_CONFORMITE_BRETAGNE
```

---

## ❌ Problèmes Courants

### Problème 1: Couche PV_CONFORMITE non détectée

**Symptômes :**
- La couche PV_CONFORMITE est chargée dans QGIS
- Elle n'apparaît pas dans le combo "🏠 PV Conformité" de l'onglet PARAMÈTRES
- Erreur : "Couche PV_CONFORMITE non trouvée"

**Causes possibles :**

#### Cause A: Faute de frappe dans le nom
```
❌ PV_CONFOMITE    (un seul M)
❌ PV_COMFORMITE   (ordre lettres)
❌ PV_CONFORMITÉ   (accent sur E)
❌ PV CONFORMITE   (espace au lieu de _)
```

#### Cause B: Mot-clé manquant
```
❌ PV               (manque "conform")
❌ CONFORMITE       (manque "pv")
❌ PV_CONTROLE      (manque "conform")
❌ POINTS_VERTS     (manque "conform")
```

#### Cause C: Couche non chargée
- La couche n'est pas visible dans le panneau des couches QGIS
- La couche est chargée mais invalide (erreur de connexion)

---

## ✅ Solutions

### Solution 1: Vérifier le nom exact de la couche

1. **Dans QGIS :**
   - Ouvrir le panneau des couches (Ctrl+1)
   - Faire un clic droit sur la couche → Propriétés
   - Onglet "Information" → Vérifier le nom exact

2. **Renommer la couche si nécessaire :**
   - Clic droit sur la couche → Renommer
   - Utiliser un nom recommandé : `PV_CONFORMITE` ou `osmose.PV_CONFORMITE`

---

### Solution 2: Ajouter manuellement dans le code (si besoin)

Si vous DEVEZ utiliser un nom non standard, modifiez le fichier :
`cheminer_indus/gui/main_dock.py`

**Ligne 431-433 :**
```python
# AVANT
if "pv" in name and ("conform" in name or "confomit" in name):
    if self.pv_combo:
        self.pv_combo.addItem(lyr.name(), lyr)

# APRÈS (exemple pour accepter "PV_CONTROLE")
if ("pv" in name and ("conform" in name or "confomit" in name)) or name == "pv_controle":
    if self.pv_combo:
        self.pv_combo.addItem(lyr.name(), lyr)
```

---

### Solution 3: Recharger les couches dans le plugin

Après avoir renommé une couche dans QGIS :

1. **Ouvrir le plugin CheminerIndus**
2. **Aller dans l'onglet ⚙️ PARAMÈTRES**
3. **Fermer et rouvrir le plugin** (ou recharger avec Plugin Reloader)
4. **Vérifier que la couche apparaît maintenant dans les combos**

---

### Solution 4: Créer une vue PostgreSQL avec le bon nom

Si vous utilisez PostgreSQL et que le nom de la table est fixe :

```sql
-- Créer une vue avec le nom attendu
CREATE VIEW pv_conformite AS 
SELECT * FROM votre_table_pv;

-- Ou renommer la table
ALTER TABLE votre_table_pv RENAME TO pv_conformite;
```

Puis charger la vue/table renommée dans QGIS.

---

## 🔧 Modification du Code pour Plus de Flexibilité

Si vous avez des noms de couches très différents, vous pouvez modifier la détection dans `main_dock.py` :

### Option 1: Détection par liste de noms exacts
```python
# Ligne 431
pv_names = ["PV_CONFORMITE", "osmose.PV_CONFORMITE", "MA_COUCHE_PV", "PV_2024"]
if any(n.lower() in name for n in [x.lower() for x in pv_names]):
    if self.pv_combo:
        self.pv_combo.addItem(lyr.name(), lyr)
```

### Option 2: Détection par expression régulière
```python
import re

# Ligne 431
if re.search(r'pv.*conform', name, re.IGNORECASE):
    if self.pv_combo:
        self.pv_combo.addItem(lyr.name(), lyr)
```

---

## 📝 Checklist de Vérification

Avant de signaler un problème de détection :

- [ ] La couche est bien chargée dans QGIS (visible dans le panneau des couches)
- [ ] La couche est valide (pas d'icône d'erreur rouge)
- [ ] Le nom contient les mots-clés requis (voir tableau ci-dessus)
- [ ] Le nom ne contient pas de caractères spéciaux problématiques (accents, espaces en trop)
- [ ] Le plugin a été rechargé après chargement/renommage de la couche
- [ ] L'onglet PARAMÈTRES a été ouvert (déclenche `_populate_layers()`)

---

## 🎓 Recommandations

### Pour PV_CONFORMITE (le plus important)

**✅ RECOMMANDÉ :**
```
PV_CONFORMITE          ← Simple et clair
osmose.PV_CONFORMITE   ← Standard avec schéma
```

**⚠️ ACCEPTABLE :**
```
PV_CONFOMITE           ← Faute de frappe acceptée
pv_conformite_2024     ← Avec suffixe
```

**❌ À ÉVITER :**
```
PV                     ← Trop court
CONFORMITE             ← Manque "pv"
PV_CONTROLES           ← Manque "conform"
Points_Verts           ← Trop différent
```

---

## 🚀 Mise à Jour Appliquée (v1.3.1)

**Modification dans `main_dock.py` ligne 431 :**

```python
# AVANT (strict)
if "pv" in name and "conform" in name:

# APRÈS (flexible)
if "pv" in name and ("conform" in name or "confomit" in name):
```

**Amélioration :**
- ✅ Accepte maintenant `PV_CONFOMITE` (faute de frappe courante)
- ✅ Accepte `PV_CONFORMITE` (standard)
- ✅ Accepte toute variation contenant "pv" + "conform" ou "confomit"

---

## 📞 Support

**Si votre couche n'est toujours pas détectée :**

1. Vérifiez le nom exact dans QGIS (Propriétés de la couche)
2. Essayez de la renommer en `PV_CONFORMITE`
3. Rechargez le plugin (Plugin Reloader)
4. Si le problème persiste, indiquez :
   - Le nom exact de votre couche
   - Le type de source (PostgreSQL, Shapefile, GeoPackage, etc.)
   - Une capture d'écran du panneau des couches QGIS

---

**CheminerIndus v1.3.1** - Détection améliorée pour PV_CONFORMITE ✅
