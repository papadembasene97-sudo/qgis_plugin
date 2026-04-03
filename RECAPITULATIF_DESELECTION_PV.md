# ✅ RÉCAPITULATIF : Désélection de branches et exclusion des industriels/PV

**Date** : 2026-01-19  
**Version** : TRACK-EAU-POLL v1.2.3  
**Objectif** : Préserver et optimiser la fonctionnalité existante

---

## 🎯 COMPRÉHENSION VALIDÉE

### ✅ Fonctionnalité existante CONFIRMÉE

**Principe de base** : Lors de la visite d'un nœud pendant un cheminement, l'utilisateur peut **désélectionner les branches non polluées** pour affiner progressivement la recherche de la source de pollution.

**Workflow complet** :

```
1. CHEMINEMENT INITIAL
   ├─ Ouvrage pollué N_START
   ├─ Remontée AMONT → 50 canalisations
   ├─ Détection : 8 industriels + 23 PV
   └─ Affichage dans IndustrialDock

2. VISITE DU NŒUD N_12345
   ├─ Question : "Pollution détectée ?"
   │  ├─ OUI → Désélection partielle
   │  └─ NON → Désélection totale amont
   │
   ├─ Identification 3 branches AMONT :
   │  ├─ Branche A (Canal C_001, amont N_11111)
   │  ├─ Branche B (Canal C_002, amont N_22222)
   │  └─ Branche C (Liaison L_456, indus IND_789)
   │
   ├─ Si POLLUTION = OUI :
   │  ├─ Dialogue : "Cochez les branches à CONSERVER"
   │  │  ☑ Branche A (polluée)
   │  │  ☐ Branche B (non polluée)
   │  │  ☐ Branche C (non polluée)
   │  │
   │  ├─ DÉSÉLECTION :
   │  │  ├─ Branche B + TOUT son amont récursif
   │  │  ├─ Branche C + industriel IND_789
   │  │  └─ TOUT l'aval de N_12345 (origine)
   │  │
   │  └─ EXCLUSION :
   │     ├─ Industriels des branches B et C
   │     ├─ Industriels en aval de N_12345
   │     └─ ❌ PV NON EXCLUS (BUG)
   │
   └─ Si POLLUTION = NON :
      ├─ Désélection AUTOMATIQUE de TOUT l'amont
      └─ Exclusion de TOUS les industriels amont

3. RÉSULTAT FINAL
   ├─ Sélection réduite (uniquement branche A + son amont)
   ├─ Tableau industriels affiné
   └─ ❌ Tableau PV PAS affiné (BUG)
```

---

## 🐛 BUG IDENTIFIÉ

### Problème actuel

**✅ Fonctionnels** :
- Désélection de branches ✅
- Exclusion des industriels des branches non polluées ✅
- Rafraîchissement du tableau IndustrialDock ✅

**❌ Manquant** :
- Exclusion des PV des branches non polluées ❌
- Rafraîchissement du tableau PV ❌

**Code actuel** (`main_dock.py`, ligne 969+) :
```python
# 6) Exclure dans le tableau des indus
removed_indus_all = set()
removed_indus_all.update(removed_indus_up or set())
removed_indus_all.update(removed_indus_down or set())

if self.industrial_dock and removed_indus_all:
    try:
        self.industrial_dock.exclude_ids(sorted(removed_indus_all))
        # ↑ SEULEMENT LES INDUSTRIELS
        # MANQUE : exclude_pv_ids(removed_pv_all)
    except Exception:
        pass
```

---

## ✅ SOLUTION PROPOSÉE

### Phase 1 : Correction du bug (PRIORITÉ HAUTE - 2-3h)

#### 1.1. Ajouter `exclude_pv_ids()` dans IndustrialDock

**Fichier** : `cheminer_indus/gui/industrial_dock.py`

```python
def exclude_pv_ids(self, pv_ids: List[str]):
    """
    Exclut du tableau PV les PV dont l'ID figure dans pv_ids.
    Identique à exclude_ids() mais pour les PV.
    
    Args:
        pv_ids: Liste de chaînes (id PV)
    """
    if not pv_ids or not hasattr(self, '_raw_pv_data'):
        return
    
    spv = set(str(i) for i in pv_ids)
    
    self._raw_pv_data = {
        k: v for k, v in self._raw_pv_data.items()
        if str(k) not in spv
    }
    
    self._visible_pv_data = {
        k: v for k, v in self._visible_pv_data.items()
        if str(k) not in spv
    }
    
    self._refresh_pv_table()
```

