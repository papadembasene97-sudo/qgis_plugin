# 📋 Nommage des Couches QGIS - CheminerIndus Plugin

**Version:** 1.3.0  
**Date:** 2026-01-19

---

## 🎯 Règles de Détection Automatique des Couches

Le plugin CheminerIndus détecte automatiquement les couches dans QGIS selon leur **nom**. Les mots-clés sont recherchés **en minuscules** (non sensible à la casse).

---

## 📊 Tableau de Détection des Couches

| Couche | Mots-clés Requis | Exemples de Noms Valides | ⚙️ Combo dans PARAMÈTRES |
|--------|------------------|--------------------------|--------------------------|
| **🔵 Canalisations** | `canal` | `canalisations`<br>`osmose.canal`<br>`CANAL_RESEAU`<br>`reseau_canal` | 🔵 Canalisations |
| **🔴 Ouvrages** | `ouvr` OU `ouvrage` | `ouvrages`<br>`osmose.ouvr`<br>`OUVRAGE_RESEAU`<br>`reseau_ouvrages` | 🔴 Ouvrages |
| **🌊 Cours d'eau / fossés** | `cours` OU `fosse` | `cours_eau`<br>`fosses`<br>`cours_d_eau`<br>`fosse_reseau` | 🌊 Cours d'eau / fossés |
| **🏭 Industriels** | `indus` OU `industriel` | `industriels`<br>`osmose.indus`<br>`INDUS_RESEAU`<br>`etablissements_industriels` | 🏭 Industriels |
| **🔗 Liaisons Indus** | `liaison` | `liaisons`<br>`liaison_indus`<br>`LIAISON_RESEAU` | 🔗 Liaisons Indus |
| **⚠️ Astreinte-Exploit** | `astreint` OU `astreinte` | `astreinte`<br>`astreint_exploit`<br>`ASTREINTE_RESEAU` | ⚠️ Astreinte-Exploit |
| **🏠 PV Conformité** | `pv` **ET** `conform` | `PV_CONFORMITE`<br>`osmose.PV_CONFORMITE`<br>`pv_conformite`<br>`PV_CONF`<br>`conformite_pv` | 🏠 PV Conformité |

---

## 🏠 **PV_CONFORMITE - Cas Spécial**

### ✅ Noms Valides (Détectés Automatiquement)

La couche PV **DOIT contenir LES DEUX mots-clés** :
- ✅ `pv` (en minuscule dans le nom)
- ✅ `conform` (en minuscule dans le nom)

**Exemples de noms détectés :**

