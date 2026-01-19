# 🔍 Guide de Débogage - Détection PV_CONFORMITE

**Date:** 2026-01-19  
**Version:** 1.3.2 (DEBUG)

---

## 🎯 Objectif

Ce guide vous aide à diagnostiquer pourquoi votre couche PV n'est pas détectée par le plugin CheminerIndus.

---

## 📋 Étape 1: Exécuter le Script de Test

### Dans la Console Python de QGIS

1. **Ouvrir QGIS**
2. **Charger votre couche PV** dans QGIS
3. **Ouvrir la console Python** : Plugins → Console Python (ou Ctrl+Alt+P)
4. **Copier-coller ce code** dans la console :

```python
from qgis.core import QgsProject

print("=" * 60)
print("TEST DE DÉTECTION PV_CONFORMITE")
print("=" * 60)

layers = QgsProject.instance().mapLayers().values()
print(f"\nNombre total de couches: {len(list(layers))}")

pv_found = []
for lyr in QgsProject.instance().mapLayers().values():
    name = lyr.name()
    name_lower = name.lower()
    
    if "pv" in name_lower:
        print(f"\n✅ Couche avec 'pv': {name}")
        print(f"   name.lower() = {name_lower}")
        has_conform = "conform" in name_lower
        has_confomit = "confomit" in name_lower
        print(f"   Contient 'conform': {has_conform}")
        print(f"   Contient 'confomit': {has_confomit}")
        detected = has_conform or has_confomit
        print(f"   DÉTECTÉE: {detected}")
        if detected:
            pv_found.append(name)

print(f"\n{'='*60}")
if pv_found:
    print(f"✅ {len(pv_found)} couche(s) PV détectée(s):")
    for n in pv_found:
        print(f"   - {n}")
else:
    print("❌ AUCUNE couche PV détectée!")
    print("\nVotre couche doit contenir:")
    print("   - 'pv' dans son nom")
    print("   - ET 'conform' OU 'confomit'")
```

5. **Appuyer sur Entrée** pour exécuter
6. **Lire le résultat** dans la console

---

## 📊 Étape 2: Interpréter les Résultats

### Résultat A: "✅ Couche(s) PV détectée(s)"

Si vous voyez ce message, **la détection fonctionne** dans le code Python.

**Le problème est ailleurs:**
- Le plugin n'a peut-être pas été rechargé après modification
- Le combo `pv_combo` n'existe peut-être pas au moment du remplissage

**Solution:**
1. Recharger le plugin avec **Plugin Reloader**
2. Ou redémarrer QGIS complètement
3. Réessayer

---

### Résultat B: "❌ AUCUNE couche PV détectée"

Votre couche n'a PAS les bons mots-clés dans son nom.

**Exemple de sortie:**
```
✅ Couche avec 'pv': MA_COUCHE_PV
   name.lower() = ma_couche_pv
   Contient 'conform': False
   Contient 'confomit': False
   DÉTECTÉE: False
```

**Solution:**
- Votre couche `MA_COUCHE_PV` ne contient ni "conform" ni "confomit"
- **Renommez-la** en `PV_CONFORMITE` dans QGIS

**Comment renommer:**
1. Clic droit sur la couche dans QGIS
2. Renommer
3. Taper: `PV_CONFORMITE`
4. Valider
5. Recharger le plugin

---

## 🔧 Étape 3: Vérifier le Plugin avec les Logs de Débogage

### Activer les Logs

Le plugin affiche maintenant des logs de débogage dans la console Python de QGIS.

1. **Ouvrir la console Python** : Plugins → Console Python
2. **Ouvrir le plugin CheminerIndus**
3. **Chercher dans la console** les messages commençant par `=== DEBUG _populate_layers ===`

### Exemple de Log Correct

```
=== DEBUG _populate_layers ===
pv_combo existe: True
Couches dans QGIS: 8
Couche avec 'pv': PV_CONFORMITE (name.lower()=pv_conformite)
  - Contient 'conform': True
  - Contient 'confomit': False
  → PV DÉTECTÉE: PV_CONFORMITE
  → Ajoutée au combo (items: 1)
pv_combo final count: 1
=== FIN DEBUG ===
```