---

#### 1.2. Créer `_get_pv_from_nodes()` dans MainDock

**Fichier** : `cheminer_indus/gui/main_dock.py`

```python
def _get_pv_from_nodes(self, nodes: Set[str]) -> Set[str]:
    """
    Retourne les IDs des PV connectés aux nœuds donnés.
    Utilisé pour exclure les PV lors de la désélection de branches.
    
    Args:
        nodes: Set de nœuds (ex: {"N_12345", "N_67890"})
    
    Returns:
        Set[str]: IDs des PV connectés à ces nœuds
    """
    pv_ids = set()
    
    # Vérifier si le PVAnalyzer est disponible
    if not hasattr(self, 'pv_analyzer') or not self.pv_analyzer:
        return pv_ids
    
    # Récupérer les canalisations de ces nœuds
    canal_ids = set()
    if self.canal_layer and self.canal_layer.isValid():
        for node in nodes:
            expr = QgsExpression(
                "trim(\"idnini\") = '{}' OR trim(\"idnterm\") = '{}'".format(
                    node.replace("'", "''"),
                    node.replace("'", "''")
                )
            )
            req = QgsFeatureRequest(expr)
            for feat in self.canal_layer.getFeatures(req):
                canal_ids.add(feat.id())
    
    # Trouver les PV proches de ces canalisations
    if canal_ids:
        try:
            pv_list = self.pv_analyzer.find_pv_in_path(list(canal_ids), distance=15.0)
            pv_ids = {str(pv.get('id', pv.get('num_pv', ''))) for pv in pv_list if pv}
        except Exception as e:
            print(f"Erreur lors de la récupération des PV : {e}")
    
    return pv_ids
```

---

#### 1.3. Modifier `_on_node_visit()` pour exclure les PV

**Fichier** : `cheminer_indus/gui/main_dock.py` (ligne 969+)

**REMPLACEMENT** :

```python
# 6) Exclure dans le tableau des indus + PV
removed_indus_all = set()
removed_indus_all.update(removed_indus_up or set())
removed_indus_all.update(removed_indus_down or set())

# ✅ NOUVEAU : Calculer les PV à exclure
removed_pv_all = set()
if nodes_removed:  # Nœuds des branches désélectionnées
    removed_pv_all.update(self._get_pv_from_nodes(nodes_removed))
# Ajouter aussi les PV en aval si pollution = OUI
if polluted and nodes_ds:
    removed_pv_all.update(self._get_pv_from_nodes(nodes_ds))

if self.industrial_dock:
    try:
        # Exclure industriels (existant)
        if removed_indus_all:
            self.industrial_dock.exclude_ids(sorted(removed_indus_all))
        
        # ✅ NOUVEAU : Exclure PV
        if removed_pv_all:
            self.industrial_dock.exclude_pv_ids(sorted(removed_pv_all))
    except Exception as e:
        print(f"Erreur lors de l'exclusion : {e}")
```

---

### Phase 2 : Optimisations (PRIORITÉ MOYENNE - 2-3h)

#### 2.1. Cache PV par canalisation

**Fichier** : `cheminer_indus/core/pv_analyzer.py`

**Ajouter au `__init__`** :
```python
self._pv_canal_cache = {}  # {canal_id: [pv_list]}
self._cache_enabled = True
```