| ✅ Nom | Détecté ? | Raison |
|--------|-----------|--------|
| `PV_CONFORMITE` | ✅ OUI | Contient "pv" et "conform" |
| `osmose.PV_CONFORMITE` | ✅ OUI | Contient "pv" et "conform" |
| `pv_conformite` | ✅ OUI | Contient "pv" et "conform" |
| `PV_CONF` | ✅ OUI | Contient "pv" et "conf" (début de "conform") |
| `conformite_pv` | ✅ OUI | Contient "conform" et "pv" (ordre n'importe pas) |
| `table_pv_conformite_v2` | ✅ OUI | Contient "pv" et "conform" |

### ❌ Noms Invalides (Non Détectés)

| ❌ Nom | Détecté ? | Raison |
|--------|-----------|--------|
| `PV` | ❌ NON | Manque "conform" |
| `CONFORMITE` | ❌ NON | Manque "pv" |
| `pv_points` | ❌ NON | Manque "conform" |
| `conformity` | ❌ NON | "conformity" ≠ "conform" (en anglais) |
| `point_visite` | ❌ NON | "pv" n'est pas un mot entier séparé |

---

## 🔍 Code de Détection

### Extrait de `main_dock.py` (ligne 431)

```python
def _populate_layers(self):
    """Remplit les combos de sélection de couches"""
    for combo in (self.canal_combo, self.ouvr_combo, self.fosse_combo,
                  self.indus_combo, self.liaison_combo, self.astreint_combo, self.pv_combo):
        combo.clear()
    
    for lyr in QgsProject.instance().mapLayers().values():
        if not isinstance(lyr, QgsVectorLayer):
            continue
        name = lyr.name().lower()
        
        if "canal" in name:
            self.canal_combo.addItem(lyr.name(), lyr)
        if "ouvr" in name or "ouvrage" in name:
            self.ouvr_combo.addItem(lyr.name(), lyr)
        if "cours" in name or "fosse" in name:
            self.fosse_combo.addItem(lyr.name(), lyr)
        if "indus" in name or "industriel" in name:
            self.indus_combo.addItem(lyr.name(), lyr)
        if "liaison" in name:
            self.liaison_combo.addItem(lyr.name(), lyr)
        if "astreint" in name or "astreinte" in name:
            self.astreint_combo.addItem(lyr.name(), lyr)
        
        # 🏠 DÉTECTION PV_CONFORMITE : DOIT CONTENIR "pv" ET "conform"
        if "pv" in name and "conform" in name:
            if self.pv_combo:
                self.pv_combo.addItem(lyr.name(), lyr)
```

**Logique :**
- `name = lyr.name().lower()` → Conversion en minuscules
- `if "pv" in name and "conform" in name:` → Les DEUX mots-clés doivent être présents

---

## 📝 Recommandations de Nommage

### ✅ Bonnes Pratiques

1. **Utiliser des mots-clés clairs et standards**
   - ✅ `PV_CONFORMITE` (nom standard)
   - ✅ `osmose.PV_CONFORMITE` (avec schéma)
   - ✅ `canalisations`, `ouvrages`, `industriels`

2. **Respecter la convention de nommage**
   - ✅ Utiliser des underscores `_` ou points `.` comme séparateurs
   - ✅ Éviter les espaces (ou les remplacer par `_`)

3. **Inclure le schéma si applicable**
   - ✅ `osmose.PV_CONFORMITE`
   - ✅ `osmose.canalisations`
   - ✅ `reseau.industriels`

4. **Ajouter des versions si nécessaire**
   - ✅ `PV_CONFORMITE_v2`
   - ✅ `canalisations_2024`
   - ✅ Les mots-clés sont toujours détectés

### ❌ Mauvaises Pratiques

1. **Noms trop vagues**
   - ❌ `layer1`, `table_points`, `data`
   - 🔧 Correction : Ajouter les mots-clés requis

2. **Mots-clés incomplets**
   - ❌ `PV` (manque "conform")
   - ❌ `CONFORMITE` (manque "pv")
   - 🔧 Correction : `PV_CONFORMITE`

3. **Mots-clés en langue étrangère**
   - ❌ `conformity` (anglais) au lieu de `conform`
   - 🔧 Correction : Utiliser `conform` (français)

4. **Espaces dans les noms**
   - ❌ `PV CONFORMITE` (avec espace)
   - 🔧 Correction : `PV_CONFORMITE` (avec underscore)

---

## 🛠️ Comment Vérifier la Détection ?

### Méthode 1 : Via l'Onglet PARAMÈTRES

1. Ouvrir le plugin CheminerIndus
2. Aller dans l'onglet **⚙️ PARAMÈTRES**
3. Vérifier les 7 combo boxes :
   - 🔵 Canalisations
   - 🔴 Ouvrages
   - 🌊 Cours d'eau / fossés
   - 🏭 Industriels
   - 🔗 Liaisons Indus
   - ⚠️ Astreinte-Exploit
   - 🏠 **PV Conformité** ← Vérifier ici
4. Si votre couche PV apparaît dans le combo "🏠 PV Conformité" → ✅ Détection OK

### Méthode 2 : Test de Nom

Tester si votre nom de couche contient les mots-clés :

```python
# Exemple de test Python
nom_couche = "osmose.PV_CONFORMITE"
nom_lower = nom_couche.lower()

# Test PV_CONFORMITE
if "pv" in nom_lower and "conform" in nom_lower:
    print("✅ Couche PV détectée !")
else:
    print("❌ Couche PV NON détectée")
```

---

## 🔧 Solutions si Couche Non Détectée

### Problème : Couche PV non visible dans PARAMÈTRES

#### Solution 1 : Renommer la Couche dans QGIS

1. Clic droit sur la couche dans le panneau Couches QGIS
2. **Propriétés** → Onglet **Source**
3. Modifier le **Nom de la couche** pour inclure "pv" et "conform"
4. Exemples valides : `PV_CONFORMITE`, `pv_conformite`, `PV_CONF`
5. Cliquer **OK**
6. **Recharger le plugin** (Plugin Reloader ou redémarrage QGIS)

#### Solution 2 : Renommer la Table dans PostgreSQL

Si la couche vient d'une base de données :

```sql
-- Renommer la table
ALTER TABLE votre_table RENAME TO PV_CONFORMITE;

-- Recharger la couche dans QGIS
```

#### Solution 3 : Créer un Alias/Vue

Si vous ne pouvez pas renommer la table :

```sql
-- Créer une vue avec le bon nom
CREATE VIEW osmose.PV_CONFORMITE AS 
SELECT * FROM osmose.votre_table_pv;

-- Charger la vue dans QGIS
```

#### Solution 4 : Sélection Manuelle (Fallback)

Si la détection automatique échoue, le plugin essaie de trouver la couche par nom :

```python
# Code dans pv_conformite_tab.py
pv_layer = self._find_layer_by_name("PV_CONFORMITE") or 
           self._find_layer_by_name("osmose.PV_CONFORMITE")
```

**Noms recherchés automatiquement :**
- `PV_CONFORMITE` (exact)
- `osmose.PV_CONFORMITE` (exact)

---

## 📚 Structure de la Table PV_CONFORMITE

### Champs Requis

La table PV_CONFORMITE doit contenir au minimum ces champs :

| Champ | Type | Description | Requis |
|-------|------|-------------|--------|
| `id` | `int4` | Identifiant unique | ✅ Oui |
| `geom` | `geometry(Point,4326)` | Géométrie point | ✅ Oui |
| `num_pv` | `varchar(254)` | Numéro du PV | ✅ Oui |
| `adresse` | `varchar(254)` | Adresse | ✅ Oui |
| `nom_com` | `varchar(254)` | Nom commune | ✅ Oui |
| `conforme` | `varchar(254)` | Statut conformité | ✅ Oui |
| `eu_vers_ep` | `varchar(254)` | Non-conformité EU→EP | ⚠️ Recommandé |
| `ep_vers_eu` | `varchar(254)` | Non-conformité EP→EU | ⚠️ Recommandé |
| `date_pv` | `date` | Date du PV | ⚠️ Optionnel |
| `lat` | `float8` | Latitude | ⚠️ Optionnel |
| `lon` | `float8` | Longitude | ⚠️ Optionnel |

**Note :** Les champs `eu_vers_ep` et `ep_vers_eu` sont utilisés pour détecter les non-conformités.

---

## 🎯 Exemples Complets

### Exemple 1 : Table PostgreSQL

```sql
-- Nom de table valide : osmose.PV_CONFORMITE
-- ✅ Contient "pv" et "conform"

CREATE TABLE osmose.PV_CONFORMITE (
    id SERIAL PRIMARY KEY,
    geom geometry(Point, 4326),
    num_pv VARCHAR(254),
    adresse VARCHAR(254),
    nom_com VARCHAR(254),
    conforme VARCHAR(254),
    eu_vers_ep VARCHAR(254),
    ep_vers_eu VARCHAR(254)
);

-- Charger dans QGIS → Détection automatique ✅
```

### Exemple 2 : Couche Shapefile

```
Nom du fichier : PV_CONFORMITE.shp
# ✅ Contient "pv" et "conform"

Champs :
- id (Integer)
- num_pv (String)
- adresse (String)
- conforme (String)
- eu_vers_ep (String)
- ep_vers_eu (String)
```

### Exemple 3 : Couche GeoPackage

```
Nom de la couche : pv_conformite
# ✅ Contient "pv" et "conform"

Fichier : reseau_assainissement.gpkg
Couche : pv_conformite
```

---

## ✅ Checklist de Vérification

Avant d'utiliser l'analyse PV, vérifiez :

- [ ] La table/couche contient **"pv"** dans son nom (minuscule)
- [ ] La table/couche contient **"conform"** dans son nom (minuscule)
- [ ] La couche est chargée dans QGIS
- [ ] La couche est de type **Vector** (points)
- [ ] La couche apparaît dans **⚙️ PARAMÈTRES** → "🏠 PV Conformité"
- [ ] Les champs requis sont présents (`id`, `geom`, `num_pv`, `adresse`, `nom_com`, `conforme`)
- [ ] La couche est sélectionnée dans le combo avant analyse

---

## 📞 Support

Si la détection ne fonctionne toujours pas :

1. ✅ Vérifier le nom de la couche (doit contenir "pv" ET "conform")
2. ✅ Recharger le plugin (Plugin Reloader)
3. ✅ Vérifier dans l'onglet PARAMÈTRES si la couche apparaît
4. ✅ Vider le cache Python si nécessaire
5. ✅ Redémarrer QGIS en dernier recours

---

## 🎊 Résumé Rapide

### Pour PV_CONFORMITE :

**✅ OBLIGATOIRE : Le nom de la couche DOIT contenir :**
- `pv` (mot-clé 1)
- `conform` (mot-clé 2)

**Exemples valides :**
- `PV_CONFORMITE` ✅
- `osmose.PV_CONFORMITE` ✅
- `pv_conformite` ✅
- `PV_CONF` ✅
- `conformite_pv` ✅

**Exemples invalides :**
- `PV` ❌ (manque "conform")
- `CONFORMITE` ❌ (manque "pv")
- `points_visite` ❌ ("pv" non séparé)

---

**CheminerIndus v1.3.0** - Détection automatique des couches 🎯