**✅ C'est BON** : La couche est détectée et ajoutée au combo.

---

### Exemple de Log avec Problème 1: Couche Non Détectée

```
=== DEBUG _populate_layers ===
pv_combo existe: True
Couches dans QGIS: 8
Couche avec 'pv': MA_COUCHE_PV (name.lower()=ma_couche_pv)
  - Contient 'conform': False
  - Contient 'confomit': False
pv_combo final count: 0
=== FIN DEBUG ===
```

**❌ PROBLÈME** : La couche contient "pv" mais pas "conform" ou "confomit".

**SOLUTION** : Renommer la couche en `PV_CONFORMITE`

---

### Exemple de Log avec Problème 2: pv_combo est None

```
=== DEBUG _populate_layers ===
pv_combo existe: False
Couches dans QGIS: 8
Couche avec 'pv': PV_CONFORMITE (name.lower()=pv_conformite)
  - Contient 'conform': True
  - Contient 'confomit': False
  → PV DÉTECTÉE: PV_CONFORMITE
  → ERREUR: pv_combo est None!
pv_combo final count: None
=== FIN DEBUG ===
```

**❌ PROBLÈME GRAVE** : Le combo `pv_combo` n'existe pas (None).

**SOLUTION** :
1. C'est un bug dans l'initialisation du plugin
2. Vérifier que l'onglet PARAMÈTRES existe bien
3. Signaler ce bug avec le log complet

---

## 📝 Étape 4: Informations à Fournir

Si le problème persiste, fournissez ces informations :

### 1. Nom Exact de Votre Couche
```
Dans QGIS:
- Panneau des couches → Clic droit sur la couche → Propriétés
- Onglet "Information" → Nom de la couche
- Copier le nom exact
```

### 2. Résultat du Script de Test
```
Copier-coller tout le résultat du script Python
(Étape 1 ci-dessus)
```

### 3. Logs de Débogage du Plugin
```
Ouvrir la console Python
Ouvrir le plugin CheminerIndus
Copier les messages entre:
  === DEBUG _populate_layers ===
  ...
  === FIN DEBUG ===
```

### 4. Capture d'Écran
- Capture du panneau des couches QGIS montrant votre couche PV
- Capture de l'onglet PARAMÈTRES du plugin montrant le combo vide

---

## 🎯 Solutions Rapides

### Solution 1: Renommer la Couche (Le Plus Simple)

```
1. Dans QGIS, clic droit sur votre couche PV
2. Renommer
3. Taper exactement: PV_CONFORMITE
4. Valider
5. Recharger le plugin (Plugin Reloader)
6. Ouvrir PARAMÈTRES → Vérifier le combo "🏠 PV Conformité"
```

### Solution 2: Créer une Vue PostgreSQL

Si vous ne pouvez pas renommer la table :

```sql
CREATE VIEW pv_conformite AS 
SELECT * FROM votre_table_pv;
```

Puis charger la vue dans QGIS.

### Solution 3: Créer un Alias dans QGIS

```
1. Clic droit sur la couche → Propriétés
2. Onglet "Source"
3. Champ "Nom de la couche" → Taper: PV_CONFORMITE
4. OK
5. Recharger le plugin
```

---

## 🚀 Version de Débogage

Cette version (1.3.2) contient des logs de débogage dans la console Python.

**Fichier modifié:**
- `cheminer_indus/gui/main_dock.py` (méthode `_populate_layers`)

**Logs ajoutés:**
- Existence de `pv_combo`
- Nombre de couches dans QGIS
- Détection détaillée pour chaque couche contenant "pv"
- Ajout au combo confirmé ou erreur

---

## 📞 Support

**Si aucune solution ne fonctionne, fournir:**

1. ✅ Nom exact de votre couche (copier-coller)
2. ✅ Résultat du script de test Python (étape 1)
3. ✅ Logs de débogage du plugin (=== DEBUG ===)
4. ✅ Capture d'écran du panneau des couches QGIS
5. ✅ Type de source (PostgreSQL, Shapefile, GeoPackage, etc.)

---

**CheminerIndus v1.3.2 (DEBUG)** - Avec logs de débogage activés 🔍
