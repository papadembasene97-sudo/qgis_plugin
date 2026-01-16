# 🔧 CORRECTIF - Erreurs SQL corrigées

## ❌ Problèmes identifiés

### 1. Colonne `pnm.commune` n'existe pas
**Erreur :**
```
ERREUR: la colonne pnm.commune n'existe pas
HINT: Peut-être que vous souhaitiez référencer la colonne « pnm.Commune »
```

**Cause :** La table `sda.POINT_NOIR_MODELISATION` a une colonne `Commune` (avec majuscule), pas `commune`.

### 2. Mauvais schéma pour PV_CONFORMITE
**Erreur :** Schéma `exploit.PV_CONFORMITE` utilisé au lieu de `osmose.PV_CONFORMITE`

**Cause :** Erreur de schéma dans le code.

---

## ✅ Corrections appliquées

### Fichier : `vue_ia_complete_v2.sql`

#### Correction 1 : Colonne `Commune` avec majuscule (3 occurrences)

**Avant :**
```sql
COUNT(CASE WHEN pnm.commune = o.commune AND pnm."Type" = 'Bouchage' THEN 1 END)
```

**Après :**
```sql
COUNT(CASE WHEN pnm."Commune" = o.commune AND pnm."Type" = 'Bouchage' THEN 1 END)
```

**Lignes modifiées :** 91-95, 220-224

#### Correction 2 : Schéma `osmose` au lieu de `exploit`

**Avant :**
```sql
LEFT JOIN exploit."PV_CONFORMITE" pv 
    ON pv.nom_com ILIKE '%' || o.commune || '%'
```

**Après :**
```sql
LEFT JOIN osmose."PV_CONFORMITE" pv 
    ON pv.nom_com ILIKE '%' || o.commune || '%'
```

**Ligne modifiée :** 261

---

### Fichier : `cheminer_indus/core/postgres_connector.py`

#### Correction : Schéma `osmose` dans la requête SQL

**Avant :**
```python
sql = f"""
    SELECT 
        *,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326) as geom
    FROM exploit."PV_CONFORMITE"
    WHERE lat IS NOT NULL AND lon IS NOT NULL
"""
```

**Après :**
```python
sql = f"""
    SELECT 
        *,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326) as geom
    FROM osmose."PV_CONFORMITE"
    WHERE lat IS NOT NULL AND lon IS NOT NULL
"""
```

**Ligne modifiée :** ~225 (dans la fonction `load_cheminer_indus_layers`)

---

## 📊 Vérifications à effectuer

### 1. Tester la création de la vue

```sql
-- Exécuter le script corrigé
\i vue_ia_complete_v2.sql
```

**Résultat attendu :**
```
CREATE MATERIALIZED VIEW
CREATE INDEX
CREATE INDEX
...
✅ Vue créée avec succès
```

### 2. Vérifier les statistiques

```sql
SELECT 
    COUNT(*) AS total_noeuds,
    AVG(nb_points_noirs_total_modelise)::NUMERIC(5,1) AS avg_pn_modelise,
    AVG(nb_pv_non_conforme)::NUMERIC(5,1) AS avg_pv_non_conforme,
    MAX(score_risque_calcule) AS score_max
FROM cheminer_indus.donnees_entrainement_ia;
```

**Résultat attendu :**
```
 total_noeuds | avg_pn_modelise | avg_pv_non_conforme | score_max 
--------------+-----------------+---------------------+-----------
          820 |             0.5 |                12.3 |       160
```

### 3. Tester le chargement dans QGIS

```python
# Console Python QGIS
from cheminer_indus.core.postgres_connector import PostgreSQLConnector

connector = PostgreSQLConnector()
connector.auto_detect_connection()
layers = connector.load_cheminer_indus_layers()

# Vérifier PV_CONFORMITE
if 'pv_conformite' in layers:
    print(f"✅ PV Conformité chargé : {layers['pv_conformite'].featureCount()} PV")
else:
    print("❌ PV Conformité non chargé")
```

---

## 📁 Fichiers modifiés

| Fichier | Modifications |
|---------|--------------|
| **vue_ia_complete_v2.sql** | 3 corrections (`pnm.Commune`, `osmose.PV_CONFORMITE`) |
| **cheminer_indus/core/postgres_connector.py** | 1 correction (`osmose.PV_CONFORMITE`) |

---

## 🚀 Commandes pour tester

### Test SQL direct

```bash
# Naviguer vers le répertoire
cd /home/user/webapp

# Exécuter le script SQL corrigé
psql -U postgres -d votre_base_de_donnees -f vue_ia_complete_v2.sql
```

### Test dans QGIS

```python
# Charger le script de test
exec(open('/home/user/webapp/test_pv_analyzer.py').read())

# Tester
stats_pv_conformite()
test_pv_analyzer()
```

---

## ✅ Checklist de validation

- [ ] Script SQL exécuté sans erreur
- [ ] Vue `cheminer_indus.donnees_entrainement_ia` créée
- [ ] Nombre de nœuds > 0 (attendu : ~820)
- [ ] Features PV non nulles (avg_pv_non_conforme > 0)
- [ ] Couche PV_CONFORMITE chargée dans QGIS (10 694 PV)
- [ ] Module PVAnalyzer fonctionne

---

## 🐛 Si d'autres erreurs apparaissent

### Erreur : "la table osmose.PV_CONFORMITE n'existe pas"

**Solution :** Vérifier que la table existe dans le schéma `osmose` :

```sql
SELECT schemaname, tablename 
FROM pg_tables 
WHERE tablename ILIKE '%pv_conformite%';
```

Si elle n'existe pas dans `osmose`, chercher dans quel schéma elle se trouve :

```sql
SELECT schemaname, tablename 
FROM pg_tables 
WHERE tablename ILIKE '%conformite%';
```

Puis ajuster le script SQL et le connecteur avec le bon schéma.

### Erreur : "la colonne Commune n'existe pas"

**Solution :** Vérifier les noms de colonnes exacts :

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'sda' 
AND table_name = 'POINT_NOIR_MODELISATION';
```

---

## 📞 Support

**Email :** papademba.sene97@gmail.com  
**GitHub :** https://github.com/papadembasene97-sudo/qgis_plugin  

**Fichiers corrigés :**
- `vue_ia_complete_v2.sql`
- `cheminer_indus/core/postgres_connector.py`

---

**Date de correction :** 2026-01-16  
**Version :** v1.2.3  
**Statut :** ✅ Corrections appliquées et prêtes à tester