**Modifier `find_pv_in_path()`** :
```python
def find_pv_in_path(self, canal_ids, distance=15.0, use_cache=True):
    """
    Trouve les PV non conformes proches des canalisations.
    Utilise un cache pour améliorer les performances.
    """
    if not use_cache:
        return self._search_pvs(canal_ids, distance)
    
    # Vérifier le cache
    cached_pvs = []
    uncached_ids = []
    
    for cid in canal_ids:
        if cid in self._pv_canal_cache:
            cached_pvs.extend(self._pv_canal_cache[cid])
        else:
            uncached_ids.append(cid)
    
    # Chercher seulement les non-cachés
    if uncached_ids:
        new_pvs = self._search_pvs(uncached_ids, distance)
        
        # Mettre à jour le cache
        for pv in new_pvs:
            cid = pv.get('canal_id')
            if cid:
                if cid not in self._pv_canal_cache:
                    self._pv_canal_cache[cid] = []
                self._pv_canal_cache[cid].append(pv)
        
        cached_pvs.extend(new_pvs)
    
    return cached_pvs

def clear_cache(self):
    """Vide le cache PV"""
    self._pv_canal_cache.clear()
```

---

#### 2.2. Désélection récursive groupée

**Fichier** : `cheminer_indus/gui/main_dock.py`

**Optimiser `bulk_deselect_unselected_branches_optimized()`** :

```python
def bulk_deselect_unselected_branches_optimized(
    self, 
    start_node: str,
    branches: List[Tuple[str, int, Optional[str], Optional[str]]],
    chosen_ids: Set[int]
):
    """
    Désélectionne tout l'amont pour les branches NON cochées.
    VERSION OPTIMISÉE : Un seul parcours récursif pour tous les nœuds amont.
    """
    removed_indus = set()
    
    # 1. Séparer les branches selon leur type
    canal_branches_to_remove = []
    fosse_branches_to_remove = []
    liaison_branches_to_remove = []
    amont_nodes_to_explore = set()
    
    for typ, fid, amont, indus in branches:
        if fid in chosen_ids:
            continue  # Branche conservée
        
        if typ == "liaison":
            liaison_branches_to_remove.append((fid, indus))
        elif typ == "canal":
            canal_branches_to_remove.append(fid)
            if amont:
                amont_nodes_to_explore.add(amont)
        elif typ == "fosse":
            fosse_branches_to_remove.append(fid)
            if amont:
                amont_nodes_to_explore.add(amont)
    
    # 2. Désélectionner les liaisons et exclure industriels
    if liaison_branches_to_remove:
        liaison_fids = [fid for fid, _ in liaison_branches_to_remove]
        indus_ids = [indus for _, indus in liaison_branches_to_remove if indus]
        
        if self.liaison_layer:
            self.liaison_layer.deselect(liaison_fids)
        removed_indus.update(str(i) for i in indus_ids if i)
    
    # 3. UN SEUL parcours récursif pour TOUS les nœuds amont
    if amont_nodes_to_explore:
        sel_c, sel_f = self._selected_id_sets()
        all_cids_up = set()
        all_fids_up = set()
        all_nodes_up = set()
        
        for amont in amont_nodes_to_explore:
            cids_up, fids_up, nodes_up = self._node_ops.walk_upstream_on_selected_optimized(
                amont, sel_c, sel_f
            )
            all_cids_up.update(cids_up)
            all_fids_up.update(fids_up)
            all_nodes_up.update(nodes_up)
        
        # Ajouter les branches directes à désélectionner
        all_cids_up.update(canal_branches_to_remove)
        all_fids_up.update(fosse_branches_to_remove)
        
        # Désélection groupée
        if self.canal_layer and all_cids_up:
            self.canal_layer.deselect(list(all_cids_up))
        if self.fosse_layer and all_fids_up:
            self.fosse_layer.deselect(list(all_fids_up))
        
        # Exclusion groupée des industriels
        removed_indus.update(
            self._node_ops.deselect_liaisons_and_indus_from_nodes_optimized(all_nodes_up)
        )
    
    return removed_indus
```

**Gain estimé** : **-60% de temps** sur les désélections multiples

---

### Phase 3 : Interface améliorée (PRIORITÉ BASSE - 3-4h)

#### 3.1. Onglets séparés dans IndustrialDock

**Fichier** : `cheminer_indus/gui/industrial_dock.py`

**Architecture proposée** :

```
IndustrialDock
├─ QTabWidget
│  ├─ Onglet "🏭 Industriels" (8)
│  │  ├─ Filtres multi-colonnes
│  │  ├─ Table industriels
│  │  └─ Boutons : Zoom | Désigner | Rafraîchir | Export CSV
│  │
│  └─ Onglet "🏠 PV non conformes" (23)
│     ├─ Filtres multi-colonnes
│     ├─ Table PV
│     └─ Boutons : Zoom | Désigner | Rafraîchir | Export CSV | Lien OSMOSE
│
└─ Indicateurs : "Industriels : 8 | PV : 23"
```

