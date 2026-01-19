# 🔧 PLAN DE MODIFICATIONS - CheminerIndus v1.2.3

## PROBLÈMES IDENTIFIÉS

1. ✅ **Couche canalisations non détectée dans l'IA** → RÉSOLU
2. 🔄 **Interface pas flexible en hauteur** → À FAIRE
3. 🔄 **PV non affichés dans le cheminement industriels** → EN COURS
4. 🔄 **PV sans les mêmes fonctions que les industriels** → À FAIRE

---

## MODIFICATIONS NÉCESSAIRES

### 1. Ajouter les PV dans IndustrialDock

#### A. Modifier la signature de `_open_or_update_industrial_dock()` (main_dock.py)

```python
def _open_or_update_industrial_dock(
    self, 
    data: Optional[Dict[str,Dict[str,str]]] = None,
    pv_data: Optional[List[Dict[str,Any]]] = None  # NOUVEAU
):
    # ...
    self.industrial_dock.set_data(data, pv_data)  # Passer les PV
```

#### B. Modifier `IndustrialDock` pour gérer les PV (industrial_dock.py)

**Changements** :
- Ajouter un **onglet PV** (QTabWidget avec 2 onglets : Industriels + PV)
- Table PV avec colonnes : N° PV, Adresse, Commune, EU→EP, EP→EU, Canal, Distance
- Boutons : Zoom, Désigner, Exclure
- Filtres sur toutes les colonnes
- Exclusion lors des visites de nœuds

**Structure visuelle** :
```
┌─────────────────────────────────────────────┐
│  Industriels connectés + PV non conformes  │
├─────────────────────────────────────────────┤
│  [Industriels] [PV non conformes]  ← Onglets│
├─────────────────────────────────────────────┤
│  Recherche : [_____________] [Filtrer]      │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐   │
│  │ Table (industriels OU PV)           │   │
│  │ ...                                  │   │
│  │ ...                                  │   │
│  └─────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│  [Zoom] [Désigner] [Rafraîchir] [CSV]      │
└─────────────────────────────────────────────┘
```

### 2. Interface flexible en hauteur

#### A. Utiliser QScrollArea pour l'interface principale

**Dans main_dock.py, méthode `_show()`** :

```python
def _show(self):
    # ...
    
    # Créer un widget scrollable
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    # Widget principal
    main = QWidget()
    lay  = QVBoxLayout(main)
    
    # ... (contenu actuel)
    
    # Mettre le widget dans le scroll area
    scroll.setWidget(main)
    
    # Définir le scroll area comme widget du dock
    self.dock.setWidget(scroll)
```

#### B. Réduire les hauteurs fixes des GroupBox

**Remplacer** :
```python
group.setMinimumHeight(300)  # Hauteur fixe ❌
```

**Par** :
```python
group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # Flexible ✅
```

### 3. Fonctions PV identiques aux industriels

#### A. Dans IndustrialDock, ajouter les méthodes PV

```python
class IndustrialDock(QDockWidget):
    def __init__(self, parent=None):
        # ...
        self.pv_data = {}  # Données PV {pv_id: {...}}
        self.pv_excluded_ids = set()  # PV exclus
        
        # Callbacks PV
        self._on_zoom_pv_callback = None
        self._on_designate_pv_callback = None
        self._on_exclude_pv_callback = None
    
    def on_zoom_pv_request(self, callback: Callable[[int], None]):
        """Définit le callback pour zoomer sur un PV"""
        self._on_zoom_pv_callback = callback
    
    def on_designate_pv_request(self, callback: Callable[[int], None]):
        """Définit le callback pour désigner un PV comme pollueur"""
        self._on_designate_pv_callback = callback
    
    def on_exclude_pv_request(self, callback: Callable[[int], None]):
        """Définit le callback pour exclure un PV"""
        self._on_exclude_pv_callback = callback
    
    def exclude_pv_ids(self, pv_ids: List[int]):
        """Exclut certains PV de l'affichage"""
        self.pv_excluded_ids.update(pv_ids)
        self._refresh_pv_table()
```

#### B. Dans main_dock.py, ajouter les handlers PV

```python
def _zoom_to_pv(self, pv_id: int):
    """Zoom sur un PV"""
    pv_layer = self._find_pv_layer()
    if not pv_layer:
        return
    
    pv = pv_layer.getFeature(pv_id)
    if pv:
        geom = pv.geometry()
        if geom:
            bbox = geom.boundingBox().buffered(50)
            self.canvas.setExtent(bbox)
            self.canvas.refresh()

def _designate_pv(self, pv_id: int):
    """Désigne un PV comme pollueur"""
    # Créer PVAnalyzer si nécessaire
    # ...
    polluter_info = pv_analyzer.designate_as_polluter(pv_id)
    
    # Lancer le cheminement depuis ce PV
    # ...
    
def _exclude_pv_from_node_visit(self, node_id: str):
    """Exclut les PV d'une branche lors d'une visite de nœud"""
    # Trouver les PV sur les canalisations de cette branche
    # ...
    self.industrial_dock.exclude_pv_ids(pv_ids_to_exclude)
```

### 4. Exclusion des PV lors des visites de nœuds

**Logique** :
1. Utilisateur visite un nœud
2. Identifier les canalisations en aval de ce nœud
3. Trouver les PV rattachés à ces canalisations
4. Les exclure de la liste PV dans IndustrialDock

```python
def _mark_node_visited(self, node_id: str, polluted: bool):
    # ... (code existant pour les industriels)
    
    # NOUVEAU : Exclure aussi les PV de la branche
    if self.industrial_dock and hasattr(self, 'pv_analyzer'):
        # Trouver les canalisations en aval du nœud
        downstream_canals = self._find_downstream_canals(node_id)
        
        # Trouver les PV sur ces canalisations
        pv_to_exclude = []
        for canal_id in downstream_canals:
            for pv in self.pv_analyzer.pv_list:
                if pv.get('canal_id') == canal_id:
                    pv_to_exclude.append(pv['id'])
        
        # Exclure les PV
        self.industrial_dock.exclude_pv_ids(pv_to_exclude)
```

---

## RÉSUMÉ DES FICHIERS À MODIFIER

| Fichier | Modifications | Complexité |
|---------|---------------|------------|
| **main_dock.py** | • `_trace_for_industrials()` ✅<br>• `_open_or_update_industrial_dock()` signature<br>• Ajouter `_zoom_to_pv()`<br>• Ajouter `_designate_pv()`<br>• Ajouter `_exclude_pv_from_node_visit()`<br>• Modifier `_show()` pour QScrollArea | 🟡 Moyenne |
| **industrial_dock.py** | • Ajouter QTabWidget (2 onglets)<br>• Table PV avec filtres<br>• Boutons PV (Zoom, Désigner, Exclure)<br>• Méthodes `set_data(data, pv_data)`<br>• Méthodes `exclude_pv_ids()` | 🔴 Haute |

---

## ESTIMATION

- **Temps nécessaire** : 4-5 heures
- **Complexité globale** : 🟡 Moyenne
- **Tests nécessaires** : Oui (dans QGIS)

---

## PROCHAINES ÉTAPES

Veux-tu que je :
1. ✅ Continue les modifications (industrial_dock.py + main_dock.py)
2. ⏸️ Créer d'abord un prototype simple à tester
3. 📝 Générer la documentation des modifications

**Choix recommandé** : Option 1 (continuer les modifications)