**Avantages** :
- Séparation claire industriels vs PV
- Chaque onglet a ses propres filtres
- Compteur visible en permanence
- Fonctions identiques (Zoom, Désigner, Exclure)

---

## 📊 TESTS DE VALIDATION

### Test 1 : Régression industriels (PRIORITÉ HAUTE)
```
✅ Scénario : Visite nœud avec 3 branches, 1 cochée
✅ Vérifier : Industriels branches non cochées EXCLUS
✅ Résultat attendu : Tableau affiché = industriels branche polluée uniquement
```

### Test 2 : Nouveau - Exclusion PV (PRIORITÉ HAUTE)
```
✅ Scénario : Visite nœud avec 3 branches, 1 cochée
✅ Vérifier : PV branches non cochées EXCLUS
✅ Résultat attendu : Tableau PV = PV branche polluée uniquement
```

### Test 3 : Performance (PRIORITÉ MOYENNE)
```
✅ Scénario : Cheminement 500 canalisations + 50 indus + 120 PV
✅ Vérifier : Temps désélection < 2 secondes
✅ Résultat attendu : Cache efficace, parcours optimisé
```

### Test 4 : Interface onglets (PRIORITÉ BASSE)
```
✅ Scénario : Affichage 8 industriels + 23 PV
✅ Vérifier : 2 onglets séparés, compteurs visibles
✅ Résultat attendu : Navigation fluide, filtres indépendants
```

---

## 🚀 PLAN D'EXÉCUTION

### Temps estimé total : 7-10 heures

| Phase | Tâches | Temps | Priorité |
|-------|--------|-------|----------|
| **Phase 1** | Correction bug PV | 2-3h | 🔴 HAUTE |
| → 1.1 | `exclude_pv_ids()` | 30min | 🔴 |
| → 1.2 | `_get_pv_from_nodes()` | 1h | 🔴 |
| → 1.3 | Modifier `_on_node_visit()` | 30min | 🔴 |
| → 1.4 | Tests unitaires | 1h | 🔴 |
| **Phase 2** | Optimisations | 2-3h | 🟡 MOYENNE |
| → 2.1 | Cache PV | 1h | 🟡 |
| → 2.2 | Désélection groupée | 1h | 🟡 |
| → 2.3 | Tests performance | 1h | 🟡 |
| **Phase 3** | Interface onglets | 3-4h | 🟢 BASSE |
| → 3.1 | QTabWidget | 1h | 🟢 |
| → 3.2 | Séparer tableaux | 1.5h | 🟢 |
| → 3.3 | Tests intégration | 1.5h | 🟢 |

---

## 📝 GARANTIES

### ✅ Rétrocompatibilité TOTALE

**Fonctionnalités v1.2.2 préservées à 100%** :
- ✅ Cheminement EU/EP inchangé
- ✅ Désélection de branches inchangée
- ✅ Exclusion industriels inchangée (améliorée)
- ✅ Rapports PDF inchangés
- ✅ IA inchangée

**Nouveautés v1.2.3 ADDITIVES** :
- ✅ Exclusion PV (NOUVELLE fonctionnalité)
- ✅ Cache PV (optimisation)
- ✅ Onglets séparés (amélioration UI optionnelle)

**Principe respecté** : Les anciennes fonctionnalités **ne changent PAS**, elles **évoluent et s'optimisent**.

---

## ❓ QUESTIONS / CONFIRMATIONS

1. **Voulez-vous que je commence l'implémentation de la Phase 1 (correction bug PV) ?**
2. **Les optimisations Phase 2 sont-elles souhaitées maintenant ou plus tard ?**
3. **L'interface onglets Phase 3 est-elle prioritaire ou peut attendre ?**

**Recommandation** : Commencer par **Phase 1** (correction critique) puis **Phase 2** (optimisation). Phase 3 peut être reportée.

---

**Prêt à démarrer** 🚀
